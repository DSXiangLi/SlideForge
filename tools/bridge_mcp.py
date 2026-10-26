#!/usr/bin/env python3
"""Official MCP SDK stdio proxy for the editor/agent bridge daemon.

双轨（设计 `docs/design/mcp-apps-upgrade.md`）：

- **轨 B（现状）**：五个面向模型的工具经 `admin_request` 走 loopback HTTP 到 daemon；
  独立浏览器标签页用 browser 凭证直连同一 daemon。
- **轨 A（MCP Apps）**：宿主把资源 `ui://pptx-html-bridge/editor.html` 渲染进 iframe，
  View 经宿主代理调用 13 个 `visibility:["app"]` 工具；这些工具同样落到同一个 daemon，
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

VIEW_URI = "ui://pptx-html-bridge/editor.html"
VIEW_MIME = "text/html;profile=mcp-app"
APPS_EXTENSION = "io.modelcontextprotocol/ui"
VIEW_BUNDLE_PATH = PROJECT_ROOT / "tools" / "ext_apps_bundle.js"
VIEW_MANIFEST_PATH = PROJECT_ROOT / "tools" / "ext_apps_bundle.json"
VIEW_SIZE_LIMIT = 2 * 1024 * 1024          # 宿主硬限制：超限静默回退纯文本（设计 §5.7）
VIEW_SIZE_WARN = int(1.5 * 1024 * 1024)    # 构建期告警线
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
# （实测 18 个工具的 title 全是 None，审计 F11）。集中一张表，避免散在 18 个装饰器里。
TOOL_TITLES = {
    "open_editor": "打开编辑器",
    "await_intent": "等待用户意图",
    "push_update": "回写发布",
    "get_status": "读取任务状态",
    "close_session": "结束会话",
    "attach_view": "附着内嵌视图",
    "read_deck": "读取目标 HTML",
    "read_asset": "读取图片资产",
    "read_export": "读取导出产物",
    "save_deck": "保存目标 HTML",
    "write_asset": "写入图片资产",
    "submit_intent": "提交用户意图",
    "cancel_intent": "取消意图",
    "retry_intent": "恢复中断意图",
    "query_intents": "查询意图",
    "save_draft": "保存服务端草稿",
    "list_versions": "列出历史版本",
    "rollback": "回滚到历史版本",
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

# app-only 工具的共用参数注记。必须放在模块级：`from __future__ import annotations`
# 会把注解变成字符串，FastMCP 用函数的 __globals__ 求值，闭包内定义的名字解析不到。
SessionId = Annotated[str, Field(min_length=1, description="Session identifier returned by open_editor.")]


def _tool_meta(resource_uri: str | None = None) -> dict[str, Any]:
    meta: dict[str, Any] = {"visibility": ["model", "app"]}
    ui: dict[str, Any] = {"visibility": ["model", "app"]}
    if resource_uri:
        ui["resourceUri"] = resource_uri
        meta["ui/resourceUri"] = resource_uri
    meta["ui"] = ui
    return meta


def build_view_html() -> str:
    """把 editor.html 与注入的 View SDK bundle 合成一个自包含资源（无外链）。"""
    html = (PROJECT_ROOT / "editor.html").read_text(encoding="utf-8")
    if not VIEW_BUNDLE_PATH.exists():
        raise RuntimeError("缺少 View bundle：先跑 python3 tools/build_ext_apps_bundle.py")
    bundle = VIEW_BUNDLE_PATH.read_text(encoding="utf-8")
    hits = sorted({m.group(0) for m in EXTERNAL_REF_RE.finditer(html)})
    if hits:
        raise RuntimeError("View HTML 含外链引用，违反 CSP 前提：" + ", ".join(hits[:5]))
    boot = VIEW_BOOTSTRAP
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
    这样轨 B（当前唯一真实宿主）看到的仍是恰好五个工具，红线不被 13 个 app-only
    工具污染；声明了扩展的宿主看到全部 18 个，其中 13 个是 `visibility:["app"]`。

    环境变量 `PPTX_HTML_APPS_TOOLS`：`auto`（默认）| `always` | `never`。
    `always` 供"能渲染 widget 却不声明扩展"的宿主（如 SproutHarness）使用。
    """

    def __init__(self, *args, app_only_names=(), **kwargs):
        self._app_only_names = set(app_only_names)
        super().__init__(*args, **kwargs)
        self._view_html: str | None = None

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
        # 标题，且宿主列表里这是唯一的人类可读名。集中一张表，不散进 18 个装饰器。
        for tool in tools:
            if not tool.title:
                tool.title = TOOL_TITLES.get(tool.name)
        if self.apps_tools_listed():
            return tools
        return [tool for tool in tools if tool.name not in self._app_only_names]


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
            raise ToolError(json.dumps(exc.payload(), ensure_ascii=False, separators=(",", ":"))) from exc
        except Exception as exc:
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

    def _register(self):
        @self.mcp.tool(
            description="Open or reuse one managed editor task in the configured workdir. Registers this MCP consumer and may initialize the task's isolated Git protection ref. Returns a browser URL containing only a session-scoped browser credential. Does not acquire queue ownership or publish files.",
            annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False),
            meta=_tool_meta(VIEW_URI),
        )
        async def open_editor(
            deck_path: Annotated[str | None, Field(description="Absolute path to an existing trusted HTML deck inside the configured workdir, or null to create a new deck through the brief view.")] = None,
            output_path: Annotated[str, Field(description="Relative HTML target path inside the configured workdir for a new deck; ignored as a source path for an existing deck.")] = "index.html",
            view: Annotated[Literal["edit", "brief", "annotate", "export"], Field(description="Editor view to open: brief for new-deck requirements, edit or annotate for existing work, or export for delivery review.")] = "edit",
            open_browser: Annotated[bool | Literal["auto"], Field(description="'auto' (default) starts a bounded existence window for an embedded MCP Apps view and only opens a standalone browser when no UI signal arrives; true opens the browser immediately; false never opens it.")] = "auto",
            brief_options: Annotated[dict[str, object] | None, Field(description="Optional dynamic brief-options object (version 2, kind 'brief-options'; see the briefing v2 schema). The daemon validates it, stores it at session level, and echoes it in session state; a provided value replaces the stored one, while omitting it keeps the stored value. Invalid input is rejected without changing the stored value.")] = None,
        ) -> dict[str, object]:
            # "auto" 的解析（设计 §10.7）：只有**本客户端可能渲染内嵌视图**时才起存在性窗口
            # （声明了 UI 扩展，或运维用 PPTX_HTML_APPS_TOOLS=always 打开工具面）。
            # 否则按 true 走——不支持 MCP Apps 的宿主保持今天的即时开浏览器行为，零回归。
            resolved_open = open_browser
            if open_browser == "auto":
                resolved_open = "auto" if self.mcp.apps_tools_listed() else True
            result = await self._request("/api/bridge/open", {"consumer_id":self.consumer_id,"deck_path":deck_path,"output_path":output_path,"view":view,"open_browser":resolved_open,"brief_options":brief_options})
            self.owned_sessions.add(result["session_id"])
            # mode_hint 只是乐观提示：两家真实宿主都不声明 UI 扩展，设计必须在"恒为 unknown"下正确（§4.2）
            result["mode_hint"] = "mcp-app" if self.mcp.apps_declared() else "unknown"
            result["mode_source"] = "client-capabilities" if self.mcp.apps_declared() else "none"
            result["open_browser_resolved"] = resolved_open
            return result

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
            session_id: Annotated[str, Field(min_length=1, description="Session identifier that owns the claimed intent.")],
            intent_id: Annotated[str, Field(min_length=1, description="Intent identifier returned by await_intent; must match the current claimed request.")],
            attempt: Annotated[int, Field(ge=1, description="Positive attempt number returned by await_intent; rebuild and resume both increment it, while resume may safely reuse the registered prior work_path.")],
            action: Annotated[Literal["progress", "complete", "fail"], Field(description="progress refreshes processing liveness telemetry without publishing or extending an ownership deadline; complete validates and publishes, and fail records a terminal failure without publishing.")],
            message: Annotated[str, Field(max_length=2000, description="Human-readable progress, completion, or actionable failure summary.")] = "",
            validation: Annotated[ValidationEvidence | None, Field(description="Required exact validation evidence for complete; omit for progress and fail.")] = None,
        ) -> dict[str, object]:
            evidence = (validation.model_dump(exclude={"export_source_revision"} if validation.export_source_revision is None else set())
                        if validation is not None else None)
            return await self._request("/api/bridge/update", {"session_id":session_id,"intent_id":intent_id,"attempt":attempt,"consumer_id":self.consumer_id,"action":action,"message":message,"validation":evidence})

        @self.mcp.tool(
            description="Read persistent task, revision, export freshness, browser, queue, recovery and capability state. This is read-only and does not register or acquire a consumer lease.",
            annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False),
        )
        async def get_status(
            session_id: Annotated[str, Field(min_length=1, description="Session identifier whose persistent bridge state should be read.")],
        ) -> dict[str, object]:
            return await self._request("/api/bridge/status", {"session_id":session_id})

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
        """13 个 app-only 工具（设计 §4.3）。全部双写 `visibility:["app"]`，返回 JSON 文本。"""
        @self.mcp.tool(description="Attach this embedded view to a bridge session. Call immediately after the view is ready, and again while polling, so the daemon can tell an embedded MCP Apps view apart from a standalone browser tab.", annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=False), meta=dict(APP_ONLY_META))
        async def attach_view(session_id: SessionId, client: Annotated[str | None, Field(description="Optional opaque client identifier for diagnostics.")] = None) -> str:
            return await self._app_request("attach_view", {"session_id": session_id, "client": client})

        @self.mcp.tool(description="Read the task's managed target HTML as text, together with the revision it was read at. The standalone editor reads the same bytes over its own credentialed HTTP channel.", annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False), meta=dict(APP_ONLY_META))
        async def read_deck(session_id: SessionId, path: Annotated[str | None, Field(description="Optional workspace-relative path; only the session's registered target HTML is accepted.")] = None) -> str:
            return await self._app_request("read_deck", {"session_id": session_id, "path": path}, timeout=120)

        @self.mcp.tool(description="Read one registered asset (assets/ or fonts/ inside the managed bundle) as base64 with its mime type and sha256, so the sandboxed view can render images without a same-origin fetch.", annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False), meta=dict(APP_ONLY_META))
        async def read_asset(session_id: SessionId, path: Annotated[str, Field(min_length=1, description="Workspace-relative path inside the managed assets/ or fonts/ directory.")]) -> str:
            return await self._app_request("read_asset", {"session_id": session_id, "path": path}, timeout=120)

        @self.mcp.tool(description="Read one registered export artifact (export/ inside the managed bundle, e.g. manifest.json or native/page-01.png) as base64. Sizes above the daemon limit are refused so the caller can fall back to collecting the file from the workspace.", annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False), meta=dict(APP_ONLY_META))
        async def read_export(session_id: SessionId, file: Annotated[str, Field(min_length=1, description="Path relative to the managed export/ directory.")]) -> str:
            return await self._app_request("read_export", {"session_id": session_id, "file": file}, timeout=120)

        @self.mcp.tool(description="Save the target HTML through the same CAS and receipt path the standalone editor uses. A stale base_revision is refused; never retry with a fabricated revision.", annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True, idempotentHint=False, openWorldHint=False), meta=dict(APP_ONLY_META))
        async def save_deck(session_id: SessionId, path: Annotated[str, Field(min_length=1, description="Workspace-relative target HTML path; must be the session's registered target.")], html: Annotated[str, Field(description="Full serialized HTML document.")], base_revision: Annotated[str | None, Field(description="Revision the document was derived from, or null for a first write.")] = None, init: Annotated[bool, Field(description="Set true only to confirm initializing Git protection when the workspace has no baseline yet.")] = False) -> str:
            return await self._app_request("save_deck", {"session_id": session_id, "path": path, "html": html, "base_revision": base_revision, "init": init})

        @self.mcp.tool(description="Overwrite one managed image asset (same-name replacement) and record the revision. Used by the embedded view's image replacement; the standalone editor writes the same asset through its own channel.", annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True, idempotentHint=False, openWorldHint=False), meta=dict(APP_ONLY_META))
        async def write_asset(session_id: SessionId, path: Annotated[str, Field(min_length=1, description="Workspace-relative path inside assets/.")], data_base64: Annotated[str, Field(min_length=1, description="Base64 image bytes.")], base_revision: Annotated[str | None, Field(description="Revision the page is displaying, or null.")] = None) -> str:
            return await self._app_request("write_asset", {"session_id": session_id, "path": path, "data_base64": data_base64, "base_revision": base_revision}, timeout=180)

        @self.mcp.tool(description="Submit a user intent through the same validation and queue as the standalone editor. Reuse the same intent_id when retrying so the request stays idempotent.", annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=False), meta=dict(APP_ONLY_META))
        async def submit_intent(session_id: SessionId, intent_id: Annotated[str, Field(min_length=1, description="UUID generated by the view; reuse it verbatim when retrying the same request.")], type: Annotated[Literal["brief.submitted", "design.submitted", "anno.submitted", "convert.requested", "bake.requested", "illustrate.requested"], Field(description="Intent type.")], payload: Annotated[dict[str, Any], Field(description="Intent payload matching the type's schema.")], base_revision: Annotated[str | None, Field(description="Revision the view is showing; instruction intents are rebased by the daemon, artifact intents are refused when stale.")] = None) -> str:
            return await self._app_request("submit_intent", {"session_id": session_id, "intent_id": intent_id, "type": type, "payload": payload, "base_revision": base_revision})

        @self.mcp.tool(description="Cancel a pending intent, or mark one as merged into another batch. Leaves an audit trail; it never deletes history and cannot stop work that already runs outside the bridge.", annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True, idempotentHint=True, openWorldHint=False), meta=dict(APP_ONLY_META))
        async def cancel_intent(session_id: SessionId, intent_id: Annotated[str, Field(min_length=1, description="Intent identifier to cancel.")]) -> str:
            return await self._app_request("cancel_intent", {"session_id": session_id, "intent_id": intent_id})

        @self.mcp.tool(description="Recover an interrupted or failed intent in rebuild or resume mode. Requires explicit confirmation because resume may reuse a work copy a still-running process could write to, and rebuild may repeat external work and cost.", annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True, idempotentHint=False, openWorldHint=False), meta=dict(APP_ONLY_META))
        async def retry_intent(session_id: SessionId, intent_id: Annotated[str, Field(min_length=1, description="Intent identifier to recover.")], retry_id: Annotated[str, Field(min_length=1, description="UUID; reuse it to make the retry request idempotent.")], expected_attempt: Annotated[int, Field(ge=1, description="Attempt number the caller believes is current.")], mode: Annotated[Literal["rebuild", "resume"], Field(description="rebuild creates an isolated fresh copy; resume reuses the registered prior work copy.")], base_revision: Annotated[str | None, Field(description="Current server revision, or null.")] = None, confirmed: Annotated[bool, Field(description="Must be true; the caller acknowledges the costs above.")] = False) -> str:
            return await self._app_request("retry_intent", {"session_id": session_id, "intent_id": intent_id, "retry_id": retry_id, "expected_attempt": expected_attempt, "mode": mode, "base_revision": base_revision, "confirmed": confirmed})

        @self.mcp.tool(description="Page through intents, or fetch one by id. Polled by the embedded view because MCP Apps has no server-sent events.", annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False), meta=dict(APP_ONLY_META))
        async def query_intents(session_id: SessionId, statuses: Annotated[list[str] | None, Field(description="Optional status filter.")] = None, cursor: Annotated[int | None, Field(ge=0, description="Last seen seq; omit for the first page.")] = None, limit: Annotated[int | None, Field(ge=1, le=100, description="Page size.")] = None, intent_id: Annotated[str | None, Field(description="Fetch a single intent by id instead of paging.")] = None) -> str:
            return await self._app_request("query_intents", {"session_id": session_id, "statuses": statuses, "cursor": cursor, "limit": limit, "intent_id": intent_id})

        @self.mcp.tool(description="Write a server-side draft. The sandboxed view has no localStorage, IndexedDB or cookie storage, so this is its only draft channel and its last line of defence when the host tears the view down.", annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False), meta=dict(APP_ONLY_META))
        async def save_draft(session_id: SessionId, client_id: Annotated[str, Field(min_length=1, description="Stable id for this view instance.")], html: Annotated[str, Field(description="Serialized HTML snapshot; empty string when nothing is loaded yet.")], annotations: Annotated[list[Any], Field(description="Annotation list belonging to the snapshot.")], base_revision: Annotated[str | None, Field(description="Revision the snapshot was taken from, or null.")] = None) -> str:
            return await self._app_request("save_draft", {"session_id": session_id, "client_id": client_id, "html": html, "annotations": annotations, "base_revision": base_revision}, timeout=180)

        @self.mcp.tool(description="List the Git-protected version history of the target HTML. The sandboxed view cannot read the workspace, so history must come through this tool.", annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False), meta=dict(APP_ONLY_META))
        async def list_versions(session_id: SessionId, path: Annotated[str, Field(min_length=1, description="Workspace-relative target HTML path.")]) -> str:
            return await self._app_request("list_versions", {"session_id": session_id, "path": path}, timeout=120)

        @self.mcp.tool(description="Roll the target HTML back to a version hash through the same CAS and snapshot machinery as a save. Protects the current state first.", annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True, idempotentHint=False, openWorldHint=False), meta=dict(APP_ONLY_META))
        async def rollback(session_id: SessionId, path: Annotated[str, Field(min_length=1, description="Workspace-relative target HTML path.")], hash: Annotated[str, Field(min_length=1, description="Version hash returned by list_versions.")], base_revision: Annotated[str | None, Field(description="Current server revision, or null.")] = None) -> str:
            return await self._app_request("rollback", {"session_id": session_id, "path": path, "hash": hash, "base_revision": base_revision}, timeout=180)

        @self.mcp.resource(
            VIEW_URI,
            name="pptx-html-bridge-editor",
            title="PPTX-HTML 编辑器",
            description="Editor workbench view (edit / annotate / compare) rendered by an MCP Apps host.",
            mime_type=VIEW_MIME,
            # `prefersBorder` 显式声明（F11）：规范建议显式给，因为宿主默认值不一致。
            # 取 False —— 工作台自带完整 chrome（顶栏 / 侧栏 / 背景），再叠宿主边框会双重框住。
            meta={"ui": {"permissions": {"clipboardWrite": {}}, "prefersBorder": False}},
        )
        def editor_view() -> str:
            if self.mcp._view_html is None:
                self.mcp._view_html = build_view_html()
            return self.mcp._view_html

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
