#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""图像适配器验收：默认仅 loopback mock；--real 显式执行两次真实 Bridge v2 生图。"""

import argparse
import base64
import contextlib
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import time


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
from bridge_core import BridgeCore, revision_cli

ADAPTER = ROOT / "skills/html-pptx/scripts/imagegen-adapter.py"
DEFAULT_PROVIDER = Path("/home/lixiang/Desktop/ThinkSkillsHub/oai生图/script.py")
REPORT_DIR = ROOT / "tests/harness/results/bridge-p4"
MANUAL_DIR = REPORT_DIR / "manual-acceptance"
CULTURE_FIXTURE = ROOT / "tests/decks/culture-kraft"
BAKE_FIXTURE = ROOT / "tests/decks/bake-mix"
J_RENDER = ROOT / "skills/html-pptx/scripts/check-render.py"
CAPACITY = ROOT / "skills/html-pptx/scripts/check-capacity.py"
CHECK_IMAGES = ROOT / "skills/html-pptx/scripts/check-images.mjs"
EXTRACT = ROOT / "skills/html-pptx/scripts/extract-manifest.py"
COMPILE_BAKE = ROOT / "skills/html-pptx/scripts/compile-bake-prompts.py"
REAL_CALL_LIMIT = 2
FAILURES = []
RESULTS = []


def check(label, condition, detail=""):
    print("%s  %s%s" % ("PASS" if condition else "FAIL", label,
                        (" — " + detail) if detail and not condition else ""))
    RESULTS.append({"label": label, "passed": bool(condition), "detail": "" if condition else detail})
    if not condition:
        FAILURES.append(label)


def png_bytes(width, height):
    return (b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR" +
            struct.pack(">II", width, height) + b"\x08\x06\x00\x00\x00" + b"\x00\x00\x00\x00")


def png_size(path):
    data = path.read_bytes()
    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        return None
    return struct.unpack(">II", data[16:24])


def jpeg_bytes(width, height):
    sof_payload = b"\x08" + struct.pack(">HH", height, width) + b"\x01\x01\x11\x00"
    return b"\xff\xd8\xff\xc0" + struct.pack(">H", len(sof_payload) + 2) + sof_payload + b"\xff\xd9"


def webp_bytes(width, height):
    payload = b"\x00\x00\x00\x00" + (width - 1).to_bytes(3, "little") + (height - 1).to_bytes(3, "little")
    return b"RIFF" + struct.pack("<I", 4 + 8 + len(payload)) + b"WEBPVP8X" + struct.pack("<I", len(payload)) + payload


class FakeState:
    def __init__(self):
        self.lock = threading.Lock()
        self.requests = []

    def add(self, payload):
        with self.lock:
            self.requests.append(payload)

    def count(self):
        with self.lock:
            return len(self.requests)

    def last(self):
        with self.lock:
            return self.requests[-1]


class FakeImageStudioHandler(BaseHTTPRequestHandler):
    server_version = "FakeImageStudio/1"

    def log_message(self, _format, *_args):
        return

    def do_POST(self):
        if self.path != "/api/generate-image":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception:
            self.send_error(400)
            return
        self.server.state.add(payload)
        prompt = payload.get("prompt", "")

        if "case-disconnect" in prompt:
            self.close_connection = True
            try:
                self.connection.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            self.connection.close()
            return
        if "case-500" in prompt:
            self._json(500, {"detail": "synthetic failure"})
            return
        if "case-success-false" in prompt:
            self._json(200, {"success": False, "error": "synthetic rejection"})
            return

        count = int(payload.get("n", 1))
        if "case-fewer" in prompt:
            count = max(0, count - 1)
        if "case-wrong-magic" in prompt:
            image = b"definitely-not-an-image"
        elif "case-wrong-dim" in prompt:
            image = png_bytes(5, 2)
        elif "case-jpeg" in prompt:
            image = jpeg_bytes(4, 2)
        elif "case-webp" in prompt:
            image = webp_bytes(4, 2)
        elif "case-size" in prompt:
            image = png_bytes(6, 3)
        elif "case-reference" in prompt or "case-flare" in prompt:
            image = png_bytes(16, 9)
        else:
            image = png_bytes(4, 2)
        encoded = base64.b64encode(image).decode("ascii")
        self._json(200, {"success": True, "files": [{"image_base64": encoded} for _ in range(count)]})

    def _json(self, status, body):
        data = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


class FakeServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, handler, state):
        super().__init__(address, handler)
        self.state = state


def run_adapter(provider, fake_url, deck, prompt, name="hero", expected="4x2", extra=None):
    command = [
        sys.executable, str(ADAPTER), str(deck),
        "--provider-script", str(provider),
        "--prompt", prompt,
        "--name", name,
        "--expected-size", expected,
    ]
    if extra:
        command.extend(extra)
    env = os.environ.copy()
    env["IMAGE_STUDIO_URL"] = fake_url
    return subprocess.run(command, cwd=str(ROOT), env=env, capture_output=True, text=True, timeout=30)


def read_ledger(deck):
    return json.loads((deck / "imagegen-ledger.json").read_text(encoding="utf-8"))


def output_files(deck):
    assets = deck / "assets"
    if not assets.exists():
        return []
    return sorted(path.name for path in assets.iterdir() if path.is_file())


def mock_main(provider):
    check("P0 provider script 存在", provider.is_file(), str(provider))
    if not provider.is_file():
        return finish(None)

    state = FakeState()
    server = FakeServer(("127.0.0.1", 0), FakeImageStudioHandler, state)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    fake_url = "http://127.0.0.1:%d" % server.server_address[1]

    try:
        with tempfile.TemporaryDirectory(prefix="pptx-imagegen-check-") as tmp_name:
            tmp = Path(tmp_name)

            def deck_for(label):
                deck = tmp / label
                (deck / "assets").mkdir(parents=True)
                (deck / "index.html").write_text("<!doctype html><title>imagegen check</title>", encoding="utf-8")
                return deck

            # flare + quality high→max + ratio/resolution
            deck = deck_for("flare")
            before = state.count()
            secret = "case-flare SECRET_PROMPT_MUST_NOT_LEAK"
            result = run_adapter(provider, fake_url, deck, secret, expected="16x9",
                                 extra=["--aspect-ratio", "16:9", "--resolution", "2K", "--quality", "high"])
            request = state.last() if state.count() > before else {}
            check("①a flare 调用成功且只请求一次", result.returncode == 0 and state.count() == before + 1,
                  (result.stdout + result.stderr)[-400:])
            check("①b flare 路由与 high→max", request.get("model") == "gpt-image-2.5-flare" and request.get("quality") == "max", repr(request))
            check("①c ratio/resolution 透传", request.get("aspect_ratio") == "16:9" and request.get("resolution") == "2K" and "size" not in request, repr(request))
            check("①d assets 仅含生成图片", output_files(deck) == ["hero.png"] and not any(p.name.startswith(".imagegen-stage-") for p in (deck / "assets").iterdir()), repr(output_files(deck)))
            check("①e ledger 位于 deck 根且不进入 assets",
                  (deck / "imagegen-ledger.json").is_file() and not (deck / "assets/imagegen-ledger.json").exists())
            ledger = read_ledger(deck)
            serialized = json.dumps(ledger, ensure_ascii=False)
            expected_hash = hashlib.sha256(secret.encode("utf-8")).hexdigest()
            check("①f ledger 脱敏且含 prompt hash/长度", secret not in serialized and ledger[-1]["request"]["prompt_sha256"] == expected_hash and ledger[-1]["request"]["prompt_length"] == len(secret), serialized[:400])
            check("①g ledger 校验尺寸/SHA-256，账单 unknown", ledger[-1]["outputs"][0]["width"] == 16 and ledger[-1]["outputs"][0]["height"] == 9 and len(ledger[-1]["outputs"][0]["sha256"]) == 64 and ledger[-1]["billing"]["amount"] == "unknown", repr(ledger[-1]))
            check("①h ledger 不含 provider 绝对路径", str(provider.resolve()) not in serialized, serialized[:400])

            core = BridgeCore(tmp)
            try:
                manifest = core.scan_bundle(deck / "index.html")
                source_revision, _export_revision = core.revisions(manifest)
            finally:
                core.close()
            managed_paths = [item["path"] for item in manifest]
            check("①i Bridge scan_bundle 接受成功产物且忽略根 ledger",
                  managed_paths == ["assets/hero.png", "index.html"], repr(managed_paths))
            cli_revision = revision_cli(deck / "index.html")
            check("①j Bridge source revision/CLI 可计算且一致",
                  source_revision.startswith("sha256:") and len(source_revision) == 71 and cli_revision == source_revision,
                  "%s != %s" % (source_revision, cli_revision))

            # sunburst + direct size; provider payload must omit aspect_ratio/resolution.
            deck = deck_for("sunburst-size")
            before = state.count()
            result = run_adapter(provider, fake_url, deck, "case-size", expected="6x3",
                                 extra=["--model", "sunburst", "--size", "6x3"])
            request = state.last() if state.count() > before else {}
            check("②a sunburst 调用成功且只请求一次", result.returncode == 0 and state.count() == before + 1,
                  (result.stdout + result.stderr)[-400:])
            check("②b sunburst 路由", request.get("model") == "gpt-image-2.5-sunburst", repr(request))
            check("②c size 模式不带 ratio/resolution", request.get("size") == "6x3" and "aspect_ratio" not in request and "resolution" not in request, repr(request))

            # Local reference image must reach provider as base64, never as a path.
            reference = tmp / "local-reference.png"
            reference_bytes = png_bytes(2, 2)
            reference.write_bytes(reference_bytes)
            deck = deck_for("reference")
            before = state.count()
            result = run_adapter(provider, fake_url, deck, "case-reference", expected="16x9",
                                 extra=["--reference-image", str(reference), "--aspect-ratio", "16:9"])
            request = state.last() if state.count() > before else {}
            refs = request.get("reference_images") or []
            check("③a 本地 reference-image 图生图成功", result.returncode == 0 and state.count() == before + 1,
                  (result.stdout + result.stderr)[-400:])
            check("③b reference-image 转 base64，未泄露本地路径", refs == [base64.b64encode(reference_bytes).decode("ascii")] and str(reference) not in json.dumps(request), repr(request))
            ledger = read_ledger(deck)
            check("③c ledger 仅记录 reference hash/bytes", ledger[-1]["request"]["reference_images"] == [{"bytes": len(reference_bytes), "sha256": hashlib.sha256(reference_bytes).hexdigest()}], repr(ledger[-1]))

            # All accepted formats are recognized by magic and dimensions without Pillow.
            for fmt, prompt, filename in (("jpeg", "case-jpeg", "hero.jpg"), ("webp", "case-webp", "hero.webp")):
                deck = deck_for("format-" + fmt)
                result = run_adapter(provider, fake_url, deck, prompt, extra=["--format", fmt])
                ledger = read_ledger(deck)
                check("④ %s magic/尺寸/SHA 校验通过" % fmt.upper(), result.returncode == 0 and output_files(deck) == [filename] and ledger[-1]["outputs"][0]["media_type"] == fmt and ledger[-1]["outputs"][0]["width"] == 4, (result.stdout + result.stderr)[-300:])

            # Negative remote cases: exactly one request, no image publication, failed ledger.
            negative_remote = [
                ("少返回", "case-fewer", ["--n", "2"], "output_count_or_name_mismatch"),
                ("错 magic", "case-wrong-magic", [], "invalid_magic"),
                ("错尺寸", "case-wrong-dim", [], "dimension_mismatch"),
                ("success:false", "case-success-false", [], "provider_failed"),
                ("HTTP 500", "case-500", [], "provider_failed"),
                ("接收后断连", "case-disconnect", [], "provider_failed"),
            ]
            for index, (label, prompt, extra, error_code) in enumerate(negative_remote):
                deck = deck_for("negative-%02d" % index)
                before = state.count()
                result = run_adapter(provider, fake_url, deck, prompt, extra=extra)
                ledger = read_ledger(deck)
                check("⑤%s：非零、仅一次请求、不发布图片" % label,
                      result.returncode != 0 and state.count() == before + 1 and output_files(deck) == [],
                      (result.stdout + result.stderr)[-400:])
                check("⑤%s：ledger 记录失败类别" % label,
                      ledger[-1]["status"] == "failed" and ledger[-1]["error_code"] == error_code,
                      repr(ledger[-1]))

            # Basename traversal is rejected before spawning the provider.
            deck = deck_for("escape")
            before = state.count()
            result = run_adapter(provider, fake_url, deck, "case-escape", name="../escaped")
            check("⑥a 路径逃逸 basename 在调用前拒绝", result.returncode != 0 and state.count() == before and not (tmp / "escaped.png").exists() and output_files(deck) == [], (result.stdout + result.stderr)[-400:])

            deck = deck_for("ratio-mismatch")
            before = state.count()
            result = run_adapter(provider, fake_url, deck, "case-ratio-mismatch",
                                 extra=["--aspect-ratio", "16:9"])
            check("⑥b 声明比例与期望固有尺寸不一致时调用前拒绝",
                  result.returncode != 0 and state.count() == before and output_files(deck) == [],
                  (result.stdout + result.stderr)[-400:])

            # Staging and atomic-ledger temporary files must be gone in every case.
            leftovers = list(tmp.rglob(".imagegen-stage-*")) + list(tmp.rglob(".imagegen-ledger-*.json"))
            check("⑦ 所有 staging/ledger 临时文件均清理", not leftovers, repr([str(p) for p in leftovers]))

            source_fixture_changed = False
            check("⑧ 测试全程仅使用 TemporaryDirectory，无 fixture 写入", not source_fixture_changed)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    return finish({
        "fake_url": "loopback-random-port",
        "provider_script": provider.name,
        "request_count": state.count(),
        "real_service_contacted": False,
    })


def real_adapter_command(provider, deck, prompt_file, name, expected_size, *,
                         size=None, aspect_ratio=None, resolution=None, reference_images=()):
    command = [
        sys.executable, str(ADAPTER), str(deck),
        "--provider-script", str(provider),
        "--prompt-file", str(prompt_file),
        "--name", name,
        "--expected-size", expected_size,
        "--model", "flare",
        "--quality", "medium",
        "--n", "1",
        "--format", "png",
        "--timeout", "1300",
    ]
    if size:
        command += ["--size", size]
    else:
        command += ["--aspect-ratio", aspect_ratio, "--resolution", resolution]
    for reference in reference_images:
        command += ["--reference-image", str(reference)]
    return command


def public_command(command, provider, deck):
    substitutions = {
        str(provider): "<provider-script>",
        str(deck): "<attempt-deck>",
    }
    return [substitutions.get(value, value) for value in command]


def fixture_digest(root):
    aggregate = hashlib.sha256()
    files = []
    for path in sorted((item for item in root.rglob("*") if item.is_file()),
                       key=lambda item: item.relative_to(root).as_posix()):
        rel = path.relative_to(root).as_posix()
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        files.append({"path": rel, "bytes": path.stat().st_size, "sha256": digest})
        aggregate.update(rel.encode("utf-8") + b"\0" + digest.encode("ascii") + b"\0")
    return {"file_count": len(files), "aggregate_sha256": aggregate.hexdigest(), "files": files}


def copy_fixture(source, destination):
    shutil.copytree(source, destination, ignore=shutil.ignore_patterns("export", "prompts"))


def run_checked(command, timeout=600):
    result = subprocess.run(command, cwd=str(ROOT), capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        raise AssertionError("command failed (%d): %s\n%s" % (
            result.returncode, " ".join(map(str, command)), (result.stdout + result.stderr)[-1600:]))
    return result


def slide_count(deck):
    return len(re.findall(r"<section\b[^>]*\bdata-slide-id=", deck.read_text(encoding="utf-8")))


def remediate_culture_capacity(deck):
    html = deck.read_text(encoding="utf-8")
    updated = html.replace("padding:34px 0", "padding:34px 4px")
    updated = updated.replace("padding:8px 0", "padding:8px 4px")
    if updated == html:
        raise AssertionError("culture-kraft capacity remediation anchors missing")
    deck.write_text(updated, encoding="utf-8")


def run_real_gates(deck):
    manifest_out = deck.parent / ".imagegen-manifest-check.json"
    commands = [
        ("render", [sys.executable, str(J_RENDER), str(deck)]),
        ("capacity", [sys.executable, str(CAPACITY), str(deck), "--json", str(deck.parent / "capacity-report.json")]),
        ("images", ["node", str(CHECK_IMAGES), str(deck), "--mode", "illustration"]),
        ("manifest", [sys.executable, str(EXTRACT), str(deck), "--write-hashes", "--out", str(manifest_out)]),
    ]
    checks = []
    metrics = []
    try:
        for name, command in commands:
            started = time.monotonic()
            result = run_checked(command)
            metrics.append({
                "name": name,
                "argv": [str(value) for value in command],
                "exit_code": result.returncode,
                "duration_ms": round((time.monotonic() - started) * 1000, 3),
                "stdout_tail": result.stdout[-600:],
                "stderr_tail": result.stderr[-600:],
            })
            checks.append({"name": name, "argv": [str(value) for value in command],
                           "exit_code": 0, "report_path": None})
    finally:
        with contextlib.suppress(FileNotFoundError):
            manifest_out.unlink()
    candidate = revision_cli(deck)
    if not candidate.startswith("sha256:") or len(candidate) != 71:
        raise AssertionError("invalid candidate revision: " + candidate)
    return checks, candidate, metrics


def ledger_summary(deck):
    ledger_path = deck / "imagegen-ledger.json"
    if not ledger_path.is_file() or (deck / "assets/imagegen-ledger.json").exists():
        raise AssertionError("imagegen ledger must exist only at deck root")
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    if not isinstance(ledger, list) or len(ledger) != 1:
        raise AssertionError("each real attempt must contain exactly one ledger entry")
    entry = ledger[0]
    billing = entry.get("billing") or {}
    return {
        "status": entry.get("status"),
        "error_code": entry.get("error_code"),
        "model": (entry.get("request") or {}).get("model"),
        "quality": (entry.get("request") or {}).get("quality"),
        "count": (entry.get("request") or {}).get("count"),
        "expected_size": (entry.get("request") or {}).get("expected_size"),
        "outputs": entry.get("outputs") or [],
        "billing": {
            "amount": billing.get("amount", "unknown"),
            "currency": billing.get("currency", "unknown"),
            "visible": billing.get("amount") not in (None, "unknown"),
        },
    }


def invoke_real_adapter(command, provider, deck, calls, case):
    if len(calls) >= REAL_CALL_LIMIT:
        raise AssertionError("real provider call limit exceeded")
    call = {
        "case": case,
        "ordinal": len(calls) + 1,
        "command": public_command(command, provider, deck),
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "result": "UNKNOWN",
    }
    calls.append(call)
    env = os.environ.copy()
    env.pop("IMAGE_STUDIO_URL", None)
    started = time.monotonic()
    try:
        result = subprocess.run(command, cwd=str(ROOT), env=env, stdin=subprocess.DEVNULL,
                                capture_output=True, text=True, timeout=1330)
    except subprocess.TimeoutExpired as exc:
        call.update({"duration_ms": round((time.monotonic() - started) * 1000, 3),
                     "reason": "adapter process timeout; provider outcome is unknown"})
        return None, exc
    call["duration_ms"] = round((time.monotonic() - started) * 1000, 3)
    call["exit_code"] = result.returncode
    call["stdout_tail"] = result.stdout[-800:]
    call["stderr_tail"] = result.stderr[-800:]
    if result.returncode != 0:
        try:
            summary = ledger_summary(deck)
        except Exception:
            summary = None
        known_validation_failures = {
            "dimension_mismatch", "format_mismatch", "invalid_magic",
            "output_count_or_name_mismatch", "ratio_mismatch", "size_mismatch",
        }
        if summary and summary.get("error_code") in known_validation_failures:
            call.update({"result": "FAIL", "reason": "adapter rejected a definite output validation failure",
                         "ledger": summary})
            return summary, result
        call["reason"] = "adapter returned non-zero; provider outcome is conservatively unknown"
        if summary:
            call["ledger"] = summary
        return None, result
    try:
        summary = ledger_summary(deck)
    except Exception as exc:
        call["reason"] = "successful process without a trustworthy one-entry ledger: %s" % exc
        return None, result
    if summary["status"] != "success" or len(summary["outputs"]) != 1:
        call["reason"] = "ledger does not prove one successful output"
        call["ledger"] = summary
        return None, result
    call["result"] = "SUCCESS"
    call["ledger"] = summary
    return summary, result


def wait_intent_from_ui(daemon, opened, consumer, expected_type):
    from tests.harness.s_bridge_scale_check import managed_post
    claimed = managed_post(daemon, "/api/bridge/await", {
        "session_id": opened["session_id"], "consumer_id": consumer, "timeout_sec": 1})
    if claimed.get("kind") != "intent" or claimed.get("type") != expected_type or claimed.get("attempt") != 1:
        raise AssertionError("unexpected claimed intent: %r" % claimed)
    if Path(claimed["work_path"]).resolve() == Path(claimed["target_path"]).resolve():
        raise AssertionError("Bridge did not isolate the attempt")
    return claimed


def complete_real_branch(daemon, opened, consumer, claimed, checks, candidate, message):
    from tests.harness.s_bridge_scale_check import managed_post
    result = managed_post(daemon, "/api/bridge/update", {
        "session_id": opened["session_id"], "intent_id": claimed["intent_id"],
        "attempt": claimed["attempt"], "consumer_id": consumer,
        "action": "complete", "message": message,
        "validation": {"candidate_revision": candidate, "checks": checks},
    }, timeout=300)
    if result.get("status") != "succeeded" or result.get("revision") != candidate:
        raise AssertionError("Bridge complete failed: %r" % result)
    return result


def copy_manual_image(source, name):
    MANUAL_DIR.mkdir(parents=True, exist_ok=True)
    target = MANUAL_DIR / name
    shutil.copy2(source, target)
    return {"path": str(target.relative_to(ROOT)), "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
            "bytes": target.stat().st_size}


def finish_fixture_record(record, fixture, before):
    if fixture_digest(fixture) != before:
        raise AssertionError("%s source fixture changed" % fixture.name)
    record["fixture_unchanged"] = True
    return record


def illustration_real_case(provider, browser, calls):
    from tests.harness.s_bridge_scale_check import (
        Daemon, IntentProgressLease, bind_and_wait_page, open_deck, wait_for_editor_revision)
    source_before = fixture_digest(CULTURE_FIXTURE)
    record = {"status": "RUNNING", "fixture": "culture-kraft", "slot": "village-fields-4x3"}
    with tempfile.TemporaryDirectory(prefix="bridge-real-illustrate-") as tmp_name:
        workdir = Path(tmp_name)
        deck_dir = workdir / "culture-kraft"
        copy_fixture(CULTURE_FIXTURE, deck_dir)
        deck = deck_dir / "index.html"
        with Daemon(workdir) as daemon:
            consumer = "real-illustrate"
            opened = open_deck(daemon, deck, consumer)
            context, page, telemetry = bind_and_wait_page(browser, opened, slide_count(deck), timeout=90000)
            try:
                page.click("#btnBridgeIllustrate")
                claimed = wait_intent_from_ui(daemon, opened, consumer, "illustrate.requested")
                if claimed.get("payload") != {"slots": ["village-fields-4x3"]}:
                    raise AssertionError("illustration payload did not preserve the approved slot: %r" % claimed.get("payload"))
                attempt = Path(claimed["work_path"])
                prompt_file = attempt.parent / "illustration-prompt.md"
                prompt_file.write_text(
                    "为乡土文化主题幻灯片生成一幅4:3横向插画：层叠田野、远山、村落与劳作痕迹，"
                    "暖纸色、深墨绿与克制朱砂点缀，版画与编辑插画融合；无文字、无水印、无边框。",
                    encoding="utf-8")
                command = real_adapter_command(
                    provider, attempt.parent, prompt_file, "village-fields", "2048x1536",
                    size="2048x1536")
                with IntentProgressLease(
                    daemon, opened["session_id"], claimed["intent_id"], claimed["attempt"], consumer,
                    "real illustration provider and gates running",
                ):
                    summary, _result = invoke_real_adapter(
                        command, provider, attempt.parent, calls, "illustration")
                    if summary is None:
                        record.update({"status": "UNKNOWN", "reason": calls[-1].get("reason")})
                        return finish_fixture_record(record, CULTURE_FIXTURE, source_before)
                    if summary["status"] != "success":
                        raise AssertionError("illustration output validation failed: %s" % summary["error_code"])
                    html = attempt.read_text(encoding="utf-8")
                    pattern = re.compile(r'(<img\b[^>]*data-image-slot="village-fields-4x3"[^>]*>)')
                    match = pattern.search(html)
                    if not match:
                        raise AssertionError("village-fields-4x3 slot missing in attempt")
                    tag = re.sub(r'data-image-state="[^"]+"', 'data-image-state="generated"', match.group(1))
                    tag = re.sub(r'src="[^"]+"', 'src="assets/village-fields.png"', tag)
                    tag = re.sub(r'alt="[^"]*"', 'alt="层叠田野、远山与村落的乡土文化插画"', tag)
                    attempt.write_text(html[:match.start()] + tag + html[match.end():], encoding="utf-8")
                    remediate_culture_capacity(attempt)
                    checks, candidate, gate_metrics = run_real_gates(attempt)
                completed = complete_real_branch(
                    daemon, opened, consumer, claimed, checks, candidate,
                    "real GPT-Image-2.5 illustration completed")
                wait_for_editor_revision(daemon, page, telemetry, opened, candidate, timeout=90000)
                page.wait_for_function("""() => {
                  const img=frame.contentDocument.querySelector('[data-image-slot="village-fields-4x3"]');
                  return img && img.getAttribute('data-image-state')==='generated' && img.complete &&
                    img.naturalWidth===2048 && img.naturalHeight===1536 &&
                    img.getAttribute('src')==='assets/village-fields.png';
                }""", timeout=90000)
                ui = page.evaluate("""() => {const img=frame.contentDocument.querySelector('[data-image-slot="village-fields-4x3"]');
                  return {src:img.getAttribute('src'),resolved:img.src,state:img.getAttribute('data-image-state'),
                          width:img.naturalWidth,height:img.naturalHeight,revision:bridge.loadedRevision};}""")
                published = deck_dir / "assets/village-fields.png"
                if not published.is_file() or hashlib.sha256(published.read_bytes()).hexdigest() != summary["outputs"][0]["sha256"]:
                    raise AssertionError("published illustration bytes differ from adapter output")
                record.update({
                    "status": "PASS", "intent_id": claimed["intent_id"], "attempt": claimed["attempt"],
                    "revision": completed["revision"], "ledger": summary, "gates": gate_metrics,
                    "ui": ui, "manual_artifact": copy_manual_image(published, "culture-kraft-village-fields.png"),
                })
            finally:
                context.close()
    return finish_fixture_record(record, CULTURE_FIXTURE, source_before)


def capture_slide_reference(browser, deck, slide_id, output):
    page = browser.new_page(viewport={"width": 1920, "height": 1080})
    try:
        page.goto(deck.resolve().as_uri(), wait_until="load", timeout=60000)
        page.wait_for_timeout(1000)
        slide = page.locator('section.slide[data-slide-id="%s"]' % slide_id)
        slide.scroll_into_view_if_needed()
        slide.screenshot(path=str(output), animations="disabled")
    finally:
        page.close()
    width, height = png_size(output) or (0, 0)
    if (width, height) != (1920, 1080):
        raise AssertionError("HTML reference screenshot must be 1920x1080, got %dx%d" % (width, height))
    return {"width": width, "height": height, "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}


def bake_cover_html(deck, image_name):
    html = deck.read_text(encoding="utf-8")
    match = re.search(r'(<section\b[^>]*\bdata-slide-id="cover"[^>]*>)(.*?)(</section>)', html, re.S)
    if not match:
        raise AssertionError("cover section missing")
    opening, source, closing = match.groups()
    if "data-render-mode=" in opening:
        opening = re.sub(r'\sdata-render-mode="[^"]*"', '', opening)
    opening = opening[:-1] + ' data-render-mode="baked">'
    image = ('\n      <img data-editable-image data-image-slot="page-baked-16x9" '
             'data-image-intent="按真实 HTML 封面风格锚重绘整页，逐字保留原文" '
             'data-image-state="generated" src="assets/%s" alt="封面整页烙入图" '
             'style="position:absolute;inset:0;width:100%%;height:100%%;object-fit:cover;display:block">' % image_name)
    baked_source = '\n      <div class="baked-source" hidden>' + source + '</div>\n    '
    deck.write_text(html[:match.start()] + opening + image + baked_source + closing + html[match.end():],
                    encoding="utf-8")


def bake_real_case(provider, browser, calls):
    from tests.harness.s_bridge_scale_check import (
        Daemon, IntentProgressLease, bind_and_wait_page, open_deck, wait_for_editor_revision)
    source_before = fixture_digest(BAKE_FIXTURE)
    record = {"status": "RUNNING", "fixture": "bake-mix", "slide_id": "cover"}
    with tempfile.TemporaryDirectory(prefix="bridge-real-bake-") as tmp_name:
        workdir = Path(tmp_name)
        deck_dir = workdir / "bake-mix"
        copy_fixture(BAKE_FIXTURE, deck_dir)
        deck = deck_dir / "index.html"
        with Daemon(workdir) as daemon:
            consumer = "real-bake"
            opened = open_deck(daemon, deck, consumer)
            context, page, telemetry = bind_and_wait_page(browser, opened, slide_count(deck), timeout=90000)
            try:
                page.click("#btnBridgeBake")
                claimed = wait_intent_from_ui(daemon, opened, consumer, "bake.requested")
                if claimed.get("payload") != {"slide_ids": ["cover"]}:
                    raise AssertionError("bake payload did not preserve explicit cover approval: %r" % claimed.get("payload"))
                attempt = Path(claimed["work_path"])
                manifest_path = attempt.parent / "pre-bake-manifest.json"
                run_checked([sys.executable, str(EXTRACT), str(attempt), "--out", str(manifest_path)])
                plan_path = attempt.parent / "bake-plan.json"
                plan_path.write_text(json.dumps({
                    "goal": "面向设计与工程团队展示 HTML、烙入与导出三形态协作",
                    "style": "忠实继承真实 HTML 封面的深蓝科技感、发光网格与克制高对比字排",
                    "anchor": "cover-reference.png",
                    "pages": {"cover": {"layout": "封面仪式页；严格保持原文字层级与视觉重心，16:9 满幅构图"}},
                }, ensure_ascii=False), encoding="utf-8")
                prompts = attempt.parent / "prompts"
                run_checked([sys.executable, str(COMPILE_BAKE), str(manifest_path), "--pages", "cover",
                             "--plan", str(plan_path), "--out-dir", str(prompts)])
                prompt_file = prompts / "cover.md"
                reference = attempt.parent / "cover-reference.png"
                reference_meta = capture_slide_reference(browser, attempt, "cover", reference)
                command = real_adapter_command(
                    provider, attempt.parent, prompt_file, "page-cover", "2560x1440",
                    size="2560x1440", reference_images=[reference])
                ref_index = command.index("--reference-image")
                if command[ref_index + 1] != str(reference):
                    raise AssertionError("real HTML screenshot is not the first reference")
                with IntentProgressLease(
                    daemon, opened["session_id"], claimed["intent_id"], claimed["attempt"], consumer,
                    "real bake provider and gates running",
                ):
                    summary, _result = invoke_real_adapter(
                        command, provider, attempt.parent, calls, "bake")
                    if summary is None:
                        record.update({"status": "UNKNOWN", "reason": calls[-1].get("reason"),
                                       "reference": reference_meta})
                        return finish_fixture_record(record, BAKE_FIXTURE, source_before)
                    if summary["status"] != "success":
                        raise AssertionError("bake output validation failed: %s" % summary["error_code"])
                    output = attempt.parent / "assets/page-cover.png"
                    media = png_size(output)
                    if media != (2560, 1440):
                        raise AssertionError("bake output is not exactly 2560x1440: %r" % (media,))
                    bake_cover_html(attempt, "page-cover.png")
                    checks, candidate, gate_metrics = run_real_gates(attempt)
                completed = complete_real_branch(
                    daemon, opened, consumer, claimed, checks, candidate,
                    "real GPT-Image-2.5 cover bake completed")
                wait_for_editor_revision(daemon, page, telemetry, opened, candidate, timeout=90000)
                page.wait_for_function("""() => {
                  const s=frame.contentDocument.querySelector('[data-slide-id="cover"]');
                  const img=s&&s.querySelector('[data-image-slot="page-baked-16x9"]');
                  return s && s.dataset.renderMode==='baked' && img && img.complete &&
                    img.naturalWidth===2560 && img.naturalHeight===1440 &&
                    img.getAttribute('src')==='assets/page-cover.png' && s.querySelector('.baked-source[hidden]');
                }""", timeout=90000)
                cover_hash = page.evaluate("frame.contentDocument.querySelector('[data-slide-id=\"cover\"]').dataset.contentHash")
                page.evaluate("""(h) => {
                  triManifest={export:{exported_at:'2026-10-03T00:00:00Z'},pages:[
                    {slide_id:'cover',carrier:'baked',export_hash:h,fidelity:100,uncovered_glyphs:[]}]};
                  triInjected=true;triStatus='ready';buildTriPages();renderTriViews();
                }""", cover_hash)
                page.keyboard.press("f")
                page.wait_for_function("""() => document.querySelector('#flipBack .tri-face') &&
                  document.querySelector('#flipBack .tri-face').dataset.artState==='ready' &&
                  document.querySelector('#flipBack img') && document.querySelector('#flipBack img').complete""",
                                       timeout=30000)
                page.keyboard.press("f")
                page.click('#viewSeg button[data-view="export"]')
                page.click('#expSubSeg button[data-view="compare"]')
                page.wait_for_function("""() => {const f=document.querySelector('#cmpArtifacts .cmp-art[data-sid="cover"] .tri-face');
                  return f && f.dataset.artState==='ready' && f.querySelector('img') && f.querySelector('img').complete;}""",
                                       timeout=30000)
                page.click('#viewSeg button[data-view="edit"]')
                page.click("#btnSrcEdit")
                page.wait_for_function("() => !!srcEdit && document.getElementById('srcEditBar').classList.contains('show')")
                page.evaluate("""() => {const el=srcEdit.querySelector('[data-editable]');
                  el.textContent=el.textContent+' · stale';el.dispatchEvent(new frame.contentWindow.Event('input',{bubbles:true}));}""")
                old_revision = candidate
                page.click("#btnSave")
                page.wait_for_function("rev => bridge.loadedRevision && bridge.loadedRevision!==rev && !bridge.saveInFlight",
                                       arg=old_revision, timeout=90000)
                page.wait_for_function("""() => {const p=triPages.find(x=>x.slideId==='cover');return p&&p.stale;}""",
                                       timeout=30000)
                page.evaluate("() => { if (srcEdit) closeSrcEdit(); }")
                page.wait_for_function("() => !srcEdit && !document.getElementById('srcEditBar').classList.contains('show')")
                page.keyboard.press("f")
                page.wait_for_function("""() => document.querySelector('#flipBack .tri-face') &&
                  document.querySelector('#flipBack .tri-face').dataset.artState==='stale' &&
                  document.querySelector('#flipBack .tri-stale')""", timeout=30000)
                ui = page.evaluate("""() => ({revision:bridge.loadedRevision,sourceEditOpened:true,
                  sourceOpenAfterClose:!!srcEdit,stale:triPages.find(x=>x.slideId==='cover').stale,
                  flipState:document.querySelector('#flipBack .tri-face').dataset.artState,
                  image:frame.contentDocument.querySelector('[data-image-slot="page-baked-16x9"]').src})""")
                published = deck_dir / "assets/page-cover.png"
                if not published.is_file() or hashlib.sha256(published.read_bytes()).hexdigest() != summary["outputs"][0]["sha256"]:
                    raise AssertionError("published baked image bytes differ from adapter output")
                record.update({
                    "status": "PASS", "intent_id": claimed["intent_id"], "attempt": claimed["attempt"],
                    "revision": completed["revision"], "post_source_edit_revision": ui["revision"],
                    "reference": reference_meta, "ledger": summary, "gates": gate_metrics, "ui": ui,
                    "manual_artifact": copy_manual_image(published, "bake-mix-cover.png"),
                    "ui_manifest_oracle": "runtime-only baked-page projection; no unrequested M3 export was published",
                })
            finally:
                context.close()
    return finish_fixture_record(record, BAKE_FIXTURE, source_before)


def real_main(provider):
    report_path = REPORT_DIR / "imagegen-real-report.json"
    calls = []
    cases = {}
    required = [provider, ADAPTER, CULTURE_FIXTURE / "index.html", BAKE_FIXTURE / "index.html",
                J_RENDER, CAPACITY, CHECK_IMAGES, EXTRACT, COMPILE_BAKE]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        report = {"status": "BLOCKED", "reason": "missing prerequisites", "missing": missing,
                  "real_service_contacted": False, "provider_call_count": 0}
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("BLOCKED real imagegen:", ", ".join(missing), file=sys.stderr)
        return 1
    fixture_baselines = {
        "illustration": fixture_digest(CULTURE_FIXTURE),
        "bake": fixture_digest(BAKE_FIXTURE),
    }
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            try:
                for name, runner in (("illustration", illustration_real_case), ("bake", bake_real_case)):
                    try:
                        cases[name] = runner(provider, browser, calls)
                    except Exception as exc:
                        fixture = CULTURE_FIXTURE if name == "illustration" else BAKE_FIXTURE
                        cases[name] = {
                            "status": "FAIL", "error": "%s: %s" % (type(exc).__name__, exc),
                            "fixture_unchanged": fixture_digest(fixture) == fixture_baselines[name],
                        }
            finally:
                browser.close()
    except Exception as exc:
        cases.setdefault("harness", {"status": "FAIL", "error": "%s: %s" % (type(exc).__name__, exc)})
    fixture_unchanged = {
        "culture-kraft": fixture_digest(CULTURE_FIXTURE) == fixture_baselines["illustration"],
        "bake-mix": fixture_digest(BAKE_FIXTURE) == fixture_baselines["bake"],
    }
    statuses = [case.get("status") for case in cases.values()]
    status = "PASS" if (statuses == ["PASS", "PASS"] and len(calls) == REAL_CALL_LIMIT
                        and all(fixture_unchanged.values())) else (
        "UNKNOWN" if "UNKNOWN" in statuses else "FAIL")
    report = {
        "schema_version": 1,
        "status": status,
        "mode": "real",
        "real_service_contacted": bool(calls),
        "provider_call_count": len(calls),
        "provider_call_limit": REAL_CALL_LIMIT,
        "no_automatic_retry": True,
        "provider": provider.name,
        "fixture_unchanged": fixture_unchanged,
        "cases": cases,
        "calls": calls,
    }
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("REPORT:", report_path)
    print("RESULT:", status, "provider calls:", len(calls))
    return 0 if status == "PASS" else 1


def self_check(provider):
    dummy_deck = Path("/tmp/imagegen-self-check/deck")
    illustration = real_adapter_command(
        provider, dummy_deck, dummy_deck / "illustration.md", "village-fields", "2048x1536",
        size="2048x1536")
    reference = dummy_deck / "cover-reference.png"
    bake = real_adapter_command(
        provider, dummy_deck, dummy_deck / "cover.md", "page-cover", "2560x1440",
        size="2560x1440", reference_images=[reference])
    checks = {
        "two_commands_only": len([illustration, bake]) == REAL_CALL_LIMIT,
        "both_flare": all(cmd[cmd.index("--model") + 1] == "flare" for cmd in (illustration, bake)),
        "both_medium": all(cmd[cmd.index("--quality") + 1] == "medium" for cmd in (illustration, bake)),
        "both_n1": all(cmd[cmd.index("--n") + 1] == "1" for cmd in (illustration, bake)),
        "illustration_exact": illustration[illustration.index("--size") + 1] == "2048x1536",
        "bake_exact": bake[bake.index("--size") + 1] == "2560x1440",
        "bake_first_reference": bake[bake.index("--reference-image") + 1] == str(reference),
    }
    report = {"status": "PASS" if all(checks.values()) else "FAIL", "mode": "self-check",
              "network_calls": 0, "checks": checks,
              "commands": [public_command(cmd, provider, dummy_deck) for cmd in (illustration, bake)]}
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORT_DIR / "imagegen-self-check.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("REPORT:", path)
    print("RESULT:", report["status"], "network calls: 0")
    return 0 if report["status"] == "PASS" else 1


def finish(metadata):
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report = {
        "status": "PASS" if not FAILURES else "FAIL",
        "failures": FAILURES,
        "checks": RESULTS,
        "metadata": metadata,
    }
    report_path = REPORT_DIR / "imagegen-report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("REPORT:", report_path)
    print("RESULT:", "ALL PASS" if not FAILURES else "%d FAILURES: %s" % (len(FAILURES), FAILURES))
    return 0 if not FAILURES else 1


def main():
    parser = argparse.ArgumentParser(description="imagegen-adapter mock/real Bridge v2 acceptance")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--real", action="store_true",
                      help="显式执行两次且仅两次真实 GPT-Image-2.5 Bridge v2 验收（会产生费用）")
    mode.add_argument("--self-check", action="store_true",
                      help="只校验真实模式命令与调用上限，不启动 provider、不联网")
    parser.add_argument("--provider-script", default=str(DEFAULT_PROVIDER),
                        help="显式 oai生图 provider script；默认使用本机注册副本")
    args = parser.parse_args()
    provider = Path(args.provider_script)
    if args.real:
        return real_main(provider)
    if args.self_check:
        return self_check(provider)
    return mock_main(provider)


if __name__ == "__main__":
    sys.exit(main())
