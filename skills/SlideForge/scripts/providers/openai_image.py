#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SlideForge 官方生图 provider：OpenAI Images API（零第三方依赖）

被 ``skills/SlideForge/scripts/imagegen-adapter.py`` 以子进程单次调用，也可独立使用。
adapter 的 CLI 契约固定如下，满足契约的任意 provider 都可即插即换：

    --mode file --prompt-file <文件>       或  --mode direct <prompt>
    --output-dir <目录> --name <basename> --n <1-10>
    --format png|jpeg|webp
    --quality auto|low|medium|high
    --moderation auto|low
    --background auto|transparent
    --advance-model                        advanced 档位
    --size WIDTHxHEIGHT   或   --aspect-ratio W:H --resolution 1K|2K|4K
    --reference-image <本地文件>（可重复；出现即走 /images/edits）
    --mask <本地文件>

输出：把 n 张图写进 ``--output-dir``，命名 ``<name>.<ext>``（n=1）或 ``<name>_i.<ext>``（n>1），
绝对路径逐行打到 stdout。任何失败都以非零退出并给出可操作原因，**不自动重试**（防重复计费）。

密钥与配置（进程环境变量优先，其次 .env 文件）：

    OPENAI_API_KEY                必填
    OPENAI_BASE_URL               可选，默认 https://api.openai.com/v1
    OPENAI_IMAGE_MODEL            可选，默认 gpt-image-2
    OPENAI_IMAGE_MODEL_ADVANCED   可选，--advance-model 档使用的模型；缺省同 OPENAI_IMAGE_MODEL
    OPENAI_INPUT_FIDELITY         可选，edits 专属 high|low

.env 查找顺序（只读第一个存在的文件，键不跨文件合并）：``./.env``（进程工作目录；经 adapter
调用时就是 deck 目录）→ 技能目录 ``.env`` → ``~/.slideforge/.env``。密钥只进本次请求的
Authorization 头，不写日志、不写文件、不打印。

尺寸口径（G7 门禁要求页级槽位 ≥2560×1440，故默认模型取 gpt-image-2）：

    gpt-image-2 系   任意尺寸，要求两边均为 16 的倍数、长短边比 ≤3:1、
                     总像素 ∈ [655360, 8294400]、最长边 ≤3840（2560×1440 合法）
    gpt-image-1 系   仅 1024x1024 / 1536x1024 / 1024x1536
    dall-e-3         仅 1024x1024 / 1792x1024 / 1024x1792
    dall-e-2         仅 256x256 / 512x512 / 1024x1024

模型给不出请求尺寸时**直接失败**并提示改用 gpt-image-2 或下调 ``--expected-size``；
不放大、不裁剪、不静默降级——交付一张非达标图冒充达标比失败更坏。
"""

import argparse
import base64
import json
import mimetypes
import os
import sys
import urllib.error
import urllib.request
import uuid
from pathlib import Path

DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-image-2"
HTTP_TIMEOUT_SEC = 1200.0

FORMAT_EXT = {"png": ".png", "jpeg": ".jpg", "webp": ".webp"}
GPT_IMAGE_2_MIN_PIXELS = 655_360
GPT_IMAGE_2_MAX_PIXELS = 8_294_400
GPT_IMAGE_2_MAX_EDGE = 3840
GPT_IMAGE_2_MAX_RATIO = 3.0
LEGACY_GPT_IMAGE_SIZES = {"1024x1024", "1536x1024", "1024x1536"}
DALL_E_3_SIZES = {"1024x1024", "1792x1024", "1024x1792"}
DALL_E_2_SIZES = {"256x256", "512x512", "1024x1024"}
# 比例模式的边长基准（长边）：1K / 2K / 4K
RESOLUTION_LONG_EDGE = {"1K": 1280, "2K": 2048, "4K": 3840}
ENV_FILE_CANDIDATES = ("./.env",)


class ProviderError(Exception):
    pass


# ─────────────────────────── 配置 ───────────────────────────

def parse_env_file(text):
    values = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export "):].strip()
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if key:
            values[key] = value
    return values


def load_env_file():
    """只读第一个存在的 .env；进程环境变量始终优先（不回填已有键）。"""
    skill_dir = Path(__file__).resolve().parents[2]
    candidates = [Path(p) for p in ENV_FILE_CANDIDATES]
    candidates.append(skill_dir / ".env")
    candidates.append(Path.home() / ".slideforge" / ".env")
    for path in candidates:
        try:
            if path.is_file():
                for key, value in parse_env_file(path.read_text(encoding="utf-8")).items():
                    os.environ.setdefault(key, value)
                return path
        except OSError as exc:
            raise ProviderError("读取 .env 失败：%s（%s）" % (path, exc)) from exc
    return None


def config():
    env_file = load_env_file()
    base_url = (os.environ.get("OPENAI_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
    model = (os.environ.get("OPENAI_IMAGE_MODEL") or DEFAULT_MODEL).strip()
    return {
        "api_key": os.environ.get("OPENAI_API_KEY", "").strip(),
        "base_url": base_url,
        "model": model,
        "model_advanced": (os.environ.get("OPENAI_IMAGE_MODEL_ADVANCED") or "").strip(),
        "input_fidelity": (os.environ.get("OPENAI_INPUT_FIDELITY") or "").strip().lower(),
        "env_file": str(env_file) if env_file else None,
    }


def require_api_key(cfg):
    if not cfg["api_key"]:
        raise ProviderError(
            "未配置 OPENAI_API_KEY。任选一种方式：\n"
            "  1. 导出环境变量 OPENAI_API_KEY=sk-...\n"
            "  2. 在 deck 目录 / 技能目录 / ~/.slideforge/.env 写 OPENAI_API_KEY=sk-...\n"
            "  3. 兼容端点另配 OPENAI_BASE_URL（默认 %s）" % DEFAULT_BASE_URL
        )


# ─────────────────────────── 尺寸 ───────────────────────────

def parse_size(value):
    try:
        width_s, height_s = value.lower().split("x", 1)
        width, height = int(width_s), int(height_s)
    except (AttributeError, ValueError) as exc:
        raise ProviderError("非法尺寸 %r，应为 WIDTHxHEIGHT（如 2560x1440）" % (value,)) from exc
    if width <= 0 or height <= 0:
        raise ProviderError("非法尺寸 %r：宽高必须为正整数" % (value,))
    return width, height


def is_gpt_image_2(model):
    return model.lower().startswith("gpt-image-2")


def is_gpt_image(model):
    name = model.lower()
    return name.startswith("gpt-image-") or name.startswith("chatgpt-image")


def validate_size(model, size):
    if is_gpt_image_2(model):
        width, height = parse_size(size)
        long_edge, short_edge = max(width, height), min(width, height)
        problems = []
        if long_edge > GPT_IMAGE_2_MAX_EDGE:
            problems.append("最长边 %dpx 超过 %dpx" % (long_edge, GPT_IMAGE_2_MAX_EDGE))
        if width % 16 or height % 16:
            problems.append("两边都必须是 16 的倍数")
        if long_edge / short_edge > GPT_IMAGE_2_MAX_RATIO:
            problems.append("长短边比不得超过 3:1")
        pixels = width * height
        if not (GPT_IMAGE_2_MIN_PIXELS <= pixels <= GPT_IMAGE_2_MAX_PIXELS):
            problems.append("总像素 %d 须落在 [%d, %d]"
                            % (pixels, GPT_IMAGE_2_MIN_PIXELS, GPT_IMAGE_2_MAX_PIXELS))
        if problems:
            raise ProviderError(
                "%s 不接受尺寸 %s：%s。请提高请求尺寸（本技能的页内插画槽位建议 ≥1024×768，"
                "页级烙入槽位 2560×1440），或改用固定档位模型（gpt-image-1 / dall-e-3）。"
                % (model, size, "；".join(problems))
            )
        return size
    if is_gpt_image(model):
        allowed = LEGACY_GPT_IMAGE_SIZES
    elif model.lower().startswith("dall-e-3"):
        allowed = DALL_E_3_SIZES
    elif model.lower().startswith("dall-e-2"):
        allowed = DALL_E_2_SIZES
    else:
        return size  # 未知的 OpenAI 兼容模型：交给端点自证
    if size not in allowed:
        raise ProviderError(
            "%s 只支持 %s，给不出 %s。改用 gpt-image-2（支持 2560x1440 等任意 16 倍数尺寸），"
            "或把 --expected-size 与 --size 一同下调到合法档位。"
            % (model, " / ".join(sorted(allowed)), size)
        )
    return size


def size_from_ratio(model, aspect_ratio, resolution):
    try:
        width_s, height_s = aspect_ratio.split(":", 1)
        ratio = int(width_s) / int(height_s)
    except (AttributeError, ValueError, ZeroDivisionError) as exc:
        raise ProviderError("非法比例 %r，应为 W:H（如 16:9）" % (aspect_ratio,)) from exc
    if resolution not in RESOLUTION_LONG_EDGE:
        raise ProviderError("非法分辨率 %r，应为 1K/2K/4K" % (resolution,))
    long_edge = RESOLUTION_LONG_EDGE[resolution]
    if ratio >= 1:
        width, height = long_edge, long_edge / ratio
    else:
        width, height = long_edge * ratio, long_edge
    width = int(round(width / 16)) * 16
    height = int(round(height / 16)) * 16
    return validate_size(model, "%dx%d" % (width, height))


def resolve_size(args, model):
    if args.size:
        return validate_size(model, args.size.lower())
    if not args.aspect_ratio or args.aspect_ratio == "auto":
        raise ProviderError(
            "缺少尺寸：请传 --size WIDTHxHEIGHT，或传具体比例 --aspect-ratio W:H --resolution 2K。"
            "（比例 auto 时无法推断目标尺寸，而 adapter 会按 --expected-size 严格验收）"
        )
    return size_from_ratio(model, args.aspect_ratio, args.resolution)


# ─────────────────────────── 请求 ───────────────────────────

def api_quality(model, quality):
    if quality == "auto":
        return None
    if model.lower().startswith("dall-e"):
        return "hd" if quality == "high" else "standard"
    return quality


def http_post_json(url, payload, api_key):
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=body, method="POST")
    request.add_header("Content-Type", "application/json")
    request.add_header("Authorization", "Bearer " + api_key)
    return read_json_response(request)


def http_post_multipart(url, fields, files, api_key):
    boundary = "----SlideForge" + uuid.uuid4().hex
    chunks = []
    for name, value in fields.items():
        if value is None:
            continue
        chunks.append(("--%s\r\n" % boundary).encode("utf-8"))
        chunks.append(('Content-Disposition: form-data; name="%s"\r\n\r\n' % name).encode("utf-8"))
        chunks.append(str(value).encode("utf-8"))
        chunks.append(b"\r\n")
    for name, path in files:
        data = Path(path).read_bytes()
        content_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        chunks.append(("--%s\r\n" % boundary).encode("utf-8"))
        chunks.append(('Content-Disposition: form-data; name="%s"; filename="%s"\r\n'
                       % (name, Path(path).name)).encode("utf-8"))
        chunks.append(("Content-Type: %s\r\n\r\n" % content_type).encode("utf-8"))
        chunks.append(data)
        chunks.append(b"\r\n")
    chunks.append(("--%s--\r\n" % boundary).encode("utf-8"))
    request = urllib.request.Request(url, data=b"".join(chunks), method="POST")
    request.add_header("Content-Type", "multipart/form-data; boundary=" + boundary)
    request.add_header("Authorization", "Bearer " + api_key)
    return read_json_response(request)


def read_json_response(request):
    try:
        with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT_SEC) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            payload = json.loads(exc.read().decode("utf-8"))
            error = payload.get("error") if isinstance(payload, dict) else None
            if isinstance(error, dict):
                detail = ": " + str(error.get("message") or error.get("code") or error)
            elif error:
                detail = ": " + str(error)
        except Exception:
            pass
        raise ProviderError("OpenAI 接口返回 HTTP %s%s" % (exc.code, detail)) from exc
    except urllib.error.URLError as exc:
        raise ProviderError("连接 %s 失败：%s" % (request.full_url, exc.reason)) from exc


def build_edit_files(args, cfg):
    files = []
    multi = is_gpt_image_2(cfg["model"]) or is_gpt_image(cfg["model"])
    for index, path in enumerate(args.reference_image or []):
        if not Path(path).is_file():
            raise ProviderError("参考图不存在：%s" % path)
        files.append(("image[]" if multi else "image", path))
    if args.mask:
        if not files:
            raise ProviderError("--mask 必须与至少一张 --reference-image 同时使用")
        if not Path(args.mask).is_file():
            raise ProviderError("遮罩图不存在：%s" % args.mask)
        files.append(("mask", args.mask))
    return files


def request_images(args, cfg, prompt, size):
    quality = api_quality(cfg["model"], args.quality)
    common = {"model": cfg["model"], "prompt": prompt, "size": size, "n": args.n}
    if is_gpt_image(cfg["model"]):
        common["output_format"] = args.format
    if quality:
        common["quality"] = quality
    if is_gpt_image(cfg["model"]):
        if args.moderation:
            common["moderation"] = args.moderation
        if args.background and args.background != "auto":
            if is_gpt_image_2(cfg["model"]) and args.background == "transparent":
                print("[openai_image] 警告：gpt-image-2 不支持 transparent 背景，已按 auto 处理",
                      file=sys.stderr)
            else:
                common["background"] = args.background
    else:
        common["response_format"] = "b64_json"

    files = build_edit_files(args, cfg)
    if not files:
        return http_post_json(cfg["base_url"] + "/images/generations", common, cfg["api_key"])
    fields = dict(common)
    if cfg["input_fidelity"] in ("high", "low"):
        fields["input_fidelity"] = cfg["input_fidelity"]
    return http_post_multipart(cfg["base_url"] + "/images/edits", fields, files, cfg["api_key"])


def save_images(result, output_dir, name, fmt, count):
    data = result.get("data") if isinstance(result, dict) else None
    if not isinstance(data, list) or not data:
        raise ProviderError("接口未返回图片数据：%s" % json.dumps(result)[:400])
    if len(data) != count:
        raise ProviderError("请求 %d 张，接口返回 %d 张" % (count, len(data)))
    ext = FORMAT_EXT[fmt]
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for index, item in enumerate(data):
        if not isinstance(item, dict):
            raise ProviderError("返回项不是对象：%r" % (item,))
        encoded = item.get("b64_json")
        if encoded:
            content = base64.b64decode(encoded)
        elif item.get("url"):
            try:
                with urllib.request.urlopen(item["url"], timeout=HTTP_TIMEOUT_SEC) as response:
                    content = response.read()
            except urllib.error.URLError as exc:
                raise ProviderError("下载返回图失败：%s" % exc.reason) from exc
        else:
            raise ProviderError("返回项既无 b64_json 也无 url：%r" % (item,))
        filename = (name + ext) if count == 1 else ("%s_%d%s" % (name, index, ext))
        target = output_dir / filename
        target.write_bytes(content)
        written.append(str(target.resolve()))
    return written


# ─────────────────────────── 入口 ───────────────────────────

def build_parser():
    parser = argparse.ArgumentParser(description="SlideForge 官方生图 provider（OpenAI Images API）")
    parser.add_argument("prompt", nargs="?", default=None, help="direct 模式提示词")
    parser.add_argument("--prompt", dest="prompt_flag", default=None,
                        help="direct 模式提示词（等价于位置参数；adapter 走 --mode file）")
    parser.add_argument("--mode", choices=["direct", "file"], default="direct")
    parser.add_argument("--prompt-file", default="prompt.md", help="file 模式提示词文件路径")
    parser.add_argument("--output-dir", default="gpt_pic", help="输出目录")
    parser.add_argument("--name", default=None, help="输出 basename（不含扩展名）")
    parser.add_argument("--n", type=int, default=1, help="图片数量 1-10")
    parser.add_argument("--format", choices=sorted(FORMAT_EXT), default="png")
    parser.add_argument("--quality", choices=["auto", "low", "medium", "high"], default="medium")
    parser.add_argument("--moderation", choices=["auto", "low"], default="auto")
    parser.add_argument("--background", choices=["auto", "transparent"], default="auto")
    parser.add_argument("--advance-model", action="store_true", default=False,
                        help="advanced 档：使用 OPENAI_IMAGE_MODEL_ADVANCED（缺省同 OPENAI_IMAGE_MODEL）")
    parser.add_argument("--size", default=None, help="直接尺寸 WIDTHxHEIGHT")
    parser.add_argument("--aspect-ratio", default="auto", help="比例 W:H（如 16:9）")
    parser.add_argument("--resolution", choices=sorted(RESOLUTION_LONG_EDGE), default="2K")
    parser.add_argument("--reference-image", action="append", default=None,
                        help="参考图本地路径，可重复；出现即走 /images/edits")
    parser.add_argument("--mask", default=None, help="遮罩图本地路径（需与参考图同用）")
    parser.add_argument("--self-check", action="store_true", default=False,
                        help="只校验配置与尺寸口径，不联网、不计费")
    return parser


def run_self_check(args, cfg):
    print("[openai_image] 自检（不联网）")
    print("  env 文件      : %s" % (cfg["env_file"] or "未找到（仅用进程环境变量）"))
    print("  OPENAI_API_KEY: %s" % ("已配置" if cfg["api_key"] else "缺失"))
    print("  base_url      : %s" % cfg["base_url"])
    print("  model         : %s" % cfg["model"])
    print("  尺寸口径      : %s" % resolve_size(args, cfg["model"]))
    print("  调用路径      : %s" % ("/images/edits" if args.reference_image
                                   else "/images/generations"))
    if not cfg["api_key"]:
        print("[openai_image] 自检失败：未配置 OPENAI_API_KEY", file=sys.stderr)
        return 1
    print("[openai_image] 自检通过")
    return 0


def run(args):
    cfg = config()
    cfg["model"] = (cfg["model_advanced"] or cfg["model"]) if args.advance_model else cfg["model"]

    if args.self_check:
        return run_self_check(args, cfg)
    require_api_key(cfg)

    if not 1 <= args.n <= 10:
        raise ProviderError("--n 必须落在 1-10，收到 %d" % args.n)
    if args.name is None:
        raise ProviderError("缺少 --name（输出 basename）")
    if args.mode == "file":
        prompt = Path(args.prompt_file).read_text(encoding="utf-8") if Path(args.prompt_file).is_file() else ""
        if not prompt.strip():
            raise ProviderError("提示词文件为空或不存在：%s" % args.prompt_file)
    else:
        prompt = args.prompt_flag or args.prompt
        if not prompt:
            raise ProviderError("direct 模式需要提示词：位置参数 <prompt> 或 --prompt")
    if cfg["model"].lower().startswith("dall-e-3") and args.n != 1:
        raise ProviderError("dall-e-3 只支持 n=1；请用 gpt-image-2 出多候选")

    size = resolve_size(args, cfg["model"])
    result = request_images(args, cfg, prompt, size)
    written = save_images(result, args.output_dir, args.name, args.format, args.n)
    if not written:
        raise ProviderError("没有写出任何图片")
    for path in written:
        print(path)
    return 0


def main():
    args = build_parser().parse_args()
    try:
        return run(args)
    except ProviderError as exc:
        print("[openai_image] ERROR: %s" % exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
