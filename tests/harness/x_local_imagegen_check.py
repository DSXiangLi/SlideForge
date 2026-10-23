#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""--imagegen 本地插画通道验收（imagegen v2 P2 G6，docs/design/imagegen-v2.md §3-G6）。

全程打桩：provider 是 harness 现场生成的本地假脚本（按 --size 输出纯色合成
PNG，颜色取环境变量 PPTX_HTML_STUB_COLOR），不真实付费、不联网。

覆盖：
  ① 端到端正例：culture-kraft 副本 → daemon(--imagegen) → POST /api/imagegen
     → illustrate.requested intent 落库 → 本地 worker 认领执行（adapter 打桩
     生图 → 槽位 state 推进 generated → render/capacity/images/manifest 四闸
     + harmony 告警口径）→ 发布 → 目标 deck 与资产落盘、ledger 脱敏；
  ② 无 placeholder 槽位的 deck：started=False 且 ok（提示并退出 0 语义）；
  ③ 未启用 --imagegen 的 daemon：POST /api/imagegen → 403 UNAUTHORIZED；
  ④ CLI 门禁：--imagegen 缺 provider 配置时 exit 2 且明示原因；
  ⑤ provider 经 .pptx-html/config.json 的 imagegen_provider 键供给时 daemon
     正常启动（环境变量缺省路径）。
"""

import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tests.harness.s_bridge_scale_check import (  # noqa: E402
    Daemon, bind_browser_token, check, copy_fixture, fixture_summary,
    assert_fixture_unchanged, managed_post, one_request, open_deck,
)
from tests.harness.t_imagegen_check import (  # noqa: E402
    png_size, remediate_culture_capacity,
)

EDIT = ROOT / "tools" / "edit.py"
CULTURE_FIXTURE = ROOT / "tests/decks/culture-kraft"
TECH_FIXTURE = ROOT / "tests/decks/tech-ikb"
# culture-kraft 主题的 --accent；打桩图纯色取它，harmony 指标 B（accent 呼应）
# 必过、指标 A（无锚率）必过，不会触发 ≥50% 双触发阻断。
STUB_COLOR = "#2a1e13"

STUB_PROVIDER = r'''#!/usr/bin/env python3
"""harness 打桩 provider：按 --size 输出纯色合成 PNG（真实 PNG，可解码）。"""
import argparse
import os
import struct
import zlib


def png_bytes(width, height, rgb):
    raw = b"".join(b"\x00" + bytes(rgb) * width for _ in range(height))
    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data +
                struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw))
            + chunk(b"IEND", b""))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode")
    parser.add_argument("--prompt-file")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--quality")
    parser.add_argument("--format", default="png")
    parser.add_argument("--moderation")
    parser.add_argument("--background")
    parser.add_argument("--n", type=int, default=1)
    parser.add_argument("--name", required=True)
    parser.add_argument("--size")
    parser.add_argument("--aspect-ratio")
    parser.add_argument("--resolution")
    parser.add_argument("--reference-image", action="append", default=[])
    parser.add_argument("--advance-model", action="store_true")
    args = parser.parse_args()
    width, height = (args.size or "2048x1152").split("x")
    color = os.environ.get("PPTX_HTML_STUB_COLOR", "#808080").lstrip("#")
    rgb = bytes.fromhex(color)
    ext = {"png": ".png", "jpeg": ".jpg", "webp": ".webp"}[args.format]
    names = ([args.name + ext] if args.n == 1
             else ["%s_%d%s" % (args.name, i, ext) for i in range(args.n)])
    for name in names:
        with open(os.path.join(args.output_dir, name), "wb") as handle:
            handle.write(png_bytes(int(width), int(height), rgb))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


def query_intent(daemon, token, session_id, intent_id):
    """/api/intents/query 是浏览器凭证路由（管理凭证不适用）。"""
    code, result = one_request(
        daemon.origin, "/api/intents/query",
        {"session_id": session_id, "intent_id": intent_id}, token, daemon.origin)
    check(code == 200 and result.get("ok"), "intent query failed: %d %r" % (code, result))
    return result["items"][0]


def wait_imagegen(daemon, session_id, timeout=900):
    deadline = time.monotonic() + timeout
    status = None
    while time.monotonic() < deadline:
        code, status = one_request(
            daemon.origin, "/api/imagegen-status?session_id=" + session_id,
            bearer=daemon.management, timeout=30)
        check(code == 200, "imagegen-status HTTP %d: %r" % (code, status))
        if status["status"] != "running":
            return status
        time.sleep(3)
    raise AssertionError("local imagegen did not finish in %ss: %r" % (timeout, status))


def positive_case(stub_provider):
    before = fixture_summary(CULTURE_FIXTURE)
    with tempfile.TemporaryDirectory(prefix="bridge-local-imagegen-") as tmp:
        workdir = Path(tmp)
        deck_dir = workdir / "culture-kraft"
        copy_fixture(CULTURE_FIXTURE, deck_dir)
        deck = deck_dir / "index.html"
        remediate_culture_capacity(deck)   # 与真实生图流程相同的容量修复锚点
        with Daemon(workdir, allow_imagegen=True, startup_timeout=30) as daemon:
            opened = open_deck(daemon, deck, "local-imagegen")
            token = bind_browser_token(daemon, opened)
            result = managed_post(daemon, "/api/imagegen",
                                  {"session_id": opened["session_id"]}, timeout=30)
            check(result.get("started") is True
                  and result.get("slots") == ["village-fields-4x3"],
                  "imagegen start unexpected: %r" % result)
            check(result.get("intent_id"), "imagegen intent id missing")
            item = query_intent(daemon, token, opened["session_id"], result["intent_id"])
            check(item["type"] == "illustrate.requested",
                  "intent type mismatch: %r" % item)
            status = wait_imagegen(daemon, opened["session_id"])
            check(status["status"] == "done",
                  "local imagegen failed: %s" % status.get("tail"))
            item = query_intent(daemon, token, opened["session_id"], result["intent_id"])
            check(item["status"] == "succeeded" and item["result_summary"],
                  "intent not succeeded: %r" % item)

            html = deck.read_text(encoding="utf-8")
            match = re.search(
                r'<img\b[^>]*data-image-slot="village-fields-4x3"[^>]*>', html)
            check(match is not None
                  and 'data-image-state="generated"' in match.group(0)
                  and 'src="assets/village-fields.png"' in match.group(0),
                  "slot not advanced to generated: %s"
                  % (match.group(0) if match else "slot missing"))
            produced = deck_dir / "assets" / "village-fields.png"
            check(produced.is_file() and png_size(produced) == (2048, 1536),
                  "published asset missing or wrong size: %r"
                  % (png_size(produced) if produced.is_file() else None,))
            # ledger 属 attempt 工作区证据，不是受管 bundle 文件：发布不得带出，
            # 但 attempt 副本中必须存在且脱敏（basename+sha256，无绝对路径）。
            check(not (deck_dir / "imagegen-ledger.json").exists(),
                  "ledger 不得随发布进入正式 deck（非受管文件）")
            attempt_deck = (workdir / ".pptx-html" / "jobs" / result["intent_id"]
                            / "attempt-1" / "work" / "culture-kraft")
            ledger_path = attempt_deck / "imagegen-ledger.json"
            ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
            serialized = json.dumps(ledger, ensure_ascii=False)
            check(len(ledger) == 1 and ledger[0]["status"] == "success",
                  "ledger unexpected: %r" % ledger)
            check(str(stub_provider) not in serialized
                  and str(stub_provider) not in html
                  and ledger[0]["provider"]["script"] == stub_provider.name,
                  "provider absolute path leaked into ledger/deck")
            final = managed_post(daemon, "/api/bridge/status",
                                 {"session_id": opened["session_id"]})
            check(final["revision"] != opened["revision"],
                  "publication did not advance revision")
            check(final["capabilities"].get("local_imagegen") is True,
                  "capabilities.local_imagegen not advertised: %r"
                  % final.get("capabilities"))
    assert_fixture_unchanged(before, fixture_summary(CULTURE_FIXTURE), "culture-kraft")
    print("PASS ① local imagegen end-to-end (stub provider)")


def no_placeholder_case(stub_provider):
    before = fixture_summary(TECH_FIXTURE)
    with tempfile.TemporaryDirectory(prefix="bridge-imagegen-empty-") as tmp:
        workdir = Path(tmp)
        deck_dir = workdir / "tech-ikb"
        copy_fixture(TECH_FIXTURE, deck_dir)
        # provider 经 config.json 供给（覆盖第 ⑤ 条：环境变量缺省路径）
        (workdir / ".pptx-html").mkdir(mode=0o700, exist_ok=True)
        (workdir / ".pptx-html" / "config.json").write_text(
            json.dumps({"imagegen_provider": str(stub_provider)}), encoding="utf-8")
        env_saved = os.environ.pop("PPTX_HTML_IMAGEGEN_PROVIDER", None)
        try:
            with Daemon(workdir, allow_imagegen=True, startup_timeout=30) as daemon:
                opened = open_deck(daemon, deck_dir / "index.html", "local-imagegen-empty")
                result = managed_post(daemon, "/api/imagegen",
                                      {"session_id": opened["session_id"]}, timeout=30)
                check(result.get("ok") is True and result.get("started") is False
                      and not result.get("slots"),
                      "no-placeholder deck should be a no-op success: %r" % result)
        finally:
            if env_saved is not None:
                os.environ["PPTX_HTML_IMAGEGEN_PROVIDER"] = env_saved
    assert_fixture_unchanged(before, fixture_summary(TECH_FIXTURE), "tech-ikb")
    print("PASS ②⑤ no-placeholder no-op + config.json provider resolution")


def unauthorized_case():
    before = fixture_summary(TECH_FIXTURE)
    with tempfile.TemporaryDirectory(prefix="bridge-imagegen-denied-") as tmp:
        workdir = Path(tmp)
        deck_dir = workdir / "tech-ikb"
        copy_fixture(TECH_FIXTURE, deck_dir)
        with Daemon(workdir, startup_timeout=30) as daemon:   # 未启用 --imagegen
            opened = open_deck(daemon, deck_dir / "index.html", "local-imagegen-denied")
            code, result = one_request(
                daemon.origin, "/api/imagegen",
                {"session_id": opened["session_id"]}, bearer=daemon.management)
            check(code == 403 and result.get("error", {}).get("code") == "UNAUTHORIZED",
                  "imagegen without --imagegen should be 403: %d %r" % (code, result))
            status = managed_post(daemon, "/api/bridge/status",
                                  {"session_id": opened["session_id"]})
            check(status["capabilities"].get("local_imagegen") is False,
                  "capabilities.local_imagegen should be false: %r"
                  % status.get("capabilities"))
    assert_fixture_unchanged(before, fixture_summary(TECH_FIXTURE), "tech-ikb")
    print("PASS ③ daemon without --imagegen rejects local imagegen")


def cli_guard_case():
    with tempfile.TemporaryDirectory(prefix="bridge-imagegen-cli-") as tmp:
        env = os.environ.copy()
        env.pop("PPTX_HTML_IMAGEGEN_PROVIDER", None)
        run = subprocess.run(
            [sys.executable, str(EDIT), tmp, "--imagegen", "--no-browser"],
            capture_output=True, text=True, env=env, timeout=30)
        check(run.returncode == 2
              and "PPTX_HTML_IMAGEGEN_PROVIDER" in run.stderr
              and "imagegen_provider" in run.stderr,
              "cli guard unexpected: rc=%d stderr=%s" % (run.returncode, run.stderr[:300]))
    print("PASS ④ --imagegen without provider config fails fast with guidance")


def main():
    with tempfile.TemporaryDirectory(prefix="bridge-imagegen-stub-") as tmp:
        stub_provider = Path(tmp) / "stub_provider.py"
        stub_provider.write_text(STUB_PROVIDER, encoding="utf-8")
        os.environ["PPTX_HTML_IMAGEGEN_PROVIDER"] = str(stub_provider)
        os.environ["PPTX_HTML_STUB_COLOR"] = STUB_COLOR
        try:
            positive_case(stub_provider)
            no_placeholder_case(stub_provider)
            unauthorized_case()
            cli_guard_case()
        finally:
            os.environ.pop("PPTX_HTML_STUB_COLOR", None)
    print("RESULT: ALL PASS (x_local_imagegen_check)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
