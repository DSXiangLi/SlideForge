#!/usr/bin/env python3
"""从官方 @modelcontextprotocol/ext-apps 提取 View 侧 bundle，拼上本项目门面。

**构建期脚本，运行时零依赖。** 产物 `tools/ext_apps_bundle.js` 提交进仓库，
并附 `tools/ext_apps_bundle.json` 的 sha256 manifest（设计 §6.3）。

用法：
    python3 tools/build_ext_apps_bundle.py [--source PATH] [--check]

`--check` 只校验仓库内产物与源文件+门面是否一致（CI/循环里用，不写文件）。

转换只做一件事：把 bundle 末尾的 ESM `export{内部名 as 公共名,...}` 重写成
`const __ext = {公共名: 内部名, ...}`，其余字节原样保留——产物仍是 module，
由 server 以 `<script type="module">` 注入（见 tools/bridge_mcp.py 的 build_view_html）。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE = Path.home() / "Desktop" / "ext-apps" / "dist" / "src" / "app-with-deps.js"
FACADE = ROOT / "tools" / "ext_apps_facade.js"
OUTPUT = ROOT / "tools" / "ext_apps_bundle.js"
MANIFEST = ROOT / "tools" / "ext_apps_bundle.json"
# editor.html 与门面共用的 View 版本号（改门面协议时同步）
VIEW_VERSION = "3.9.2"


def strip_export(text: str) -> str:
    matches = list(re.finditer(r"export\{([^}]*)\};?[ \t]*\n?$", text))
    if len(matches) != 1:
        raise SystemExit(f"预期恰好一条末尾 export 语句，实际 {len(matches)} 条；源 bundle 格式已变，请人工核对")
    names = []
    for item in matches[0].group(1).split(","):
        parts = item.strip().split(" as ")
        if len(parts) == 2:
            names.append((parts[1].strip(), parts[0].strip()))
        elif len(parts) == 1 and parts[0]:
            names.append((parts[0].strip(), parts[0].strip()))
    body = text[: matches[0].start()]
    mapping = ",".join(f"{public}:{internal}" for public, internal in names)
    return body + f"const __ext = {{{mapping}}};\n"


def build(source: Path) -> str:
    raw = source.read_text(encoding="utf-8")
    if "import " in raw.split("const __ext")[0][:2000]:
        raise SystemExit("源 bundle 含 import 语句，无法作为单文件 module 注入")
    facade = FACADE.read_text(encoding="utf-8").replace("VIEW_VERSION", json.dumps(VIEW_VERSION))
    banner = (
        "/* 自动生成，请勿手改：python3 tools/build_ext_apps_bundle.py\n"
        f"   源：@modelcontextprotocol/ext-apps {source.name} sha256:{hashlib.sha256(raw.encode()).hexdigest()}\n"
        f"   门面：tools/ext_apps_facade.js  版本：{VIEW_VERSION}\n"
        "   MCP Apps View 侧 bundle，仅经 server 资源 ui://pptx-html-bridge/editor.html 注入 */\n"
    )
    return banner + strip_export(raw) + "\n" + facade


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    ap.add_argument("--check", action="store_true", help="只校验产物是否最新，不写盘")
    args = ap.parse_args()
    if not args.source.exists():
        raise SystemExit(f"找不到官方 bundle：{args.source}（用 --source 指定）")
    bundle = build(args.source)
    digest = hashlib.sha256(bundle.encode()).hexdigest()
    manifest = {
        "generated_by": "tools/build_ext_apps_bundle.py",
        "view_version": VIEW_VERSION,
        "source": str(args.source),
        "source_sha256": hashlib.sha256(args.source.read_bytes()).hexdigest(),
        "bundle_sha256": digest,
        "bundle_bytes": len(bundle.encode()),
        "inject": "script-module",
    }
    if args.check:
        current = OUTPUT.read_text(encoding="utf-8") if OUTPUT.exists() else ""
        ok = current == bundle and MANIFEST.exists() and json.loads(MANIFEST.read_text())["bundle_sha256"] == digest
        print(("OK " if ok else "STALE ") + f"bundle sha256={digest} bytes={manifest['bundle_bytes']}")
        return 0 if ok else 1
    OUTPUT.write_text(bundle, encoding="utf-8")
    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {OUTPUT.relative_to(ROOT)} sha256={digest} bytes={manifest['bundle_bytes']}")
    print(f"wrote {MANIFEST.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
