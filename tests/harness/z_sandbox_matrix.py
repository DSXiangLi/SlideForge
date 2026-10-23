#!/usr/bin/env python3
"""MCP Apps 沙箱能力矩阵实测 —— 证据工具，非回归项。

用途：回答"editor.html 在 MCP Apps 宿主沙箱里还剩哪些能力"，为
`docs/design/mcp-apps-upgrade.md` §1.2 / §2.4 的判定提供可复现证据。

本脚本复刻 SproutHarness（自研框架 `feature/mcp-apps` 分支）的确切宿主配置：
  - src/sprout_harness/agent/webui.html:2052  iframe.sandbox = 'allow-scripts'
  - src/sprout_harness/mcp/sandbox.py:107     build_csp_header({}) 无 csp 声明时的默认值
  - src/sprout_harness/agent/server.py:2628   GET /mcp-sandbox/{id} -> HTML + CSP header

对照臂：同一 widget 同时跑在 `allow-scripts`（宿主现状）与
`allow-scripts allow-same-origin`（官方规范 `apps.mdx:470-476` 要求）两种 sandbox 下，
差异即"宿主偏离规范"造成的额外约束。

依赖 Playwright + Chromium（与其它 harness 检查一致）。
**不纳入 `run_e2e.py`**：本脚本只输出矩阵供人读与文档引用，不设 pass/fail 断言。

用法：`python3 tests/harness/z_sandbox_matrix.py [--json <out.json>]`
"""
import http.server
import argparse
import json
import os
import socketserver
import sys
import threading

from playwright.sync_api import sync_playwright

PORT = 8765
BASE = f"http://127.0.0.1:{PORT}"
RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")

# Exactly what build_csp_header({}) returns for a resource that declares no CSP domains.
CSP = "; ".join([
    "default-src 'self' 'unsafe-inline'",
    "script-src 'self' 'unsafe-inline' 'unsafe-eval' blob: data:",
    "style-src 'self' 'unsafe-inline' blob: data:",
    "img-src 'self' data: blob:",
    "font-src 'self' data: blob:",
    "connect-src 'self'",
    "frame-src 'none'",
    "object-src 'none'",
    "base-uri 'none'",
])

PIXEL = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000a49444154789c6300010000050001"
    "0d0a2db40000000049454e44ae426082"
)

WIDGET = """<!DOCTYPE html><html><head><meta charset="utf-8"><style>body{font:12px sans-serif}</style></head>
<body><p id="p">probe</p>
<script>
const results = {};
const violations = [];
document.addEventListener('securitypolicyviolation', e => {
  violations.push({blockedURI: e.blockedURI, directive: e.violatedDirective});
});
function rec(name, fn) {
  try { const v = fn(); results[name] = (v === undefined) ? 'ok(undefined)' : v; }
  catch (e) { results[name] = 'THROW: ' + e.name + ': ' + String(e.message).slice(0, 80); }
}
rec('origin', () => String(window.origin));
rec('localStorage.setItem', () => { localStorage.setItem('k', '1'); return localStorage.getItem('k'); });
rec('sessionStorage.setItem', () => { sessionStorage.setItem('k', '1'); return 'ok'; });
rec('indexedDB.open', () => { indexedDB.open('db', 1); return 'called'; });
rec('document.cookie', () => { document.cookie = 'a=1'; return document.cookie === '' ? 'empty' : document.cookie; });
rec('crypto.randomUUID', () => crypto.randomUUID().slice(0, 8));
rec('crypto.getRandomValues', () => { const a = new Uint8Array(2); crypto.getRandomValues(a); return 'ok'; });
rec('crypto.subtle.digest', () => crypto.subtle ? 'present' : 'absent');
rec('navigator.clipboard', () => navigator.clipboard ? 'present' : 'absent');
rec('showSaveFilePicker', () => typeof window.showSaveFilePicker);
rec('showOpenFilePicker', () => typeof window.showOpenFilePicker);
rec('window.open', () => { const w = window.open('about:blank'); if (w) { w.close(); return 'opened'; } return 'BLOCKED(null)'; });
rec('document.domain', () => { document.domain = 'x'; return 'set ok'; });
rec('history.replaceState', () => { history.replaceState(null, '', '#hash'); return 'ok'; });
rec('location.hash', () => location.hash);
rec('eval', () => String(eval('1+1')));
rec('new Function', () => String(new Function('return 3')()));
rec('URL.createObjectURL', () => { const u = URL.createObjectURL(new Blob(['x'])); return u.slice(0, 5); });
rec('Worker(blobURL)', () => { const u = URL.createObjectURL(new Blob(['self.postMessage(1)'], {type:'text/javascript'})); new Worker(u); return 'constructed'; });
rec('iframe.srcdoc(create)', () => { const f = document.createElement('iframe'); f.srcdoc = '<p>n</p>'; document.body.appendChild(f); return 'appended'; });
rec('iframe.src(about:blank)', () => { const f = document.createElement('iframe'); f.src = 'about:blank'; document.body.appendChild(f); return 'appended'; });
rec('img data:URI', () => { const i = new Image(); i.src = 'data:image/png;base64,iVBORw0KGgo='; document.body.appendChild(i); return 'appended'; });
rec('img blob:URI', () => { const i = new Image(); i.src = URL.createObjectURL(new Blob([new Uint8Array([1])])); document.body.appendChild(i); return 'appended'; });
rec('link rel=stylesheet rel', () => { const l = document.createElement('link'); l.rel='stylesheet'; l.href='/assets/x.css'; document.head.appendChild(l); return 'appended'; });
rec('script src relative', () => { const s = document.createElement('script'); s.src='/assets/x.js'; document.body.appendChild(s); return 'appended'; });

// async probes
const async_out = {};
function arec(name, p) { return Promise.resolve(p).then(
  () => { async_out[name] = 'OK'; }, e => { async_out[name] = 'FAIL: ' + String(e.message || e).slice(0, 90); }); }
const tasks = [
  arec('fetch relative /assets/pixel.png', fetch('/assets/pixel.png').then(r => { if (!r.ok) throw new Error('http '+r.status); })),
  arec('fetch data:url', fetch('data:text/plain,hi')),
  arec('fetch absolute same-origin', fetch(location.origin + '/assets/pixel.png').then(r => { if (!r.ok) throw new Error('http '+r.status); })),
  arec('sendBeacon relative', Promise.resolve().then(() => { if (!navigator.sendBeacon || !navigator.sendBeacon('/beacon', 'x')) throw new Error('returned false'); })),
  arec('img relative load', new Promise((res, rej) => { const i = new Image(); i.onload = () => res(); i.onerror = () => rej(new Error('onerror')); i.src = '/assets/pixel.png'; setTimeout(() => rej(new Error('timeout')), 2000); })),
  arec('srcdoc iframe load', new Promise((res, rej) => { const f = document.createElement('iframe'); f.srcdoc = '<p>x</p>'; f.onload = () => res(); f.onerror = () => rej(new Error('onerror')); document.body.appendChild(f); setTimeout(() => rej(new Error('no load event (blocked)')), 2000); })),
  /* ⭐ 关键探针（设计 §10.10）：嵌套 srcdoc 能"加载"不等于父文档能"访问"它。
     编辑器把 deck 装进嵌套 iframe 后必须读写它的文档（就地编辑/批注/序列化），
     在不透明源（只有 allow-scripts）下 contentDocument 取不到 —— 这会直接决定轨 A 能否编辑。 */
  arec('nested srcdoc contentDocument', new Promise((res, rej) => {
    const f = document.createElement('iframe');
    f.srcdoc = '<!doctype html><html><body><p id="t">x</p></body></html>';
    f.onload = () => {
      try {
        const d = f.contentDocument;
        if (!d) return rej(new Error('contentDocument 为 null（不透明源不可访问）'));
        if (!d.getElementById('t')) return rej(new Error('读到了文档但取不到节点'));
        const w = f.contentWindow;
        if (!w || !w.document) return rej(new Error('contentWindow.document 不可用'));
        res();
      } catch (e) { rej(new Error('访问抛错：' + (e.message || e))); }
    };
    document.body.appendChild(f);
    setTimeout(() => rej(new Error('no load event')), 2000);
  })),
  arec('about:blank iframe load', new Promise((res, rej) => { const f = document.createElement('iframe'); f.src = 'about:blank'; f.onload = () => res(); document.body.appendChild(f); setTimeout(() => rej(new Error('no load event')), 2000); })),
  arec('a[download] click', new Promise((res, rej) => { try { const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob(['x'])); a.download = 'a.txt'; a.click(); res(); } catch (e) { rej(e); } })),
];
Promise.all(tasks).then(() => {
  results._async = async_out;
  results._violations = violations;
  parent.postMessage({__probe: JSON.parse(JSON.stringify(results))}, '*');
});
</script></body></html>"""

PARENT = """<!DOCTYPE html><html><body><div id="host"></div>
<script>
window.__RESULTS = {};
window.addEventListener('message', e => {
  if (e.data && e.data.__probe) { window.__RESULTS[e.data.__probe.origin || 'unknown'] = e.data.__probe; }
});
function spawn(sandbox) {
  const f = document.createElement('iframe');
  f.setAttribute('sandbox', sandbox);
  f.style.cssText = 'width:600px;height:400px';
  f.src = '/mcp-sandbox/widget';
  document.getElementById('host').appendChild(f);
}
setTimeout(() => { spawn('allow-scripts'); spawn('allow-scripts allow-same-origin'); }, 300);
</script></body></html>"""


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path.startswith("/mcp-sandbox/widget"):
            body = WIDGET.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Security-Policy", CSP)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/parent":
            body = PARENT.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path in ("/assets/pixel.png",):
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(PIXEL)))
            self.end_headers()
            self.wfile.write(PIXEL)
        elif self.path in ("/assets/x.css", "/assets/x.js"):
            body = b"/*x*/" if self.path.endswith(".css") else b"/*x*/"
            self.send_response(200)
            self.send_header("Content-Type", "text/css" if self.path.endswith(".css") else "text/javascript")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/beacon":
            self.send_response(204)
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()


def _verdict(value):
    """同步探针返回值 → 判定。注意：'present'/'function' 只说明 API 存在，
    在不透明源下并不代表可调用（实测 showSaveFilePicker 存在但受沙箱限制），
    故这类结果保留原文以便人工判读，不归入 OK。"""
    s = str(value)
    if s.startswith("THROW") or s.startswith("FAIL") or s == "BLOCKED(null)":
        return "BLOCKED"
    if s in ("present", "function"):
        return "EXISTS?"
    return "OK"


def _summary(results, sandbox_label):
    block = results.get(sandbox_label) or {}
    async_out = block.get("_async", {})
    rows = []
    for key in sorted(block):
        if key.startswith("_"):
            continue
        rows.append((key, _verdict(block[key]), str(block[key])[:70]))
    for key in sorted(async_out):
        verdict = _verdict(async_out[key])
        rows.append((key, verdict, str(async_out[key])[:70]))
    return rows


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="MCP Apps sandbox capability matrix probe")
    ap.add_argument("--json", dest="json_out", default=os.path.join(RESULTS_DIR, "z_sandbox_matrix.json"),
                    help="where to write the raw matrix (default: tests/harness/results/z_sandbox_matrix.json)")
    ap.add_argument("--wait-ms", type=int, default=6000, help="time to let async probes settle")
    args = ap.parse_args()

    socketserver.TCPServer.allow_reuse_address = True
    srv = socketserver.ThreadingTCPServer(("127.0.0.1", PORT), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            logs = []
            page.on("console", lambda m: logs.append(f"{m.type}: {m.text}"))
            page.on("pageerror", lambda e: logs.append(f"pageerror: {e}"))
            page.goto(f"{BASE}/parent")
            page.wait_for_timeout(args.wait_ms)
            results = page.evaluate("window.__RESULTS") or {}
            browser.close()
    finally:
        srv.shutdown()

    os.makedirs(os.path.dirname(args.json_out), exist_ok=True)
    with open(args.json_out, "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2, ensure_ascii=False)

    for label in ("null", f"http://127.0.0.1:{PORT}"):
        if label not in results:
            print(f"\n[missing] sandbox arm '{label}' produced no results")
            continue
        sandbox = "allow-scripts" if label == "null" else "allow-scripts allow-same-origin"
        print(f"\n=== sandbox={sandbox} (origin={label}) ===")
        for name, verdict, detail in _summary(results, label):
            print(f"  {verdict:8} {name:38} {detail}")

    print(f"\n--- console (first 40) ---")
    for line in logs[:40]:
        print(line)
    print(f"\nraw matrix written to {args.json_out}")
    sys.exit(0)
