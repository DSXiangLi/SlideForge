#!/usr/bin/env python3
"""编辑器 View（MCP Apps 轨）到 Bridge 路由的映射层。

轨 B 的浏览器用 loopback HTTP + browser 凭证直连 daemon；轨 A 的 View 在宿主 iframe
里既没有凭证也不能 fetch（不透明源 → CORS），只能经宿主代理调用 app-only 工具。
本模块是这批工具的**唯一路由真相**：工具名 → 方法/路径/字段契约，加上工具层的
二次校验（session 归属），供 `tools/bridge_mcp.py` 注册 app-only 工具时使用。

设计依据：`docs/design/mcp-apps-upgrade.md` §4.3（工具面）、§5.8（宿主 isolation 缺口
→ 全部自校验）、§6.2（server 侧改造清单）。本模块不依赖 MCP 包，也不做 I/O。
"""
from __future__ import annotations

import uuid

# 每个 app-only 工具的字段契约。required/optional 之外的字段一律拒绝（防宿主代理塞私货）。
OPERATIONS: dict[str, dict] = {
    "attach_view": {
        "method": "POST", "path": "/api/bridge/attach",
        "required": ("session_id",), "optional": ("client",),
        "summary": "View 连接后立即上报，用于轨道判定（实证信号，不靠能力声明）。",
    },
    "read_deck": {
        "method": "POST", "path": "/api/bridge/read",
        "required": ("session_id",), "optional": ("path",),
        "summary": "读取本任务受管的目标 HTML（默认 target_path），返回文本与当前 revision。",
    },
    "read_asset": {
        "method": "POST", "path": "/api/bridge/asset-read",
        "required": ("session_id", "path"), "optional": (),
        "summary": "读取受管 assets/ 或 fonts/ 内的已登记资产，返回 base64 与 sha256。",
    },
    "read_export": {
        "method": "POST", "path": "/api/bridge/export-read",
        "required": ("session_id", "file"), "optional": (),
        "summary": "读取本任务 export/ 内的已登记产物（如 manifest.json、native/page-01.png），返回 base64 与字节数。",
    },
    "save_deck": {
        "method": "POST", "path": "/api/save",
        "required": ("session_id", "path", "html", "base_revision"), "optional": ("init",),
        "summary": "经 CAS 保存目标 HTML 并等待 receipt；语义与轨 B 的 POST /api/save 完全一致。",
    },
    "write_asset": {
        "method": "POST", "path": "/api/bridge/asset",
        "required": ("session_id", "path", "data_base64", "base_revision"), "optional": (),
        "summary": "同名覆盖写入受管 assets/ 图片，语义与轨 B 的 POST /api/bridge/asset 一致。",
    },
    "submit_intent": {
        "method": "POST", "path": "/api/intent",
        "required": ("intent_id", "session_id", "type", "base_revision", "payload"), "optional": ("client_ts",),
        "summary": "提交意图（同一 accept_intent 校验与入队）。intent_id 由 View 生成并在重试时复用，保证幂等。",
        "defaults": {"protocol_version": 2},
    },
    "cancel_intent": {
        "method": "POST", "path": "/api/intent/cancel",
        "required": ("session_id", "intent_id"), "optional": (),
        "summary": "取消尚未认领的意图，或作为批次合并的审计标记。",
    },
    "retry_intent": {
        "method": "POST", "path": "/api/intent/retry",
        "required": ("session_id", "intent_id", "retry_id", "expected_attempt", "mode", "base_revision", "confirmed"), "optional": (),
        "summary": "按 rebuild|resume 恢复中断的意图；必须显式 confirmed=true。",
    },
    "query_intents": {
        "method": "POST", "path": "/api/intents/query",
        "required": ("session_id",), "optional": ("statuses", "cursor", "limit", "intent_id"),
        "summary": "分页查询意图列表或单条意图，用于无 SSE 的轮询恢复。",
    },
    "save_draft": {
        "method": "POST", "path": "/api/bridge/draft",
        "required": ("session_id", "client_id", "html", "annotations", "base_revision"), "optional": (),
        "summary": "服务端草稿。轨 A 无 localStorage/indexedDB，这是唯一的草稿通道。",
    },
    "list_versions": {
        "method": "GET", "path": "/api/versions",
        "required": ("session_id", "path"), "optional": (),
        "summary": "列出 Git 隔离 ref 中的版本历史。",
    },
    "rollback": {
        "method": "POST", "path": "/api/rollback",
        "required": ("session_id", "path", "hash", "base_revision"), "optional": (),
        "summary": "按版本 hash 回滚目标 HTML，走与 save 相同的 CAS 与快照机制。",
    },
}

# 与桥的五工具区分：这些只对 View 开放（宿主要求 visibility:["app"] 根级 + ui 双写）。
APP_ONLY_TOOL_NAMES = tuple(OPERATIONS)


class DispatchError(Exception):
    """工具层校验失败。bridge_mcp 会把它转成与 daemon 同形状的 ToolError。"""

    def __init__(self, code: str, message: str, retryable=False):
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = bool(retryable)

    def payload(self):
        return {"ok": False, "error": {"code": self.code, "message": self.message,
                                       "retryable": self.retryable, "details": {}}}


def operation(name: str) -> dict:
    spec = OPERATIONS.get(name)
    if spec is None:
        raise DispatchError("INVALID_ARGUMENT", f"未知的 app-only 工具: {name}")
    return spec


def _is_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def build_request(name: str, arguments, *, owned_sessions):
    """校验并构造 daemon 请求。

    返回 (method, path, body)；GET 操作的筛选条件拼进 path 的 query。
    `owned_sessions` 是本 consumer 通过 open_editor 登记过的 session 集合——
    工具层自校验，不依赖宿主鉴权（宿主 isolation 缺口仍在）。
    """
    spec = operation(name)
    if arguments is None:
        arguments = {}
    if not isinstance(arguments, dict):
        raise DispatchError("INVALID_ARGUMENT", f"{name} 的 arguments 必须是对象")
    args = dict(arguments)
    allowed = set(spec["required"]) | set(spec["optional"])
    unknown = sorted(set(args) - allowed)
    if unknown:
        raise DispatchError("INVALID_ARGUMENT", f"{name} 收到未声明字段: {unknown}")
    # base_revision is allowed to be None (null) for submit_intent, save_deck, etc.
    # but the key must still be present for submit_intent (checked later per-tool).
    _nullable_fields = {"base_revision"}
    missing = sorted(f for f in spec["required"] if f not in args or (args.get(f) is None and f not in _nullable_fields))
    if missing:
        raise DispatchError("INVALID_ARGUMENT", f"{name} 缺少必填字段: {missing}")
    session_id = args.get("session_id")
    if not isinstance(session_id, str) or not session_id:
        raise DispatchError("INVALID_ARGUMENT", f"{name} 的 session_id 必须是非空字符串")
    if owned_sessions is not None and session_id not in owned_sessions:
        raise DispatchError("SESSION_NOT_OWNED",
                            f"{name} 的 session 不属于本 consumer；请先 open_editor 登记（MCP 重启后需重新打开）")
    body = {k: v for k, v in args.items() if v is not None or k == "base_revision"}
    body.update(spec.get("defaults") or {})

    if name == "submit_intent":
        if not isinstance(body.get("payload"), dict):
            raise DispatchError("INVALID_ARGUMENT", "submit_intent 的 payload 必须是对象")
        if body.get("type") not in {"brief.submitted", "design.submitted", "anno.submitted",
                                    "convert.requested", "bake.requested", "illustrate.requested"}:
            raise DispatchError("INVALID_ARGUMENT", f"未知 intent type: {body.get('type')!r}")
        try:
            uuid.UUID(str(body["intent_id"]))
        except (ValueError, AttributeError, TypeError):
            raise DispatchError("INVALID_ARGUMENT", "submit_intent 的 intent_id 必须是 UUID")
        if "base_revision" not in body:
            raise DispatchError("INVALID_ARGUMENT", "submit_intent 必须带 base_revision（可为 null）")
        import datetime as _dt
        body.setdefault("client_ts", _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"))
    elif name in ("save_deck", "write_asset", "rollback", "save_draft"):
        for field in ("path", "html", "data_base64"):
            if field in body and not isinstance(body[field], str):
                raise DispatchError("INVALID_ARGUMENT", f"{name} 的 {field} 必须是字符串")
        if name == "save_draft" and not isinstance(body.get("annotations"), list):
            raise DispatchError("INVALID_ARGUMENT", "save_draft 的 annotations 必须是数组")
        if "init" in body and type(body["init"]) is not bool:
            raise DispatchError("INVALID_ARGUMENT", "save_deck 的 init 必须是布尔值")
        if "base_revision" in body and body["base_revision"] is not None and not isinstance(body["base_revision"], str):
            raise DispatchError("INVALID_ARGUMENT", f"{name} 的 base_revision 必须是字符串或 null")
    elif name == "query_intents":
        if "cursor" in body and not _is_int(body["cursor"]):
            raise DispatchError("INVALID_ARGUMENT", "query_intents 的 cursor 必须是整数")
        if "limit" in body and not _is_int(body["limit"]):
            raise DispatchError("INVALID_ARGUMENT", "query_intents 的 limit 必须是整数")
        if "statuses" in body and not isinstance(body["statuses"], list):
            raise DispatchError("INVALID_ARGUMENT", "query_intents 的 statuses 必须是数组")
    elif name == "retry_intent":
        if not _is_int(body.get("expected_attempt")) or body["expected_attempt"] < 1:
            raise DispatchError("INVALID_ARGUMENT", "retry_intent 的 expected_attempt 必须是正整数")
        if body.get("mode") not in {"rebuild", "resume"}:
            raise DispatchError("INVALID_ARGUMENT", "retry_intent 的 mode 必须是 rebuild 或 resume")
        if body.get("confirmed") is not True:
            raise DispatchError("INVALID_ARGUMENT", "retry_intent 必须显式 confirmed=true")
    elif name == "read_asset":
        if not str(body.get("path", "")).startswith(("assets/", "fonts/")):
            raise DispatchError("INVALID_ARGUMENT", "read_asset 的 path 必须位于受管 assets/ 或 fonts/ 内")

    path = spec["path"]
    if spec["method"] == "GET":
        from urllib.parse import quote
        query = "&".join(f"{k}={quote(str(body[k]), safe='')}" for k in sorted(body) if k != "session_id")
        query = f"session_id={quote(str(body['session_id']))}" + (f"&{query}" if query else "")
        return "GET", f"{path}?{query}", None
    return spec["method"], path, body


def tool_descriptions() -> dict[str, str]:
    return {name: spec["summary"] for name, spec in OPERATIONS.items()}
