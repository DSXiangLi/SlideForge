#!/usr/bin/env python3
"""Official MCP SDK stdio proxy for the editor/agent bridge daemon.

双轨（设计 `docs/design/mcp-apps-upgrade.md`）：

- **轨 B（现状）**：五个面向模型的工具经 `admin_request` 走 loopback HTTP 到 daemon；
  独立浏览器标签页用 browser 凭证直连同一 daemon。
- **轨 A（MCP Apps）**：宿主把资源 `ui://pptx-html-bridge/editor.html` 渲染进 iframe，
  View 经宿主代理调用 9 个 `visibility:["app"]` 工具；这些工具同样落到同一个 daemon，
  **状态机与轨 B 完全同一份**（BridgeCore 原样复用）。

⚠️ 与设计的一处偏离（已记入设计文档）：轨 A 的传输层**并没有"整层不启动"**——
`ensure_daemon` 在 MCP server 启动时就拉起了 daemon，且注册期早于 `initialize`，
没有可用的宿主信号能决定"这次不开 daemon"。因此 app-only 工具复用 loopback HTTP
（management 凭证）而不是在 MCP 进程内直连 BridgeCore。好处之一是设计 §6.2 第 4 条
的异步约束自动满足：`BridgeCore.await_intent` 的同步轮询发生在 daemon 自己的线程里，
不会堵住本进程服务 View 的事件循环。
"""
from __future__ import annotations

import asyncio
import contextlib
import hashlib
import json
import os
import re
import sys
import threading
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# 本模块既作为脚本被宿主启动（tools/edit.py --mcp），也被测试按包路径导入。
# 兄弟模块 bridge_core / bridge_dispatch 是扁平模块，因此显式挂上自身目录。
_HERE = str(Path(__file__).resolve().parent)
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)


class CheckEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Annotated[
        Literal["render", "capacity", "images", "manifest", "export"],
        Field(description="Validated check category; generation intents require render, capacity, images, and manifest, while conversion requires export."),
    ]
    argv: Annotated[
        list[Annotated[str, Field(min_length=1, description="One non-empty argv token from the command that was actually executed.")]],
        Field(min_length=1, description="Exact argv array for the completed validation command; never a shell command string."),
    ]
    exit_code: Annotated[int, Field(description="Actual process exit code; publication accepts only zero.")]
    report_path: Annotated[
        str | None,
        Field(description="Optional report path relative to the attempt work bundle, or null when the check produces no report file."),
    ]


class ValidationEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")
    candidate_revision: Annotated[
        str,
        Field(pattern=r"^sha256:[0-9a-f]{64}$", description="Source bundle revision computed from the assigned work_path after all writes and checks."),
    ]
    checks: Annotated[
        list[CheckEvidence],
        Field(min_length=1, description="Non-empty evidence list for every validation check required by the current intent type."),
    ]
    export_source_revision: Annotated[
        str | None,
        Field(pattern=r"^sha256:[0-9a-f]{64}$", description="For a conversion completion, the source revision to which the complete dual-track export is bound."),
    ] = None

try:
    from mcp.server.fastmcp import FastMCP
    from mcp.server.fastmcp.exceptions import ToolError
    from mcp.types import CallToolResult, TextContent, ToolAnnotations, Tool
except ImportError as exc:
    print("缺少官方 MCP SDK；请安装 mcp>=1.28,<2（手动编辑器不需要此依赖）", file=sys.stderr)
    raise SystemExit(3) from exc

from bridge_core import (
    AWAIT_TIMEOUT_DEFAULT_SEC,
    AWAIT_TIMEOUT_MAX_SEC,
    AWAIT_TIMEOUT_MIN_SEC,
    VIEW_WAIT_SEC_DEFAULT,
    VIEW_WAIT_SEC_MAX,
    BridgeError,
    PROJECT_ROOT,
    admin_request,
    ensure_daemon,
)
from bridge_dispatch import APP_ONLY_TOOL_NAMES, DispatchError, build_request

AWAIT_HTTP_TIMEOUT_MARGIN_SEC = 15
# 仲裁窗口 = 存在性窗口 + 该余量（设计 §4.2 硬化 ③）：浏览器在存在性窗口到期后才启动，
# 加上加载与首心跳的时延，余量不足会让仲裁先判"轨 B"而实际上轨 A 已经接上。
VIEW_ARBITRATION_MARGIN_SEC = 4

EDITOR_URI = "ui://pptx-html-bridge/editor.html"
BRIEF_URI = "ui://pptx-html-bridge/brief.html"
# 兼容别名：编辑器资源的旧名（部分验收脚本仍按此导入）。新代码请用 EDITOR_URI / BRIEF_URI。
VIEW_URI = EDITOR_URI
VIEW_MIME = "text/html;profile=mcp-app"
APPS_EXTENSION = "io.modelcontextprotocol/ui"
VIEW_BUNDLE_PATH = PROJECT_ROOT / "tools" / "ext_apps_bundle.js"
VIEW_MANIFEST_PATH = PROJECT_ROOT / "tools" / "ext_apps_bundle.json"
VIEW_SIZE_LIMIT = 2 * 1024 * 1024          # 桥侧构建期硬上限（设计 §5.7）；**不是**宿主的预取上限
VIEW_SIZE_WARN = int(1.5 * 1024 * 1024)    # 构建期告警线
# 宿主 CLI 的 MCP_UI_HTML_MAX_BYTES（实测 WorkBuddy codebuddy.js 模块 28326：eh=262144）。
# 超过它时宿主 broadcastMcpUiForToolCall 的 pickPrefetchedMcpUiHtml 返回空，广播出去的
# mcpUi 对象不带 html 字段，renderer 必须自己 readResource（200ms loading / 30s 超时）。
# 当前自包含 View 约 828 KB，必然走这条异步路径。
#
# **这个上限只影响 Agent CLI 的 inline-widget 广播，不决定「宿主内是否弹面板」。**
# WorkBuddy 有两条互不相干的 MCP App 通路（2026-11-12 从 app.asar + 诊断日志实证）：
#   ① Agent CLI（cli/dist/codebuddy.js）broadcastMcpUiForToolCall：只看工具
#      `_meta.ui.resourceUri`，把 mcpUi 载荷 stash 给 renderer 的内联卡片／历史回放，
#      **不查 catalog**。日志 `broadcast ok ... pendingStashed=true` 属于这条，与本上限相关。
#   ② daemon（app.asar）McpAppsHost + McpAppCatalog + openHostApp：才是「宿主内弹面板」。
#      catalog 的发现源只有 connectorService 注册的 remote MCP（configId `custom-mcp:*`）
#      与 bundled `workbuddy-builtin/mcps`；**用户 mcp.json 里的本地 stdio MCP 不在其中**
#      （它由 Agent CLI 按会话持有）。实测 catalog.refresh scanned=67 acceptedCount=2
#      liveApps=["ardot/open_design","ardot/create_design"]，`pptx` 在诊断日志出现 0 次，
#      故 openHostApp 查不到本工具 → catalogMiss → 不弹面板。
# 结论：面板不弹的根因是宿主侧 catalog 准入，不是资源体积、不是 capabilities 声明、
# 也不是 renderer 消费缺口。256 KB 只让 ① 少带一个 html 字段；压缩资源修不了 ②。
HOST_UI_PREFETCH_LIMIT = 262144
_PREFETCH_WARN_EMITTED = False
VIEW_HANDSHAKE_TIMEOUT_MS = 15000          # View 等 ui/initialize 应答的上限（引导期承诺）
EXTERNAL_REF_RE = re.compile(
    r"<script[^>]+\bsrc=|<link[^>]+\bhref\s*=\s*[\"']?https?:|<iframe[^>]+\bsrc=|<object\b|<embed\b", re.I
)


def _view_version() -> str:
    """View 版本号：**单源**取自 bundle manifest（由构建脚本从 editor.html 头解析）。

    历史上 `bridge_mcp.py` 与 `build_ext_apps_bundle.py` 各写一份字面量，于是出现
    "编辑器 v3.9.3 / 上报 3.9.2"的漂移（F8）。读不到就报 `unknown`，不猜一个版本。
    """
    try:
        manifest = json.loads(VIEW_MANIFEST_PATH.read_text(encoding="utf-8"))
        return str(manifest["view_version"])
    except Exception:
        return "unknown"


VIEW_VERSION = _view_version()

# 工具 `title`：规范不强制，但官方示例都给 app 工具标题，且宿主列表里这是唯一的人类可读名
# （审计 F11 实测各工具的 title 全是 None）。集中一张表，不散进各工具装饰器里。
TOOL_TITLES = {
    "open_brief": "打开需求脑暴",
    "get_revision": "读取候选 revision",
    "open_editor": "打开编辑器",
    "await_intent": "等待用户意图",
    "push_update": "回写发布",
    "get_status": "读取任务状态",
    "close_session": "结束会话",
    "attach_view": "附着内嵌视图",
    "read_deck": "读取目标 HTML",
    "read_bundle_file": "读取受管文件",
    "save_deck": "保存目标 HTML",
    "write_asset": "写入图片资产",
    "submit_intent": "提交用户意图",
    "save_draft": "保存服务端草稿",
    "list_versions": "列出历史版本",
    "rollback": "回滚到历史版本",
    "rebaseline": "对齐版本基线",
}

# View 引导：必须在 editor.html 自身脚本之前**同步**定义 window.pptxMcp，
# 否则 hostKindDetect 看不到门面而回落到既有三态。真正的实现在随后注入的 bundle
# 里经 __install 覆盖（门面源码见 tools/ext_apps_facade.js）。
VIEW_BOOTSTRAP = """<script>
/* MCP Apps View 引导（server 注入，勿手改；见 tools/bridge_mcp.py） */
(function(){
  var api = {};
  var resolveReady, rejectReady;
  api.version = %s;
  api.__pending = true;
  api.ready = new Promise(function(resolve, reject){ resolveReady = resolve; rejectReady = reject; });
  api.__resolveReady = function(ctx){ resolveReady(ctx); };
  api.__rejectReady = function(err){ rejectReady(err); };
  function deferred(method){
    return function(){
      var args = Array.prototype.slice.call(arguments);
      return api.ready.then(function(){ return api[method].apply(null, args); });
    };
  }
  ["callTool","notifyAgent","setModelContext","downloadFile","openLink","hostContext","hostCapabilities"]
    .forEach(function(method){ api[method] = deferred(method); });
  api.log = function(){};
  api.reportSize = function(){};
  /* 引导期注册必须**存下来**：editor.html 的启动脚本早于 bundle 执行，它注册的
     onToolResult（session 上下文的唯一来源）与 onTeardown 都要在安装后接上。
     存成裸函数会被静默丢弃，表现为"编辑器一直停在等待宿主下发会话"。
     注册时**重放缓冲**：宿主在 connect 后立刻发 tool-input/tool-result，可能早于注册。 */
  api.onTeardown = function(cb){ api.__teardown = cb; };
  api.onToolInput = function(cb){ api.__toolInput = cb;
    if (api.__lastToolInput){ try { cb(api.__lastToolInput); } catch(e){} } };
  api.onToolResult = function(cb){ api.__toolResult = cb;
    if (api.__lastToolResult){ try { cb(api.__lastToolResult); } catch(e){} } };
  /* 引导期注册同样必须存下来（安装后由 facade 的 app.onhostcontextchanged 转发） */
  api.onHostContextChanged = function(cb){ api.__hostCtx = cb; };
  window.pptxMcp = api;
  /* 优雅失联：宿主导入资源却没完成握手（或 bundle 未注入）时，ready 不能永远悬着。
     文案与计时**同源**（VIEW_HANDSHAKE_TIMEOUT_MS）——历史上写死"8s"而实际 15000ms（F13）。 */
  setTimeout(function(){
    if (api.__pending && api.__rejectReady) api.__rejectReady(new Error("MCP Apps 握手超时：%ds 内未收到 ui/initialize 应答"));
  }, %d);
})();
</script>""" % (json.dumps(VIEW_VERSION), VIEW_HANDSHAKE_TIMEOUT_MS // 1000, VIEW_HANDSHAKE_TIMEOUT_MS)

# app-only 工具：`visibility` 只写在 `_meta.ui` —— 这是规范里的**唯一**位置（S:324-333，
# SDK 读取路径见 `src/app-bridge.ts:151-171`）。历史上这里还双写了根级 `_meta.visibility`，
# 那是**非规范字段**（规范明确否决扁平键，S:1668），1022 复读已确认原宿主（N15）改为标准路径
# 优先，故不再需要（F4）。
APP_ONLY_META = {"ui": {"visibility": ["app"]}}

# 仅轨 A 列举的**面向模型**入口：`open_brief`。
# 为什么单独一组：轨 B 的工具面是**冻结的恰好五个**（AGENTS.md 红线），
# 而脑暴拆成独立工具是轨 A 的可移植性诉求（一个 View 一份形态声明）。
# 两者的列举门相同（`apps_tools_listed()`），但可见性语义不同，故不并入 APP_ONLY_META。
# 仅轨 A 列举的**面向模型**入口：
#   open_brief —— 脑暴页（形态拆分要求一个 View 一份声明）
#   get_revision —— 只读取本 attempt 工作副本的源 revision（轨 A 的 agent 在沙箱里拿不到
#     `tools/bridge_core.py`，算不出 `candidate_revision`；轨 B 的 agent 在宿主机上跑，够得着，不需要它）
MODEL_GATED_TOOL_NAMES = ("open_brief", "get_revision")

# app-only 工具的共用参数注记。必须放在模块级：`from __future__ import annotations`
# 会把注解变成字符串，FastMCP 用函数的 __globals__ 求值，闭包内定义的名字解析不到。
SessionId = Annotated[str, Field(min_length=1, description="Session identifier returned by open_editor.")]


def _tool_meta(resource_uri: str | None = None) -> dict[str, Any]:
    """工具 `_meta`：`_meta.ui` **只允许**标准两键（`resourceUri` / `visibility`）。

    呈现形态（inline / pip / fullscreen）**不在工具元数据里声明**——规范的
    `McpUiToolMeta` 没有这个字段（`src/spec.types.ts:764-793`），形态归宿主裁量
    （官方概览 `docs/overview.md:201`：the Host always has final say over its own UI）。
    我方表达形态诉求的标准位置只有两处，都在 View 侧：`appCapabilities.availableDisplayModes`
    （硬约束：宿主 MUST NOT 切到未声明形态）与 `ui/request-display-mode`（软请求）。
    历史上这里写过宿主扩展 `mode` / `mode_inline_when`，已废弃——见
    `docs/design/mcp-apps-standard-split.md`（"零自定义协议字段"）。
    """
    meta: dict[str, Any] = {"visibility": ["model", "app"]}
    ui: dict[str, Any] = {"visibility": ["model", "app"]}
    if resource_uri:
        ui["resourceUri"] = resource_uri
        # 扁平键是规范的**已废弃**形式（`apps.mdx:347` 明文 deprecated，GA 前移除），
        # 保留只为兼容尚未升级的读取方；嵌套键优先。
        meta["ui/resourceUri"] = resource_uri
    meta["ui"] = ui
    return meta


def _variant_boot(variant: str) -> str:
    """呈现变体常量（编译期注入，View 侧据此声明能力形态）。

    两个资源共用同一份 `editor.html` 源码，差异只在**这里注入的常量**：
    `brief` 只声明 `["inline"]`（一次性表单，结果落信息流）；`editor` 声明
    `["inline","pip"]` 并在握手后请求 pip（"能同时看到对话与编辑器"，见设计 §0 D-1）。
    **刻意不声明 fullscreen**——声明集合就是宿主 MUST NOT 越过的边界。
    """
    return (
        "<script>\n"
        "/* MCP Apps View 呈现变体（server 注入，勿手改；见 tools/bridge_mcp.py 与\n"
        "   docs/design/mcp-apps-standard-split.md）。取值：brief | editor */\n"
        f"window.__PPTX_VIEW_VARIANT__ = {json.dumps(variant)};\n"
        "</script>"
    )


def build_view_html(variant: str = "editor") -> str:
    """把 editor.html 与注入的 View SDK bundle 合成一个自包含资源（无外链）。

    `variant` 只影响注入的呈现变体常量，不改变源码——单源双资源，避免两份 UI 代码漂移。
    """
    html = (PROJECT_ROOT / "editor.html").read_text(encoding="utf-8")
    if not VIEW_BUNDLE_PATH.exists():
        raise RuntimeError("缺少 View bundle：先跑 python3 tools/build_ext_apps_bundle.py")
    bundle = VIEW_BUNDLE_PATH.read_text(encoding="utf-8")
    hits = sorted({m.group(0) for m in EXTERNAL_REF_RE.finditer(html)})
    if hits:
        raise RuntimeError("View HTML 含外链引用，违反 CSP 前提：" + ", ".join(hits[:5]))
    boot = _variant_boot(variant) + VIEW_BOOTSTRAP
    module = "<script>\n(function(){\"use strict\";\n" + bundle.replace("</script", "<\\/script") + "\n})();\n</script>"
    match = re.search(r"<head[^>]*>", html, re.I)
    if not match:
        raise RuntimeError("editor.html 缺少 <head> 锚点，无法注入 View 引导")
    view = html[: match.end()] + boot + module + html[match.end():]
    size = len(view.encode("utf-8"))
    if size > VIEW_SIZE_LIMIT:
        raise RuntimeError(f"View HTML {size} 字节超过宿主 {VIEW_SIZE_LIMIT} 字节上限（宿主会静默回退纯文本）")
    if size > VIEW_SIZE_WARN:
        print(f"[bridge_mcp] 警告：View HTML {size} 字节已超过告警线 {VIEW_SIZE_WARN}", file=sys.stderr)
    global _PREFETCH_WARN_EMITTED
    if size > HOST_UI_PREFETCH_LIMIT and not _PREFETCH_WARN_EMITTED:
        _PREFETCH_WARN_EMITTED = True
        print(
            f"[bridge_mcp] 提示：View HTML {size} 字节超过宿主 MCP UI 预取上限 "
            f"{HOST_UI_PREFETCH_LIMIT}；宿主广播的 mcpUi 将不含 html，renderer 需异步 "
            "readResource 才能渲染，宿主未消费时内嵌视图不会出现（轨 A 实证须看 view_attached）。",
            file=sys.stderr,
        )
    return view


def error_envelope(exc: BaseException) -> dict[str, Any]:
    """把工具调用失败归一成与 daemon 同形的 JSON 信封（F9）。

    捕获到的异常通常是 SDK 的包装（`ToolError("Error executing tool <name>: …")`），
    `exc.__cause__` 才是原始异常：我们自己的 `ToolError`（字符串就是 JSON 载荷）
    或 pydantic 的 `ValidationError`。
    """
    inner = exc.__cause__ or exc
    if isinstance(inner, ToolError):
        try:
            parsed = json.loads(str(inner))
        except Exception:
            parsed = None
        if isinstance(parsed, dict) and parsed.get("ok") is False and isinstance(parsed.get("error"), dict):
            return parsed
    text = " ".join(str(inner).split())
    invalid = "validation error" in text
    return {"ok": False, "error": {
        "code": "INVALID_ARGUMENT" if invalid else "STORAGE_UNAVAILABLE",
        "message": text[:500] or "工具调用失败",
        "retryable": not invalid,
        "details": {},
    }}


class BridgeFastMCP(FastMCP):
    """工具面双模：宿主未声明 MCP Apps UI 扩展时只列出面向模型的五个工具。

    设计 §3.1 已证明"注册期早于 initialize"，所以不能按能力注册两套工具集；
    但 `tools/list` 发生在 `initialize` 之后，可以在**列举期**按客户端能力分流。
    这样轨 B 看到的仍是恰好五个工具，红线不被 app-only 工具与轨 A 专属入口污染；
    声明了扩展的宿主（或 `always`）看到全部 15 个：6 个面向模型 + 9 个 `visibility:["app"]`。

    环境变量 `PPTX_HTML_APPS_TOOLS`：`auto`（默认）| `always` | `never`。
    `always` 供"能渲染 widget 却不声明扩展"的宿主使用（本机实测宿主属此类）。
    """

    def __init__(self, *args, app_only_names=(), model_gated_names=(), **kwargs):
        """`app_only_names` = `visibility:["app"]` 的工具；`model_gated_names` = 仅轨 A 列举的
        **面向模型**入口（`open_brief`）——两者的列举门相同，语义不同，别混。
        """
        self._app_only_names = set(app_only_names)
        self._gated_names = set(app_only_names) | set(model_gated_names)
        super().__init__(*args, **kwargs)
        # 每个变体缓存一份合成 HTML（单源双资源，见 build_view_html）
        self._view_html: dict[str, str] = {}

    async def call_tool(self, name, arguments):
        """统一错误信封（F9）：任何失败都以 `isError=true` + **纯 JSON 文本** 返回。

        mcp 1.28 的 `Tool.run`（`server/fastmcp/tools/base.py:117`）把**任何**异常重包成
        `ToolError("Error executing tool <name>: …")`，参数校验失败更是连 JSON 都不是，
        于是模型与 View 拿到的是带散文前缀的文本，与 AGENTS/SKILL 声称的"错误是 JSON"不符。
        这里兜住失败并直接构造 `CallToolResult`——低层会**原样透传**（`lowlevel/server.py:546`），
        因此不会拿错误载荷去撞成功路径的 `outputSchema` 校验。
        """
        try:
            return await super().call_tool(name, arguments)
        except Exception as exc:
            payload = error_envelope(exc)
            return CallToolResult(
                content=[TextContent(type="text",
                                     text=json.dumps(payload, ensure_ascii=False, separators=(",", ":")))],
                isError=True,
            )

    def apps_declared(self) -> bool:
        """客户端是否声明 MCP Apps 扩展**且**支持 html profile（F5）。

        只认扩展键是不够的：规范把 `mimeTypes` 标为 REQUIRED（S:1522），官方助手也以
        `mimeTypes.includes("text/html;profile=mcp-app")` 为门（`src/server/index.ts:478`）。
        缺省时按**宽松**处理——生成式 schema 把它标成可选（`src/generated/schema.ts:767-769`），
        把"没写 mimeTypes"判成"不支持"会误伤真实宿主；声明了却给别的类型才必须挡住。
        """
        try:
            params = self._mcp_server.request_context.session.client_params
        except Exception:
            return False
        caps = getattr(params, "capabilities", None)
        extra = getattr(caps, "model_extra", None) or {}
        declared = (extra.get("extensions") or {}).get(APPS_EXTENSION)
        if not isinstance(declared, dict):
            return False
        mimes = declared.get("mimeTypes")
        if mimes is None:
            return True
        return isinstance(mimes, list) and VIEW_MIME in mimes

    def apps_capability_probe(self) -> dict[str, object]:
        """能力协商的**原始证据**——「为什么没走轨 A」必须可观测，不能靠工具列表反推。

        有一类宿主（本机实测 WorkBuddy 属此类）实现了完整的 MCP Apps 宿主侧协议
        （`ui/initialize` / `ui/message` / `ui/resourceUri` / `text/html;profile=mcp-app`），
        却不在 MCP `initialize` 的 `capabilities.extensions` 里声明
        `io.modelcontextprotocol/ui`。`apps_declared()` 按规范只认声明，必然 False；
        默认 `auto` 于是把工具面冻结到五个、把 `open_browser="auto"` 退化成立即开浏览器，
        轨 A 连尝试机会都没有。把证据随回执返回，才能判断该不该开
        `PPTX_HTML_APPS_TOOLS=always`，而不是把现象误判成「框架不支持 mcp-app」。

        **但本探针只描述「桥侧工具面」，不描述「宿主会不会弹面板」**。宿主内独立
        面板是另一条通路（daemon 侧 MCP App catalog → openHostApp），其准入由宿主
        自己的发现源决定，桥无法检测。发现源按**传输形态**过滤：
        `ConnectorService.buildDesiredConfigs()` 读 `mcp.json` 并把条目注册为
        `custom-mcp:<name>`，但 `McpAppsRemoteRuntime` 只 inspect 有 `url` 且无
        `command` 的 remote 条目；stdio 形态被 `isRemoteConfig()` 判为 skipped，
        本地手配的 stdio 桥因此不会被 catalog 收录（诊断日志 `catalogMiss` /
        `catalogHit` 恒为 0 次）。把桥以 remote(`url`) 形态注册即可进入发现源——
        这与 `PPTX_HTML_APPS_TOOLS=always` 无关。故 `host_panel_admission` 恒为
        `"host-owned"`，真正的实证只有运行时 `view_attached` / `await_intent.kind`。
        """
        mode = (os.environ.get("PPTX_HTML_APPS_TOOLS") or "auto").strip().lower()
        probe: dict[str, object] = {
            "apps_tools_mode": mode,
            # 面板准入归宿主：能力协商/工具面全开都**不**构成宿主会弹面板的证据。
            # 只有把配置从 stdio 改成 remote(url) 形态，宿主 catalog 才会发现本桥。
            # Agent 不得据 track=A / wake=notifyAgent / broadcast ok 向用户承诺内嵌视图。
            "host_panel_admission": "host-owned",
            "host_panel_evidence": "get_status.view_attached=true | await_intent.kind=mcp_app",
        }
        try:
            params = self._mcp_server.request_context.session.client_params
            caps = getattr(params, "capabilities", None)
            extra = getattr(caps, "model_extra", None) or {}
            exts = extra.get("extensions")
            probe["declared_extensions"] = sorted(exts.keys()) if isinstance(exts, dict) else []
            ui = exts.get(APPS_EXTENSION) if isinstance(exts, dict) else None
            probe["ui_extension_declared"] = isinstance(ui, dict)
            if isinstance(ui, dict) and isinstance(ui.get("mimeTypes"), list):
                probe["ui_mime_types"] = list(ui["mimeTypes"])
        except Exception as exc:
            probe["declared_extensions"] = []
            probe["client_params_error"] = type(exc).__name__
        probe["apps_declared"] = self.apps_declared()
        probe["apps_tools_listed"] = self.apps_tools_listed()
        ui_declared = bool(probe.get("ui_extension_declared"))
        declared = bool(probe["apps_declared"])
        listed = bool(probe["apps_tools_listed"])
        if listed and declared:
            reason = "宿主已按规范声明 UI 扩展，走标准轨 A"
        elif listed and not declared:
            reason = ("宿主未声明 UI 扩展，但运维开关放开了工具面（兼容模式）："
                      "桥侧轨 A 工具面已开放；宿主是否真的渲染内嵌面板由其 catalog 准入决定，"
                      "本探针无法判定，只以运行时 view_attached 为准")
        elif declared and not listed:
            reason = ("宿主已声明 UI 扩展，但 PPTX_HTML_APPS_TOOLS=never 强制冻结工具面，"
                      "轨 A 被运维关闭")
        elif ui_declared:
            reason = ("宿主声明了 io.modelcontextprotocol/ui，但 mimeTypes 不含 "
                      "text/html;profile=mcp-app：按规范判为不支持，轨 A 未开放")
        else:
            reason = ("宿主未声明 io.modelcontextprotocol/ui 且未开 "
                      "PPTX_HTML_APPS_TOOLS=always：工具面冻结到 5 个、"
                      "open_browser=auto 退化为立即开独立浏览器，轨 A 未被尝试")
        probe["reason"] = reason
        return probe

    def apps_tools_listed(self) -> bool:
        mode = (os.environ.get("PPTX_HTML_APPS_TOOLS") or "auto").strip().lower()
        if mode == "always":
            return True
        if mode == "never":
            return False
        return self.apps_declared()

    async def list_tools(self) -> list[Tool]:
        tools = await super().list_tools()
        # 工具标题在这里统一补齐（F11）：`title` 在规范里不是必填，但官方示例都给 app 工具
        # 标题，且宿主列表里这是唯一的人类可读名。集中一张表，不散进各工具装饰器。
        for tool in tools:
            if not tool.title:
                tool.title = TOOL_TITLES.get(tool.name)
        if self.apps_tools_listed():
            return tools
        return [tool for tool in tools if tool.name not in self._gated_names]


def consumer_id_for(workdir: str) -> str:
    """轨 A 的 consumer 身份：由 workdir 派生，**跨进程稳定**。

    宿主（如 langchain_mcp_adapters）可能每次工具调用都新起一个 stdio 进程，随机 UUID
    会让 `open_editor` 与后续调用落在不同 consumer 上。派生值让同一工作目录的所有进程
    共享一个身份——daemon 因此能在 MCP 重启后继续正确判定会话归属（见
    `BridgeCore.assert_consumer`）。测试 harness 复用本函数，避免两处各写一份。
    """
    return "mcp-" + hashlib.sha256(str(Path(workdir).resolve()).encode()).hexdigest()[:16]


class BridgeMCP:
    def __init__(self, workdir: str, *, allow_convert=False, allow_imagegen=False):
        self.workdir = str(Path(workdir).resolve())
        self.consumer_id = consumer_id_for(self.workdir)
        # daemon 懒解析（F1）：注册期早于 `initialize`，这里**不得**依赖 daemon 可用性——
        # 若在构造函数里就 `ensure_daemon`，任何失败（工作目录不可写、启动超时……）都会让
        # 整个 MCP server 崩溃，宿主看到的是"一个工具都没有"。改为首次调用时解析，
        # 失败以干净的工具错误（STORAGE_UNAVAILABLE）返回给模型与 View。
        self._allow_convert = allow_convert
        self._allow_imagegen = allow_imagegen
        self.discovery: dict[str, object] | None = None
        self._discovery_lock = threading.Lock()
        self.owned_sessions: set[str] = set()
        self.view_wait_sec = self._env_view_wait_sec()
        self._stop = asyncio.Event()

        @contextlib.asynccontextmanager
        async def lifespan(_server):
            task = asyncio.create_task(self._heartbeat())
            try:
                yield {}
            finally:
                self._stop.set()
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task

        self.mcp = BridgeFastMCP(
            name="pptx-html-bridge",
            instructions="Open an editor task, await explicit browser intents, modify only the assigned work_path, validate, then push an update.",
            log_level="ERROR",
            lifespan=lifespan,
            app_only_names=APP_ONLY_TOOL_NAMES,
            model_gated_names=MODEL_GATED_TOOL_NAMES,
        )
        # serverInfo.version（F7）：mcp 1.28 的 `FastMCP` 不接受 version 形参，低层 Server 于是
        # 回落成 SDK 自己的版本（实测报 1.28.0）。直接写低层实例属性，让 initialize 报**本应用**
        # 的版本——与 editor.html 同源，避免宿主日志里认不出服务身份。
        with contextlib.suppress(Exception):
            self.mcp._mcp_server.version = VIEW_VERSION
        self._register()

    @staticmethod
    def _env_view_wait_sec() -> float:
        raw = os.environ.get("PPTX_HTML_VIEW_WAIT_SEC")
        if raw is None or not str(raw).strip():
            return float(VIEW_WAIT_SEC_DEFAULT)
        try:
            return max(0.0, min(float(raw), float(VIEW_WAIT_SEC_MAX)))
        except ValueError:
            return float(VIEW_WAIT_SEC_DEFAULT)

    def _discovery(self) -> dict[str, object]:
        """解析（并缓存）daemon discovery；失败一律转成带 JSON 载荷的 ToolError。

        `ensure_daemon` 在 daemon 不可达时会同步尝试拉起（最长 10 秒），所以调用方
        必须经 `asyncio.to_thread` 走线程，别堵住事件循环。
        """
        if self.discovery is not None:
            return self.discovery
        with self._discovery_lock:
            if self.discovery is not None:
                return self.discovery
            try:
                self.discovery = ensure_daemon(self.workdir, allow_convert=self._allow_convert,
                                               allow_imagegen=self._allow_imagegen)
            except BridgeError as exc:
                raise ToolError(json.dumps(exc.payload(), ensure_ascii=False, separators=(",", ":"))) from exc
            except Exception as exc:
                raise ToolError(json.dumps(
                    {"ok": False, "error": {"code": "STORAGE_UNAVAILABLE",
                                            "message": f"bridge daemon 不可用：{exc}",
                                            "retryable": True, "details": {}}},
                    ensure_ascii=False, separators=(",", ":"))) from exc
            return self.discovery

    async def _request(self, path: str, body: dict, timeout=130):
        try:
            discovery = await asyncio.to_thread(self._discovery)
            return await asyncio.to_thread(admin_request, discovery, path, body, timeout)
        except ToolError:
            raise
        except BridgeError as exc:
            # 韧性：STORAGE_UNAVAILABLE（daemon 死/存储故障）时失效 discovery 缓存，让下次
            # _discovery 重新 ensure_daemon（其 verify_discovery 会探测旧地址，不通则重启
            # daemon）。业务错误（400/409 等）不清——daemon 仍健康，清了只多一次无谓重启。
            if exc.code == "STORAGE_UNAVAILABLE":
                self.discovery = None
            raise ToolError(json.dumps(exc.payload(), ensure_ascii=False, separators=(",", ":"))) from exc
        except Exception as exc:
            # 网络层异常（ConnectionRefused 等）穿透 admin_request 到这里 = daemon 不可达；
            # 失效缓存同上。下次 _discovery 拿不到缓存会重新 ensure_daemon。
            self.discovery = None
            raise ToolError(json.dumps({"ok":False,"error":{"code":"STORAGE_UNAVAILABLE","message":"bridge daemon unavailable","retryable":True,"details":{}}},separators=(",", ":"))) from exc

    async def _app_request(self, name: str, arguments: dict[str, Any], timeout: int = 60) -> str:
        """app-only 工具的统一出口：附 consumer 身份 → daemon 校验归属 → **JSON 文本**。

        必须返回字符串：宿主 `mcp_result_to_ui_text` 把 CallToolResult 剥成纯文本，
        `structuredContent` 不会到达 View（设计 §3.1 第 4 条）。
        """
        try:
            _method, path, body = build_request(name, arguments, consumer_id=self.consumer_id)
        except DispatchError as exc:
            raise ToolError(json.dumps(exc.payload(), ensure_ascii=False, separators=(",", ":"))) from exc
        result = await self._request(path, body, timeout=timeout)
        return json.dumps(result, ensure_ascii=False, separators=(",", ":"))

    async def _open(self, deck_path, output_path, view, open_browser, brief_options) -> dict[str, object]:
        """`open_editor` / `open_brief` 的共同出口——两条轨的开会话语义完全相同（设计 §0）。

        "auto" 的解析（设计 §10.7）：只有**本客户端可能渲染内嵌视图**时才起存在性窗口
        （声明了 UI 扩展，或运维用 PPTX_HTML_APPS_TOOLS=always 打开工具面）。
        否则按 true 走——不支持 MCP Apps 的宿主保持即时开浏览器行为，零回归。
        """
        resolved_open = open_browser
        if open_browser == "auto":
            resolved_open = "auto" if self.mcp.apps_tools_listed() else True
        result = await self._request("/api/bridge/open", {"consumer_id":self.consumer_id,"deck_path":deck_path,"output_path":output_path,"view":view,"open_browser":resolved_open,"brief_options":brief_options})
        self.owned_sessions.add(result["session_id"])
        declared = self.mcp.apps_declared()
        # `mode_hint` 只表达"宿主有没有按规范声明"；轨 A 通道是否开放由 `apps_tools_listed()`
        # 决定（它同时管工具面与 open_browser=auto 的存在性窗口）。两者在兼容模式下会分叉：
        # 宿主实现了 MCP Apps 却不声明扩展时，`always` 能让轨 A 跑起来，而 mode_hint 仍是 unknown。
        result["mode_hint"] = "mcp-app" if declared else "unknown"
        result["mode_source"] = "client-capabilities" if declared else "none"
        listed = self.mcp.apps_tools_listed()
        # 能力协商结果必须对模型**显式可见**：轨 B 没有 notifyAgent 敲门，页面提交只是入队。
        # 以前只回一个隐晦的 mode_hint=unknown，Agent 无从判断该不该在交付回复里写「回对话
        # 说继续」，于是出现「编辑器里发布了批注但 AI 没开始执行」。以下均为纯增量字段，
        # 不改任何既有语义；Skill §0 判轨表直接读 track/wake 作为判据。
        result["track"] = "A" if listed else "B"
        result["wake"] = "notifyAgent" if listed else "chat"
        result["track_basis"] = "capability-negotiation"
        # 静态回执不能证明 View 真的挂载过：运行时实证是 get_status.view_attached /
        # await_intent 回执 kind="mcp_app"（bridge_core 的 track_of 明确"不靠能力声明"）。
        result["wake_confirmed"] = False
        if not listed:
            hint = ("宿主未声明 MCP Apps UI 扩展、轨 A 通道未开放：页面提交只入队（pending），"
                    "Agent 不会自动开始；请在交付回复里让用户回对话说「继续」，再调 await_intent 认领")
        elif declared:
            hint = ("宿主已按规范声明 UI 扩展，内嵌视图提交 intent 后会敲门叫醒 Agent，"
                    "无需用户在对话里再说一次；仍以 view_attached 实证为准")
        else:
            hint = ("运维开关已放开轨 A 工具面，但宿主未声明 UI 扩展（兼容模式）："
                    "请先确认内嵌视图确实出现（get_status.view_attached=true 或 "
                    "await_intent 回执 kind=mcp_app）。若实际仍是独立浏览器页，"
                    "提交只入队，须让用户回对话说「继续」再 await_intent 认领")
        result["wake_hint"] = hint
        result["apps_tools_listed"] = listed
        result["capability_probe"] = self.mcp.apps_capability_probe()
        result["open_browser_resolved"] = resolved_open
        return result

    def _register(self):
        @self.mcp.tool(
            description="Open or reuse one managed editor task and render the **editing workbench** (edit / annotate / export). Registers this MCP consumer and may initialize the task's isolated Git protection ref. Returns a browser URL containing only a session-scoped browser credential. Does not acquire queue ownership or publish files. Requirements brainstorming is a separate tool in MCP Apps hosts — call open_brief for it; in those hosts this tool rejects view='brief'.",
            annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False),
            meta=_tool_meta(EDITOR_URI),
        )
        async def open_editor(
            deck_path: Annotated[str | None, Field(description="Absolute path to an existing trusted HTML deck inside the configured workdir, or null to create a new deck through the brief view.")] = None,
            output_path: Annotated[str, Field(description="Relative HTML target path inside the configured workdir for a new deck; ignored as a source path for an existing deck.")] = "index.html",
            view: Annotated[Literal["edit", "brief", "annotate", "export"], Field(description="Editor view to open: brief for new-deck requirements, edit or annotate for existing work, or export for delivery review.")] = "edit",
            open_browser: Annotated[bool | Literal["auto"], Field(description="'auto' (default) starts a bounded existence window for an embedded MCP Apps view and only opens a standalone browser when no UI signal arrives; true opens the browser immediately; false never opens it.")] = "auto",
            brief_options: Annotated[dict[str, object] | None, Field(description="Optional dynamic brief-options object (version 2, kind 'brief-options'; see the briefing v2 schema). The daemon validates it, stores it at session level, and echoes it in session state; a provided value replaces the stored one, while omitting it keeps the stored value. Invalid input is rejected without changing the stored value.")] = None,
        ) -> dict[str, object]:
            # 轨 A：脑暴是**独立工具 + 独立资源**（`open_brief`），因为呈现形态由 View 声明、
            # 一个 View 只能有一份声明（设计 §3.2）。这样报错而不是静默按编辑器资源打开——
            # 静默会把脑暴塞进编辑器的侧栏，正是本次拆分要消除的形态。
            if view == "brief" and self.mcp.apps_tools_listed():
                raise ToolError(json.dumps({
                    "ok": False,
                    "error": {
                        "code": "INVALID_ARGUMENT",
                        "message": "view='brief' 在本宿主不适用：脑暴已拆为独立工具，请调用 open_brief(...)",
                        "retryable": False,
                        "details": {"use_instead": "open_brief", "views": ["edit", "annotate", "export"]},
                    },
                }, ensure_ascii=False, separators=(",", ":")))
            return await self._open(deck_path, output_path, view, open_browser, brief_options)

        @self.mcp.tool(
            description="Open the requirements brainstorming page for a new deck (or a re-alignment pass on an existing one) in a managed editor task. The page renders inline in the conversation, collects the design brief, and submits it as an intent; it is not the editing workbench.",
            annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False),
            meta=_tool_meta(BRIEF_URI),
        )
        async def open_brief(
            deck_path: Annotated[str | None, Field(description="Absolute path to an existing trusted HTML deck inside the configured workdir when the brief is a re-alignment pass, or null to create a new deck from the brief.")] = None,
            output_path: Annotated[str, Field(description="Relative HTML target path inside the configured workdir for a new deck; ignored as a source path for an existing deck.")] = "index.html",
            open_browser: Annotated[bool | Literal["auto"], Field(description="'auto' (default) starts a bounded existence window for an embedded MCP Apps view and only opens a standalone browser when no UI signal arrives; true opens the browser immediately; false never opens it.")] = "auto",
            brief_options: Annotated[dict[str, object] | None, Field(description="Optional dynamic brief-options object (version 2, kind 'brief-options'; see the briefing v2 schema). The daemon validates it, stores it at session level, and echoes it in session state; a provided value replaces the stored one, while omitting it keeps the stored value. Invalid input is rejected without changing the stored value.")] = None,
        ) -> dict[str, object]:
            return await self._open(deck_path, output_path, "brief", open_browser, brief_options)

        @self.mcp.tool(
            description=f"Atomically acquire this registered consumer's waiting lease and wait for the earliest pending browser intent. Timeout is bounded to {AWAIT_TIMEOUT_MIN_SEC}-{AWAIT_TIMEOUT_MAX_SEC} seconds and defaults to one day. After claim, processing ownership is durable and does not time-expire; the same owner receives the same attempt until complete, fail, explicit stop/close, or daemon restart. Cancellation only stops this wait and never deletes an intent.",
            annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False),
        )
        async def await_intent(
            session_id: Annotated[str, Field(min_length=1, description="Session identifier returned by open_editor for the managed editor task.")],
            timeout_sec: Annotated[int, Field(ge=AWAIT_TIMEOUT_MIN_SEC, le=AWAIT_TIMEOUT_MAX_SEC, description="Maximum seconds to wait for a pending browser intent before returning a normal timeout result; defaults to 86400 seconds (one day).")] = AWAIT_TIMEOUT_DEFAULT_SEC,
        ) -> dict[str, object]:
            arbitration = await self._arbitrate_view(session_id, timeout_sec)
            if arbitration is not None:
                return arbitration
            return await self._request("/api/bridge/await", {"session_id":session_id,"consumer_id":self.consumer_id,"timeout_sec":timeout_sec}, timeout=timeout_sec+AWAIT_HTTP_TIMEOUT_MARGIN_SEC)

        @self.mcp.tool(
            description="Report progress, fail the current attempt, or complete it. Complete publishes only the daemon-assigned attempt work copy after ownership, revision, exact validation evidence, artifact and journal checks. It never accepts arbitrary source paths or shell commands. Successful complete retries return the original persisted receipt.",
            annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True, idempotentHint=False, openWorldHint=False),
        )
        async def push_update(
            action: Annotated[Literal["progress", "complete", "fail", "abort"], Field(description="progress refreshes processing liveness telemetry without publishing or extending an ownership deadline; complete validates and publishes; fail records a terminal failure without publishing; abort records that the producer stopped without finishing — the intent becomes interrupted, the work copy is kept and both resume and rebuild stay available. Use abort when the user terminates the turn so the daemon stops showing a phantom 'processing'.")],
            session_id: Annotated[str | None, Field(description="Session identifier that owns the claimed intent; required for progress/complete/fail. **Optional for action=abort** — omitting it (together with intent_id/attempt) aborts whatever in-flight intent this consumer currently holds, resolved from the consumer registration.")] = None,
            intent_id: Annotated[str | None, Field(description="Intent identifier returned by await_intent; required for progress/complete/fail. **Optional for action=abort** — omitting it means 'abort whatever this consumer currently holds' (the framework's cancel path uses this: it knows the session but not the intent id).")] = None,
            attempt: Annotated[int | None, Field(description="Positive attempt number returned by await_intent; required for progress/complete/fail, optional for abort.")] = None,
            message: Annotated[str, Field(max_length=2000, description="Human-readable progress, completion, or actionable failure summary.")] = "",
            validation: Annotated[ValidationEvidence | None, Field(description="Required exact validation evidence for complete; omit for progress and fail.")] = None,
        ) -> dict[str, object]:
            evidence = (validation.model_dump(exclude={"export_source_revision"} if validation.export_source_revision is None else set())
                        if validation is not None else None)
            return await self._request("/api/bridge/update", {"session_id":session_id,"intent_id":intent_id,"attempt":attempt,"consumer_id":self.consumer_id,"action":action,"message":message,"validation":evidence})

        @self.mcp.tool(
            description="Return the source revision of the assigned attempt work copy — the exact value push_update(action='complete') requires as validation.candidate_revision. Call it once after every check has passed and touch no file afterwards: reading it again after any write yields a different value, and complete will be refused (that fence is the point of the field). Read-only — it changes no state, extends no lease and emits no event.",
            annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False),
        )
        async def get_revision(
            session_id: Annotated[str, Field(min_length=1, description="Session identifier that owns the claimed intent.")],
            intent_id: Annotated[str, Field(min_length=1, description="Intent identifier returned by await_intent.")],
            attempt: Annotated[int, Field(ge=1, description="Positive attempt number returned by await_intent.")],
        ) -> dict[str, object]:
            return await self._request("/api/bridge/revision", {"session_id":session_id,"intent_id":intent_id,"attempt":attempt,"consumer_id":self.consumer_id})

        @self.mcp.tool(
            description="Read persistent task, revision, export freshness, browser, queue, recovery and capability state. This is read-only and does not register or acquire a consumer lease.",
            annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False),
        )
        async def get_status(
            session_id: Annotated[str, Field(min_length=1, description="Session identifier whose persistent bridge state should be read.")],
        ) -> dict[str, object]:
            result = await self._request("/api/bridge/status", {"session_id":session_id})
            # 零副作用判轨：get_status 是只读探针，过去只能靠有副作用的 open_editor 回执
            # 才知道 apps_tools_mode。补上能力协商诊断后，Agent 可在任意回合直接确认当前
            # 连接属于轨 A 还是轨 B；改 PPTX_HTML_APPS_TOOLS 后必须重连 MCP 才生效，
            # 用本字段即可验证重连是否成功，不必再开一次编辑器。
            result["capability_probe"] = self.mcp.apps_capability_probe()
            return result

        @self.mcp.tool(
            description="Pause only this MCP consumer, interrupt its unfinished attempt, release its owner lease, and require a later explicit open_editor before awaiting again. It does not stop the daemon or browser and does not delete pending work, drafts, history or files.",
            annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True, idempotentHint=True, openWorldHint=False),
        )
        async def close_session(
            session_id: Annotated[str, Field(min_length=1, description="Session identifier to pause for this MCP consumer.")],
            reason: Annotated[str, Field(max_length=2000, description="Short reason recorded when the consumer releases the session and interrupts its unfinished attempt.")] = "user-ended",
        ) -> dict[str, object]:
            result = await self._request("/api/bridge/close", {"session_id":session_id,"consumer_id":self.consumer_id,"reason":reason})
            self.owned_sessions.discard(session_id)
            return result

        self._register_app_only_tools()

    def _register_app_only_tools(self):
        """9 个 app-only 工具（设计 §4.3；1027 精简前为 13 个，见 `docs/progress/1027_tool_surface_slimming.md`）。全部双写 `visibility:["app"]`，返回 JSON 文本。"""
        @self.mcp.tool(description="Attach this embedded view to a bridge session. Call immediately after the view is ready, and again while polling, so the daemon can tell an embedded MCP Apps view apart from a standalone browser tab.", annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=False), meta=dict(APP_ONLY_META))
        async def attach_view(session_id: SessionId, client: Annotated[str | None, Field(description="Optional opaque client identifier for diagnostics.")] = None) -> str:
            return await self._app_request("attach_view", {"session_id": session_id, "client": client})

        @self.mcp.tool(description="Read the task's managed target HTML as text, together with the revision it was read at. The standalone editor reads the same bytes over its own credentialed HTTP channel.", annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False), meta=dict(APP_ONLY_META))
        async def read_deck(session_id: SessionId, path: Annotated[str | None, Field(description="Optional workspace-relative path; only the session's registered target HTML is accepted.")] = None) -> str:
            return await self._app_request("read_deck", {"session_id": session_id, "path": path}, timeout=120)

        @self.mcp.tool(description="Read one registered file inside the managed bundle as base64 with its mime type and sha256, so the sandboxed view can render images and deliver artifacts without a same-origin fetch. assets/ and fonts/ read image and font assets; export/ reads export artifacts such as manifest.json or native/page-01.png. Sizes above the daemon limit are refused so the caller can fall back to collecting the file from the workspace.", annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False), meta=dict(APP_ONLY_META))
        async def read_bundle_file(session_id: SessionId, path: Annotated[str, Field(min_length=1, description="Bundle-relative path: assets/... or fonts/... for image and font assets, export/... for export artifacts.")]) -> str:
            return await self._app_request("read_bundle_file", {"session_id": session_id, "path": path}, timeout=120)

        @self.mcp.tool(description="Save the target HTML through the same CAS and receipt path the standalone editor uses. A stale base_revision is refused; never retry with a fabricated revision.", annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True, idempotentHint=False, openWorldHint=False), meta=dict(APP_ONLY_META))
        async def save_deck(session_id: SessionId, path: Annotated[str, Field(min_length=1, description="Workspace-relative target HTML path; must be the session's registered target.")], html: Annotated[str, Field(description="Full serialized HTML document.")], base_revision: Annotated[str | None, Field(description="Revision the document was derived from, or null for a first write.")] = None, init: Annotated[bool, Field(description="Set true only to confirm initializing Git protection when the workspace has no baseline yet.")] = False) -> str:
            return await self._app_request("save_deck", {"session_id": session_id, "path": path, "html": html, "base_revision": base_revision, "init": init})

        @self.mcp.tool(description="Overwrite one managed image asset (same-name replacement) and record the revision. Used by the embedded view's image replacement; the standalone editor writes the same asset through its own channel.", annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True, idempotentHint=False, openWorldHint=False), meta=dict(APP_ONLY_META))
        async def write_asset(session_id: SessionId, path: Annotated[str, Field(min_length=1, description="Workspace-relative path inside assets/.")], data_base64: Annotated[str, Field(min_length=1, description="Base64 image bytes.")], base_revision: Annotated[str | None, Field(description="Revision the page is displaying, or null.")] = None) -> str:
            return await self._app_request("write_asset", {"session_id": session_id, "path": path, "data_base64": data_base64, "base_revision": base_revision}, timeout=180)

        @self.mcp.tool(description="Submit a user intent through the same validation and queue as the standalone editor. Reuse the same intent_id when retrying so the request stays idempotent.", annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=False), meta=dict(APP_ONLY_META))
        async def submit_intent(session_id: SessionId, intent_id: Annotated[str, Field(min_length=1, description="UUID generated by the view; reuse it verbatim when retrying the same request.")], type: Annotated[Literal["brief.submitted", "design.submitted", "anno.submitted", "convert.requested", "bake.requested", "illustrate.requested"], Field(description="Intent type.")], payload: Annotated[dict[str, Any], Field(description="Intent payload matching the type's schema.")], base_revision: Annotated[str | None, Field(description="Revision the view is showing; instruction intents are rebased by the daemon, artifact intents are refused when stale.")] = None) -> str:
            return await self._app_request("submit_intent", {"session_id": session_id, "intent_id": intent_id, "type": type, "payload": payload, "base_revision": base_revision})

        @self.mcp.tool(description="Write a server-side draft. The sandboxed view has no localStorage, IndexedDB or cookie storage, so this is its only draft channel and its last line of defence when the host tears the view down.", annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False), meta=dict(APP_ONLY_META))
        async def save_draft(session_id: SessionId, client_id: Annotated[str, Field(min_length=1, description="Stable id for this view instance.")], html: Annotated[str, Field(description="Serialized HTML snapshot; empty string when nothing is loaded yet.")], annotations: Annotated[list[Any], Field(description="Annotation list belonging to the snapshot.")], base_revision: Annotated[str | None, Field(description="Revision the snapshot was taken from, or null.")] = None) -> str:
            return await self._app_request("save_draft", {"session_id": session_id, "client_id": client_id, "html": html, "annotations": annotations, "base_revision": base_revision}, timeout=180)

        @self.mcp.tool(description="Adopt the workspace's current bytes as the new published baseline (drift repair). Needed when someone changed the managed file outside the CAS: afterwards the daemon and the workspace agree again, so intents can be claimed and published. It writes no business file — it re-scans, records reality and keeps a snapshot of the previous state, so the old baseline stays revertible. Idempotent: if nothing drifted it reports aligned=false.", annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=False), meta=dict(APP_ONLY_META))
        async def rebaseline(session_id: SessionId) -> str:
            return await self._app_request("rebaseline", {"session_id": session_id})

        @self.mcp.tool(description="List the Git-protected version history of the target HTML. The sandboxed view cannot read the workspace, so history must come through this tool.", annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False), meta=dict(APP_ONLY_META))
        async def list_versions(session_id: SessionId, path: Annotated[str, Field(min_length=1, description="Workspace-relative target HTML path.")]) -> str:
            return await self._app_request("list_versions", {"session_id": session_id, "path": path}, timeout=120)

        @self.mcp.tool(description="Roll the target HTML back to a version hash through the same CAS and snapshot machinery as a save. Protects the current state first.", annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True, idempotentHint=False, openWorldHint=False), meta=dict(APP_ONLY_META))
        async def rollback(session_id: SessionId, path: Annotated[str, Field(min_length=1, description="Workspace-relative target HTML path.")], hash: Annotated[str, Field(min_length=1, description="Version hash returned by list_versions.")], base_revision: Annotated[str | None, Field(description="Current server revision, or null.")] = None) -> str:
            return await self._app_request("rollback", {"session_id": session_id, "path": path, "hash": hash, "base_revision": base_revision}, timeout=180)

        @self.mcp.resource(
            EDITOR_URI,
            name="pptx-html-bridge-editor",
            title="PPTX-HTML 编辑器",
            description="Editor workbench view (edit / annotate / compare) rendered by an MCP Apps host.",
            mime_type=VIEW_MIME,
            # `prefersBorder` 显式声明（F11）：规范建议显式给，因为宿主默认值不一致。
            # 取 False —— 工作台自带完整 chrome（顶栏 / 侧栏 / 背景），再叠宿主边框会双重框住。
            meta={"ui": {"permissions": {"clipboardWrite": {}}, "prefersBorder": False}},
        )
        def editor_view() -> str:
            return self._view_html_for("editor")

        @self.mcp.resource(
            BRIEF_URI,
            name="pptx-html-bridge-brief",
            title="PPTX-HTML 需求脑暴",
            description="Requirements brainstorming page rendered inline by an MCP Apps host; submits the brief as an intent and is not the editing workbench.",
            mime_type=VIEW_MIME,
            # 与编辑器相反：脑暴是对话流里的表单，需要宿主的边界与底色把自己从正文里分出来。
            meta={"ui": {"prefersBorder": True}},
        )
        def brief_view() -> str:
            return self._view_html_for("brief")

    def _view_html_for(self, variant: str) -> str:
        """按变体缓存合成视图（同一份源码 + 注入的呈现变体常量，见 `build_view_html`）。"""
        html = self.mcp._view_html.get(variant)
        if html is None:
            html = build_view_html(variant)
            self.mcp._view_html[variant] = html
        return html

    async def _arbitrate_view(self, session_id: str, timeout_sec: int) -> dict[str, object] | None:
        """轨道仲裁（设计 §4.2）。三条硬化：

        ① **已决即采用**：本会话已出现 `view_attached` → 直接判定轨 A（返回 mcp_app 结果，
           不阻塞）；已出现浏览器心跳 → 按轨 B 走既有阻塞逻辑；
        ② **自解除**：只有"本会话从未出现过任何 UI 信号"才付窗口时间；一旦出现过信号，
           后续每次 await 都跳过仲裁 —— 轨 B 只在第一次 await 付一次短窗口；
        ③ **窗口 = 存在性窗口 + 4s**，且一旦有 pending/processing 意图立刻结束仲裁。

        窗口从 `timeout_sec` 里扣：`await_intent(timeout_sec=1)` 这种轮询用法窗口为 0，
        不会被仲裁吃掉时延（SKILL 里"用户不点确认"的兜底路径必须保持轻快）。

        放在 MCP 层而不是 `BridgeCore.await_intent` 里：这里才知道客户端能力，而且
        不动双轨共用的阻塞语义（core 单测与 HTTP 层回归因此零影响）。
        """
        def snapshot(status: dict[str, object]) -> str:
            if status.get("view_attached"):
                return "mcp-app"
            if status.get("page_online"):
                return "bridge"
            if not status.get("ui_signal_ever"):
                return "pending"
            return "bridge"
        try:
            status = await self._request("/api/bridge/status", {"session_id": session_id}, timeout=10)
        except ToolError:
            raise
        decision = snapshot(status)
        if decision == "mcp-app":
            return self._mcp_app_result(session_id, status)
        window = min(self.view_wait_sec + VIEW_ARBITRATION_MARGIN_SEC, max(0, timeout_sec - 1))
        if decision != "pending" or window <= 0:
            return None
        deadline = asyncio.get_running_loop().time() + window
        while True:
            await asyncio.sleep(0.25)
            try:
                status = await self._request("/api/bridge/status", {"session_id": session_id}, timeout=10)
            except ToolError:
                return None
            decision = snapshot(status)
            if decision == "mcp-app":
                return self._mcp_app_result(session_id, status)
            if decision == "bridge":
                return None
            if status.get("pending_count") or status.get("processing"):
                return None
            if asyncio.get_running_loop().time() >= deadline:
                return None

    @staticmethod
    def _mcp_app_result(session_id: str, status: dict[str, object]) -> dict[str, object]:
        return {"ok": True, "kind": "mcp_app", "session_id": session_id, "track": "mcp-app",
                "view_attached": True, "agent_state": status.get("agent_state"),
                "page_online": status.get("page_online"),
                "note": "编辑器已嵌入宿主（MCP Apps 轨），不要阻塞：结束本回合，用户在页面提交后编辑器会主动敲门；"
                        "若用户说已在页面操作而你没有收到请求，用 await_intent(timeout_sec=1) 主动查一次。"}

    async def _heartbeat(self):
        while not self._stop.is_set():
            await asyncio.sleep(15)
            for session_id in tuple(self.owned_sessions):
                try:
                    await self._request("/api/bridge/heartbeat", {"protocol_version":2,"role":"consumer","session_id":session_id,"consumer_id":self.consumer_id}, timeout=5)
                except ToolError:
                    pass

    def run(self):
        self.mcp.run(transport="stdio")


def run(workdir: str, *, allow_convert=False, allow_imagegen=False):
    BridgeMCP(workdir, allow_convert=allow_convert, allow_imagegen=allow_imagegen).run()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: bridge_mcp.py WORKDIR", file=sys.stderr)
        raise SystemExit(2)
    run(sys.argv[1])
