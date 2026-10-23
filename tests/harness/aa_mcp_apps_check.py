#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MCP Apps 轨 A（View 第四态）端到端验收——宿主模拟器驱动。

为什么需要它：真实宿主（SproutHarness 分支未合并 / Claude Desktop 本机无法实测）
都不可用，因此本脚本自带一个宿主模拟器 `mcp_apps_host_sim.html`，复刻宿主的
**关键约束**（sandbox 只有 allow-scripts 的不透明源、宿主默认 CSP、两阶段拆卸、
工具经宿主代理）而不是复刻它的实现细节。产品侧被测对象是**真货**：
`tools/bridge_mcp.build_view_html()` 产出的 View HTML（editor.html + 官方 View SDK
bundle + window.pptxMcp 门面）与真实 daemon（BridgeCore 全套状态机）。

覆盖：
  ① 握手与轨道判定：View 内 window.pptxMcp 存在 → hostKindDetect 走轨 A →
     ui/initialize 握手成功 → 宿主收到 initialized；
  ② 会话下发：宿主发 ui/notifications/tool-result（open_editor 结果文本）→ View
     自动 attach_view → get_status → read_deck → 渲染 deck；daemon 侧 track=mcp-app；
  ③ 保存：View 内改文字后 saveDeck() → save_deck（CAS + receipt）→ 目标文件与
     revision 变化；
  ④ 草稿：脏状态触发防抖 save_draft → /api/bridge/drafts 能查到；
  ⑤ 便条：防抖 2s 后 setModelContext → 宿主收到"编辑器状态镜"；
  ⑥ 两阶段拆卸：宿主请求 ui/resource-teardown → View 先落草稿再回执，宿主 ≤5s 收到；
  ⑦ 负例臂：宿主默认沙箱（只有 allow-scripts，即 allow_same_origin:false）时**明确报错并给处置指引**——按官方规范
     开发（用户决策），不提供只读降级模式，也不静默装成可编辑。
  ⑧ 首屏分流（brief-page-split §10 #1–#13）：`open_editor(view=…)` 真正下发后，无 deck 恒落脑暴、
     有 deck + `view=brief` 直达脑暴（S3 回归）、`edit`/`annotate`/`export` 各落对应 mode/页签、
     脑暴视图整屏且工作台 chrome 隐藏、`tool-input`/`tool-result` 不打架（含门面缓冲重放）、
     Esc/✕ 关闭解除标记、`get_status` 轮询不翻回视图、高度上报自愈、注入 brief_options 动态渲染；
     **症状类断言两臂都跑**（受信 + 受限沙箱），另用裸静态态与嵌入态断言"无 session 的两态不参与分流"
     （#11，静态/嵌入 DOM 断言即可，不新建宿主臂）。
"""

from __future__ import annotations

import base64
import contextlib
import http.server
import json
import os
import socketserver
import sys
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from tools.bridge_core import admin_request  # noqa: E402
from tools.bridge_dispatch import build_request  # noqa: E402
from tests.harness.s_bridge_scale_check import (  # noqa: E402
    Daemon, bind_browser_token, check, managed_post, one_request,
)

PNG_1PX = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFAAH/q842iQAAAABJRU5ErkJggg==")

DECK = ('<!doctype html><html><head><meta charset="utf-8"><title>轨 A 验收</title>'
        '<style>@font-face{font-family:"HarnessSub";src:url("fonts/harness.woff2") format("woff2")}'
        '.hf{font-family:"HarnessSub"}</style></head><body>'
        '<section class="slide" data-slide-id="s1"><h1 data-editable>桥接首屏</h1>'
        '<img src="assets/pixel.png" data-image-slot="pixel-1x1" data-image-intent="测试像素" '
        'data-image-state="placeholder"></section>'
        '<section class="slide" data-slide-id="s2"><h2 data-editable>第二节</h2></section>'
        '</body></html>')

# 字体夹具：@font-face 的 url() 在轨 A 也必须水合成 data:（A4），内容不参与渲染断言
FONT_BYTES = b"wOF2" + b"\x00" * 60


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


@contextlib.contextmanager
def static_server(directory: Path):
    handler = lambda *a, **kw: QuietHandler(*a, directory=str(directory), **kw)  # noqa: E731
    with socketserver.TCPServer(("127.0.0.1", 0), handler) as httpd:
        httpd.allow_reuse_address = True
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        try:
            yield f"http://127.0.0.1:{httpd.server_address[1]}"
        finally:
            httpd.shutdown()


def find_view_frame(page):
    """View 是模拟页里的第一个 srcdoc iframe；用内联脚本的函数名识别，别靠顺序猜。"""
    deadline = time.time() + 20
    while time.time() < deadline:
        for frame in page.frames:
            if frame == page.main_frame:
                continue
            try:
                if frame.evaluate("() => typeof saveDeck === 'function' && !!window.hostKindDetect"):
                    return frame
            except Exception:
                continue
        page.wait_for_timeout(200)
    raise AssertionError("找不到 View frame（editor.html 未在 iframe 内启动？）")


def wait_for(fn, timeout=15, interval=0.2, what="条件"):
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        try:
            last = fn()
            if last:
                return last
        except Exception as exc:  # noqa: BLE001 - 轮询期间的异常要继续等
            last = exc
        time.sleep(interval)
    raise AssertionError(f"等待超时（{timeout}s）：{what}；最后结果={last!r}")


MODEL_TOOL_ROUTES = {
    # 五个面向模型的工具也经宿主代理到达（设计 §4.3：View 轮询走 get_status）。
    # 真实宿主把 tools/call 转发给 MCP server；harness 里由本代理直接落 daemon 路由，
    # 语义等价（同一 accept/status 实现），只是少了一层 stdio。
    "get_status": "POST /api/bridge/status",
    "open_editor": "POST /api/bridge/open",
    "await_intent": "POST /api/bridge/await",
    "push_update": "POST /api/bridge/update",
    "close_session": "POST /api/bridge/close",
}


def make_tool_proxy(discovery):
    def proxy(name, args_json):
        args = json.loads(args_json or "{}")
        if name in MODEL_TOOL_ROUTES:
            method, path = MODEL_TOOL_ROUTES[name].split(" ", 1)
            try:
                return json.dumps(admin_request(discovery, path, args if method == "POST" else None, 120),
                                  ensure_ascii=False)
            except Exception as exc:  # BridgeError
                payload = exc.payload() if hasattr(exc, "payload") else {
                    "ok": False, "error": {"code": "STORAGE_UNAVAILABLE", "message": str(exc)}}
                return "Error executing tool %s: %s" % (name, json.dumps(payload, ensure_ascii=False))
        try:
            _method, path, body = build_request(name, args, owned_sessions=None)
        except Exception as exc:  # DispatchError
            return "Error executing tool %s: %s" % (name, json.dumps(
                {"ok": False, "error": {"code": "INVALID_ARGUMENT", "message": str(exc)}}, ensure_ascii=False))
        try:
            return json.dumps(admin_request(discovery, path, body, 120), ensure_ascii=False)
        except Exception as exc:  # BridgeError
            payload = exc.payload() if hasattr(exc, "payload") else {
                "ok": False, "error": {"code": "STORAGE_UNAVAILABLE", "message": str(exc)}}
            return "Error executing tool %s: %s" % (name, json.dumps(payload, ensure_ascii=False))
    return proxy


def run_trusted_arm(base, page, daemon, opened, work, discovery, browser_token, rel="view.html"):
    """受信沙箱臂（`allow-scripts allow-same-origin`，对应宿主 `mcp.apps.allow_same_origin: true`）：
    轨 A 的完整能力都应成立——这是**宿主开启该配置后的预期形态**。"""
    page.goto(base + f"/mcp_apps_host_sim.html?view={rel}&sandbox=trusted")
    check(page.evaluate("() => window.hostSim.errors") == [], "宿主模拟器自身报错")
    wait_for(lambda: page.evaluate("() => window.hostSim.state") == "initialized", what="View 完成 ui/initialize 握手")
    frame = find_view_frame(page)
    check(frame.evaluate("() => window.hostBridge && window.hostBridge.kind") == "mcp-app",
          "View 未判定为 mcp-app 态（门面没被 hostKindDetect 看到？）")

    page.evaluate("payload => window.hostSim.sendToolResult(payload)", opened)
    chain = lambda: [c["name"] for c in page.evaluate("() => window.hostSim.toolCalls")]  # noqa: E731
    wait_for(lambda: "read_deck" in chain(), what="View 调 read_deck")
    seq = chain()
    check(seq.index("attach_view") < seq.index("get_status") < seq.index("read_deck"),
          f"附着序列不符合设计（attach→status→read）: {seq}")
    wait_for(lambda: frame.evaluate(
        "() => { var d = doc(); return !!(d && d.body && d.body.textContent.indexOf('桥接首屏') >= 0); }"),
        what="deck 在 View 内可读")
    page.evaluate("payload => window.hostSim.toolCalls = []", None)
    status = managed_post(daemon, "/api/bridge/status", {"session_id": opened["session_id"]})
    check(status["track"] == "mcp-app" and status["view_attached"] is True,
          f"daemon 侧轨道判定错: track={status['track']} view_attached={status['view_attached']}")

    # A2 · 高度上报：官方 SDK 的 autoResize 会按文档自身尺寸自动发 size-changed（可能被宿主钳制），
    # 编辑器还要**明确请求**宿主 hostContext.containerDimensions.maxHeight=1200 这一档。
    # 断言"出现 1200 这一档"而不是"最后一条是 1200"：autoResize 的重报时机不保证顺序。
    wait_for(lambda: page.evaluate("() => (window.hostSim.sizes || []).length > 0"), what="View 上报 size-changed")
    sizes = page.evaluate("() => window.hostSim.sizes")
    check(any(s.get("height") == 1200 for s in sizes), f"未按宿主 maxHeight 上报高度: {sizes}")

    # A1 · 工具错误码：FastMCP 给错误加的是散文前缀，门面剥前缀后必须仍还原 error.code
    err = frame.evaluate("""async () => {
      try { await window.pptxMcp.callTool('read_asset', {session_id: mcpApp.sessionId, path: 'etc/passwd'}); return {code:'NO_ERROR'}; }
      catch(e){ return {code: e.code || null, message: e.message}; }
    }""")
    check(err.get("code") == "INVALID_ARGUMENT", f"带前缀的 ToolError 未还原出 error.code: {err}")
    check("Error executing tool" not in (err.get("message") or ""), f"错误消息仍带 SDK 前缀: {err}")

    # A4 · CSS 资产水合：@font-face 的 url() 在轨 A 必须变成 data: URI
    wait_for(lambda: frame.evaluate("""() => {
        var d = doc(); if (!d) return false;
        var sheets = d.styleSheets || [];
        for (var i = 0; i < sheets.length; i++){
          var rules = [];
          try { rules = sheets[i].cssRules || []; } catch(e){ continue; }
          for (var j = 0; j < rules.length; j++){
            if (rules[j].style && (rules[j].style.getPropertyValue('src') || '').indexOf('data:') >= 0) return true;
          }
        }
        return false;
      }"""), what="deck 的 @font-face 被水合成 data: URI")

    # 保存：改文字 → saveDeck() → save_deck（CAS + receipt）→ 目标文件与 revision 变化
    before = status["revision"]
    frame.evaluate("""() => {
      var d = doc(); var h = d.querySelector('[data-editable]');
      h.textContent = '桥接首屏（已改）'; setDirty(true); return true;
    }""")
    frame.evaluate("() => saveDeck()")
    after = wait_for(lambda: managed_post(daemon, "/api/bridge/status", {"session_id": opened["session_id"]})["revision"],
                     what="保存后 revision 前进")
    check(after != before, "save_deck 未推进 revision")
    check("save_deck" in chain(), f"未走 save_deck 通道: {chain()}")
    saved_text = (work / "index.html").read_text(encoding="utf-8")
    check("桥接首屏（已改）" in saved_text, "目标 deck 未写入 View 的修改")
    check("data:image" not in saved_text, "保存产物里出现 data: URI（水合没还原成 assets/ 相对路径）")
    check("data:font" not in saved_text and 'url("fonts/harness.woff2")' in saved_text,
          "CSS 水合没有还原成 fonts/ 相对路径")

    # 草稿：脏状态 → 防抖 save_draft → 服务端可查（/api/bridge/drafts 是 GET + query）
    frame.evaluate("() => setDirty(true)")
    wait_for(lambda: "save_draft" in chain(), what="防抖 save_draft")
    # /api/bridge/drafts 是 browser 凭证路由（管理凭证只用在该轨工具面上）
    drafts = json.loads(one_request(discovery["origin"], "/api/bridge/drafts?session_id=" + opened["session_id"],
                                    bearer=browser_token, origin_header=discovery["origin"])[1] and
                        json.dumps(one_request(discovery["origin"], "/api/bridge/drafts?session_id=" + opened["session_id"],
                                               bearer=browser_token, origin_header=discovery["origin"])[1]))
    check(drafts["items"], f"服务端草稿为空: {drafts}")

    # 便条：防抖 2s → setModelContext（状态镜）
    notes = wait_for(lambda: page.evaluate("() => window.hostSim.modelContext"), timeout=10, what="便条 setModelContext")
    check("编辑器状态镜" in json.dumps(notes, ensure_ascii=False), f"便条内容不符: {str(notes)[:200]}")

    # 两阶段拆卸：View 必须先落草稿再回执（≤5s）
    before_calls = len(chain())
    check(page.evaluate("() => window.hostSim.requestTeardown()"), "宿主拆卸请求未收到回执")
    check(page.evaluate("() => window.hostSim.state") == "torn-down", "拆卸后宿主状态未推进")
    check("save_draft" in chain()[before_calls:], f"拆卸前未 flush 草稿: {chain()[before_calls:]}")


# ============================================================
# 首屏分流（P1，docs/design/brief-page-split.md §10）：T36 的 #1–#13。
# 每换一个**会话类型**就换一份 daemon + workdir——`register_session` 对同一
# target_path 是**直接复用已有会话**（不是报错），所以"无 deck"会话必须自己占一个
# 干净 workdir（里面不能有 index.html），否则会复用出有 deck 的会话、断言全部失真。
# ============================================================

# 轨 A 的动态脑暴注入（§10 #6 / §9）：形状与 T35a 的 options_v1 同源，值加 T36 标记以便断言。
BRIEF_OPTIONS = {
    "version": 2,
    "kind": "brief-options",
    "context_summary": "T36 验收·宿主内动态脑暴",
    "profile": {"signals": ["t36-marker"]},
    "groups": [
        {"id": "scene", "title": "使用场景", "impact": "决定密度与动效锚点", "state": "ask", "multi": False,
         "options": [
             {"id": "present", "label": "T36 动态场景·登台述职", "desc": "限时讲完，结论先行",
              "recommended": True, "reason": "T36 注入"},
             {"id": "asyncread", "label": "T36 动态场景·会后自读", "desc": "阅读分发形态", "default": True}]},
        {"id": "audience", "title": "受众", "impact": "影响语言深度", "state": "prefilled",
         "prefill_reason": "T36 注入", "multi": False,
         "options": [
             {"id": "exec", "label": "T36 动态受众·投委会", "desc": "结论先行", "recommended": True,
              "reason": "T36 注入"},
             {"id": "ops", "label": "T36 动态受众·一线运营", "desc": "执行细节", "default": True}]},
    ],
}

# View 内的未捕获异常：Playwright 的 pageerror 只报**宿主页**，sandboxed srcdoc iframe
# （View 本身）里的异常要靠帧内收集器（§10 #12）。
FRAME_ERROR_COLLECTOR = (
    "window.__frameErrors = [];"
    "window.addEventListener('error', function(e){ window.__frameErrors.push(String((e && e.message) || e)); });"
    "window.addEventListener('unhandledrejection',"
    " function(e){ window.__frameErrors.push('unhandledrejection: ' + String((e && e.reason) || e)); });")

LAUNCH_PROBE = """() => {
  const overlay = document.getElementById('briefOverlay');
  const rect = overlay.getBoundingClientRect();
  const hit = document.elementFromPoint(Math.round(window.innerWidth / 2), Math.round(window.innerHeight / 2));
  const box = id => { const n = document.getElementById(id); return n ? Math.round(n.getBoundingClientRect().height) : -1; };
  const header = document.querySelector('body > header'), footer = document.querySelector('body > footer');
  return { launch: document.body.getAttribute('data-launch'),
           overlayShown: overlay.classList.contains('show'),
           coversViewport: rect.width >= window.innerWidth - 2 && rect.height >= window.innerHeight - 2,
           centerInOverlay: !!(hit && overlay.contains(hit)),
           headerH: header ? Math.round(header.getBoundingClientRect().height) : -1,
           footerH: footer ? Math.round(footer.getBoundingClientRect().height) : -1,
           barH: box('bridgeBar'), barShown: document.getElementById('bridgeBar').classList.contains('show'),
           view: typeof view === 'string' ? view : null,
           mode: typeof mode === 'string' ? mode : null,
           applied: typeof launch === 'object' && launch ? launch.applied : null,
           exportHidden: document.getElementById('exportView').hidden,
           annoPanel: document.getElementById('annoPanel').classList.contains('show'),
           deckText: (function(){ var d = doc(); return !!(d && d.body && d.body.textContent.indexOf('桥接首屏') >= 0); })(),
           frameErrors: window.__frameErrors || null };
}"""


def split_workdir(root, name, deck=None):
    """一个会话一个 workdir：有 deck 的场景把 index.html 落盘，无 deck 的场景**不能有**它。"""
    work = root / "split" / name
    work.mkdir(parents=True)
    (work / "assets").mkdir()
    (work / "assets" / "pixel.png").write_bytes(PNG_1PX)
    if deck is not None:
        (work / "index.html").write_text(deck, encoding="utf-8")
    return work


def open_split(daemon, work, *, view="__absent__", with_deck=True, brief_options="__absent__", consumer="split-harness"):
    body = {"consumer_id": consumer,
            "deck_path": str(work / "index.html") if with_deck else None,
            "output_path": "index.html", "open_browser": False}
    if view != "__absent__":
        body["view"] = view
    if brief_options != "__absent__":
        body["brief_options"] = brief_options
    return managed_post(daemon, "/api/bridge/open", body)


class ViewPage:
    """宿主模拟器里装载 View 的一页：驱动 tool-input / tool-result 并读取帧内状态。"""

    def __init__(self, browser, base, discovery, sandbox="trusted", view_rel="view.html"):
        self.page = browser.new_page()
        self.errors = []
        self.page.on("pageerror", lambda e: self.errors.append(str(e)))
        self.page.add_init_script(FRAME_ERROR_COLLECTOR)
        self.page.expose_function("mcpCall", make_tool_proxy(discovery))
        self.page.goto(base + f"/mcp_apps_host_sim.html?view={view_rel}&sandbox={sandbox}")
        wait_for(lambda: self.page.evaluate("() => window.hostSim.state") == "initialized", what="View 完成 ui/initialize 握手")
        check(self.page.evaluate("() => window.hostSim.errors") == [], "宿主模拟器自身报错")
        self.frame = find_view_frame(self.page)

    def result(self, payload):
        self.page.evaluate("payload => window.hostSim.sendToolResult(payload)", payload)

    def input(self, args):
        self.page.evaluate("args => window.hostSim.sendToolInput(args)", args)

    def state(self):
        return self.frame.evaluate(LAUNCH_PROBE)

    def wait_state(self, predicate, what, timeout=15):
        return wait_for(lambda: (lambda st: st if predicate(st) else None)(self.state()), timeout=timeout, what=what)

    def wait_launch(self, value, what, timeout=15):
        return self.wait_state(lambda st: st["launch"] == value, what, timeout=timeout)

    def chain(self):
        return [c["name"] for c in self.page.evaluate("() => window.hostSim.toolCalls")]

    def sizes(self):
        return self.page.evaluate("() => window.hostSim.sizes")

    def assert_clean(self, label):
        st = self.state()
        check(self.errors == [] and (st["frameErrors"] or []) == [],
              f"{label}：隐藏态/运行期出现 JS 报错（AGENTS.md 框架 null 检查红线）—— host={self.errors} view={st['frameErrors']}")

    def close(self):
        # 关闭前先掐掉帧内的定时器（2s get_status 轮询 / 草稿与便条防抖 / 高度去抖）：
        # 否则在途的工具调用会在页面关闭瞬间变成 Playwright 的 TargetClosedError 噪声。
        with contextlib.suppress(Exception):
            self.frame.evaluate("""() => {
              if (typeof mcpAppStopPoll === 'function') mcpAppStopPoll();
              clearTimeout(mcpApp.draftTimer); clearTimeout(mcpApp.noteTimer); clearTimeout(mcpApp.sizeTimer);
              if (mcpApp.sizeObserver) { try { mcpApp.sizeObserver.disconnect(); } catch (e) {} }
            }""")
        # 再等一拍让在途的工具调用应答落定，避免关闭瞬间弃掉 Playwright 的 binding 回执
        self.page.wait_for_timeout(200)
        self.page.close()


def discover(work):
    return json.loads((work / ".pptx-html" / "serve.json").read_text(encoding="utf-8"))


def run_launch_split_trusted_arm(browser, base, root):
    """受信沙箱臂（宿主 `mcp.apps.allow_same_origin: true`）的首屏分流全集（§10 #1–#10、#12、#13）。"""
    # ---------- 会话类型 1：无 deck（#1 / #5a / #6 / #12） ----------
    work = split_workdir(root, "none")
    with Daemon(work) as daemon:
        discovery = discover(work)
        # #1 + #6：view="brief" + 无 deck，并注入 brief_options（轨 A 的动态脑暴修复，§9）
        opened = open_split(daemon, work, view="brief", with_deck=False, brief_options=BRIEF_OPTIONS)
        check(opened["view"] == "brief", f"open_editor 未回显 view=brief: {opened['view']!r}")
        view = ViewPage(browser, base, discovery)
        try:
            view.result(opened)
            st = view.wait_launch("brief", "无 deck + view=brief 落脑暴视图")
            check(st["overlayShown"], f"脑暴视图未显示: {st}")
            check(st["coversViewport"], f"脑暴仍是抽屉而非整屏视图（§7.2 几何改写缺失）: {st}")
            check(st["centerInOverlay"], f"视口中心不在脑暴层内（工作台没被盖住）: {st}")
            check(st["headerH"] == 0 and st["footerH"] == 0 and st["barH"] == 0,
                  f"脑暴视图下工作台 chrome 仍可见（header/footer/桥栏）: {st}")
            body = lambda: view.frame.evaluate("() => document.getElementById('briefBody').innerText")  # noqa: E731
            wait_for(lambda: "T36 动态场景·登台述职" in body(), what="轨 A 动态脑暴渲染（brief_options 注入）")
            check(view.frame.evaluate("() => !!document.querySelector('#briefBody .brief-profile')"),
                  "注入 brief_options 后没有画像卡（轨 A 动态脑暴没生效）")
            check("T36 验收·宿主内动态脑暴" in body(), f"注入的 context_summary 未渲染: {body()[:200]}")
            view.assert_clean("#1/#6")
        finally:
            view.close()
        # #5a：**不传 view**（MCP 层缺省 "edit"）→ 无 deck 仍须落脑暴，否则新建任务首开退化成空工作台
        default_opened = open_split(daemon, work, with_deck=False)
        check(default_opened["view"] == "edit", f"缺省 view 不是 edit: {default_opened['view']!r}")
        view = ViewPage(browser, base, discovery)
        try:
            view.result(default_opened)
            st = view.wait_launch("brief", "无 deck + 不传 view 落脑暴视图（§7.1 缺省规则）")
            check(st["headerH"] == 0 and st["centerInOverlay"], f"缺省路径未隐藏工作台: {st}")
            view.assert_clean("#5a")
        finally:
            view.close()
        managed_post(daemon, "/api/bridge/stop", {"reason": "cli-stop"})

    # ---------- 会话类型 2：有 deck（#2/#3/#4/#5b/#7/#8/#9/#10/#12/#13） ----------
    work = split_workdir(root, "deck", deck=DECK)
    with Daemon(work) as daemon:
        discovery = discover(work)

        # #2 + #10 + #13：view="brief" + **有 deck**（用户报告的 S3）——首屏分流不得短路 deck 加载
        opened = open_split(daemon, work, view="brief")
        view = ViewPage(browser, base, discovery)
        try:
            view.result(opened)
            st = view.wait_launch("brief", "有 deck + view=brief 落脑暴视图（S3 回归）")
            check(st["overlayShown"] and st["coversViewport"] and st["centerInOverlay"],
                  f"有 deck 时脑暴不是整屏视图: {st}")
            check(st["headerH"] == 0 and st["footerH"] == 0 and st["barH"] == 0,
                  f"有 deck 时脑暴视图下工作台 chrome 仍可见: {st}")
            wait_for(lambda: "read_deck" in view.chain(), what="脑暴视图下仍调 read_deck（#10）")
            wait_for(lambda: view.state()["deckText"], what="脑暴视图下 deck 仍被载入（#10）")
            # #13：2s 轮询 get_status 不得把视图翻回去（验证"view 不落库"这一关键决定）
            polls = view.chain().count("get_status")
            view.page.wait_for_timeout(5000)
            check(view.chain().count("get_status") > polls, "等待期内没有发生 get_status 轮询，#13 前提不成立")
            st = view.state()
            check(st["launch"] == "brief" and st["coversViewport"] and st["centerInOverlay"],
                  f"get_status 轮询把视图翻回去了: {st}")
            view.assert_clean("#2/#10/#13")
        finally:
            view.close()

        # #7 + #9：关闭脑暴（Esc）→ 标记清除、工作台恢复可见、已载入 deck 仍在；高度上报自愈
        opened = open_split(daemon, work, view="brief")
        view = ViewPage(browser, base, discovery)
        try:
            view.result(opened)
            view.wait_launch("brief", "Esc 用例的脑暴视图")
            wait_for(lambda: view.state()["deckText"], what="Esc 用例的 deck 载入")
            # 高度上报稳定到宿主编制内的最高档（模拟器 maxHeight=1200）后再关，才能证明"重发同值"
            wait_for(lambda: bool(view.sizes()) and view.sizes()[-1]["height"] == 1200,
                     what="高度上报稳定在宿主 maxHeight")
            reports = len(view.sizes())
            view.frame.click(".brief-head h2")      # 先让 View 帧取得焦点，Esc 才落到它的 window 上
            view.page.keyboard.press("Escape")
            view.wait_launch(None, "Esc 解除 data-launch")
            st = view.state()
            check(not st["overlayShown"] and not st["centerInOverlay"], f"Esc 后脑暴层仍盖住工作台: {st}")
            check(st["headerH"] > 0 and st["footerH"] > 0, f"Esc 后工作台 chrome 未恢复可见: {st}")
            check(st["deckText"], "Esc 后已载入的 deck 丢失")
            wait_for(lambda: len(view.sizes()) > reports, what="视图切换后重新上报高度（§7.2 reportedHeight 重置）")
            check(view.sizes()[-1]["height"] >= 1000, f"恢复后的高度上报过小: {view.sizes()}")
            view.assert_clean("#7/#9 Esc")
        finally:
            view.close()

        # #7（✕ 一次）：关闭入口不同、后果必须相同（closeBrief 共用；标记不清就是白屏，评审硬错误 #3）
        opened = open_split(daemon, work, view="brief")
        view = ViewPage(browser, base, discovery)
        try:
            view.result(opened)
            view.wait_launch("brief", "✕ 用例的脑暴视图")
            wait_for(lambda: view.state()["deckText"], what="✕ 用例的 deck 载入")
            view.frame.evaluate("() => document.getElementById('btnBriefClose').click()")
            view.wait_launch(None, "✕ 解除 data-launch")
            st = view.state()
            check(not st["overlayShown"] and st["headerH"] > 0 and st["deckText"], f"✕ 关闭后未回到工作台: {st}")
            view.assert_clean("#7 ✕")
        finally:
            view.close()

        # #3：view="edit" + 有 deck → 工作台（不误入脑暴）
        opened = open_split(daemon, work, view="edit")
        view = ViewPage(browser, base, discovery)
        try:
            view.result(opened)
            wait_for(lambda: view.state()["deckText"], what="edit 落点的 deck 载入")
            st = view.wait_state(lambda s: s["applied"] == "edit", "view=edit 落工作台（launch 分流的落点）")
            check(st["launch"] is None and not st["overlayShown"] and st["headerH"] > 0,
                  f"view=edit 误入脑暴视图: {st}")
            check(st["view"] == "edit" and st["exportHidden"] is True, f"view=edit 未落在编辑页签: {st}")
            view.assert_clean("#3")
        finally:
            view.close()

        # #4a：view="annotate" → §7.3 一入两出（内部 view=edit + mode=annotate）
        opened = open_split(daemon, work, view="annotate")
        view = ViewPage(browser, base, discovery)
        try:
            view.result(opened)
            st = view.wait_state(lambda s: s["mode"] == "annotate", "view=annotate 落批注模式")
            check(st["annoPanel"] and st["view"] == "edit" and st["launch"] is None and st["headerH"] > 0,
                  f"annotate 落点不对（应在 edit 视图 + annotate 模式）: {st}")
            view.assert_clean("#4a")
        finally:
            view.close()

        # #4b：view="export" → 内部 view=export（工作台可见，非脑暴视图）
        opened = open_split(daemon, work, view="export")
        view = ViewPage(browser, base, discovery)
        try:
            view.result(opened)
            st = view.wait_state(lambda s: s["view"] == "export", "view=export 落导出页签")
            check(st["exportHidden"] is False and st["launch"] is None and st["headerH"] > 0,
                  f"export 落点不对: {st}")
            view.assert_clean("#4b")
        finally:
            view.close()

        # #5b：**不传 view** + 有 deck → 工作台（缺省路径的另一半；无 deck 的另一半在上面）
        opened = open_split(daemon, work)
        check(opened["view"] == "edit", f"缺省 view 不是 edit: {opened['view']!r}")
        view = ViewPage(browser, base, discovery)
        try:
            view.result(opened)
            wait_for(lambda: view.state()["deckText"], what="缺省路径的 deck 载入")
            st = view.wait_state(lambda s: s["applied"] == "edit", "有 deck + 不传 view 落工作台")
            check(st["launch"] is None and st["headerH"] > 0 and not st["overlayShown"], f"缺省路径误隐藏工作台: {st}")
            view.assert_clean("#5b")
        finally:
            view.close()

        # #8：tool-input 与 tool-result 不打架（C7）——门面缓冲重放 + §6 取值优先级
        opened = open_split(daemon, work, view="annotate")
        view = ViewPage(browser, base, discovery)
        try:
            # (a) 注册前到达的 tool-input 必须被门面缓冲、注册时重放（否则 C7 的丢消息窗口会吃掉它）
            view.frame.evaluate("() => { window.__inputHandler = window.pptxMcp.__toolInput; window.pptxMcp.__toolInput = null; }")
            check(view.frame.evaluate("() => typeof window.pptxMcp.onToolInput") == "function",
                  "门面没有 onToolInput（tool-input 通道缺失，宿主期的 view 只能靠 tool-result 猜）")
            view.input({"view": "brief"})
            wait_for(lambda: view.frame.evaluate(
                "() => !!(window.pptxMcp.__lastToolInput && window.pptxMcp.__lastToolInput.arguments"
                " && window.pptxMcp.__lastToolInput.arguments.view === 'brief')"), what="门面缓冲 tool-input")
            check(view.frame.evaluate("() => mcpApp.inputView") is None, "未注册的 tool-input 竟被投递")
            view.frame.evaluate("() => window.pptxMcp.onToolInput(window.__inputHandler)")
            check(view.frame.evaluate("() => mcpApp.inputView") == "brief", "注册时没有重放缓冲的 tool-input")
            # (b) 冲突：tool-input(brief) 先到、tool-result(annotate) 后到 → §6 优先级取 tool-input
            view.result(opened)
            st = view.wait_launch("brief", "tool-input 与 tool-result 冲突时按优先级落 brief")
            check(st["overlayShown"] and st["headerH"] == 0, f"冲突时两条通道打架（落在工作台）: {st}")
            view.assert_clean("#8")
        finally:
            view.close()

        managed_post(daemon, "/api/bridge/stop", {"reason": "cli-stop"})


def run_launch_split_host_arm(browser, base, root):
    """受限沙箱臂（仓库默认 `allow_same_origin: false` → 只有 allow-scripts）。

    症状类断言必须两臂都跑，否则等于在**非发货配置**上验证（设计 §10 开篇）。本臂专注
    "首屏分流本身成立"（视图/几何/chrome/无 JS 报错）；受限沙箱下的编辑能力报错由既有
    `run_noncompliant_host_arm` 覆盖。
    """
    for name, deck, view_name, expect_launch, label in (
            ("host-none-brief", None, "brief", "brief", "#1 受限臂（无 deck + view=brief）"),
            ("host-none-default", None, "__absent__", "brief", "#5 受限臂（无 deck + 不传 view）"),
            ("host-deck-brief", DECK, "brief", "brief", "#2 受限臂（有 deck + view=brief）"),
            ("host-deck-default", DECK, "__absent__", None, "#5 受限臂（有 deck + 不传 view）")):
        work = split_workdir(root, name, deck=deck)
        with Daemon(work) as daemon:
            discovery = discover(work)
            opened = open_split(daemon, work, view=view_name, with_deck=deck is not None)
            view = ViewPage(browser, base, discovery, sandbox="host")
            try:
                view.result(opened)
                st = view.wait_launch(expect_launch, f"{label} 落 {'脑暴视图' if expect_launch else '工作台'}")
                if expect_launch == "brief":
                    check(st["overlayShown"] and st["coversViewport"] and st["centerInOverlay"],
                          f"{label} 脑暴不是整屏视图: {st}")
                    check(st["headerH"] == 0 and st["footerH"] == 0 and st["barH"] == 0,
                          f"{label} 工作台 chrome 仍可见: {st}")
                else:
                    check(st["headerH"] > 0 and not st["overlayShown"], f"{label} 误隐藏工作台: {st}")
                if deck is not None:
                    # 不透明源下 doc() 为 null（本臂的已知限制），但 deck 仍要被读取（#10 在两臂都成立）
                    wait_for(lambda: "read_deck" in view.chain(), what=f"{label} 仍调 read_deck")
                view.assert_clean(label)
            finally:
                view.close()
            managed_post(daemon, "/api/bridge/stop", {"reason": "cli-stop"})


def run_launch_split_static_state(browser, base, serve):
    """§10 #11：嵌入态 / 裸静态态没有 session —— 缺省恒 edit，**绝不隐藏工作台**（防 §7.1 轨界限写错）。

    不新建宿主臂：裸静态态直接用仓库真 `editor.html`（非 View 产物），嵌入态用一个同源
    iframe 包住它（`state.embedded = window.parent !== window`）。
    """
    (serve / "editor.html").write_text((ROOT / "editor.html").read_text(encoding="utf-8"), encoding="utf-8")
    (serve / "embed_host.html").write_text(
        '<!doctype html><meta charset="utf-8"><title>embed host</title>'
        '<iframe id="ed" src="editor.html" style="width:1100px;height:820px;border:0"></iframe>', encoding="utf-8")

    def probe(target, label):
        state = target.evaluate("""() => ({kind: hostBridge.kind,
          launch: document.body.getAttribute('data-launch'),
          header: document.querySelector('body > header').getBoundingClientRect().height,
          applied: (typeof applyLaunch === 'function') ? applyLaunch('brief') : 'missing',
          after: document.body.getAttribute('data-launch'),
          overlay: document.getElementById('briefOverlay').classList.contains('show')})""")
        check(state["header"] > 0, f"{label} 工作台被隐藏（首屏分流越了轨界限）: {state}")
        check(state["launch"] is None and state["applied"] is False and state["after"] is None and not state["overlay"],
              f"{label} 参与了首屏分流（无 session 的两态必须恒工作台）: {state}")

    page = browser.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    try:
        page.goto(base + "/editor.html")
        wait_for(lambda: page.evaluate("() => window.hostBridge && hostBridge.kind") == "static",
                 what="裸静态态判定")
        probe(page, "裸静态态")
        page.goto(base + "/embed_host.html")
        frame = wait_for(lambda: next((f for f in page.frames if f.url.endswith("/editor.html")), None),
                         what="嵌入态 iframe")
        wait_for(lambda: frame.evaluate("() => window.hostBridge && hostBridge.kind") == "embedded",
                 what="嵌入态判定")
        probe(frame, "嵌入态")
        check(errors == [], f"裸静态/嵌入态出现 JS 报错: {errors}")
    finally:
        page.close()


def run_noncompliant_host_arm(base, page, opened, rel="view.html"):
    """负例臂：宿主保持默认（`allow_same_origin: false` → 只有 allow-scripts）时**必须明确报错并给处置指引**。

    按官方规范开发（用户决策，见设计 §10.10）：不提供只读降级模式，也不静默装成可编辑。
    """
    page.goto(base + f"/mcp_apps_host_sim.html?view={rel}&sandbox=host")
    wait_for(lambda: page.evaluate("() => window.hostSim.state") == "initialized", what="非规范宿主的握手")
    frame = find_view_frame(page)
    page.evaluate("payload => window.hostSim.sendToolResult(payload)", opened)
    wait_for(lambda: "read_deck" in [c["name"] for c in page.evaluate("() => window.hostSim.toolCalls")],
             what="非规范宿主的 read_deck")
    state_label = wait_for(
        lambda: (lambda text: text if "沙箱" in text else None)(
            frame.evaluate("() => document.getElementById('bridgeState').textContent")),
        what="非规范沙箱的报错状态")
    notice = frame.evaluate("() => document.getElementById('bridgeNotice').textContent")
    check("allow-same-origin" in notice, f"报错未给出处置指引: {notice!r}")
    check(frame.evaluate("() => document.getElementById('bridgeBar').dataset.state") == "error",
          "非规范沙箱未置为错误态")
    check(frame.evaluate("() => doc() === null"), "非规范宿主竟然能访问渲染文档（Chrome 行为变了？本臂需重写）")
    warn_text = frame.evaluate(
        "() => document.getElementById('warnBanner').classList.contains('show') "
        "? document.getElementById('warnText').textContent : ''")
    check("allow-same-origin" in warn_text, f"横幅未说明处置办法: {warn_text!r}")
    check("只能查看" not in state_label + notice + warn_text,
          "不应存在只读降级模式的措辞（决策：按官方规范开发）")


def main() -> int:
    from playwright.sync_api import sync_playwright
    from tools.bridge_mcp import build_view_html

    with tempfile.TemporaryDirectory(prefix="mcp-apps-") as tmp:
        root = Path(tmp)
        work = root / "work"
        work.mkdir()
        (work / "assets").mkdir()
        (work / "assets" / "pixel.png").write_bytes(PNG_1PX)
        (work / "fonts").mkdir()
        (work / "fonts" / "harness.woff2").write_bytes(FONT_BYTES)
        (work / "index.html").write_text(DECK, encoding="utf-8")

        serve = root / "serve"
        serve.mkdir()
        (serve / "mcp_apps_host_sim.html").write_text(
            (ROOT / "tests" / "harness" / "mcp_apps_host_sim.html").read_text(encoding="utf-8"), encoding="utf-8")
        view_html = build_view_html()
        (serve / "view.html").write_text(view_html, encoding="utf-8")
        check(len(view_html.encode("utf-8")) <= 2 * 1024 * 1024,
              "View HTML 超过宿主 2MB 上限（宿主会静默回退纯文本）")
        check("<script" in view_html and "window.pptxMcp" in view_html, "View HTML 未注入门面")

        with Daemon(work) as daemon:
            discovery = json.loads((work / ".pptx-html" / "serve.json").read_text(encoding="utf-8"))
            opened = managed_post(daemon, "/api/bridge/open", {
                "consumer_id": "apps-harness", "deck_path": str(work / "index.html"),
                "output_path": "index.html", "view": "edit", "open_browser": False})
            sid = opened["session_id"]

            with static_server(serve) as base, sync_playwright() as pw:
                browser = pw.chromium.launch()
                page = browser.new_page()
                page.expose_function("mcpCall", make_tool_proxy(discovery))
                browser_token = bind_browser_token(daemon, opened)
                run_trusted_arm(base, page, daemon, opened, work, discovery, browser_token)
                page2 = browser.new_page()
                page2.expose_function("mcpCall", make_tool_proxy(discovery))
                run_noncompliant_host_arm(base, page2, opened)
                # 首屏分流（P1 / brief-page-split §10 #1–#13）：两臂 + 无 session 两态
                run_launch_split_trusted_arm(browser, base, root)
                run_launch_split_host_arm(browser, base, root)
                run_launch_split_static_state(browser, base, serve)
                browser.close()
            managed_post(daemon, "/api/bridge/stop", {"reason": "cli-stop"})

    print("RESULT: ALL PASS (aa_mcp_apps_check)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
