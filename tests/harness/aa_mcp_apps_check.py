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
  ⑨ 首份 deck 到达（v3.9.5）：无 deck 的脑暴会话里**用户提交简报**（真按钮路径 → submit_intent 工具）
     → agent 侧认领 intent、写工作副本、push_update 发布 → View 的 2s 轮询必须 `read_deck`、
     渲染 deck、摘掉 `data-launch` 并落到编辑页签。这条覆盖"`mcpApp.revision` 为 null 时
     旧条件恒假 → read_deck 永不发生"的缺陷（症状：agent 生成完 deck 后页面既不关脑暴也不进编辑视图）。
  ⑩ 本地画布守卫 + 轨 A 换图（v3.9.5）：`<input type=file>` 回路加载的**本地画布**不属于受管
     工作区，保存必须被拒（`mcpAppPath(null)` 会回落到 `resourcePath`，等于用本地文件覆盖 agent 的
     deck）；受管画布的换图必须走 host 通道 `write_asset` 且产物保持 `assets/` 引用（旧代码是空
     catch 的静默 no-op）。
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

from tools.bridge_core import admin_request, revision_cli  # noqa: E402
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

# ⑨ 首份 deck 到达用的最小 deck：**不外引** assets/fonts（briefing 会话的发布按 candidate
# manifest 校验目录，任何未随发布落盘的外引文件都会让 post-flight 清单校验失败）。
FIRST_DECK = ('<!doctype html><html><head><meta charset="utf-8"><title>首份 deck</title></head>'
              '<body><section class="slide" data-slide-id="s1">'
              '<h1 data-editable>首份 deck 已生成</h1></section></body></html>')

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


def _tool_error_payload(exc):
    if hasattr(exc, "payload"):
        return exc.payload()
    return {"ok": False, "error": {"code": "STORAGE_UNAVAILABLE", "message": str(exc),
                                   "retryable": True, "details": {}}}


def make_tool_proxy(discovery, consumer):
    """模拟真实宿主的 `tools/call` 代理。

    返回 `{text, isError}`，与 server 端 `BridgeFastMCP.call_tool` 的 `CallToolResult`
    **同形**：失败一律 `isError=True` + **纯 JSON 文本**（审计 F9 之后不再有
    `Error executing tool <name>: ` 散文前缀）。
    """
    def proxy(name, args_json):
        args = json.loads(args_json or "{}")
        if name in MODEL_TOOL_ROUTES:
            method, path = MODEL_TOOL_ROUTES[name].split(" ", 1)
            try:
                payload = admin_request(discovery, path, args if method == "POST" else None, 120)
            except Exception as exc:  # BridgeError
                return {"isError": True, "text": json.dumps(_tool_error_payload(exc), ensure_ascii=False)}
            return {"isError": False, "text": json.dumps(payload, ensure_ascii=False)}
        try:
            _method, path, body = build_request(name, args, consumer_id=consumer)
        except Exception as exc:  # DispatchError
            return {"isError": True, "text": json.dumps(_tool_error_payload(exc), ensure_ascii=False)}
        try:
            payload = admin_request(discovery, path, body, 120)
        except Exception as exc:  # BridgeError
            return {"isError": True, "text": json.dumps(_tool_error_payload(exc), ensure_ascii=False)}
        return {"isError": False, "text": json.dumps(payload, ensure_ascii=False)}
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

    # A1/F9 · 工具错误：server 端已是**纯 JSON 信封**（无 SDK 散文前缀），
    # 宿主原样下发的 CallToolResult 必须 isError 且文本可直接 JSON.parse 出 error.code。
    raw = frame.evaluate("""async () => {
      var r = await window.pptxMcp.app.callServerTool({name:'read_bundle_file', arguments:{session_id: mcpApp.sessionId, path: 'etc/passwd'}});
      var blocks = (r && r.content) || [];
      return {isError: !!(r && r.isError), text: ((blocks[0] || {}).text) || '',
              structured: (r && r.structuredContent) == null ? null : r.structuredContent};
    }""")
    check(raw.get("isError") is True, f"宿主导游下发的错误结果没有 isError: {raw}")
    check("Error executing tool" not in (raw.get("text") or ""),
          f"错误文本仍带 SDK 散文前缀（F9）: {raw.get('text')[:160]}")
    body = json.loads(raw.get("text") or "{}")
    check(body.get("ok") is False and (body.get("error") or {}).get("code") == "INVALID_ARGUMENT",
          f"错误文本不是可解析的 JSON 信封（F9）: {raw.get('text')[:160]}")
    err = frame.evaluate("""async () => {
      try { await window.pptxMcp.callTool('read_bundle_file', {session_id: mcpApp.sessionId, path: 'etc/passwd'}); return {code:'NO_ERROR'}; }
      catch(e){ return {code: e.code || null, message: e.message}; }
    }""")
    check(err.get("code") == "INVALID_ARGUMENT", f"未还原出 error.code: {err}")
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

    def __init__(self, browser, base, discovery, sandbox="trusted", view_rel="view.html", consumer="split-harness"):
        self.page = browser.new_page()
        self.errors = []
        self.page.on("pageerror", lambda e: self.errors.append(str(e)))
        self.page.add_init_script(FRAME_ERROR_COLLECTOR)
        self.page.expose_function("mcpCall", make_tool_proxy(discovery, consumer))
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


# ============================================================
# 首份 deck 到达（v3.9.5，⑨）：脑暴会话从「没有 deck」到「有 deck」——
# `open_editor(view="brief")` 建的是 briefing 会话（deck_path=NULL / revision=NULL），agent 生成完
# deck 后再发布。旧轮询条件 `st.revision && mcpApp.revision && …` 里 `mcpApp.revision` 恒为 null
# → 条件恒假 → `read_deck` 永不发生：脑暴不关、编辑视图不出现（用户报告的症状）。
# 这条用例驱动**真按钮路径**（#btnBriefSend → submit_intent 工具）+ 真 daemon 发布，只断言
# View 侧的行为；断言非恒真由"旧条件必超时"保证（可复现：把 editor.html 的条件改回旧式即红）。
# ============================================================

def publish_first_deck(discovery, daemon, session_id, consumer, deck_text, timeout=30):
    """扮演 agent 侧：认领 pending intent → 在工作副本写 deck → push_update complete 发布。"""
    claimed = admin_request(discovery, "/api/bridge/await",
                            {"session_id": session_id, "consumer_id": consumer, "timeout_sec": timeout},
                            timeout + 10)
    check(claimed.get("kind") == "intent" and claimed.get("work_path"),
          f"agent 未认领到简报 intent（View 没提交成功？）: {claimed}")
    work_path = Path(claimed["work_path"])
    work_path.parent.mkdir(parents=True, exist_ok=True)
    work_path.write_text(deck_text, encoding="utf-8")
    validation = {"candidate_revision": revision_cli(work_path), "checks": [
        {"name": name, "argv": ["test", name], "exit_code": 0, "report_path": None}
        for name in ("render", "capacity", "images", "manifest")]}
    return managed_post(daemon, "/api/bridge/update", {
        "session_id": session_id, "intent_id": claimed["intent_id"], "attempt": claimed["attempt"],
        "consumer_id": consumer, "action": "complete", "message": "T36 首份 deck", "validation": validation})


def run_brief_first_deck_trusted_arm(browser, base, root):
    """⑨ 受信沙箱臂：无 deck 的脑暴会话 → 提交简报 → agent 发布 deck → View 切编辑视图。

    workdir 手工建（不用 `split_workdir`）：briefing 会话的目录必须**干净**——发布按 candidate
    manifest 做 post-flight 校验（`_publish` 的 `obs_rev != new_rev` → RECOVERY_FAILED），
    `split_workdir` 预置的 assets/pixel.png 是未登记文件，会让首次发布直接失败。
    """
    work = root / "split" / "first-deck"
    work.mkdir(parents=True)
    with Daemon(work) as daemon:
        discovery = discover(work)
        opened = open_split(daemon, work, view="brief", with_deck=False)
        check(opened["deck_path"] is None and not opened["revision"],
              f"无 deck 会话的前提不成立: deck_path={opened['deck_path']!r} revision={opened['revision']!r}")
        view = ViewPage(browser, base, discovery)
        try:
            view.result(opened)
            st = view.wait_launch("brief", "首份 deck 用例的脑暴视图")
            check(st["overlayShown"] and st["centerInOverlay"] and st["headerH"] == 0,
                  f"无 deck + view=brief 未落整屏脑暴视图: {st}")
            # 用户在脑暴页点「确认并发送简报」——真按钮路径（buildBriefExport → bridgeSend → submit_intent）。
            # 用 DOM click 而不是 Playwright 的鼠标点击：静态问卷表单很长，按钮落在 iframe 可见区之外
            # （overlay 是固定定位 + 内部滚动，Playwright 的"滚进视口"对内部滚动容器无能为力）。
            view.frame.evaluate("() => document.getElementById('btnBriefSend').click()")
            wait_for(lambda: "submit_intent" in view.chain(), what="脑暴页提交简报（submit_intent 工具）")
            check("read_deck" not in view.chain(), "提交简报阶段不该读 deck（那时还没有 deck）")

            published = publish_first_deck(discovery, daemon, opened["session_id"], "split-harness", FIRST_DECK)
            check(published.get("revision"), f"发布未返回 revision: {published}")
            # 轮询是 2s 一档：给足窗口（首份 deck 的到达本身算一次"变化"）
            wait_for(lambda: "read_deck" in view.chain(), timeout=25,
                     what="首份 deck 到达后 View 调 read_deck（旧条件恒假时这里必定超时）")
            st = view.wait_launch(None, "首份 deck 到达后摘除脑暴视图", timeout=25)
            check(view.frame.evaluate(
                "() => { var d = doc(); return !!(d && d.body && d.body.textContent.indexOf('首份 deck 已生成') >= 0); }"),
                f"首份 deck 未在 View 内渲染: {st}")
            check(not st["overlayShown"] and not st["centerInOverlay"], f"脑暴层仍盖住工作台: {st}")
            check(st["headerH"] > 0 and st["footerH"] > 0, f"切回工作台后 chrome 未恢复可见: {st}")
            check(st["view"] == "edit", f"deck 到达后未落到编辑页签: {st}")
            check(st["applied"] == "brief", f"落点记录被改写（应为最初判定的 brief）: {st}")
            view.assert_clean("⑨ 首份 deck 到达")
        finally:
            view.close()
        managed_post(daemon, "/api/bridge/stop", {"reason": "cli-stop"})


# ============================================================
# ⑩ 本地画布守卫 + 轨 A 换图（v3.9.5）：嵌入态与轨 A 里 `showOpenFilePicker` 探测为真但**调用**
# 被宿主权限策略拒绝，「打开文件」改用 `<input type=file>` 之后会引入"本地画布"——它不属于本会话
# 的受管 deck，保存/换图必须被拒（否则 `mcpAppPath(null)` 回落到 `mcpApp.resourcePath`，用本地
# 文件覆盖 agent 的受管 deck）。同一条用例顺带验证受管画布的换图走通 host 通道 `write_asset`
# ——旧代码在这里是空的 catch（静默 no-op），这条路从未跑到。
# ============================================================

LOCAL_DECK = ('<!doctype html><html><head><meta charset="utf-8"></head><body>'
              '<section class="slide" data-slide-id="s9"><h1 data-editable>本地文件</h1></section>'
              '</body></html>')


def run_local_canvas_and_asset_arm(browser, base, root):
    """⑩ 受信沙箱臂：本地画布必须写不进受管工作区；受管画布的换图必须走 host 通道。"""
    work = root / "managed"
    work.mkdir(parents=True)
    (work / "assets").mkdir()
    (work / "assets" / "pixel.png").write_bytes(PNG_1PX)
    (work / "fonts").mkdir()
    (work / "fonts" / "harness.woff2").write_bytes(FONT_BYTES)
    (work / "index.html").write_text(DECK, encoding="utf-8")
    with Daemon(work) as daemon:
        discovery = discover(work)
        opened = managed_post(daemon, "/api/bridge/open", {
            "consumer_id": "split-harness", "deck_path": str(work / "index.html"),
            "output_path": "index.html", "view": "edit", "open_browser": False})
        view = ViewPage(browser, base, discovery)
        try:
            view.result(opened)
            wait_for(lambda: view.state()["deckText"], what="⑩ 受管 deck 载入")
            managed_before = (work / "index.html").read_bytes()

            # (a) 本地画布（与 <input type=file> 回路完全同形：handle=null / deckPath=null）→ 保存必须被拒
            view.frame.evaluate("text => openHtml(text, 'local.html', null, undefined, null)", LOCAL_DECK)
            wait_for(lambda: view.frame.evaluate("() => state.deckPath === null"), what="⑩ 本地画布就位")
            view.page.evaluate("() => window.hostSim.toolCalls = []")
            view.frame.evaluate("() => saveDeck()")
            wait_for(lambda: view.frame.evaluate(
                "() => document.getElementById('warnBanner').classList.contains('show')"),
                what="⑩ 本地画布保存被拒并给出路")
            check("save_deck" not in view.chain(), f"本地画布竟然写了受管 deck: {view.chain()}")
            check("受管 deck" in view.frame.evaluate(
                "() => document.getElementById('warnText').textContent"),
                "本地画布被拒时没有说明原因（守卫必须有声音）")
            check((work / "index.html").read_bytes() == managed_before, "受管 deck 被本地画布改写了")

            # (b) 回到受管画布：换图走 host 通道 write_asset，并把**引用**（assets/）保存回 deck
            view.frame.evaluate("() => mcpAppLoadDeck(mcpApp.resourcePath, mcpApp.revision, false)")
            wait_for(lambda: view.frame.evaluate("() => state.deckPath === 'index.html'"), what="⑩ 受管画布重载")
            view.page.evaluate("() => window.hostSim.toolCalls = []")
            # 轨 A 没有系统文件选择器（调了也是被拒）——按轨走 `<input type=file>`。喂文件用
            # Playwright 的 filechooser 事件（拦截 input.click() 打开的选择器）而不是事后再
            # set_input_files：后者与"选择器正在打开"竞争，实测偶发十几秒的延迟。
            view.page.on("filechooser", lambda chooser: chooser.set_files({
                "name": "pixel.png", "mimeType": "image/png", "buffer": PNG_1PX}))
            view.frame.evaluate("""() => {
              var img = doc().querySelector('img'); window.__assetImg = img; replaceImage(img);
            }""")
            wait_for(lambda: "write_asset" in view.chain(),
                     what="⑩ 轨 A 换图走 write_asset（旧代码为静默 no-op）")
            wait_for(lambda: view.frame.evaluate(
                "() => window.__assetImg.getAttribute('data-image-state') === 'uploaded'"), what="⑩ 换图置 uploaded")
            # 轮询谓词必须落在**浏览器侧**：纯 Python 的 sleep/读文件不会驱动 Playwright 同步 API 的
            # 回调分发，宿主代理（mcpCall 绑定）的在途调用会一直挂着（实测表现为保存卡 ~15s 后
            # 才落地）。dirty 复位 = save_deck 成功（daemon 回执之后磁盘文件已提交）。
            wait_for(lambda: view.frame.evaluate("() => state.dirty === false"), what="⑩ 换图后的引用保存成功")
            saved = (work / "index.html").read_text(encoding="utf-8")
            check("assets/pixel.png" in saved and "data:image" not in saved and 'data-image-state="uploaded"' in saved,
                  "换图后的产物没有保持 assets/ 引用（数据 URI 不得进磁盘 deck）")
            view.assert_clean("⑩ 本地画布守卫 + 轨 A 换图")
        finally:
            view.close()
        managed_post(daemon, "/api/bridge/stop", {"reason": "cli-stop"})


SVG_PAGE = ('<svg xmlns="http://www.w3.org/2000/svg" width="16" height="9" viewBox="0 0 16 9">'
            '<rect width="16" height="9" fill="#123456"/></svg>')

EXPORT_MANIFEST = {
    "deck": {"title": "轨 A 产物通道验收"},
    "theme": {},
    "pages": [
        {"slide_id": "s1", "render_mode": "html", "carrier": "svg", "fidelity": 99.5},
        {"slide_id": "s2", "render_mode": "html", "carrier": "svg", "fidelity": 98.0},
    ],
    "export": {"exported_at": "2026-10-29T00:00:00+00:00", "exporter": "harness",
               "carriers": {"svg": 2, "baked": 0, "png-fallback": 0}, "fidelity_avg": 98.75,
               "tracks": {"editable": {"ok": True}, "vector": {"ok": True}}},
}


def run_track_a_artifacts_arm(browser, base, root):
    """⑪ 受信沙箱臂（v3.10 轨 A 产物通道）：export/ 必须经 read_bundle_file 自动加载。

    回归的病：轨 A 结构性读不到 `export/`（`triBaseUrl=null` → 产物清单恒空、对比恒黑面、
    下载恒不可用；转换成功、`export-refreshed` 也到了却什么都不加载）。本臂断言：装载即可
    读到 manifest、当前页产物水合成 `data:` URI、下载判据不再依赖 HTTP 基址、
    `export_revision` 变化（轨 A 唯一的"产物已更新"信号）触发重读。
    """
    work = root / "tracka-artifacts"
    work.mkdir(parents=True)
    (work / "assets").mkdir()
    (work / "assets" / "pixel.png").write_bytes(PNG_1PX)
    (work / "fonts").mkdir()
    (work / "fonts" / "harness.woff2").write_bytes(FONT_BYTES)
    (work / "index.html").write_text(DECK, encoding="utf-8")
    exp = work / "export"
    (exp / "native").mkdir(parents=True)
    (exp / "manifest.json").write_text(json.dumps(EXPORT_MANIFEST), encoding="utf-8")
    for i in (1, 2):
        (exp / f"page-{i:02d}.svg").write_text(SVG_PAGE, encoding="utf-8")
        (exp / f"page-{i:02d}.diff.png").write_bytes(PNG_1PX)
        (exp / "native" / f"page-{i:02d}.png").write_bytes(PNG_1PX)
    for name in ("deck.pptx", "deck-vector.pptx", "deck.pdf"):
        (exp / name).write_bytes(b"harness")
    with Daemon(work) as daemon:
        discovery = discover(work)
        opened = managed_post(daemon, "/api/bridge/open", {
            "consumer_id": "split-harness", "deck_path": str(work / "index.html"),
            "output_path": "index.html", "view": "edit", "open_browser": False})
        sid = opened["session_id"]
        # 发布一次：bundle 登记表是**白名单**，export/ 只有在某次发布扫到之后才可读
        # （真实链路由 agent 的 complete/save 发布建立；这里用一次 asset 写触发）。
        managed_post(daemon, "/api/bridge/asset", {
            "session_id": sid, "path": "assets/pixel.png",
            "data_base64": base64.b64encode(PNG_1PX).decode("ascii"),
            "base_revision": opened["revision"]})
        view = ViewPage(browser, base, discovery)
        try:
            view.result(opened)
            wait_for(lambda: view.state()["deckText"], what="⑪ 受管 deck 载入")
            view.frame.evaluate("() => triRefresh()")
            wait_for(lambda: view.frame.evaluate("() => triStatus") == "ready",
                     what="⑪ 轨 A 经 read_bundle_file 读到 export/manifest.json")
            check("read_bundle_file" in view.chain(), "⑪ 轨 A 没有走 read_bundle_file 读产物")
            check(view.frame.evaluate("() => triManifest.pages.length") == 2, "⑪ manifest 页数不符")
            check(view.frame.evaluate("() => !$('expTable').hidden") is True,
                  "⑪ 产物清单表未显示（轨 A 仍是空/引导态）")
            check(view.frame.evaluate("() => $('expRows').children.length") == 2, "⑪ 产物清单没有两行")
            check(not view.frame.evaluate("() => document.body.innerText.includes('无产物通道')"),
                  "⑪ 轨 A 仍在报「无产物通道」")
            check(view.frame.evaluate("() => !!$('btnDlPptx').dataset.url"),
                  "⑪ 主产物下载仍不可用（判据不该依赖 HTTP 基址）")
            view.frame.evaluate("() => triArtifactUri('export/page-01.svg')")
            wait_for(lambda: str(view.frame.evaluate(
                "() => triDataUri['export/page-01.svg'] || ''")).startswith("data:image/svg"),
                what="⑪ 当前页产物水合成 data: URI")
            before = view.chain().count("read_bundle_file")
            view.frame.evaluate("() => mcpAppApplyStatus({export_revision: 'sha256:changed-export'})")
            wait_for(lambda: view.chain().count("read_bundle_file") > before,
                     what="⑪ export_revision 变化触发重读 manifest")
            view.assert_clean("⑪ 轨 A 产物通道")
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


def run_font_csp_arm(browser, base, discovery, opened, rel="view.html"):
    """F10 正例：**规范默认 CSP**（没有 `font-src` ⇒ 落到 `default-src 'none'`）下 data: 字体必被挡，
    编辑器必须检测到并**一次性告警**说明原因与出路。

    默认臂用的是参考宿主 CSP（`font-src 'self' data:`），字体能显示、也就没什么可告警——
    所以这条只能在 `csp=spec` 下复现（`_meta.ui.csp` 的 `resourceDomains` 表达不了 `data:`）。
    """
    page = browser.new_page()
    errors = []
    console = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("console", lambda m: console.append(m.text))
    page.expose_function("mcpCall", make_tool_proxy(discovery, "apps-harness"))
    page.goto(base + f"/mcp_apps_host_sim.html?view={rel}&sandbox=trusted&csp=spec")
    wait_for(lambda: page.evaluate("() => window.hostSim.state") == "initialized", what="spec-CSP 臂的握手")
    frame = find_view_frame(page)
    page.evaluate("payload => window.hostSim.sendToolResult(payload)", opened)
    wait_for(lambda: "read_deck" in [c["name"] for c in page.evaluate("() => window.hostSim.toolCalls")],
             what="spec-CSP 臂的 read_deck")
    deadline = time.time() + 15
    while time.time() < deadline and not frame.evaluate("() => !!(window.mcpApp && window.mcpApp.fontCspWarned)"):
        time.sleep(0.2)
    diag = frame.evaluate("""() => ({
      warned: !!(window.mcpApp && window.mcpApp.fontCspWarned),
      hasDeckDoc: !!doc(),
      bridgeState: document.getElementById('bridgeState').textContent,
      warnText: (document.getElementById('warnText') || {}).textContent || ''
    })""")
    csp_console = [c for c in console if "Content Security Policy" in c or "Refused" in c]
    check(diag["warned"], f"F10：规范默认 CSP 挡下字体后应触发一次性告警；诊断={diag}；CSP 控制台={csp_console[:2]}")
    text = diag["warnText"]
    check("font-src" in text and "data:" in text, f"F10 告警未说明原因与出路: {text[:220]}")
    check(errors == [], f"spec-CSP 臂出现 JS 报错: {errors}")
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


# ── P3.1 登记制静态断言（2026-10-28）──────────────────────────────────────────
# 共享 UI 代码**不得**直连"轨通道"函数——那正是"某个形态下点了没用"的成因（审计 S1/§2.2）。
# 规则：`bridgeFetch` / `mcpAppCall` 的调用者只能是①四态实现内部，或②下方**登记在册**的
#       "轨专属传输包装"。往登记表里加名字 = 明确承认"这是轨专属实现"，是一项需评审的动作。
_TRANSPORT_CALLERS = {
    # 轨 B（bridge）传输包装
    "bridgeSubmitIntent", "bridgeResendIntent", "bridgeCancelIntent", "bridgeStopIntent",
    "bridgeRetryIntent", "bridgeRecoverIntents", "bridgeLoadDeck", "bridgePersistDraft",
    "bridgeConnectSSE", "bridgeStatusAndRecover", "bridgeForceExport", "bridgeHeartbeat",
    "pollConvertStatus",   # 静态态(伴随服务)/轨 B 的本地转换轮询，内部按 bridge.enabled 分流
    # 轨 A（mcpApp）传输包装
    "mcpAppBoot", "mcpAppLoadDeck", "mcpAppPollOnce", "mcpAppPersistDraft", "mcpAppSubmitIntent",
    "mcpAppHydrateImage", "mcpAppHydrateCss",
    # v3.10 轨 A 产物通道：export/manifest.json（mcpAppLoadExport）与逐页产物图（mcpAppFetchArtifact）
    "mcpAppLoadExport", "mcpAppFetchArtifact",
}
_TRANSPORT_PROXIES = ("bridgeFetch", "mcpAppCall")
_NAME_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_$")


def _is_call(line: str, fn: str) -> bool:
    """行内是否出现 `fn(` 形式的调用（排除定义行与更长的标识符前缀）。"""
    start = 0
    while True:
        i = line.find(fn + "(", start)
        if i < 0:
            return False
        if (line[i - 1] if i else " ") not in _NAME_CHARS:
            return True
        start = i + 1


def _fn_name(line: str):
    s = line.strip()
    for prefix in ("async function ", "function "):
        if s.startswith(prefix):
            return s[len(prefix):].split("(")[0].strip() or None
    return None


def assert_ui_plane_discipline() -> None:
    """登记制：共享 UI 不得直连轨通道（P3.1 的反回潮断言；失败即退出）。"""
    src = (ROOT / "editor.html").read_text(encoding="utf-8").split("\n")
    ranges = {}
    for name in ("staticHost", "embeddedHost", "bridgeHost", "mcpAppHost"):
        starts = [i for i, l in enumerate(src) if l.strip().startswith("var %s = {" % name)]
        assert starts, f"找不到四态实现 {name}（editor.html 结构已变，断言需更新）"
        s = starts[0]
        e = next(j for j in range(s + 1, len(src)) if src[j].startswith("};"))
        ranges[name] = (s + 1, e + 1)

    def in_host(ln: int) -> bool:
        return any(a <= ln <= b for a, b in ranges.values())

    violations = []
    for i, line in enumerate(src, 1):
        for fn in _TRANSPORT_PROXIES:
            if not _is_call(line, fn) or _fn_name(line) == fn:
                continue
            if in_host(i):
                continue
            caller = None
            for j in range(i - 1, -1, -1):
                nm = _fn_name(src[j])
                if nm:
                    caller = nm
                    break
            if caller in _TRANSPORT_CALLERS:
                continue
            violations.append(f":{i} {fn} ← {caller or '<顶层>'}")
    if violations:
        raise SystemExit(
            "P3.1 违规：共享 UI 直连轨通道（应改走 hostBridge 策略面；确属轨专属实现则登记进 "
            "_TRANSPORT_CALLERS）：\n  " + "\n  ".join(violations))


def main() -> int:
    assert_ui_plane_discipline()   # P3.1 登记制：静态、廉价、先于浏览器臂失败
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
                page.expose_function("mcpCall", make_tool_proxy(discovery, "apps-harness"))
                browser_token = bind_browser_token(daemon, opened)
                run_trusted_arm(base, page, daemon, opened, work, discovery, browser_token)
                run_font_csp_arm(browser, base, discovery, opened)
                page2 = browser.new_page()
                page2.expose_function("mcpCall", make_tool_proxy(discovery, "apps-harness"))
                run_noncompliant_host_arm(base, page2, opened)
                # 首屏分流（P1 / brief-page-split §10 #1–#13）：两臂 + 无 session 两态
                run_launch_split_trusted_arm(browser, base, root)
                run_launch_split_host_arm(browser, base, root)
                run_launch_split_static_state(browser, base, serve)
                # ⑨ 首份 deck 到达（v3.9.5）：briefing 会话 → 提交简报 → 发布 deck → 切编辑视图
                run_brief_first_deck_trusted_arm(browser, base, root)
                # ⑩ 本地画布守卫 + 轨 A 换图（v3.9.5）
                run_local_canvas_and_asset_arm(browser, base, root)
                # ⑪ 轨 A 产物通道（v3.10）：export/ 经 read_bundle_file 自动加载
                run_track_a_artifacts_arm(browser, base, root)
                browser.close()
            managed_post(daemon, "/api/bridge/stop", {"reason": "cli-stop"})

    print("RESULT: ALL PASS (aa_mcp_apps_check)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
