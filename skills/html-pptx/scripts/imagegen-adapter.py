#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""受控调用外部图像 provider CLI，并校验后发布到 deck/assets。"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import sys
import tempfile
from datetime import datetime, timezone


SAFE_BASENAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")
FORMAT_EXT = {"png": ".png", "jpeg": ".jpg", "webp": ".webp"}
MODEL_NAMES = {
    "flare": "gpt-image-2.5-flare",
    "sunburst": "gpt-image-2.5-sunburst",
}


class AdapterError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_size(value, flag):
    match = re.fullmatch(r"([1-9][0-9]*)x([1-9][0-9]*)", value or "")
    if not match:
        raise AdapterError("invalid_size", "%s 必须为正整数 WIDTHxHEIGHT" % flag)
    return int(match.group(1)), int(match.group(2))


def parse_ratio(value):
    match = re.fullmatch(r"([1-9][0-9]*):([1-9][0-9]*)", value or "")
    if not match:
        raise AdapterError("invalid_ratio", "--aspect-ratio 必须为 W:H 或 auto")
    return int(match.group(1)) / int(match.group(2))


def png_dimensions(data):
    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        return None
    return struct.unpack(">II", data[16:24])


def jpeg_dimensions(data):
    if len(data) < 4 or data[:2] != b"\xff\xd8":
        return None
    offset = 2
    sof = {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
           0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}
    while offset < len(data):
        while offset < len(data) and data[offset] != 0xFF:
            offset += 1
        while offset < len(data) and data[offset] == 0xFF:
            offset += 1
        if offset >= len(data):
            break
        marker = data[offset]
        offset += 1
        if marker in (0x01, 0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
            continue
        if offset + 2 > len(data):
            break
        length = struct.unpack(">H", data[offset:offset + 2])[0]
        if length < 2 or offset + length > len(data):
            break
        if marker in sof:
            if length < 7:
                break
            height, width = struct.unpack(">HH", data[offset + 3:offset + 7])
            return width, height
        offset += length
    return None


def webp_dimensions(data):
    if len(data) < 30 or data[:4] != b"RIFF" or data[8:12] != b"WEBP":
        return None
    kind = data[12:16]
    if kind == b"VP8X" and len(data) >= 30:
        width = 1 + int.from_bytes(data[24:27], "little")
        height = 1 + int.from_bytes(data[27:30], "little")
        return width, height
    if kind == b"VP8L" and len(data) >= 25 and data[20] == 0x2F:
        b0, b1, b2, b3 = data[21:25]
        width = 1 + b0 + ((b1 & 0x3F) << 8)
        height = 1 + ((b1 >> 6) | (b2 << 2) | ((b3 & 0x0F) << 10))
        return width, height
    if kind == b"VP8 " and len(data) >= 30 and data[23:26] == b"\x9d\x01\x2a":
        width = struct.unpack("<H", data[26:28])[0] & 0x3FFF
        height = struct.unpack("<H", data[28:30])[0] & 0x3FFF
        return width, height
    return None


def inspect_image(path):
    data = path.read_bytes()
    for media_type, parser in (("png", png_dimensions), ("jpeg", jpeg_dimensions),
                               ("webp", webp_dimensions)):
        dimensions = parser(data)
        if dimensions:
            return media_type, dimensions[0], dimensions[1], sha256_bytes(data), len(data)
    raise AdapterError("invalid_magic", "%s 不是可识别的 PNG/JPEG/WebP" % path.name)


def safe_regular_file(path, label):
    try:
        if path.is_symlink() or not path.is_file():
            raise AdapterError("invalid_path", "%s 必须是普通文件" % label)
        return path.resolve(strict=True)
    except OSError as exc:
        raise AdapterError("invalid_path", "%s 不可访问：%s" % (label, exc)) from exc


def write_ledger(deck, entry):
    ledger = deck / "imagegen-ledger.json"
    records = []
    if ledger.exists():
        if ledger.is_symlink() or not ledger.is_file():
            raise AdapterError("invalid_ledger", "ledger 必须是 deck 根目录普通文件")
        try:
            records = json.loads(ledger.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise AdapterError("invalid_ledger", "现有 ledger 不是有效 JSON：%s" % exc) from exc
        if not isinstance(records, list):
            raise AdapterError("invalid_ledger", "现有 ledger 顶层必须是数组")
    records.append(entry)
    fd, tmp_name = tempfile.mkstemp(prefix=".imagegen-ledger-", suffix=".json", dir=str(deck))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(records, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, ledger)
    finally:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass


def load_prompt(args):
    if args.prompt is not None:
        prompt = args.prompt
    else:
        prompt_path = safe_regular_file(Path(args.prompt_file), "prompt 文件")
        try:
            prompt = prompt_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise AdapterError("invalid_prompt", "prompt 文件读取失败：%s" % exc) from exc
    if not prompt:
        raise AdapterError("invalid_prompt", "prompt 不能为空")
    return prompt


def load_rubric(value):
    """G3 生图评审 rubric：读取 JSON 并原样透传进 ledger 条目（顶层须为对象）。"""
    path = safe_regular_file(Path(value), "rubric JSON 文件")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        raise AdapterError("invalid_rubric", "rubric JSON 读取/解析失败：%s" % exc) from exc
    if not isinstance(data, dict):
        raise AdapterError("invalid_rubric", "rubric JSON 顶层必须是对象")
    return data


def prepare_context(args, prompt):
    deck_arg = Path(args.deck)
    if deck_arg.is_symlink() or not deck_arg.is_dir():
        raise AdapterError("invalid_deck", "deck 必须是现有普通目录")
    deck = deck_arg.resolve(strict=True)
    if not SAFE_BASENAME.fullmatch(args.name):
        raise AdapterError("invalid_basename", "--name 仅允许 1–128 位 ASCII 字母、数字、下划线或连字符，且须以字母或数字开头")
    provider = safe_regular_file(Path(args.provider_script), "provider script")
    expected_width, expected_height = parse_size(args.expected_size, "--expected-size")
    if args.ratio_tolerance < 0 or args.ratio_tolerance > 0.25:
        raise AdapterError("invalid_tolerance", "--ratio-tolerance 必须在 0–0.25 之间")
    expected_ratio = expected_width / expected_height
    if args.size:
        size_width, size_height = parse_size(args.size, "--size")
        if (size_width, size_height) != (expected_width, expected_height):
            raise AdapterError("size_mismatch", "--size 必须与 --expected-size 一致")
    elif args.aspect_ratio != "auto":
        requested_ratio = parse_ratio(args.aspect_ratio)
        ratio_error = abs(expected_ratio - requested_ratio) / requested_ratio
        if ratio_error > args.ratio_tolerance:
            raise AdapterError("ratio_mismatch", "--expected-size 与 --aspect-ratio 的比例不一致")
    if not 1 <= args.n <= 10:
        raise AdapterError("invalid_count", "--n 必须在 1–10 之间")

    assets = deck / "assets"
    if assets.exists() and (assets.is_symlink() or not assets.is_dir()):
        raise AdapterError("invalid_assets", "deck/assets 必须是普通目录且不能是符号链接")
    assets.mkdir(mode=0o755, exist_ok=True)
    if assets.resolve(strict=True).parent != deck:
        raise AdapterError("invalid_assets", "输出目录必须是 deck 的直接 assets 子目录")

    references = []
    reference_meta = []
    for value in args.reference_image:
        ref = safe_regular_file(Path(value), "reference-image")
        references.append(ref)
        reference_meta.append({"sha256": sha256_file(ref), "bytes": ref.stat().st_size})

    return {
        "deck": deck,
        "assets": assets,
        "provider": provider,
        "expected": (expected_width, expected_height),
        "references": references,
        "reference_meta": reference_meta,
        "prompt": prompt,
    }


def make_entry(args, context):
    prompt_bytes = context["prompt"].encode("utf-8")
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "failed",
        "error_code": "unknown",
        "provider": {
            "script": context["provider"].name,
            "sha256": sha256_file(context["provider"]),
        },
        "request": {
            "prompt_sha256": sha256_bytes(prompt_bytes),
            "prompt_length": len(context["prompt"]),
            "prompt_bytes": len(prompt_bytes),
            "name": args.name,
            "count": args.n,
            "model": MODEL_NAMES[args.model],
            "quality": args.quality,
            "format": args.format,
            "size": args.size,
            "aspect_ratio": None if args.size else args.aspect_ratio,
            "resolution": None if args.size else args.resolution,
            "expected_size": "%dx%d" % context["expected"],
            "reference_images": context["reference_meta"],
        },
        "billing": {"amount": "unknown", "currency": "unknown"},
        "outputs": [],
    }


def provider_command(args, context, prompt_file, output_dir):
    command = [
        sys.executable, str(context["provider"]),
        "--mode", "file", "--prompt-file", str(prompt_file),
        "--output-dir", str(output_dir),
        "--quality", args.quality,
        "--format", args.format,
        "--moderation", args.moderation,
        "--background", args.background,
        "--n", str(args.n),
        "--name", args.name,
    ]
    if args.model == "sunburst":
        command.append("--advance-model")
    if args.size:
        command += ["--size", args.size]
    else:
        command += ["--aspect-ratio", args.aspect_ratio, "--resolution", args.resolution]
    for ref in context["references"]:
        command += ["--reference-image", str(ref)]
    return command


def expected_filenames(args):
    ext = FORMAT_EXT[args.format]
    if args.n == 1:
        return [args.name + ext]
    return ["%s_%d%s" % (args.name, index, ext) for index in range(args.n)]


def run(args):
    prompt = load_prompt(args)
    context = prepare_context(args, prompt)
    entry = make_entry(args, context)
    if args.rubric_json:  # 先于 provider 调用加载：rubric 非法则不计费、不落账
        entry["rubric"] = load_rubric(args.rubric_json)
    deck = context["deck"]
    assets = context["assets"]
    try:
        with tempfile.TemporaryDirectory(prefix=".imagegen-stage-", dir=str(assets)) as stage_name:
            stage = Path(stage_name)
            output_dir = stage / "output"
            output_dir.mkdir()
            prompt_file = stage / "prompt.txt"
            prompt_file.write_text(prompt, encoding="utf-8")
            command = provider_command(args, context, prompt_file, output_dir)
            try:
                completed = subprocess.run(
                    command,
                    cwd=str(context["deck"]),
                    env=os.environ.copy(),
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=args.timeout,
                    shell=False,
                )
            except subprocess.TimeoutExpired as exc:
                raise AdapterError("provider_timeout", "provider 超时；未自动重试") from exc
            if completed.returncode != 0:
                raise AdapterError("provider_failed", "provider 退出码 %d；未自动重试" % completed.returncode)

            children = list(output_dir.iterdir())
            if any(child.is_symlink() or not child.is_file() for child in children):
                raise AdapterError("invalid_output_path", "provider 输出必须是 staging 目录中的普通文件")
            expected_names = expected_filenames(args)
            actual_names = sorted(child.name for child in children)
            if actual_names != sorted(expected_names):
                raise AdapterError(
                    "output_count_or_name_mismatch",
                    "provider 输出文件应为 %s，实际为 %s" % (expected_names, actual_names),
                )

            validated = []
            expected_width, expected_height = context["expected"]
            expected_ratio = expected_width / expected_height
            for name in expected_names:
                source = output_dir / name
                media_type, width, height, digest, byte_count = inspect_image(source)
                if media_type != args.format:
                    raise AdapterError("format_mismatch", "%s magic=%s，与请求格式 %s 不符" % (name, media_type, args.format))
                if (width, height) != (expected_width, expected_height):
                    raise AdapterError(
                        "dimension_mismatch",
                        "%s 固有尺寸 %dx%d，期望 %dx%d" % (name, width, height, expected_width, expected_height),
                    )
                ratio_error = abs(width / height - expected_ratio) / expected_ratio
                if ratio_error > args.ratio_tolerance:
                    raise AdapterError("ratio_mismatch", "%s 比例误差 %.6f 超过容差" % (name, ratio_error))
                validated.append((source, assets / name, {
                    "file": name,
                    "media_type": media_type,
                    "width": width,
                    "height": height,
                    "bytes": byte_count,
                    "sha256": digest,
                }))

            for source, target, _metadata in validated:
                os.replace(source, target)
            entry["outputs"] = [metadata for _source, _target, metadata in validated]
            entry["status"] = "success"
            entry["error_code"] = None
    except AdapterError as exc:
        entry["error_code"] = exc.code
        write_ledger(deck, entry)
        raise

    write_ledger(deck, entry)
    print(json.dumps({
        "status": "success",
        "outputs": entry["outputs"],
        "ledger": str(deck / "imagegen-ledger.json"),
    }, ensure_ascii=False))


def build_parser():
    parser = argparse.ArgumentParser(description="受控调用显式图像 provider，并校验发布到 deck/assets")
    parser.add_argument("deck", help="deck 根目录；产物仅发布到其 assets/ 目录")
    parser.add_argument("--provider-script", required=True, help="显式 provider Python script 路径")
    prompt_group = parser.add_mutually_exclusive_group(required=True)
    prompt_group.add_argument("--prompt", help="生图提示词")
    prompt_group.add_argument("--prompt-file", help="UTF-8 生图提示词文件")
    parser.add_argument("--name", required=True, help="输出 basename，不含扩展名或路径")
    parser.add_argument("--n", type=int, default=1, help="输出数量，1–10")
    parser.add_argument("--format", choices=sorted(FORMAT_EXT), default="png")
    parser.add_argument("--model", choices=sorted(MODEL_NAMES), default="flare")
    parser.add_argument("--quality", choices=["auto", "low", "medium", "high"], default="medium")
    parser.add_argument("--background", choices=["auto", "transparent"], default="auto")
    parser.add_argument("--moderation", choices=["auto", "low"], default="auto")
    parser.add_argument("--aspect-ratio", default="auto")
    parser.add_argument("--resolution", choices=["1K", "2K", "4K"], default="2K")
    parser.add_argument("--size", help="直接尺寸 WIDTHxHEIGHT；使用时不向 provider 传 ratio/resolution")
    parser.add_argument("--expected-size", required=True, help="验收固有尺寸 WIDTHxHEIGHT")
    parser.add_argument("--ratio-tolerance", type=float, default=0.05)
    parser.add_argument("--reference-image", action="append", default=[], help="本地参考图，可重复，最多 16 张")
    parser.add_argument("--rubric-json", help="可选：生图评审 rubric JSON 文件（bake-prompts.md §5 格式），原样透传进 ledger 条目")
    parser.add_argument("--timeout", type=float, default=1300.0, help="单次 provider 子进程超时秒数")
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    if len(args.reference_image) > 16:
        print("[imagegen-adapter] ERROR: reference-image 最多 16 张", file=sys.stderr)
        return 2
    if args.timeout <= 0:
        print("[imagegen-adapter] ERROR: --timeout 必须大于 0", file=sys.stderr)
        return 2
    try:
        run(args)
        return 0
    except AdapterError as exc:
        print("[imagegen-adapter] ERROR [%s]: %s" % (exc.code, exc), file=sys.stderr)
        return 1
    except Exception as exc:
        print("[imagegen-adapter] ERROR [internal_error]: %s" % exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
