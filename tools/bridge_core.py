#!/usr/bin/env python3
"""Persistent editor/agent bridge core and standard-library HTTP daemon."""
from __future__ import annotations

import argparse
import base64
import binascii
import contextlib
import datetime as dt
import fcntl
import hashlib
import hmac
import html as _html
import json
import mimetypes
import os
import re
import secrets
import select
import shutil
import socket
import sqlite3
import stat
import subprocess
import sys
import tempfile
import threading
import time
import uuid
import webbrowser
import xml.etree.ElementTree as ET
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path, PurePosixPath
from urllib.parse import parse_qs, quote, unquote, urlsplit
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

PROTOCOL_VERSION = 2
CONTROL_BODY_MAX = 2 * 1024 * 1024
INTENT_PAYLOAD_MAX = 1024 * 1024
INTENT_INLINE_MAX = 16 * 1024
DOCUMENT_BODY_MAX = 64 * 1024 * 1024
ASSET_BODY_MAX = 48 * 1024 * 1024
ASSET_RAW_MAX = 32 * 1024 * 1024
BOOTSTRAP_TTL_SEC = 300
CONSUMER_LEASE_SEC = 90
CLIENT_ONLINE_SEC = 45
# MCP Apps 轨：View 的 attach_view 存续判定与"存在性窗口"（设计 §4.2）。
# 仲裁相位本身在 MCP 层（tools/bridge_mcp.py）——那里才知道客户端能力，
# 且改 core 的 await_intent 会牵动双轨共用的阻塞语义。
VIEW_WAIT_SEC_DEFAULT = 8
VIEW_WAIT_SEC_MAX = 120
VIEW_SIGNAL_STALE_SEC = 30
# app-only 工具读取上限（base64 经 JSON 中转，别把内存吃光）
DOCUMENT_READ_MAX = 8 * 1024 * 1024
ARTIFACT_READ_MAX = 24 * 1024 * 1024
SSE_PING_SEC = 15
AWAIT_TIMEOUT_MIN_SEC = 1
AWAIT_TIMEOUT_DEFAULT_SEC = 86400
AWAIT_TIMEOUT_MAX_SEC = 86400
INTERNAL_STORAGE_MAX = 10 * 1024 ** 3
BUNDLE_MAX = 2 * 1024 ** 3
BUNDLE_FILE_MAX = 20_000
MIN_FREE_BYTES = 512 * 1024 ** 2
SCHEMA_VERSION = 3
PROJECT_ROOT = Path(__file__).resolve().parent.parent
INTERNAL = ".pptx-html"
SOURCE_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"}
SOURCE_LEGACY_EXTS = {".wmf", ".emf"}
SOURCE_FONT_EXTS = {".woff2", ".woff", ".ttf", ".otf"}
EXPORT_EXTS = {".pptx", ".pdf", ".svg", ".png", ".json"}
DERIVED_NAMES = {"manifest.json", ".manifest-baseline.json", "capacity-report.json"}
INTENT_TYPES = {"brief.submitted", "design.submitted", "anno.submitted", "convert.requested", "bake.requested", "illustrate.requested"}
INSTRUCTION_INTENT_TYPES = {"brief.submitted", "design.submitted", "anno.submitted"}
INTENT_STATUSES = {"pending", "processing", "succeeded", "failed", "conflict", "interrupted", "cancelled"}
UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$", re.I)
REVISION_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
INLINE_RASTER_DATA_RE = re.compile(
    r"data:image/(png|jpeg);base64,([A-Za-z0-9+/]*={0,2})", re.I)

BRIEF_GROUP_IDS = {"scene", "audience", "source", "pages", "style", "font", "motion", "cover",
                   "x-data", "x-brand", "x-fidelity"}
BRIEF_GROUP_STATES = {"ask", "prefilled", "skipped"}
THEME_PICK_ID_RE = re.compile(r"^[a-z0-9]+(/[a-z0-9-]+)?$")


def validate_brief_options(value):
    """校验动态脑暴 brief_options（docs/design/brief-dynamic-brainstorming.md §6）。
    超限一律拒绝（fail-fast），错误消息指出具体字段；合法时原样返回。"""
    def fail(field, msg):
        raise BridgeError(400, "INVALID_ARGUMENT", f"brief_options.{field}: {msg}" if field else f"brief_options: {msg}")
    if not isinstance(value, dict):
        fail("", "必须为对象")
    if not set(value) <= {"version", "kind", "context_summary", "profile", "groups", "theme_pick", "static_fallback"}:
        fail("", "顶层含未知字段: " + ",".join(sorted(set(value) - {"version", "kind", "context_summary", "profile", "groups", "theme_pick", "static_fallback"})))
    if isinstance(value.get("version"), bool) or value.get("version") != 2:
        fail("version", "必须为整数 2")
    if value.get("kind") != "brief-options":
        fail("kind", '必须为 "brief-options"')
    summary = value.get("context_summary")
    if summary is not None and (not isinstance(summary, str) or len(summary) > 500):
        fail("context_summary", "必须为 ≤500 字字符串")
    profile = value.get("profile")
    if profile is not None:
        if not isinstance(profile, dict) or not set(profile) <= {"signals"}:
            fail("profile", "必须为对象且仅含 signals")
        signals = profile.get("signals")
        if signals is not None and (not isinstance(signals, list) or len(signals) > 12
                                    or any(not isinstance(s, str) or len(s) > 60 for s in signals)):
            fail("profile.signals", "必须为 ≤12 项字符串数组，每项 ≤60 字")
    if "static_fallback" in value and not isinstance(value["static_fallback"], bool):
        fail("static_fallback", "必须为 boolean")
    groups = value.get("groups")
    if not isinstance(groups, list):
        fail("groups", "必填且必须为数组")
    for i, g in enumerate(groups):
        p = f"groups[{i}]"
        if not isinstance(g, dict) or not set(g) <= {"id", "title", "impact", "state", "prefill_reason", "multi", "options"}:
            fail(p, "必须为对象且仅含 id/title/impact/state/prefill_reason/multi/options")
        if g.get("id") not in BRIEF_GROUP_IDS:
            fail(p + ".id", "维度 id 不在固定枚举内（八维度 + x-data/x-brand/x-fidelity）")
        for key in ("title", "impact"):
            if not isinstance(g.get(key), str) or not g.get(key):
                fail(p + "." + key, "必填非空字符串")
        state = g.get("state")
        if state not in BRIEF_GROUP_STATES:
            fail(p + ".state", "必填且必须为 ask|prefilled|skipped")
        reason = g.get("prefill_reason")
        if state in ("prefilled", "skipped") and (not isinstance(reason, str) or not reason.strip()):
            fail(p + ".prefill_reason", "prefilled/skipped 必填非空推断依据")
        if reason is not None and not isinstance(reason, str):
            fail(p + ".prefill_reason", "必须为字符串")
        if not isinstance(g.get("multi"), bool):
            fail(p + ".multi", "必填且必须为 boolean")
        options = g.get("options")
        if not isinstance(options, list):
            fail(p + ".options", "必填且必须为数组")
        if len(options) > 6:
            fail(p + ".options", "每组至多 6 项")
        if state == "ask" and not 2 <= len(options) <= 6:
            fail(p + ".options", "ask 组必须 2–6 项")
        for j, o in enumerate(options):
            q = f"{p}.options[{j}]"
            if not isinstance(o, dict) or not set(o) <= {"id", "label", "desc", "recommended", "default", "reason"}:
                fail(q, "必须为对象且仅含 id/label/desc/recommended/default/reason")
            for key in ("id", "label", "desc"):
                if not isinstance(o.get(key), str) or not o.get(key):
                    fail(q + "." + key, "必填非空字符串")
            if len(o["label"]) > 30:
                fail(q + ".label", "必须 ≤30 字")
            if len(o["desc"]) > 120:
                fail(q + ".desc", "必须 ≤120 字")
            for key in ("recommended", "default"):
                if key in o and not isinstance(o[key], bool):
                    fail(q + "." + key, "必须为 boolean")
            if "reason" in o and (not isinstance(o["reason"], str) or len(o["reason"]) > 120):
                fail(q + ".reason", "必须为 ≤120 字字符串")
    theme_pick = value.get("theme_pick")
    if theme_pick is not None:
        if not isinstance(theme_pick, dict) or not set(theme_pick) <= {"recommended", "reason", "library_open"}:
            fail("theme_pick", "必须为对象且仅含 recommended/reason/library_open")
        recommended = theme_pick.get("recommended")
        if (not isinstance(recommended, list) or not 1 <= len(recommended) <= 3
                or any(not isinstance(x, str) or not THEME_PICK_ID_RE.fullmatch(x) for x in recommended)):
            fail("theme_pick.recommended", "必须为 1–3 个主题/变体 id（形如 e3 或 e3/red）")
        if "reason" in theme_pick and (not isinstance(theme_pick["reason"], str) or len(theme_pick["reason"]) > 200):
            fail("theme_pick.reason", "必须为 ≤200 字字符串")
        if "library_open" in theme_pick and not isinstance(theme_pick["library_open"], bool):
            fail("theme_pick.library_open", "必须为 boolean")
    return value


def valid_inline_raster_data_uri(value: str) -> bool:
    match = INLINE_RASTER_DATA_RE.fullmatch(value.strip())
    if not match:
        return False
    try:
        raw = base64.b64decode(match.group(2), validate=True)
    except (binascii.Error, ValueError):
        return False
    mime = match.group(1).lower()
    return (mime == "png" and raw.startswith(b"\x89PNG\r\n\x1a\n")) or (
        mime == "jpeg" and raw.startswith(b"\xff\xd8\xff"))


def utcnow() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def parse_time(value: str | None) -> float:
    if not value:
        return 0.0
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()


def future(seconds: int) -> str:
    return (dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=seconds)).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def canonical_json(value) -> bytes:
    def reject(value):
        raise ValueError("non-finite number")
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False, default=reject).encode("utf-8")


def digest_json(value) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def token_digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def new_id(prefix: str) -> str:
    return prefix + secrets.token_urlsafe(18)


def revision_from_records(records: list[list], domain: bytes) -> str | None:
    if not records:
        return None
    encoded = json.dumps(records, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(domain + encoded).hexdigest()


def file_hash(path: Path) -> tuple[str, int]:
    h = hashlib.sha256()
    size = 0
    with path.open("rb") as f:
        while True:
            part = f.read(1024 * 1024)
            if not part:
                break
            h.update(part)
            size += len(part)
    return h.hexdigest(), size


def _safe_regular(path: Path, root: Path, allow_missing=False) -> None:
    try:
        rel = path.relative_to(root)
    except ValueError:
        raise BridgeError(403, "PATH_DENIED", "路径越出工作区")
    if any(p in ("", ".", "..") or "\\" in p or "\x00" in p for p in rel.parts):
        raise BridgeError(403, "PATH_DENIED", "非法路径")
    cur = root
    for part in rel.parts:
        cur = cur / part
        if not cur.exists() and allow_missing:
            continue
        try:
            info = cur.lstat()
        except FileNotFoundError:
            if allow_missing:
                continue
            raise BridgeError(403, "PATH_DENIED", "文件不存在")
        if stat.S_ISLNK(info.st_mode):
            raise BridgeError(403, "PATH_DENIED", "拒绝符号链接")
    if path.exists():
        info = path.stat()
        if not stat.S_ISREG(info.st_mode) or info.st_nlink > 1:
            raise BridgeError(403, "PATH_DENIED", "拒绝非普通文件或硬链接")


def normalize_rel(value: str, *, suffix: str | None = None) -> str:
    if not isinstance(value, str) or not value or "\x00" in value or "\\" in value:
        raise BridgeError(400, "INVALID_ARGUMENT", "非法路径")
    p = PurePosixPath(value)
    if p.is_absolute() or any(x in ("", ".", "..") for x in p.parts):
        raise BridgeError(403, "PATH_DENIED", "路径必须是工作区相对路径")
    rel = p.as_posix()
    if any(part.lower() in {INTERNAL, ".git"} for part in p.parts):
        raise BridgeError(403, "PATH_DENIED", "内部目录不可访问")
    if suffix and not rel.lower().endswith(suffix):
        raise BridgeError(400, "INVALID_ARGUMENT", "目标文件类型错误")
    return rel


class BridgeError(Exception):
    def __init__(self, status: int, code: str, message: str, retryable=False, details=None):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.retryable = bool(retryable)
        self.details = details or {}

    def payload(self):
        return {"ok": False, "error": {"code": self.code, "message": self.message,
                "retryable": self.retryable, "details": self.details}}


class SecureRoot:
    def __init__(self, root: Path):
        required=("O_DIRECTORY","O_NOFOLLOW")
        if any(not hasattr(os,name) for name in required) or os.open not in os.supports_dir_fd or os.rename not in os.supports_dir_fd:
            raise BridgeError(503,"STORAGE_UNAVAILABLE","当前平台不支持安全的 dir_fd/O_NOFOLLOW 文件访问")
        self.root=root
        self.fd=os.open(root,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        st=os.fstat(self.fd);self.identity=(st.st_dev,st.st_ino)

    def close(self):
        if self.fd is not None:os.close(self.fd);self.fd=None

    def _parts(self,rel):
        value=str(rel)
        if not value or "\x00" in value or "\\" in value:
            raise BridgeError(403,"PATH_DENIED","非法安全路径")
        path=PurePosixPath(value)
        if path.is_absolute() or any(part in ("",".","..") for part in path.parts):
            raise BridgeError(403,"PATH_DENIED","非法安全路径")
        return path.parts

    def parent_fd(self,rel,create=False):
        parts=self._parts(rel);fd=os.dup(self.fd)
        try:
            for part in parts[:-1]:
                if create:
                    with contextlib.suppress(FileExistsError):os.mkdir(part,0o700,dir_fd=fd)
                nxt=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd);os.close(fd);fd=nxt
            return fd,parts[-1]
        except BaseException:
            os.close(fd);raise

    def open_read(self,rel):
        parent,name=self.parent_fd(rel)
        try:fd=os.open(name,os.O_RDONLY|os.O_NOFOLLOW,dir_fd=parent)
        finally:os.close(parent)
        st=os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or st.st_nlink!=1:
            os.close(fd);raise BridgeError(403,"PATH_DENIED","拒绝非普通文件、符号链接或硬链接")
        return fd,st

    def hash(self,rel):
        fd,st=self.open_read(rel);h=hashlib.sha256()
        try:
            while True:
                chunk=os.read(fd,1024*1024)
                if not chunk:break
                h.update(chunk)
        finally:os.close(fd)
        return h.hexdigest(),st.st_size

    def read(self,rel):
        fd,st=self.open_read(rel);parts=[]
        try:
            while True:
                chunk=os.read(fd,1024*1024)
                if not chunk:break
                parts.append(chunk)
        finally:os.close(fd)
        return b"".join(parts)

    def copy_out(self,rel,destination):
        source,_=self.open_read(rel)
        destination.parent.mkdir(parents=True,exist_ok=True)
        try:
            with destination.open("wb") as out:
                while True:
                    chunk=os.read(source,1024*1024)
                    if not chunk:break
                    out.write(chunk)
        finally:os.close(source)

    def atomic_replace_from(self,rel,source):
        parent,name=self.parent_fd(rel,create=True);tmp=".bridge-"+secrets.token_hex(12)
        try:
            src=os.open(source,os.O_RDONLY|os.O_NOFOLLOW);sst=os.fstat(src)
            if not stat.S_ISREG(sst.st_mode) or sst.st_nlink!=1:
                os.close(src);raise BridgeError(403,"PATH_DENIED","候选文件不是安全普通文件")
            out=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=parent)
            try:
                while True:
                    chunk=os.read(src,1024*1024)
                    if not chunk:break
                    os.write(out,chunk)
                os.fsync(out)
            finally:os.close(src);os.close(out)
            os.replace(tmp,name,src_dir_fd=parent,dst_dir_fd=parent);os.fsync(parent)
        finally:
            with contextlib.suppress(FileNotFoundError):os.unlink(tmp,dir_fd=parent)
            os.close(parent)

    def unlink(self,rel):
        parent,name=self.parent_fd(rel)
        try:os.unlink(name,dir_fd=parent);os.fsync(parent)
        finally:os.close(parent)

    def exists(self,rel):
        try:
            fd,_=self.open_read(rel);os.close(fd);return True
        except FileNotFoundError:return False


class WorkdirLock:
    def __init__(self, path: Path):
        self.path = path
        self.fd = None

    def acquire(self, blocking=False):
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.fd = os.open(self.path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        flags = fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB)
        try:
            fcntl.flock(self.fd, flags)
        except BlockingIOError:
            os.close(self.fd)
            self.fd = None
            return False
        return True

    def close(self):
        if self.fd is not None:
            fcntl.flock(self.fd, fcntl.LOCK_UN)
            os.close(self.fd)
            self.fd = None


class BridgeCore:
    def __init__(self, workdir: str | Path, *, allow_convert=False, require_lock=False, fault_injector=None,
                 allow_imagegen=False, imagegen_provider=None):
        os.umask(0o077)
        self.workdir = Path(workdir).resolve(strict=True)
        if not self.workdir.is_dir():
            raise BridgeError(400, "INVALID_ARGUMENT", "工作目录不存在")
        self.secure = SecureRoot(self.workdir)
        self.internal = self.workdir / INTERNAL
        if self.internal.exists():
            st = self.internal.lstat()
            if stat.S_ISLNK(st.st_mode) or not stat.S_ISDIR(st.st_mode) or st.st_uid != os.getuid():
                raise BridgeError(503, "STORAGE_UNAVAILABLE", "内部目录权限或类型不安全")
        else:
            self.internal.mkdir(mode=0o700)
        os.chmod(self.internal, 0o700)
        for name in ("intents", "jobs", "snapshots", "drafts", "transactions", "git-index"):
            (self.internal / name).mkdir(mode=0o700, exist_ok=True)
        self.lock = WorkdirLock(self.internal / "daemon.lock")
        if require_lock and not self.lock.acquire():
            raise BridgeError(409, "SESSION_BUSY", "该工作区已有 daemon")
        self.instance_id = new_id("inst_")
        self.management_token = secrets.token_urlsafe(32)
        self.allow_convert = bool(allow_convert)
        self.allow_imagegen = bool(allow_imagegen)
        self.imagegen_provider = imagegen_provider
        self.origin = None
        self.ready = False
        self.frozen = False
        self._fault_injector = fault_injector
        self._db_lock = threading.RLock()
        self._conditions: dict[str, threading.Condition] = {}
        self._session_locks: dict[str, threading.RLock] = {}
        self._stop = threading.Event()
        self.view_wait_sec = self._env_view_wait_sec()
        self._convert_lock = threading.RLock()
        self._convert_state = {"status":"idle","session_id":None,"intent_id":None,"started":None,"tail":""}
        self._imagegen_lock = threading.RLock()
        self._imagegen_state = {"status":"idle","session_id":None,"intent_id":None,"started":None,"tail":"","slots":[]}
        self.db = sqlite3.connect(self.internal / "bridge.sqlite3", timeout=5, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA busy_timeout=5000")
        self.db.execute("PRAGMA synchronous=FULL")
        self._migrate()
        self.recover_publications()
        self._invalidate_previous_instance()
        self.ready = True

    def begin_shutdown(self):
        self.ready = False
        self._stop.set()
        for condition in list(self._conditions.values()):
            with condition:
                condition.notify_all()

    def close(self):
        self.begin_shutdown()
        with self._db_lock:
            self.db.close()
        self.lock.close()
        self.secure.close()

    def _fault(self, point, **context):
        if self._fault_injector is not None:
            self._fault_injector(point, context)

    def _migrate(self):
        with self.db:
            self.db.executescript("""
            CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS sessions(
              id TEXT PRIMARY KEY,target_path TEXT NOT NULL UNIQUE,deck_path TEXT,phase TEXT NOT NULL,
              created_at TEXT NOT NULL,updated_at TEXT NOT NULL,revision TEXT,export_revision TEXT,
              export_source_revision TEXT,agent_state TEXT NOT NULL DEFAULT 'offline',owner_consumer_id TEXT,
              git_ready INTEGER NOT NULL DEFAULT 0,git_ref TEXT,brief_options_json TEXT);
            CREATE TABLE IF NOT EXISTS consumers(
              session_id TEXT NOT NULL,consumer_id TEXT NOT NULL,state TEXT NOT NULL,registered_at TEXT NOT NULL,
              requires_open INTEGER NOT NULL DEFAULT 0,lease_until TEXT,
              PRIMARY KEY(session_id,consumer_id),FOREIGN KEY(session_id) REFERENCES sessions(id));
            CREATE TABLE IF NOT EXISTS browser_tokens(
              token_digest TEXT PRIMARY KEY,session_id TEXT NOT NULL,client_id TEXT,created_at TEXT NOT NULL,revoked_at TEXT,
              FOREIGN KEY(session_id) REFERENCES sessions(id));
            CREATE TABLE IF NOT EXISTS bootstrap_tokens(
              token_digest TEXT PRIMARY KEY,instance_id TEXT NOT NULL,mode TEXT NOT NULL,target_path TEXT NOT NULL,
              expires_at TEXT NOT NULL,used_at TEXT);
            CREATE TABLE IF NOT EXISTS intents(
              id TEXT PRIMARY KEY,session_id TEXT NOT NULL,seq INTEGER NOT NULL UNIQUE,type TEXT NOT NULL,payload_json TEXT NOT NULL,
              payload_digest TEXT NOT NULL,payload_bytes INTEGER NOT NULL,base_revision TEXT,status TEXT NOT NULL,
              consumer_id TEXT,lease_until TEXT,attempt INTEGER NOT NULL DEFAULT 1,result_json TEXT,error_json TEXT,
              created_at TEXT NOT NULL,updated_at TEXT NOT NULL,UNIQUE(session_id,id),
              FOREIGN KEY(session_id) REFERENCES sessions(id));
            CREATE INDEX IF NOT EXISTS intents_session_status_seq ON intents(session_id,status,seq);
            CREATE TABLE IF NOT EXISTS attempts(
              session_id TEXT NOT NULL,intent_id TEXT NOT NULL,attempt INTEGER NOT NULL,base_revision TEXT,work_path TEXT,
              consumer_id TEXT,status TEXT NOT NULL,result_json TEXT,export_baseline_json TEXT NOT NULL DEFAULT '[]',created_at TEXT NOT NULL,
              PRIMARY KEY(intent_id,attempt),FOREIGN KEY(intent_id) REFERENCES intents(id));
            CREATE TABLE IF NOT EXISTS retry_receipts(
              session_id TEXT NOT NULL,retry_id TEXT NOT NULL,intent_id TEXT NOT NULL,request_digest TEXT NOT NULL,
              expected_attempt INTEGER NOT NULL,mode TEXT NOT NULL,base_revision TEXT,confirmed INTEGER NOT NULL,
              result_json TEXT NOT NULL,created_at TEXT NOT NULL,PRIMARY KEY(session_id,retry_id));
            CREATE TABLE IF NOT EXISTS events(
              id INTEGER PRIMARY KEY AUTOINCREMENT,session_id TEXT NOT NULL,type TEXT NOT NULL,data_json TEXT NOT NULL,created_at TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS events_session_id ON events(session_id,id);
            CREATE TABLE IF NOT EXISTS clients(
              id TEXT NOT NULL,session_id TEXT NOT NULL,token_digest TEXT NOT NULL UNIQUE,last_seen TEXT NOT NULL,
              dirty INTEGER NOT NULL,active_edit INTEGER NOT NULL,draft_pending INTEGER NOT NULL,revision TEXT,last_event_id INTEGER NOT NULL,
              PRIMARY KEY(session_id,id));
            CREATE TABLE IF NOT EXISTS bundle_files(
              session_id TEXT NOT NULL,path TEXT NOT NULL,class TEXT NOT NULL,sha256 TEXT NOT NULL,size INTEGER NOT NULL,
              present INTEGER NOT NULL DEFAULT 1,snapshot_id TEXT,PRIMARY KEY(session_id,path));
            CREATE TABLE IF NOT EXISTS snapshots(
              id TEXT PRIMARY KEY,session_id TEXT NOT NULL,source_revision TEXT,export_revision TEXT,manifest_json TEXT NOT NULL,
              git_commit TEXT,created_at TEXT NOT NULL,action TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS publications(
              id TEXT PRIMARY KEY,session_id TEXT NOT NULL,action TEXT NOT NULL,intent_id TEXT,attempt INTEGER,
              base_revision TEXT,new_revision TEXT,new_export_revision TEXT,status TEXT NOT NULL,receipt_id TEXT NOT NULL,
              old_snapshot_id TEXT,new_snapshot_id TEXT,journal_path TEXT NOT NULL,result_json TEXT,created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS write_receipts(
              session_id TEXT NOT NULL,write_key TEXT NOT NULL,action TEXT NOT NULL,receipt_id TEXT NOT NULL,snapshot_id TEXT NOT NULL,
              result_json TEXT NOT NULL,created_at TEXT NOT NULL,PRIMARY KEY(session_id,write_key));
            CREATE TABLE IF NOT EXISTS drafts(
              id TEXT PRIMARY KEY,session_id TEXT NOT NULL,client_id TEXT NOT NULL,html TEXT NOT NULL,annotations_json TEXT NOT NULL,
              base_revision TEXT,created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS facts(
              id INTEGER PRIMARY KEY AUTOINCREMENT,session_id TEXT NOT NULL,type TEXT NOT NULL,data_json TEXT NOT NULL,created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS dependency_reports(
              session_id TEXT NOT NULL,source_revision TEXT,urls_json TEXT NOT NULL,created_at TEXT NOT NULL,
              PRIMARY KEY(session_id,source_revision));
            """)
            current = self.db.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
            version=int(current[0]) if current else 0
            if version > SCHEMA_VERSION:
                raise BridgeError(503, "STORAGE_UNAVAILABLE", "数据库版本高于当前程序")
            attempt_columns={row[1] for row in self.db.execute("PRAGMA table_info(attempts)")}
            if "export_baseline_json" not in attempt_columns:
                self.db.execute("ALTER TABLE attempts ADD COLUMN export_baseline_json TEXT NOT NULL DEFAULT '[]'")
            session_columns={row[1] for row in self.db.execute("PRAGMA table_info(sessions)")}
            if "brief_options_json" not in session_columns:
                self.db.execute("ALTER TABLE sessions ADD COLUMN brief_options_json TEXT")
            if "view_attached_at" not in session_columns:
                # MCP Apps 轨的实证信号：View 经 attach_view 上报（设计 §4.2）。
                # 列可为空，且永不回退为 NULL——"本会话是否出现过 UI 信号"是仲裁自解除的判据。
                self.db.execute("ALTER TABLE sessions ADD COLUMN view_attached_at TEXT")
                self.db.execute("ALTER TABLE sessions ADD COLUMN view_client TEXT")
            self.db.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('schema_version',?)", (str(SCHEMA_VERSION),))

    def _invalidate_previous_instance(self):
        now=utcnow()
        interrupted=self.db.execute(
            "SELECT session_id,id,attempt FROM intents WHERE status='processing'").fetchall()
        error=canonical_json({"code":"RECOVERY_REQUIRED","message":"daemon-restarted","retryable":True}).decode()
        with self.db:
            self.db.execute("UPDATE browser_tokens SET revoked_at=? WHERE revoked_at IS NULL",(now,))
            for row in interrupted:
                self.db.execute("UPDATE intents SET status='interrupted',error_json=?,consumer_id=NULL,lease_until=NULL,updated_at=? WHERE id=?",(error,now,row["id"]))
                self.db.execute("UPDATE attempts SET status='interrupted' WHERE intent_id=? AND attempt=?",(row["id"],row["attempt"]))
                self._event(row["session_id"],"intent-status",{"session_id":row["session_id"],"intent_id":row["id"],"status":"interrupted","attempt":row["attempt"]})
            self.db.execute("UPDATE consumers SET state=CASE WHEN state='paused' THEN 'paused' ELSE 'expired' END,lease_until=NULL")
            self.db.execute("UPDATE sessions SET owner_consumer_id=NULL,agent_state=CASE WHEN EXISTS(SELECT 1 FROM intents WHERE intents.session_id=sessions.id AND intents.status='interrupted') THEN 'recovering' ELSE 'offline' END")
        for session_id in {row["session_id"] for row in interrupted}:
            self._notify(session_id)

    def _condition(self, session_id):
        with self._db_lock:
            return self._conditions.setdefault(session_id, threading.Condition())

    def _session_lock(self, session_id):
        with self._db_lock:
            return self._session_locks.setdefault(session_id, threading.RLock())

    def _session(self, session_id):
        row = self.db.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
        if not row:
            raise BridgeError(404, "SESSION_NOT_FOUND", "任务不存在")
        return row

    def _event(self, session_id, typ, data):
        cur = self.db.execute("INSERT INTO events(session_id,type,data_json,created_at) VALUES(?,?,?,?)",
                              (session_id, typ, canonical_json(data).decode(), utcnow()))
        keep = self.db.execute("SELECT id FROM events WHERE session_id=? ORDER BY id DESC LIMIT 1 OFFSET 999", (session_id,)).fetchone()
        if keep:
            cutoff = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=7)).isoformat(timespec="milliseconds").replace("+00:00", "Z")
            self.db.execute("DELETE FROM events WHERE session_id=? AND id<? AND created_at<?", (session_id, keep[0], cutoff))
        return cur.lastrowid

    def _notify(self, session_id):
        cond = self._condition(session_id)
        with cond:
            cond.notify_all()

    def _classify(self, rel: str, target_rel: str):
        p = PurePosixPath(rel)
        if rel == target_rel:
            return "source-html"
        if p.parts and p.parts[0] == "assets" and p.suffix.lower() in SOURCE_IMAGE_EXTS:
            return "source-image"
        if p.parts and p.parts[0] == "assets" and p.suffix.lower() in SOURCE_LEGACY_EXTS:
            return "source-legacy"
        if p.parts and p.parts[0] == "fonts" and p.suffix.lower() in SOURCE_FONT_EXTS:
            return "source-font"
        if p.parts and p.parts[0] == "export" and p.suffix.lower() in EXPORT_EXTS:
            return "export-manifest" if rel == "export/manifest.json" else "export"
        if rel in DERIVED_NAMES:
            return "derived"
        return None

    def _validate_svg(self,path):
        raw=self.secure.read(self._work_rel(path))
        if b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper(): raise BridgeError(422,"INVALID_ARTIFACT","SVG 禁止 DTD/entity")
        try:root=ET.fromstring(raw)
        except ET.ParseError as exc:raise BridgeError(422,"INVALID_ARTIFACT","SVG XML 非法") from exc
        for element in root.iter():
            tag=element.tag.rsplit("}",1)[-1].lower()
            if tag in {"script","foreignobject"}: raise BridgeError(422,"INVALID_ARTIFACT",f"SVG 禁止 {tag}")
            for name,value in element.attrib.items():
                local=name.rsplit("}",1)[-1].lower();text=value.strip();lower=text.lower()
                if local.startswith("on"): raise BridgeError(422,"INVALID_ARTIFACT","SVG 禁止事件处理器")
                if local in {"href","src"} and text and not text.startswith("#") and not valid_inline_raster_data_uri(text):
                    raise BridgeError(422,"INVALID_ARTIFACT","SVG 禁止外部或非法内联资源引用")
                for match in re.findall(r"url\(([^)]+)\)",lower,re.I):
                    if not match.strip(" '\"").startswith("#"): raise BridgeError(422,"INVALID_ARTIFACT","SVG 禁止外部 url()")
        if re.search(rb"url\(\s*(['\"]?)(?!#)",raw,re.I): raise BridgeError(422,"INVALID_ARTIFACT","SVG 禁止外部 CSS url()")

    def external_dependencies(self,target_abs):
        if not target_abs.exists():return []
        text=self.secure.read(self._work_rel(target_abs)).decode("utf-8")
        values=[]
        for value in re.findall(r"(?:src|href)\s*=\s*['\"]([^'\"]+)",text,re.I)+re.findall(r"url\(\s*['\"]?([^)'\"]+)",text,re.I):
            value=value.strip()
            if re.match(r"^(?:https?:)?//",value,re.I):values.append(value)
        return sorted(set(values))

    def scan_bundle(self, target_abs: Path, *, allow_missing_html=False):
        bundle_root = target_abs.parent
        target_rel = target_abs.name
        found = []
        candidates = []
        if target_abs.exists():
            candidates.append(target_abs)
        elif not allow_missing_html:
            raise BridgeError(422, "INVALID_ARTIFACT", "目标 HTML 不存在")
        for folder in ("assets", "fonts", "export"):
            root = bundle_root / folder
            if root.exists():
                if root.is_symlink() or not root.is_dir():
                    raise BridgeError(403, "PATH_DENIED", f"拒绝链接目录: {folder}")
                candidates.extend(p for p in root.rglob("*") if p.is_file() or p.is_symlink())
        for name in DERIVED_NAMES:
            p = bundle_root / name
            if p.exists():
                candidates.append(p)
        total = 0
        for path in candidates:
            _safe_regular(path, self.workdir)
            rel = path.relative_to(bundle_root).as_posix()
            klass = self._classify(rel, target_rel)
            if not klass:
                if PurePosixPath(rel).parts[0] in {"assets","fonts","export"}:
                    raise BridgeError(422,"INVALID_ARTIFACT",f"受管目录包含不允许的文件类型: {rel}")
                continue
            if path.suffix.lower()==".svg":self._validate_svg(path)
            digest, size = self._managed_hash(path)
            total += size
            found.append({"path": rel, "class": klass, "sha256": digest, "size": size, "present": True})
        if len(found) > BUNDLE_FILE_MAX or total > BUNDLE_MAX:
            raise BridgeError(413, "PAYLOAD_TOO_LARGE", "受管 bundle 超出容量限制")
        found.sort(key=lambda x: x["path"].encode("utf-8"))
        return found

    @staticmethod
    def revisions(manifest):
        src = [[x["path"], x["size"], x["sha256"]] for x in manifest if x["present"] and x["class"].startswith("source-")]
        exp = [[x["path"], x["size"], x["sha256"]] for x in manifest if x["present"] and x["class"].startswith("export")]
        return revision_from_records(src, b"pptx-html-source-v1\n"), revision_from_records(exp, b"pptx-html-export-v1\n")

    def _target_abs(self, session):
        return self.workdir / session["target_path"]

    def _bundle_root(self, session):
        return self._target_abs(session).parent

    def _work_rel(self,path):
        try:return Path(path).relative_to(self.workdir).as_posix()
        except ValueError as exc:raise BridgeError(403,"PATH_DENIED","路径越出工作区") from exc

    def _managed_hash(self,path):
        return self.secure.hash(self._work_rel(path))

    def _managed_copy_out(self,path,destination):
        return self.secure.copy_out(self._work_rel(path),destination)

    def _managed_replace(self,path,source):
        return self.secure.atomic_replace_from(self._work_rel(path),source)

    def _managed_unlink(self,path):
        return self.secure.unlink(self._work_rel(path))

    def _ensure_git(self, session_id, allow_init):
        git = shutil.which("git")
        if not git:
            raise BridgeError(503, "STORAGE_UNAVAILABLE", "git 不可用")
        probe = subprocess.run([git, "-C", str(self.workdir), "rev-parse", "--show-toplevel"], capture_output=True, text=True)
        if probe.returncode:
            if not allow_init:
                raise BridgeError(409, "GIT_INIT_REQUIRED", "首次发布前需要确认初始化 Git")
            init = subprocess.run([git, "-C", str(self.workdir), "init"], capture_output=True, text=True)
            if init.returncode:
                raise BridgeError(503, "STORAGE_UNAVAILABLE", "Git 初始化失败")
            probe = subprocess.run([git, "-C", str(self.workdir), "rev-parse", "--show-toplevel"], capture_output=True, text=True)
        repo = Path(probe.stdout.strip()).resolve()
        key = hashlib.sha256(str(self.workdir).encode()).hexdigest()[:16]
        ref = f"refs/pptx-html/{key}/{session_id}"
        return git, repo, ref

    def _git_protect(self, session_id, manifest, snapshot_root: Path, allow_init=True, update_ref=True):
        git, repo, ref = self._ensure_git(session_id, allow_init)
        index = self.internal / "git-index" / (new_id("idx_") + ".index")
        env = os.environ.copy(); env["GIT_INDEX_FILE"] = str(index)
        try:
            subprocess.run([git, "-C", str(repo), "read-tree", "--empty"], env=env, check=True, capture_output=True)
            bundle_root = self._bundle_root(self._session(session_id))
            for item in manifest:
                if not item["present"]:
                    continue
                src = snapshot_root / item["path"]
                source_fd,_=self.secure.open_read(self._work_rel(src))
                with os.fdopen(source_fd,"rb") as source:
                    h = subprocess.run([git, "-C", str(repo), "hash-object", "-w", "--stdin"], stdin=source, check=True, capture_output=True, text=True).stdout.strip()
                repo_rel = (bundle_root / item["path"]).relative_to(repo).as_posix()
                subprocess.run([git, "-C", str(repo), "update-index", "--add", "--cacheinfo", "100644", h, repo_rel], env=env, check=True, capture_output=True)
            tree = subprocess.run([git, "-C", str(repo), "write-tree"], env=env, check=True, capture_output=True, text=True).stdout.strip()
            old = subprocess.run([git, "-C", str(repo), "rev-parse", "--verify", ref], capture_output=True, text=True)
            old_hash = old.stdout.strip() if old.returncode == 0 else None
            args = [git, "-C", str(repo), "-c", "user.name=pptx-html-bridge", "-c", "user.email=bridge@localhost", "commit-tree", tree, "-m", "pptx-html protected snapshot"]
            if old_hash:
                args += ["-p", old_hash]
            commit = subprocess.run(args, check=True, capture_output=True, text=True).stdout.strip()
            if update_ref:
                self._git_ref_cas(git, repo, ref, old_hash, commit)
            return commit, ref, old_hash
        except (subprocess.CalledProcessError, ValueError) as exc:
            raise BridgeError(503, "STORAGE_UNAVAILABLE", "Git 保护版本创建失败") from exc
        finally:
            with contextlib.suppress(OSError): index.unlink()

    def _git_ref_cas(self, git, repo, ref, old_hash, new_hash):
        command = [git, "-C", str(repo), "update-ref", ref, new_hash]
        if old_hash:
            command.append(old_hash)
        subprocess.run(command, check=True, capture_output=True)

    def _git_ref_restore(self, session_id, ref, old_hash, new_hash):
        git, repo, expected_ref = self._ensure_git(session_id, False)
        if ref != expected_ref:
            raise BridgeError(503, "RECOVERY_FAILED", "journal Git ref 身份不匹配")
        current = subprocess.run([git, "-C", str(repo), "rev-parse", "--verify", ref], capture_output=True, text=True)
        current_hash = current.stdout.strip() if current.returncode == 0 else None
        if current_hash == old_hash:
            return
        if current_hash != new_hash:
            raise BridgeError(503, "RECOVERY_FAILED", "Git 专用 ref 出现第三方值")
        if old_hash:
            subprocess.run([git, "-C", str(repo), "update-ref", ref, old_hash, new_hash], check=True, capture_output=True)
        else:
            subprocess.run([git, "-C", str(repo), "update-ref", "-d", ref, new_hash], check=True, capture_output=True)

    def _snapshot(self, session_id, manifest, source_root: Path, action: str, protect_git=False, allow_init=True):
        sid = new_id("snap_")
        dst = self.internal / "snapshots" / sid / "bundle"
        dst.mkdir(parents=True, mode=0o700)
        for item in manifest:
            if item["present"]:
                out = dst / item["path"]
                self._managed_copy_out(source_root / item["path"], out)
        src_rev, exp_rev = self.revisions(manifest)
        commit = ref = None
        if protect_git:
            commit, ref, _ = self._git_protect(session_id, manifest, dst, allow_init)
        with self.db:
            self.db.execute("INSERT INTO snapshots VALUES(?,?,?,?,?,?,?,?)",
                (sid, session_id, src_rev, exp_rev, canonical_json(manifest).decode(), commit, utcnow(), action))
            if ref:
                self.db.execute("UPDATE sessions SET git_ready=1,git_ref=? WHERE id=?", (ref, session_id))
        return sid, dst, commit

    def register_session(self, *, deck_path=None, output_path="index.html", auto_git=False):
        if deck_path is not None:
            path = Path(deck_path)
            if not path.is_absolute():
                raise BridgeError(400, "INVALID_ARGUMENT", "deck_path 必须是绝对路径")
            path = path.resolve(strict=True)
            _safe_regular(path, self.workdir)
            if path.suffix.lower() != ".html":
                raise BridgeError(400, "INVALID_ARGUMENT", "deck_path 必须是 HTML")
            target_rel = path.relative_to(self.workdir).as_posix()
            phase, deck_rel = "editing", target_rel
        else:
            target_rel = normalize_rel(output_path, suffix=".html")
            path = self.workdir / target_rel
            if path.exists():
                raise BridgeError(409, "REVISION_CONFLICT", "新建目标已存在")
            phase, deck_rel = "briefing", None
        with self._db_lock:
            existing = self.db.execute("SELECT * FROM sessions WHERE target_path=?", (target_rel,)).fetchone()
            if existing:
                if auto_git and not existing["git_ready"]:
                    manifest = [dict(r) for r in self.db.execute("SELECT path,class,sha256,size,present FROM bundle_files WHERE session_id=? ORDER BY path", (existing["id"],))]
                    snapshot_id, _, _ = self._snapshot(existing["id"], manifest, self._bundle_root(existing), "baseline", protect_git=True, allow_init=True)
                    with self.db:
                        self.db.execute("UPDATE bundle_files SET snapshot_id=? WHERE session_id=?", (snapshot_id, existing["id"]))
                    existing = self._session(existing["id"])
                return existing
            bundle_dir = str(Path(target_rel).parent)
            rows = self.db.execute("SELECT target_path FROM sessions").fetchall()
            for row in rows:
                if str(Path(row[0]).parent) == bundle_dir:
                    raise BridgeError(409, "SESSION_BUSY", "同一目录只能登记一个 deck")
            manifest = self.scan_bundle(path, allow_missing_html=True) if deck_rel else []
            rev, exp = self.revisions(manifest)
            session_id = new_id("s_")
            now = utcnow()
            with self.db:
                self.db.execute("INSERT INTO sessions(id,target_path,deck_path,phase,created_at,updated_at,revision,export_revision,agent_state) VALUES(?,?,?,?,?,?,?,?,?)",
                                (session_id,target_rel,deck_rel,phase,now,now,rev,exp,"offline"))
                for item in manifest:
                    self.db.execute("INSERT INTO bundle_files(session_id,path,class,sha256,size,present) VALUES(?,?,?,?,?,1)",
                                    (session_id,item["path"],item["class"],item["sha256"],item["size"]))
                if rev:
                    self.db.execute("INSERT OR REPLACE INTO dependency_reports VALUES(?,?,?,?)",(session_id,rev,canonical_json(self.external_dependencies(path)).decode(),now))
            if auto_git:
                snap_id, _, _ = self._snapshot(session_id, manifest, path.parent, "baseline", protect_git=True, allow_init=True)
                with self.db:
                    self.db.execute("UPDATE bundle_files SET snapshot_id=? WHERE session_id=?", (snap_id, session_id))
            return self._session(session_id)

    def issue_browser_token(self, session_id):
        self._session(session_id)
        raw = secrets.token_urlsafe(32)
        with self.db:
            self.db.execute("INSERT INTO browser_tokens(token_digest,session_id,created_at) VALUES(?,?,?)", (token_digest(raw),session_id,utcnow()))
        return raw

    def open_editor(self, consumer_id, deck_path=None, output_path="index.html", view="edit", open_browser=True, brief_options=None):
        if view not in {"edit","brief","annotate","export"}:
            raise BridgeError(400,"INVALID_ARGUMENT","非法 view")
        if open_browser is not True and open_browser is not False and open_browser != "auto":
            raise BridgeError(400,"INVALID_ARGUMENT","open_browser 必须是 true/false 或 \"auto\"")
        if brief_options is not None:
            validate_brief_options(brief_options)
        session = self.register_session(deck_path=deck_path, output_path=output_path, auto_git=True)
        if brief_options is not None:
            with self.db:
                self.db.execute("UPDATE sessions SET brief_options_json=? WHERE id=?",
                                (canonical_json(brief_options).decode(), session["id"]))
        now = utcnow()
        with self.db:
            current = self.db.execute("SELECT * FROM consumers WHERE session_id=? AND consumer_id=?", (session["id"],consumer_id)).fetchone()
            owner = self.db.execute("SELECT owner_consumer_id FROM sessions WHERE id=?", (session["id"],)).fetchone()[0]
            state = current["state"] if current and owner == consumer_id and current["state"] in ("waiting","working") else "registered"
            self.db.execute("INSERT INTO consumers(session_id,consumer_id,state,registered_at,requires_open,lease_until) VALUES(?,?,?,?,0,NULL) ON CONFLICT(session_id,consumer_id) DO UPDATE SET state=excluded.state,registered_at=excluded.registered_at,requires_open=0,lease_until=CASE WHEN consumers.state IN ('waiting','working') THEN consumers.lease_until ELSE NULL END",
                            (session["id"],consumer_id,state,now))
        browser = self.issue_browser_token(session["id"])
        # view 是一次性启动提示（设计 brief-page-split §6）：经 URL fragment / 工具结果下发，
        # **不落库、不进会话状态**——落库会让驻留页每 2s 的 get_status 轮询把用户当前视图翻回去。
        url = f"{self.origin}/editor.html#brt={browser}&session={session['id']}&view={view}"
        page_online = self.page_online(session["id"])
        view_online = self.view_attached(session["id"])
        if page_online:
            # 会话已有在线页面：既不会开新窗，fragment 也到不了它 → 用一次性事件投递（C9）。
            with self.db:
                self._event(session["id"], "view-hint", {"session_id": session["id"], "view": view})
            self._notify(session["id"])
        if open_browser is True and not page_online:
            with contextlib.suppress(Exception): webbrowser.open(url)
        elif open_browser == "auto" and not page_online and not view_online:
            # 轨道未定：先给 MCP Apps 的 View 一个存在性窗口，窗口内无任何 UI 信号才开浏览器。
            self._schedule_view_window(session["id"], url)
        return self._open_result(self._session(session["id"]), state, url, page_online, view_online, view)

    @staticmethod
    def _brief_options_of(s):
        raw = s["brief_options_json"]
        return json.loads(raw) if raw else None

    def _open_result(self, s, consumer_state, url, page_online, view_online=False, view="edit"):
        return {"ok":True,"protocol_version":2,"session_id":s["id"],
                "view":view,
                "deck_path":str(self.workdir/s["deck_path"]) if s["deck_path"] else None,
                "target_path":str(self.workdir/s["target_path"]),"resource_path":s["target_path"],"revision":s["revision"],"phase":s["phase"],
                "url":url,"page_online":page_online,"view_attached":view_online,"track":self.track_of(s["id"]),
                "agent_state":self.agent_state(s["id"]),
                "consumer_state":consumer_state,"git_initialized":bool(s["git_ready"]),
                "brief_options":self._brief_options_of(s),
                "capabilities":{"local_convert":self.allow_convert,"local_imagegen":self.allow_imagegen,"git_ready":bool(s["git_ready"])}}

    def page_online(self, session_id):
        cutoff = time.time() - CLIENT_ONLINE_SEC
        return any(parse_time(r[0]) >= cutoff for r in self.db.execute("SELECT last_seen FROM clients WHERE session_id=?",(session_id,)))

    @staticmethod
    def _env_view_wait_sec():
        """轨 A 的存在性窗口（设计 §4.2）。设 0 等价于旧行为：不等待，直接开浏览器。"""
        raw = os.environ.get("PPTX_HTML_VIEW_WAIT_SEC")
        if raw is None or not str(raw).strip():
            return float(VIEW_WAIT_SEC_DEFAULT)
        try:
            value = float(raw)
        except ValueError:
            return float(VIEW_WAIT_SEC_DEFAULT)
        return max(0.0, min(value, float(VIEW_WAIT_SEC_MAX)))

    def view_attached(self, session_id):
        """View 是否在存续窗口内上报过 attach_view —— 轨 A 的实证信号，不靠能力声明。"""
        row = self.db.execute("SELECT view_attached_at FROM sessions WHERE id=?",(session_id,)).fetchone()
        return bool(row and row[0] and parse_time(row[0]) >= time.time() - VIEW_SIGNAL_STALE_SEC)

    def ui_signal_ever(self, session_id):
        """本会话历史上是否出现过任何 UI 信号（轨 A 的 attach_view / 轨 B 的浏览器心跳）。

        这是仲裁相位的自解除判据：一旦出现过，await_intent 就不再付仲裁时延，
        轨 B 的行为与升级前逐字节一致。
        """
        row = self.db.execute("SELECT view_attached_at FROM sessions WHERE id=?",(session_id,)).fetchone()
        if row and row[0]: return True
        return bool(self.db.execute("SELECT 1 FROM clients WHERE session_id=? LIMIT 1",(session_id,)).fetchone())

    def track_of(self, session_id):
        if self.view_attached(session_id): return "mcp-app"
        if self.page_online(session_id): return "bridge"
        return "pending"

    def attach_view(self, session_id, client=None):
        """View 连接后立即上报（app-only 工具 attach_view）。"""
        if client is not None and (not isinstance(client, str) or len(client) > 200):
            raise BridgeError(400,"INVALID_ARGUMENT","client 字段非法")
        self._session(session_id)
        now = utcnow()
        with self.db:
            self.db.execute("UPDATE sessions SET view_attached_at=?,view_client=?,updated_at=? WHERE id=?",(now,client,now,session_id))
        self._notify(session_id)
        return {"ok":True,"session_id":session_id,"track":"mcp-app","view_attached":True,"server_time":now}

    def _schedule_view_window(self, session_id, url):
        """存在性窗口：窗口内没有 View 信号也没有浏览器心跳，才打开独立浏览器（轨 B）。"""
        wait = self.view_wait_sec
        def fire():
            with contextlib.suppress(Exception):
                if self._stop.is_set(): return
                if self.view_attached(session_id) or self.page_online(session_id): return
                with contextlib.suppress(Exception): webbrowser.open(url)
        timer = threading.Timer(wait, fire)
        timer.daemon = True
        timer.start()
        return timer

    def _bundle_rel(self, session, rel):
        try:
            return (self.workdir/rel).relative_to(self._bundle_root(session)).as_posix()
        except ValueError:
            raise BridgeError(403,"PATH_DENIED","路径不属于本任务")

    def read_document(self, session_id, path=None):
        """读取本任务受管的目标 HTML（轨 A 的 read_deck）。"""
        session=self._session(session_id)
        rel=session["target_path"] if path is None else normalize_rel(path)
        if rel!=session["target_path"]:
            raise BridgeError(403,"PATH_DENIED","只能读取本任务登记的目标 HTML")
        data=self.secure.read(rel)
        if len(data)>DOCUMENT_READ_MAX:
            raise BridgeError(413,"PAYLOAD_TOO_LARGE","目标 HTML 超出单次读取上限")
        return {"ok":True,"session_id":session_id,"path":rel,"revision":session["revision"],"phase":session["phase"],
                "bytes":len(data),"sha256":hashlib.sha256(data).hexdigest(),"html":data.decode("utf-8",errors="replace")}

    def read_artifact(self, session_id, path, *, kind):
        """读取受管 bundle 内**已登记**的资产或导出产物（轨 A 的 read_asset / read_export）。

        未登记的路径一律拒绝：登记表就是白名单，避免把宿主代理变成任意文件读取。
        """
        session=self._session(session_id)
        rel=normalize_rel(path)
        bundle_rel=self._bundle_rel(session,rel)
        if kind=="asset":
            if not bundle_rel.startswith(("assets/","fonts/")):
                raise BridgeError(403,"PATH_DENIED","只能读取受管 assets/ 或 fonts/")
            classes={"source-image","source-font"}
        else:
            if not bundle_rel.startswith("export/"):
                raise BridgeError(403,"PATH_DENIED","只能读取受管 export/")
            classes={"export","export-manifest"}
        row=self.db.execute("SELECT class,size FROM bundle_files WHERE session_id=? AND path=? AND present=1",(session_id,bundle_rel)).fetchone()
        if not row or row["class"] not in classes:
            raise BridgeError(404,"NOT_FOUND","文件未在本任务登记")
        data=self.secure.read(rel)
        if len(data)>ARTIFACT_READ_MAX:
            raise BridgeError(413,"PAYLOAD_TOO_LARGE","产物超出单次读取上限，请在宿主工作目录取件")
        return {"ok":True,"session_id":session_id,"path":bundle_rel,"bytes":len(data),
                "mime":mimetypes.guess_type(bundle_rel)[0] or "application/octet-stream",
                "sha256":hashlib.sha256(data).hexdigest(),"data_base64":base64.b64encode(data).decode("ascii")}

    def read_export_file(self, session_id, file):
        session=self._session(session_id)
        directory=PurePosixPath(session["target_path"]).parent
        prefix="" if directory.as_posix()=="." else directory.as_posix()+"/"
        return self.read_artifact(session_id,prefix+"export/"+file,kind="export")


    def _expire(self, session_id):
        now = time.time()
        with self.db:
            owner = self.db.execute("SELECT owner_consumer_id FROM sessions WHERE id=?",(session_id,)).fetchone()
            if not owner or not owner[0]: return
            consumer = self.db.execute("SELECT * FROM consumers WHERE session_id=? AND consumer_id=?",(session_id,owner[0])).fetchone()
            if not consumer or consumer["state"] != "waiting": return
            if parse_time(consumer["lease_until"]) < now:
                self.db.execute("UPDATE consumers SET state='expired',lease_until=NULL WHERE session_id=? AND consumer_id=?",(session_id,owner[0]))
                self.db.execute("UPDATE sessions SET owner_consumer_id=NULL,agent_state='offline' WHERE id=? AND owner_consumer_id=?",(session_id,owner[0]))

    def agent_state(self, session_id):
        self._expire(session_id)
        row=self.db.execute("SELECT owner_consumer_id FROM sessions WHERE id=?",(session_id,)).fetchone()
        if row and row[0]:
            c=self.db.execute("SELECT state FROM consumers WHERE session_id=? AND consumer_id=?",(session_id,row[0])).fetchone()
            if c: return "working" if c[0]=="working" else "waiting"
        if self.db.execute("SELECT 1 FROM intents WHERE session_id=? AND status IN ('failed','conflict','interrupted') LIMIT 1",(session_id,)).fetchone(): return "recovering"
        if self.db.execute("SELECT 1 FROM consumers WHERE session_id=? AND state='paused' LIMIT 1",(session_id,)).fetchone(): return "paused"
        return "offline"

    def _acquire_owner(self, session_id, consumer_id):
        self._expire(session_id)
        with self.db:
            c=self.db.execute("SELECT * FROM consumers WHERE session_id=? AND consumer_id=?",(session_id,consumer_id)).fetchone()
            if not c or c["requires_open"]:
                raise BridgeError(409,"RECOVERY_REQUIRED","consumer 必须先 open_editor 登记",True)
            s=self._session(session_id)
            if s["owner_consumer_id"] and s["owner_consumer_id"] != consumer_id:
                raise BridgeError(409,"SESSION_BUSY","任务由另一 consumer 占有",True)
            self.db.execute("UPDATE sessions SET owner_consumer_id=?,agent_state='waiting',updated_at=? WHERE id=?",(consumer_id,utcnow(),session_id))
            self.db.execute("UPDATE consumers SET state='waiting',lease_until=? WHERE session_id=? AND consumer_id=?",(future(CONSUMER_LEASE_SEC),session_id,consumer_id))
            if self.db.execute("SELECT 1 FROM intents WHERE session_id=? AND status IN ('failed','conflict','interrupted') LIMIT 1",(session_id,)).fetchone():
                raise BridgeError(409,"RECOVERY_REQUIRED","存在待用户处理的恢复请求",True)

    def _copy_attempt(self, intent, consumer_id):
        session=self._session(intent["session_id"])
        target=self._target_abs(session)
        rel_target=session["target_path"]
        registered=self.db.execute(
            "SELECT work_path,export_baseline_json FROM attempts WHERE intent_id=? AND attempt=?",
            (intent["id"],intent["attempt"])).fetchone()
        if registered and registered["work_path"]:
            work_path=Path(registered["work_path"])
            _safe_regular(work_path,self.internal)
            expected_suffix=PurePosixPath(rel_target).parts
            if tuple(work_path.parts[-len(expected_suffix):]) != expected_suffix:
                raise BridgeError(503,"STORAGE_UNAVAILABLE","resume 工作副本身份不匹配")
            self.scan_bundle(work_path)
            return work_path,json.loads(registered["export_baseline_json"] or "[]"),True
        work_root=self.internal/"jobs"/intent["id"]/f"attempt-{intent['attempt']}"/"work"
        work_path=work_root/rel_target
        if work_root.exists():
            raise BridgeError(503,"STORAGE_UNAVAILABLE","attempt 目录冲突")
        work_root.mkdir(parents=True,mode=0o700)
        export_baseline=[]
        if session["deck_path"]:
            manifest=[dict(r) for r in self.db.execute("SELECT path,class,sha256,size,present FROM bundle_files WHERE session_id=?",(session["id"],))]
            export_baseline=[x for x in manifest if x["class"].startswith("export")]
            for item in manifest:
                if item["present"]:
                    src=target.parent/item["path"]; dst=work_path.parent/item["path"]
                    self._managed_copy_out(src,dst)
            check=self.scan_bundle(work_path)
            if self.revisions(check)[0] != session["revision"]:
                shutil.rmtree(work_root,ignore_errors=True)
                raise BridgeError(503,"STORAGE_UNAVAILABLE","工作副本校验失败")
            if intent["type"]=="convert.requested":
                export_dir=work_path.parent/"export"
                if export_dir.exists():shutil.rmtree(export_dir)
                export_dir.mkdir(mode=0o700)
        else:
            work_path.parent.mkdir(parents=True,exist_ok=True)
        return work_path,export_baseline,False

    def await_intent(self, session_id, consumer_id, timeout_sec=AWAIT_TIMEOUT_DEFAULT_SEC, cancelled=None):
        if (isinstance(timeout_sec,bool) or not isinstance(timeout_sec,int)
                or not AWAIT_TIMEOUT_MIN_SEC <= timeout_sec <= AWAIT_TIMEOUT_MAX_SEC):
            raise BridgeError(
                400,"INVALID_ARGUMENT",
                f"timeout_sec 必须为 {AWAIT_TIMEOUT_MIN_SEC}..{AWAIT_TIMEOUT_MAX_SEC} 整数")
        if cancelled is not None and cancelled():
            raise ConnectionAbortedError("await client disconnected")
        self._session(session_id); self._acquire_owner(session_id,consumer_id)
        deadline=time.monotonic()+timeout_sec
        while True:
            if self._stop.is_set():
                raise ConnectionAbortedError("bridge is shutting down")
            if cancelled is not None and cancelled():
                raise ConnectionAbortedError("await client disconnected")
            with self._session_lock(session_id):
                current=self.db.execute("SELECT * FROM intents WHERE session_id=? AND status='processing' AND consumer_id=? ORDER BY seq LIMIT 1",(session_id,consumer_id)).fetchone()
                if current: return self._intent_result(current,True)
                row=self.db.execute("SELECT * FROM intents WHERE session_id=? AND status='pending' ORDER BY seq LIMIT 1",(session_id,)).fetchone()
                if row:
                    if cancelled is not None and cancelled():
                        raise ConnectionAbortedError("await client disconnected")
                    s=self._session(session_id)
                    if row["base_revision"] != s["revision"]:
                        if row["type"] in INSTRUCTION_INTENT_TYPES:
                            # 指令型：base_revision 是写入基线不是锚点，归一化到认领时刻的版本，锚点版本另存 payload.anchor
                            with self.db: self.db.execute("UPDATE intents SET base_revision=?,updated_at=? WHERE id=?",(s["revision"],utcnow(),row["id"]))
                            row=self.db.execute("SELECT * FROM intents WHERE id=?",(row["id"],)).fetchone()
                        else:
                            err={"code":"REVISION_CONFLICT","message":"请求基线已过期","retryable":True}
                            with self.db:
                                self.db.execute("UPDATE intents SET status='conflict',error_json=?,updated_at=? WHERE id=?",(canonical_json(err).decode(),utcnow(),row["id"]))
                                self._event(session_id,"intent-status",{"session_id":session_id,"intent_id":row["id"],"status":"conflict","attempt":row["attempt"]})
                                self._release_owner(session_id,consumer_id)
                            self._notify(session_id)
                            raise BridgeError(409,"RECOVERY_REQUIRED","请求基线冲突，需要用户决定重试",True,{"intent_id":row["id"],"status":"conflict"})
                    work_path,export_baseline,resumed=self._copy_attempt(row,consumer_id)
                    intent_file=self.internal/"intents"/(row["id"]+".json")
                    intent_doc={"protocol_version":2,"intent_id":row["id"],"session_id":session_id,"type":row["type"],"base_revision":row["base_revision"],"payload":json.loads(row["payload_json"])}
                    self._atomic_json(intent_file,intent_doc)
                    lease=future(CONSUMER_LEASE_SEC)
                    with self.db:
                        self.db.execute("INSERT INTO attempts(session_id,intent_id,attempt,base_revision,work_path,consumer_id,status,export_baseline_json,created_at) VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(intent_id,attempt) DO UPDATE SET work_path=excluded.work_path,consumer_id=excluded.consumer_id,status='processing',export_baseline_json=excluded.export_baseline_json",(session_id,row["id"],row["attempt"],row["base_revision"],str(work_path),consumer_id,"processing",canonical_json(export_baseline).decode(),utcnow()))
                        self.db.execute("UPDATE intents SET status='processing',consumer_id=?,lease_until=?,updated_at=? WHERE id=?",(consumer_id,lease,utcnow(),row["id"]))
                        self.db.execute("UPDATE consumers SET state='working',lease_until=? WHERE session_id=? AND consumer_id=?",(lease,session_id,consumer_id))
                        self.db.execute("UPDATE sessions SET agent_state='working' WHERE id=?",(session_id,))
                        self._event(session_id,"intent-status",{"session_id":session_id,"intent_id":row["id"],"status":"processing","attempt":row["attempt"]})
                    self._notify(session_id)
                    return self._intent_result(self.db.execute("SELECT * FROM intents WHERE id=?",(row["id"],)).fetchone(),False)
            remain=deadline-time.monotonic()
            if remain<=0:
                return {"ok":True,"kind":"timeout","session_id":session_id,"page_online":self.page_online(session_id),"agent_state":self.agent_state(session_id),"pending_count":self._count(session_id,"pending"),"interrupted_count":self._count(session_id,"interrupted")}
            cond=self._condition(session_id)
            poll_interval=0.05 if cancelled is not None else 0.5
            with cond: cond.wait(min(remain,poll_interval))

    def _intent_result(self,row,redelivered):
        a=self.db.execute("SELECT work_path FROM attempts WHERE intent_id=? AND attempt=?",(row["id"],row["attempt"])).fetchone()
        resumed=bool(a and a[0] and self.db.execute("SELECT 1 FROM attempts WHERE intent_id=? AND attempt<? AND work_path=? LIMIT 1",(row["id"],row["attempt"],a[0])).fetchone())
        payload=json.loads(row["payload_json"])
        result={"ok":True,"kind":"intent","session_id":row["session_id"],"intent_id":row["id"],"seq":row["seq"],"attempt":row["attempt"],"type":row["type"],"base_revision":row["base_revision"],"payload_bytes":row["payload_bytes"],"intent_file":str(self.internal/"intents"/(row["id"]+".json")),"work_path":a[0] if a else None,"target_path":str(self._target_abs(self._session(row["session_id"]))),"redelivered":redelivered,"resumed":resumed,"facts":[json.loads(x[0]) for x in self.db.execute("SELECT data_json FROM facts WHERE session_id=? ORDER BY id DESC LIMIT 20",(row["session_id"],))],"page_online":self.page_online(row["session_id"])}
        if row["payload_bytes"]<=INTENT_INLINE_MAX: result["payload"]=payload
        else: result["payload_digest"]=row["payload_digest"]
        return result

    def _count(self,sid,status): return self.db.execute("SELECT COUNT(*) FROM intents WHERE session_id=? AND status=?",(sid,status)).fetchone()[0]

    def accept_intent(self, session_id, body):
        expected={"protocol_version","intent_id","session_id","type","base_revision","payload","client_ts"}
        if set(body)!=expected or body.get("protocol_version")!=2 or body.get("session_id")!=session_id:
            raise BridgeError(400,"INVALID_ARGUMENT","intent 顶层字段不符合协议")
        iid=body["intent_id"]
        if not isinstance(iid,str) or not UUID_RE.match(iid): raise BridgeError(400,"INVALID_ARGUMENT","intent_id 必须为 UUID")
        typ=body["type"]
        if typ not in INTENT_TYPES: raise BridgeError(400,"INVALID_ARGUMENT","未知 intent type")
        self._validate_payload(typ,body["payload"])
        raw=canonical_json(body["payload"])
        if len(raw)>INTENT_PAYLOAD_MAX: raise BridgeError(413,"PAYLOAD_TOO_LARGE","intent payload 超过 1MiB")
        request_digest=digest_json({k:body[k] for k in ("type","base_revision","payload")})
        existing=self.db.execute("SELECT * FROM intents WHERE id=?",(iid,)).fetchone()
        if existing:
            if existing["session_id"]==session_id and existing["payload_digest"]==request_digest:
                return {"ok":True,"accepted":True,"intent_id":iid,"seq":existing["seq"],"status":existing["status"]}
            raise BridgeError(409,"IDEMPOTENCY_CONFLICT","intent_id 已用于不同请求")
        session=self._session(session_id)
        base=body["base_revision"]
        if typ in INSTRUCTION_INTENT_TYPES: base=session["revision"]
        elif base != session["revision"]: raise BridgeError(409,"REVISION_CONFLICT","base_revision 与当前版本不一致",True,{"revision":session["revision"]})
        now=utcnow()
        with self.db:
            seq=self.db.execute("SELECT COALESCE(MAX(seq),0)+1 FROM intents").fetchone()[0]
            self.db.execute("INSERT INTO intents(id,session_id,seq,type,payload_json,payload_digest,payload_bytes,base_revision,status,attempt,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",(iid,session_id,seq,typ,raw.decode(),request_digest,len(raw),base,"pending",1,now,now))
            self._event(session_id,"intent-status",{"session_id":session_id,"intent_id":iid,"status":"pending","attempt":1})
        self._notify(session_id)
        return {"ok":True,"accepted":True,"intent_id":iid,"seq":seq,"status":"pending"}

    def _validate_payload(self,typ,p):
        if not isinstance(p,dict): raise BridgeError(400,"INVALID_ARGUMENT","payload 必须为对象")
        if typ in ("design.submitted","anno.submitted") and "anchor" in p:
            a=p["anchor"]
            if not isinstance(a,dict) or set(a)!={"revision","dirty"} or not (a["revision"] is None or isinstance(a["revision"],str)) or not isinstance(a["dirty"],bool): raise BridgeError(400,"INVALID_ARGUMENT","anchor 字段非法")
        if typ=="brief.submitted" and (set(p)!={"text","json"} or not isinstance(p["text"],str) or not isinstance(p["json"],dict) or p["json"].get("kind")!="design-brief"): raise BridgeError(400,"INVALID_ARGUMENT","brief payload 非法")
        if typ=="design.submitted" and set(p)-{"anchor"}!={"version","kind","deck","answers"}: raise BridgeError(400,"INVALID_ARGUMENT","design payload 非法")
        if typ=="anno.submitted" and set(p)-{"anchor"}!={"version","kind","deck","annotations"}: raise BridgeError(400,"INVALID_ARGUMENT","annotation payload 非法")
        if typ=="convert.requested":
            if set(p)!={"formats","scope"} or p["scope"]!="all" or not isinstance(p["formats"],list) or not p["formats"] or len(p["formats"])!=len(set(p["formats"])) or not set(p["formats"])<={"pptx","vector","pdf"}: raise BridgeError(400,"INVALID_ARGUMENT","convert payload 非法")
        if typ=="bake.requested" and (set(p)!={"slide_ids"} or not isinstance(p["slide_ids"],list) or not p["slide_ids"] or len(p["slide_ids"])!=len(set(p["slide_ids"]))): raise BridgeError(400,"INVALID_ARGUMENT","bake payload 非法")
        if typ=="illustrate.requested" and (set(p)!={"slots"} or not isinstance(p["slots"],list) or len(p["slots"])!=len(set(p["slots"]))): raise BridgeError(400,"INVALID_ARGUMENT","illustrate payload 非法")

    def retry_intent(self,session_id,body):
        expected={"session_id","intent_id","retry_id","expected_attempt","mode","base_revision","confirmed"}
        if set(body)!=expected or body["session_id"]!=session_id or not UUID_RE.match(str(body["retry_id"])) or isinstance(body["expected_attempt"],bool) or not isinstance(body["expected_attempt"],int) or body["expected_attempt"]<1 or body["mode"] not in {"rebuild","resume"} or body["confirmed"] is not True:
            raise BridgeError(400,"INVALID_ARGUMENT","retry 报文非法")
        dig=digest_json(body)
        with self._session_lock(session_id):
            old=self.db.execute("SELECT * FROM retry_receipts WHERE session_id=? AND retry_id=?",(session_id,body["retry_id"])).fetchone()
            if old:
                if old["request_digest"]!=dig: raise BridgeError(409,"IDEMPOTENCY_CONFLICT","retry_id 报文不一致")
                return json.loads(old["result_json"])
            row=self.db.execute("SELECT * FROM intents WHERE id=? AND session_id=?",(body["intent_id"],session_id)).fetchone()
            if not row: raise BridgeError(404,"INTENT_NOT_FOUND","请求不存在")
            allowed={"interrupted"} if body["mode"]=="resume" else {"failed","conflict","interrupted"}
            if row["attempt"]!=body["expected_attempt"] or row["status"] not in allowed: raise BridgeError(409,"RECOVERY_REQUIRED","请求当前不可按所选模式恢复",True)
            if self.db.execute("SELECT 1 FROM publications WHERE session_id=? AND status IN ('PREPARED','APPLYING') LIMIT 1",(session_id,)).fetchone():
                raise BridgeError(409,"RECOVERY_REQUIRED","存在未完成发布事务",True)
            session=self._session(session_id)
            actual=self.observe_revision(session_id) if session["deck_path"] else None
            if actual!=session["revision"] or body["base_revision"]!=actual:
                raise BridgeError(409,"REVISION_CONFLICT","重试基线已过期",True,{"revision":actual})
            previous=self.db.execute("SELECT * FROM attempts WHERE intent_id=? AND attempt=?",(row["id"],row["attempt"])).fetchone()
            work_path=None; export_baseline=[]
            if body["mode"]=="resume":
                if not previous or not previous["work_path"] or previous["base_revision"]!=actual:
                    raise BridgeError(409,"RECOVERY_REQUIRED","原工作副本没有完整登记或基线已变化",True)
                work_path=Path(previous["work_path"])
                _safe_regular(work_path,self.internal)
                expected_prefix=self.internal/"jobs"/row["id"]
                try: relative=work_path.relative_to(expected_prefix)
                except ValueError as exc: raise BridgeError(409,"RECOVERY_REQUIRED","原工作副本身份不匹配",True) from exc
                parts=relative.parts
                if len(parts)<3 or not re.fullmatch(r"attempt-[1-9][0-9]*",parts[0]) or parts[1]!="work" or tuple(parts[2:])!=PurePosixPath(session["target_path"]).parts:
                    raise BridgeError(409,"RECOVERY_REQUIRED","原工作副本路径不安全",True)
                self.scan_bundle(work_path)
                export_baseline=json.loads(previous["export_baseline_json"] or "[]")
            attempt=row["attempt"]+1
            result={"ok":True,"session_id":session_id,"intent_id":row["id"],"retry_id":body["retry_id"],"mode":body["mode"],"attempt":attempt,"status":"pending","base_revision":actual,"reused_work_path":body["mode"]=="resume"}
            with self.db:
                changed = self.db.execute("UPDATE intents SET attempt=?,base_revision=?,status='pending',consumer_id=NULL,lease_until=NULL,result_json=NULL,error_json=NULL,updated_at=? WHERE id=? AND attempt=? AND status IN ("+",".join("?" for _ in allowed)+")",(attempt,actual,utcnow(),row["id"],row["attempt"],*allowed))
                if changed.rowcount != 1: raise BridgeError(409,"RECOVERY_REQUIRED","重试竞争失败",True)
                self.db.execute("INSERT INTO attempts(session_id,intent_id,attempt,base_revision,work_path,consumer_id,status,result_json,export_baseline_json,created_at) VALUES(?,?,?,?,?,NULL,'pending',NULL,?,?)",(session_id,row["id"],attempt,actual,str(work_path) if work_path else None,canonical_json(export_baseline).decode(),utcnow()))
                self.db.execute("INSERT INTO retry_receipts VALUES(?,?,?,?,?,?,?,?,?,?)",(session_id,body["retry_id"],row["id"],dig,row["attempt"],body["mode"],actual,1,canonical_json(result).decode(),utcnow()))
                self._event(session_id,"intent-status",{"session_id":session_id,"intent_id":row["id"],"status":"pending","attempt":attempt})
            self._notify(session_id)
            return result

    def cancel_intent(self,session_id,intent_id):
        with self._session_lock(session_id):
            row=self.db.execute("SELECT * FROM intents WHERE id=? AND session_id=?",(intent_id,session_id)).fetchone()
            if not row: raise BridgeError(404,"INTENT_NOT_FOUND","请求不存在")
            if row["status"]=="processing":
                if self.db.execute("SELECT 1 FROM publications WHERE intent_id=? AND attempt=? AND status IN ('PREPARED','APPLYING') LIMIT 1",(intent_id,row["attempt"])).fetchone():
                    raise BridgeError(409,"RECOVERY_REQUIRED","请求正在发布，等待发布恢复到唯一终态",True)
                error={"code":"RECOVERY_REQUIRED","message":"user-stopped","retryable":True}
                with self.db:
                    self.db.execute("UPDATE intents SET status='interrupted',consumer_id=NULL,lease_until=NULL,error_json=?,updated_at=? WHERE id=?",(canonical_json(error).decode(),utcnow(),intent_id))
                    self.db.execute("UPDATE attempts SET status='interrupted' WHERE intent_id=? AND attempt=?",(intent_id,row["attempt"]))
                    self._event(session_id,"intent-status",{"session_id":session_id,"intent_id":intent_id,"status":"interrupted","attempt":row["attempt"]})
                    self._release_owner(session_id,row["consumer_id"])
                self._notify(session_id)
                return {"ok":True,"session_id":session_id,"intent_id":intent_id,"status":"interrupted","external_work_may_continue":True}
            if row["status"]=="pending":
                with self.db:
                    self.db.execute("UPDATE intents SET status='cancelled',updated_at=? WHERE id=?",(utcnow(),intent_id))
                    self._event(session_id,"intent-status",{"session_id":session_id,"intent_id":intent_id,"status":"cancelled","attempt":row["attempt"]})
                self._notify(session_id)
                return {"ok":True,"session_id":session_id,"intent_id":intent_id,"status":"cancelled","external_work_may_continue":False}
            return {"ok":True,"session_id":session_id,"intent_id":intent_id,"status":row["status"],"external_work_may_continue":row["status"]=="interrupted"}

    def _validate_validation(self,row,validation,work_path):
        if not isinstance(validation,dict) or not set(validation)<={"candidate_revision","checks","export_source_revision"} or not {"candidate_revision","checks"}<=set(validation): raise BridgeError(422,"VALIDATION_REQUIRED","complete 需要精确 validation")
        candidate=validation["candidate_revision"]
        if not isinstance(candidate,str) or not REVISION_RE.match(candidate): raise BridgeError(422,"VALIDATION_REQUIRED","candidate_revision 非法")
        checks=validation["checks"]
        if not isinstance(checks,list) or not checks: raise BridgeError(422,"VALIDATION_REQUIRED","checks 不能为空")
        names=[]
        for check in checks:
            if not isinstance(check,dict) or set(check)!={"name","argv","exit_code","report_path"}: raise BridgeError(400,"INVALID_ARGUMENT","check 字段非法")
            if check["name"] not in {"render","capacity","images","manifest","export"} or check["name"] in names: raise BridgeError(400,"INVALID_ARGUMENT","check name 非法或重复")
            if not isinstance(check["argv"],list) or not check["argv"] or any(not isinstance(x,str) or not x or "\x00" in x for x in check["argv"]): raise BridgeError(400,"INVALID_ARGUMENT","check argv 非法")
            if isinstance(check["exit_code"],bool) or check["exit_code"]!=0: raise BridgeError(422,"VALIDATION_REQUIRED","check 未成功")
            report=check["report_path"]
            if report is not None:
                rel=normalize_rel(report); p=work_path.parent/rel; _safe_regular(p,work_path.parent)
            names.append(check["name"])
        required={"export"} if row["type"]=="convert.requested" else {"render","capacity","images","manifest"}
        if not required<=set(names): raise BridgeError(422,"VALIDATION_REQUIRED","缺少必需验收项")
        manifest=self.scan_bundle(work_path)
        actual,_=self.revisions(manifest)
        if actual!=candidate: raise BridgeError(422,"VALIDATION_REQUIRED","候选 revision 与工作副本不符")
        if row["type"]=="convert.requested":
            if candidate!=row["base_revision"] or validation.get("export_source_revision")!=candidate: raise BridgeError(422,"VALIDATION_REQUIRED","转换 source binding 非法")
            self._validate_export(work_path,manifest)
        elif "export_source_revision" in validation:
            if validation["export_source_revision"]!=candidate or "export" not in names: raise BridgeError(422,"VALIDATION_REQUIRED","export binding 非法")
            self._validate_export(work_path,manifest)
        return manifest,actual

    def _validate_export(self,work_path,manifest):
        root=work_path.parent; must=["export/deck.pptx","export/deck-vector.pptx","export/deck.pdf","export/manifest.json"]
        for rel in must:
            p=root/rel
            if not p.is_file() or p.is_symlink(): raise BridgeError(422,"INVALID_ARTIFACT",f"缺少完整导出件 {rel}")
        try: data=json.loads((root/"export/manifest.json").read_text("utf-8"))
        except Exception as exc: raise BridgeError(422,"INVALID_ARTIFACT","export manifest 非法") from exc
        tracks=data.get("export",{}).get("tracks",data.get("tracks",{}))
        if not isinstance(tracks,dict) or not all(k in tracks for k in ("editable","vector")) or any(not isinstance(tracks[k],dict) or tracks[k].get("ok") is not True for k in ("editable","vector")): raise BridgeError(422,"INVALID_ARTIFACT","manifest 双轨未全部成功")
        native=root/"export/native"; pages=list(native.glob("page-*.png")) if native.is_dir() else []
        html=work_path.read_text("utf-8",errors="strict"); count=max(html.count('class="slide"'),html.count("class='slide'"),html.count("data-slide-id="))
        if count and len(pages)<count: raise BridgeError(422,"INVALID_ARTIFACT","native 参考页图不完整")

    def push_update(self,session_id,intent_id,attempt,consumer_id,action,message="",validation=None):
        if action not in {"progress","complete","fail"} or not isinstance(message,str) or len(message)>2000 or isinstance(attempt,bool) or not isinstance(attempt,int) or attempt<1: raise BridgeError(400,"INVALID_ARGUMENT","update 参数非法")
        if action in {"progress","fail"} and validation is not None: raise BridgeError(400,"INVALID_ARGUMENT","progress/fail 不接受 validation")
        with self._session_lock(session_id):
            self._expire(session_id)
            row=self.db.execute("SELECT * FROM intents WHERE id=? AND session_id=?",(intent_id,session_id)).fetchone()
            if not row: raise BridgeError(404,"INTENT_NOT_FOUND","请求不存在")
            if action=="complete" and row["status"]=="succeeded" and row["attempt"]==attempt and row["consumer_id"]==consumer_id and row["result_json"]:
                return json.loads(row["result_json"])
            if row["status"]!="processing" or row["attempt"]!=attempt or row["consumer_id"]!=consumer_id: raise BridgeError(409,"RECOVERY_REQUIRED","consumer/attempt 所有权已失效",True)
            if action=="progress":
                lease=future(CONSUMER_LEASE_SEC)
                with self.db:
                    changed=self.db.execute("UPDATE intents SET lease_until=?,updated_at=? WHERE id=? AND session_id=? AND status='processing' AND attempt=? AND consumer_id=?",(lease,utcnow(),intent_id,session_id,attempt,consumer_id))
                    if changed.rowcount!=1: raise BridgeError(409,"RECOVERY_REQUIRED","progress 所有权竞争失败",True)
                    consumer=self.db.execute("UPDATE consumers SET lease_until=? WHERE session_id=? AND consumer_id=? AND state='working'",(lease,session_id,consumer_id))
                    if consumer.rowcount!=1: raise BridgeError(409,"RECOVERY_REQUIRED","progress owner 状态已变化",True)
                    eid=self._event(session_id,"notice",{"session_id":session_id,"intent_id":intent_id,"level":"info","message":message})
                self._notify(session_id)
                return {"ok":True,"intent_id":intent_id,"status":"processing","events":[eid],"page_online":self.page_online(session_id)}
            if action=="fail":
                error={"code":"AGENT_FAILED","message":message,"retryable":True}
                with self.db:
                    changed=self.db.execute("UPDATE intents SET status='failed',error_json=?,updated_at=? WHERE id=? AND session_id=? AND status='processing' AND attempt=? AND consumer_id=?",(canonical_json(error).decode(),utcnow(),intent_id,session_id,attempt,consumer_id))
                    if changed.rowcount!=1: raise BridgeError(409,"RECOVERY_REQUIRED","fail 所有权竞争失败",True)
                    changed_attempt=self.db.execute("UPDATE attempts SET status='failed' WHERE intent_id=? AND attempt=? AND status='processing' AND consumer_id=?",(intent_id,attempt,consumer_id))
                    if changed_attempt.rowcount!=1: raise BridgeError(409,"RECOVERY_REQUIRED","fail attempt 状态已变化",True)
                    eid=self._event(session_id,"intent-status",{"session_id":session_id,"intent_id":intent_id,"status":"failed","attempt":attempt}); self._release_owner(session_id,consumer_id)
                self._notify(session_id)
                return {"ok":True,"intent_id":intent_id,"status":"failed","events":[eid],"page_online":self.page_online(session_id)}
        attempt_row=self.db.execute("SELECT work_path FROM attempts WHERE intent_id=? AND attempt=?",(intent_id,attempt)).fetchone()
        if not attempt_row: raise BridgeError(422,"INVALID_ARTIFACT","工作副本不存在")
        work_path=Path(attempt_row[0]); _safe_regular(work_path,self.internal)
        manifest,candidate=self._validate_validation(row,validation,work_path)
        try:
            return self._publish(session_id,work_path.parent,manifest,row["base_revision"],"agent-complete",intent=row,consumer_id=consumer_id,message=message,export_source_revision=validation.get("export_source_revision"))
        except BridgeError as exc:
            if exc.code=="REVISION_CONFLICT":
                with self._session_lock(session_id):
                    with self.db:
                        err={"code":"REVISION_CONFLICT","message":"正式目标已变化","retryable":True}
                        changed=self.db.execute("UPDATE intents SET status='conflict',error_json=?,updated_at=? WHERE id=? AND session_id=? AND status='processing' AND attempt=? AND consumer_id=?",(canonical_json(err).decode(),utcnow(),intent_id,session_id,attempt,consumer_id))
                        if changed.rowcount!=1: raise BridgeError(409,"RECOVERY_REQUIRED","complete 冲突状态已被后续操作推进",True) from exc
                        changed_attempt=self.db.execute("UPDATE attempts SET status='conflict' WHERE intent_id=? AND attempt=? AND status='processing' AND consumer_id=?",(intent_id,attempt,consumer_id))
                        if changed_attempt.rowcount!=1: raise BridgeError(409,"RECOVERY_REQUIRED","complete attempt 状态已变化",True) from exc
                        self._event(session_id,"intent-status",{"session_id":session_id,"intent_id":intent_id,"status":"conflict","attempt":attempt}); self._release_owner(session_id,consumer_id)
                    self._notify(session_id)
            raise

    def _release_owner(self,sid,cid):
        self.db.execute("UPDATE consumers SET state='registered',lease_until=NULL WHERE session_id=? AND consumer_id=?",(sid,cid)); self.db.execute("UPDATE sessions SET owner_consumer_id=NULL,agent_state='offline' WHERE id=? AND owner_consumer_id=?",(sid,cid))

    def _write_key(self,action,base_revision,payload): return hashlib.sha256(b"pptx-html-write-v1\n"+canonical_json([action,base_revision,payload])).hexdigest()

    def save(self,session_id,path,html,base_revision,init=False):
        if not isinstance(html,str): raise BridgeError(400,"INVALID_ARGUMENT","html 必须为字符串")
        session=self._session(session_id)
        if normalize_rel(path)!=session["target_path"]: raise BridgeError(403,"PATH_DENIED","只能保存当前任务目标")
        key=self._write_key("save",base_revision,{"path":path,"html_sha256":hashlib.sha256(html.encode()).hexdigest()})
        replay=self._write_replay(session_id,key)
        if replay: return replay
        tmp=Path(tempfile.mkdtemp(prefix="save-",dir=self.internal))
        try:
            root=tmp/"bundle"; self._copy_current_bundle(session_id,root); target=root/Path(session["target_path"]).name; target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(html.encode("utf-8")); manifest=self.scan_bundle(target)
            return self._publish(session_id,root,manifest,base_revision,"save",write_key=key,allow_git_init=init)
        finally: shutil.rmtree(tmp,ignore_errors=True)

    def asset(self,session_id,path,data_base64,base_revision):
        rel=normalize_rel(path)
        if not rel.startswith("assets/") or Path(rel).suffix.lower() not in {".png",".jpg",".jpeg",".webp",".gif"}: raise BridgeError(403,"PATH_DENIED","浏览器仅可上传 assets 图片")
        try: raw=base64.b64decode(data_base64,validate=True)
        except (ValueError,binascii.Error): raise BridgeError(400,"INVALID_ARGUMENT","data_base64 非法")
        if len(raw)>ASSET_RAW_MAX: raise BridgeError(413,"PAYLOAD_TOO_LARGE","图片超过 32MiB")
        self._validate_image(raw,Path(rel).suffix.lower())
        key=self._write_key("asset",base_revision,{"path":rel,"sha256":hashlib.sha256(raw).hexdigest()})
        replay=self._write_replay(session_id,key)
        if replay:return replay
        session=self._session(session_id); tmp=Path(tempfile.mkdtemp(prefix="asset-",dir=self.internal))
        try:
            root=tmp/"bundle"; self._copy_current_bundle(session_id,root); out=root/rel
            current=self._bundle_root(session)/rel
            registered=self.db.execute("SELECT 1 FROM bundle_files WHERE session_id=? AND path=?",(session_id,rel)).fetchone()
            if self.secure.exists(self._work_rel(current)) and not registered: raise BridgeError(409,"REVISION_CONFLICT","未登记同名资产已存在")
            out.parent.mkdir(parents=True,exist_ok=True); out.write_bytes(raw); manifest=self.scan_bundle(root/Path(session["target_path"]).name)
            return self._publish(session_id,root,manifest,base_revision,"asset",write_key=key,event_override=("assets-changed",{"session_id":session_id,"files":[rel]}))
        finally: shutil.rmtree(tmp,ignore_errors=True)

    def _validate_image(self,raw,ext):
        ok=(ext==".png" and raw.startswith(b"\x89PNG\r\n\x1a\n")) or (ext in {".jpg",".jpeg"} and raw.startswith(b"\xff\xd8")) or (ext==".gif" and raw[:6] in (b"GIF87a",b"GIF89a")) or (ext==".webp" and raw.startswith(b"RIFF") and raw[8:12]==b"WEBP")
        if not ok: raise BridgeError(422,"INVALID_ARTIFACT","图片扩展名与签名不符")

    def _write_replay(self,sid,key):
        row=self.db.execute("SELECT result_json FROM write_receipts WHERE session_id=? AND write_key=?",(sid,key)).fetchone()
        if not row:return None
        result=json.loads(row[0]); current=self.observe_revision(sid)
        if current==result["revision"]: return result
        raise BridgeError(409,"REVISION_CONFLICT","原写入已成功但目标已继续前进",True,{"receipt_id":result["receipt_id"],"revision":current})

    def _copy_current_bundle(self,sid,dst):
        session=self._session(sid); root=self._bundle_root(session); dst.mkdir(parents=True,exist_ok=True)
        for row in self.db.execute("SELECT path,present FROM bundle_files WHERE session_id=?",(sid,)):
            if row["present"]:
                src=root/row["path"];out=dst/row["path"];self._managed_copy_out(src,out)

    def observe_revision(self,sid):
        session=self._session(sid); target=self._target_abs(session)
        if not self.secure.exists(self._work_rel(target)): return None
        manifest=self.scan_bundle(target); return self.revisions(manifest)[0]

    def _atomic_json(self,path,data):
        path.parent.mkdir(parents=True,exist_ok=True)
        fd,tmp=tempfile.mkstemp(dir=path.parent,prefix=".tmp-")
        try:
            with os.fdopen(fd,"wb") as f: f.write(canonical_json(data)); f.flush(); os.fsync(f.fileno())
            os.replace(tmp,path); dfd=os.open(path.parent,os.O_DIRECTORY); os.fsync(dfd); os.close(dfd)
        finally:
            with contextlib.suppress(OSError): os.unlink(tmp)

    def _publish(self,sid,candidate_root,manifest,base_revision,action,*,intent=None,consumer_id=None,message="",write_key=None,allow_git_init=True,export_source_revision=None,event_override=None):
        with self._session_lock(sid):
            session=self._session(sid); current=self.observe_revision(sid)
            if intent:
                live=self.db.execute("SELECT status,attempt,consumer_id FROM intents WHERE id=? AND session_id=?",(intent["id"],sid)).fetchone()
                if not live or live["status"]!="processing" or live["attempt"]!=intent["attempt"] or live["consumer_id"]!=consumer_id:
                    raise BridgeError(409,"RECOVERY_REQUIRED","consumer/attempt 所有权已失效",True)
            if current!=base_revision: raise BridgeError(409,"REVISION_CONFLICT","正式目标 revision 已变化",True,{"revision":current})
            if intent:
                observed_candidate=self.scan_bundle(candidate_root/Path(session["target_path"]).name)
                if observed_candidate!=manifest:
                    raise BridgeError(422,"VALIDATION_REQUIRED","验收后工作副本发生变化")
            new_rev,new_exp=self.revisions(manifest)
            old_manifest=[dict(x) for x in self.db.execute("SELECT path,class,sha256,size,present FROM bundle_files WHERE session_id=? ORDER BY path",(sid,))]
            old_paths={x["path"] for x in old_manifest};target_root=self._bundle_root(session)
            for item in manifest:
                target=target_root/item["path"]
                if item["path"] not in old_paths and self.secure.exists(self._work_rel(target)):
                    raise BridgeError(409,"REVISION_CONFLICT",f"未登记同名文件碰撞: {item['path']}")
            old_sid,old_root,_=self._snapshot(sid,old_manifest,self._bundle_root(session),"pre-"+action,protect_git=False) if old_manifest else (None,None,None)
            new_sid,new_root,_=self._snapshot(sid,manifest,candidate_root,action,protect_git=False)
            if intent and self.scan_bundle(new_root/Path(session["target_path"]).name)!=manifest:
                raise BridgeError(422,"VALIDATION_REQUIRED","工作副本在 seal 期间发生变化")
            commit,ref,old_ref=self._git_protect(sid,manifest,new_root,allow_git_init,update_ref=False)
            receipt=new_id("rcpt_"); txid=new_id("tx_"); journal=self.internal/"transactions"/(txid+".json")
            doc={"schema_version":1,"transaction_id":txid,"session_id":sid,"action":action,"base_revision":base_revision,"source_revision":new_rev,"export_revision":new_exp,"old_snapshot_id":old_sid,"new_snapshot_id":new_sid,"receipt_id":receipt,"stage":"PREPARED","old_manifest":old_manifest,"new_manifest":manifest,"git_ref":ref,"git_old":old_ref,"git_new":commit}
            self._atomic_json(journal,doc)
            now=utcnow()
            with self.db:
                self.db.execute("INSERT INTO publications(id,session_id,action,intent_id,attempt,base_revision,new_revision,new_export_revision,status,receipt_id,old_snapshot_id,new_snapshot_id,journal_path,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(txid,sid,action,intent["id"] if intent else None,intent["attempt"] if intent else None,base_revision,new_rev,new_exp,"PREPARED",receipt,old_sid,new_sid,str(journal),now,now))
            self._fault("publication.prepared", transaction_id=txid)
            with self.db:
                self.db.execute("UPDATE publications SET status='APPLYING',updated_at=? WHERE id=?",(utcnow(),txid))
            self._fault("publication.applying", transaction_id=txid)
            target_root=self._bundle_root(session)
            old_map={x["path"]:x for x in old_manifest}; new_map={x["path"]:x for x in manifest}
            try:
                operation_index=0
                for rel in sorted(set(old_map)-set(new_map)):
                    p=target_root/rel
                    if self.secure.exists(self._work_rel(p)):
                        actual,_=self._managed_hash(p)
                        if actual!=old_map[rel]["sha256"]: raise BridgeError(503,"RECOVERY_FAILED","发布遇到第三方文件字节")
                        self._managed_unlink(p)
                        self._fault("publication.file_applied",transaction_id=txid,index=operation_index,path=rel,operation="delete")
                        operation_index+=1
                order={"source-image":0,"source-legacy":0,"source-font":0,"source-html":1,"derived":2,"export":3,"export-manifest":4}
                for item in sorted(manifest,key=lambda x:(order.get(x["class"],9),x["path"])):
                    src=new_root/item["path"]; dst=target_root/item["path"]; exists=self.secure.exists(self._work_rel(dst))
                    if exists and item["path"] not in old_map: raise BridgeError(409,"REVISION_CONFLICT",f"未登记同名文件碰撞: {item['path']}")
                    if exists:
                        actual,_=self._managed_hash(dst)
                        if actual not in {old_map[item["path"]]["sha256"],item["sha256"]}: raise BridgeError(503,"RECOVERY_FAILED","发布遇到第三方文件字节")
                    self._managed_replace(dst,src)
                    self._fault("publication.file_applied",transaction_id=txid,index=operation_index,path=item["path"],operation="replace")
                    operation_index+=1
                observed=self.scan_bundle(self._target_abs(session)); obs_rev,obs_exp=self.revisions(observed)
                if obs_rev!=new_rev or obs_exp!=new_exp: raise BridgeError(503,"RECOVERY_FAILED","发布后清单校验失败")
                git,repo,expected_ref=self._ensure_git(sid,False)
                if expected_ref!=ref: raise BridgeError(503,"RECOVERY_FAILED","Git ref 身份变化")
                self._git_ref_cas(git,repo,ref,old_ref,commit)
                self._fault("publication.git_ref_updated",transaction_id=txid,git_ref=ref)
            except BridgeError as exc:
                if exc.code=="RECOVERY_FAILED":
                    self.frozen=True
                    with self.db:self.db.execute("UPDATE publications SET status='RECOVERY_FAILED',updated_at=? WHERE id=?",(utcnow(),txid))
                    raise
                self._recover_files(sid,old_sid,old_manifest,manifest);self._git_ref_restore(sid,ref,old_ref,commit)
                with self.db:self.db.execute("UPDATE publications SET status='ROLLED_BACK',updated_at=? WHERE id=?",(utcnow(),txid))
                raise
            except Exception:
                self._recover_files(sid,old_sid,old_manifest,manifest);self._git_ref_restore(sid,ref,old_ref,commit)
                with self.db:self.db.execute("UPDATE publications SET status='ROLLED_BACK',updated_at=? WHERE id=?",(utcnow(),txid))
                raise
            dependencies=self.external_dependencies(self._target_abs(session)) if new_rev else []
            event_ids=[]
            result={"ok":True,"session_id":sid,"path":session["target_path"],"receipt_id":receipt,"revision":new_rev,"export_revision":new_exp,"snapshot_id":new_sid,"events":event_ids,"committed":True,"hash":commit[:12],"gitReady":True}
            with self.db:
                self.db.execute("DELETE FROM bundle_files WHERE session_id=?",(sid,))
                for item in manifest:self.db.execute("INSERT INTO bundle_files(session_id,path,class,sha256,size,present,snapshot_id) VALUES(?,?,?,?,?,1,?)",(sid,item["path"],item["class"],item["sha256"],item["size"],new_sid))
                phase="editing" if new_rev else session["phase"]
                deck=session["target_path"] if new_rev else session["deck_path"]
                binding=export_source_revision if export_source_revision is not None else session["export_source_revision"]
                self.db.execute("UPDATE sessions SET deck_path=?,phase=?,revision=?,export_revision=?,export_source_revision=?,git_ready=1,git_ref=?,updated_at=? WHERE id=?",(deck,phase,new_rev,new_exp,binding,ref,utcnow(),sid))
                if new_rev:self.db.execute("INSERT OR REPLACE INTO dependency_reports VALUES(?,?,?,?)",(sid,new_rev,canonical_json(dependencies).decode(),utcnow()))
                if event_override:
                    typ,data=event_override; data={**data,"revision":new_rev,"receipt_id":receipt}; event_ids.append(self._event(sid,typ,data))
                else:
                    event_ids.append(self._event(sid,"deck-changed",{"session_id":sid,"revision":new_rev,"path":session["target_path"],"source":action,"receipt_id":receipt}))
                if export_source_revision is not None:event_ids.append(self._event(sid,"export-refreshed",{"session_id":sid,"revision":new_rev,"export_revision":new_exp}))
                result["events"][:]=event_ids
                if intent:
                    result.update({"intent_id":intent["id"],"status":"succeeded","message":message,"page_online":self.page_online(sid)})
                    self.db.execute("UPDATE intents SET status='succeeded',result_json=?,updated_at=? WHERE id=?",(canonical_json(result).decode(),utcnow(),intent["id"])); self.db.execute("UPDATE attempts SET status='succeeded',result_json=? WHERE intent_id=? AND attempt=?",(canonical_json(result).decode(),intent["id"],intent["attempt"])); event_ids.append(self._event(sid,"intent-status",{"session_id":sid,"intent_id":intent["id"],"status":"succeeded","attempt":intent["attempt"]})); result["events"][:]=event_ids; self.db.execute("UPDATE intents SET result_json=? WHERE id=?",(canonical_json(result).decode(),intent["id"])); self._release_owner(sid,consumer_id)
                if write_key:self.db.execute("INSERT INTO write_receipts VALUES(?,?,?,?,?,?,?)",(sid,write_key,action,receipt,new_sid,canonical_json(result).decode(),utcnow()))
                self.db.execute("INSERT INTO facts(session_id,type,data_json,created_at) VALUES(?,?,?,?)",(sid,action,canonical_json({"revision":new_rev,"receipt_id":receipt}).decode(),utcnow()))
                self.db.execute("UPDATE publications SET status='COMMITTED',result_json=?,updated_at=? WHERE id=?",(canonical_json(result).decode(),utcnow(),txid))
            self._fault("publication.db_committed",transaction_id=txid,receipt_id=receipt)
            doc["stage"]="COMMITTED"; self._atomic_json(journal,doc); self._notify(sid)
            self._fault("publication.before_response",transaction_id=txid,receipt_id=receipt)
            return result

    def _recover_files(self,sid,desired_snapshot_id,desired_manifest,alternative_manifest):
        root=self._bundle_root(self._session(sid)); desired={x["path"]:x for x in desired_manifest}; alternative={x["path"]:x for x in alternative_manifest}; snapshot=self.internal/"snapshots"/desired_snapshot_id/"bundle" if desired_snapshot_id else None
        for rel in sorted(set(desired)|set(alternative)):
            target=root/rel; actual=None;exists=self.secure.exists(self._work_rel(target))
            if exists:actual=self._managed_hash(target)[0]
            allowed={x["sha256"] for x in (desired.get(rel),alternative.get(rel)) if x}
            if actual is not None and actual not in allowed:
                raise BridgeError(503,"RECOVERY_FAILED",f"恢复发现第三种字节: {rel}")
            if rel in desired:
                if actual!=desired[rel]["sha256"]:
                    src=snapshot/rel
                    if not src.is_file() or self._managed_hash(src)[0]!=desired[rel]["sha256"]: raise BridgeError(503,"RECOVERY_FAILED","恢复快照损坏")
                    self._managed_replace(target,src)
            elif exists:
                self._managed_unlink(target)

    def _git_ref_forward(self,sid,journal):
        git,repo,ref=self._ensure_git(sid,False)
        if ref!=journal["git_ref"]: raise BridgeError(503,"RECOVERY_FAILED","journal Git ref 身份不匹配")
        current=subprocess.run([git,"-C",str(repo),"rev-parse","--verify",ref],capture_output=True,text=True)
        value=current.stdout.strip() if current.returncode==0 else None
        if value==journal["git_new"]: return
        if value!=journal.get("git_old"): raise BridgeError(503,"RECOVERY_FAILED","Git 专用 ref 出现第三方值")
        self._git_ref_cas(git,repo,ref,journal.get("git_old"),journal["git_new"])

    def recover_publications(self):
        known={r[0] for r in self.db.execute("SELECT id FROM publications")}
        for path in (self.internal/"transactions").glob("*.json"):
            try: journal=json.loads(path.read_text("utf-8"))
            except Exception as exc: self.frozen=True;raise BridgeError(503,"RECOVERY_FAILED","publication journal 损坏") from exc
            if journal.get("transaction_id") not in known and journal.get("stage")=="PREPARED":
                journal["stage"]="ORPHANED";self._atomic_json(path,journal)
        rows=self.db.execute("SELECT * FROM publications WHERE status IN ('PREPARED','APPLYING')").fetchall()
        for row in rows:
            try:
                old_row=self.db.execute("SELECT manifest_json FROM snapshots WHERE id=?",(row["old_snapshot_id"],)).fetchone();new_row=self.db.execute("SELECT manifest_json FROM snapshots WHERE id=?",(row["new_snapshot_id"],)).fetchone()
                old_manifest=json.loads(old_row[0]) if old_row else [];new_manifest=json.loads(new_row[0]) if new_row else []
                self._recover_files(row["session_id"],row["old_snapshot_id"],old_manifest,new_manifest)
                journal=json.loads(Path(row["journal_path"]).read_text("utf-8"));self._git_ref_restore(row["session_id"],journal["git_ref"],journal.get("git_old"),journal["git_new"])
                with self.db:
                    self.db.execute("UPDATE publications SET status='ROLLED_BACK',updated_at=? WHERE id=?",(utcnow(),row["id"]))
                    if row["intent_id"]:
                        self.db.execute("UPDATE intents SET status='interrupted',consumer_id=NULL,lease_until=NULL,error_json=?,updated_at=? WHERE id=?",(canonical_json({"code":"RECOVERY_REQUIRED","message":"publication-recovered","retryable":True}).decode(),utcnow(),row["intent_id"]))
                        self.db.execute("UPDATE attempts SET status='interrupted' WHERE intent_id=? AND attempt=?",(row["intent_id"],row["attempt"]))
                        self._event(row["session_id"],"intent-status",{"session_id":row["session_id"],"intent_id":row["intent_id"],"status":"interrupted","attempt":row["attempt"]})
                if row["intent_id"]: self._notify(row["session_id"])
                journal["stage"]="ROLLED_BACK";self._atomic_json(Path(row["journal_path"]),journal)
            except Exception as exc:
                self.frozen=True; raise BridgeError(503,"RECOVERY_FAILED","publication 恢复失败") from exc
        for row in self.db.execute("SELECT * FROM publications WHERE status='COMMITTED'").fetchall():
            journal_path=Path(row["journal_path"])
            try:
                journal=json.loads(journal_path.read_text("utf-8"))
                if journal.get("stage")=="COMMITTED": continue
                old_row=self.db.execute("SELECT manifest_json FROM snapshots WHERE id=?",(row["old_snapshot_id"],)).fetchone();new_row=self.db.execute("SELECT manifest_json FROM snapshots WHERE id=?",(row["new_snapshot_id"],)).fetchone()
                old_manifest=json.loads(old_row[0]) if old_row else [];new_manifest=json.loads(new_row[0]) if new_row else []
                self._recover_files(row["session_id"],row["new_snapshot_id"],new_manifest,old_manifest);self._git_ref_forward(row["session_id"],journal)
                journal["stage"]="COMMITTED";self._atomic_json(journal_path,journal)
            except Exception as exc:
                self.frozen=True;raise BridgeError(503,"RECOVERY_FAILED","已提交 publication 恢复校验失败") from exc

    def versions(self,sid):
        rows=self.db.execute("SELECT id,source_revision,export_revision,git_commit,created_at,action FROM snapshots WHERE session_id=? ORDER BY created_at DESC",(sid,)).fetchall()
        return {"ok":True,"gitReady":bool(self._session(sid)["git_ready"]),"versions":[{"snapshot_id":r["id"],"hash":r["git_commit"],"revision":r["source_revision"],"export_revision":r["export_revision"],"time":r["created_at"],"message":r["action"]} for r in rows]}

    def rollback(self,sid,path,hash_value,base_revision):
        s=self._session(sid)
        if normalize_rel(path)!=s["target_path"]: raise BridgeError(403,"PATH_DENIED","只能回滚当前任务")
        row=self.db.execute("SELECT * FROM snapshots WHERE session_id=? AND (id=? OR git_commit=?)",(sid,hash_value,hash_value)).fetchone()
        if not row: raise BridgeError(404,"INTENT_NOT_FOUND","版本不属于当前任务")
        key=self._write_key("rollback",base_revision,{"snapshot":row["id"]}); replay=self._write_replay(sid,key)
        if replay:return replay
        manifest=json.loads(row["manifest_json"]); root=self.internal/"snapshots"/row["id"]/"bundle"
        return self._publish(sid,root,manifest,base_revision,"rollback",write_key=key,export_source_revision=row["source_revision"] if row["export_revision"] else None)

    def close_consumer(self,sid,cid,reason="user-ended"):
        self._session(sid)
        with self._session_lock(sid):
            with self.db:
                c=self.db.execute("SELECT * FROM consumers WHERE session_id=? AND consumer_id=?",(sid,cid)).fetchone()
                if c:
                    rows=self.db.execute("SELECT id,attempt FROM intents WHERE session_id=? AND consumer_id=? AND status='processing'",(sid,cid)).fetchall()
                    for row in rows:
                        err={"code":"RECOVERY_REQUIRED","message":reason,"retryable":True}
                        self.db.execute("UPDATE intents SET status='interrupted',consumer_id=NULL,lease_until=NULL,error_json=?,updated_at=? WHERE id=?",(canonical_json(err).decode(),utcnow(),row["id"]))
                        self.db.execute("UPDATE attempts SET status='interrupted' WHERE intent_id=? AND attempt=?",(row["id"],row["attempt"]))
                        self._event(sid,"intent-status",{"session_id":sid,"intent_id":row["id"],"status":"interrupted","attempt":row["attempt"]})
                    self.db.execute("UPDATE consumers SET state='paused',requires_open=1,lease_until=NULL WHERE session_id=? AND consumer_id=?",(sid,cid))
                    self.db.execute("UPDATE sessions SET owner_consumer_id=NULL,agent_state=CASE WHEN EXISTS(SELECT 1 FROM intents WHERE session_id=? AND status IN ('failed','conflict','interrupted')) THEN 'recovering' ELSE 'paused' END WHERE id=? AND owner_consumer_id=?",(sid,sid,cid))
            self._notify(sid)
        return {"ok":True,"session_id":sid,"consumer_state":"paused","agent_state":self.agent_state(sid),"pending_count":self._count(sid,"pending")}

    def heartbeat_consumer(self,sid,cid):
        self._expire(sid); s=self._session(sid)
        if s["owner_consumer_id"]!=cid: raise BridgeError(409,"RECOVERY_REQUIRED","consumer 不是有效 owner",True)
        c=self.db.execute("SELECT * FROM consumers WHERE session_id=? AND consumer_id=?",(sid,cid)).fetchone()
        if not c or c["requires_open"] or c["state"] not in {"waiting","working"}: raise BridgeError(409,"RECOVERY_REQUIRED","consumer 不可续租",True)
        lease=future(CONSUMER_LEASE_SEC)
        with self.db:
            self.db.execute("UPDATE consumers SET lease_until=? WHERE session_id=? AND consumer_id=?",(lease,sid,cid)); self.db.execute("UPDATE intents SET lease_until=? WHERE session_id=? AND consumer_id=? AND status='processing'",(lease,sid,cid))
        return {"ok":True,"role":"consumer","session_id":sid,"server_time":utcnow(),"lease_until":lease,"agent_state":self.agent_state(sid)}

    def heartbeat_browser(self,token,sid,body):
        expected={"protocol_version","role","session_id","client_id","dirty","active_edit","draft_pending","revision","last_event_id"}
        if set(body)!=expected or body["protocol_version"]!=2 or body["role"]!="browser" or body["session_id"]!=sid or not UUID_RE.match(str(body["client_id"])) or any(type(body[x]) is not bool for x in ("dirty","active_edit","draft_pending")) or isinstance(body["last_event_id"],bool) or not isinstance(body["last_event_id"],int) or body["last_event_id"]<0: raise BridgeError(400,"INVALID_ARGUMENT","browser heartbeat 非法")
        latest=self.db.execute("SELECT COALESCE(MAX(id),0) FROM events WHERE session_id=?",(sid,)).fetchone()[0]
        if body["last_event_id"]>latest: raise BridgeError(400,"INVALID_ARGUMENT","last_event_id 超出服务端游标")
        dig=token_digest(token); t=self.db.execute("SELECT * FROM browser_tokens WHERE token_digest=? AND session_id=? AND revoked_at IS NULL",(dig,sid)).fetchone()
        if not t: raise BridgeError(401,"UNAUTHORIZED","browser token 无效")
        if t["client_id"] and t["client_id"]!=body["client_id"]: raise BridgeError(403,"UNAUTHORIZED","browser token 已绑定另一 client")
        now=utcnow()
        with self.db:
            self.db.execute("UPDATE browser_tokens SET client_id=? WHERE token_digest=? AND client_id IS NULL",(body["client_id"],dig)); self.db.execute("INSERT INTO clients(id,session_id,token_digest,last_seen,dirty,active_edit,draft_pending,revision,last_event_id) VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(session_id,id) DO UPDATE SET last_seen=excluded.last_seen,dirty=excluded.dirty,active_edit=excluded.active_edit,draft_pending=excluded.draft_pending,revision=excluded.revision,last_event_id=excluded.last_event_id",(body["client_id"],sid,dig,now,int(body["dirty"]),int(body["active_edit"]),int(body["draft_pending"]),body["revision"],body["last_event_id"]))
        return {"ok":True,"role":"browser","session_id":sid,"client_id":body["client_id"],"server_time":now,"last_seen":now,"online_until":future(CLIENT_ONLINE_SEC),"revision":body["revision"],"last_event_id":body["last_event_id"]}

    def authorize_browser(self,token,sid,require_bound=True):
        row=self.db.execute("SELECT * FROM browser_tokens WHERE token_digest=? AND session_id=? AND revoked_at IS NULL",(token_digest(token),sid)).fetchone()
        if not row or (require_bound and not row["client_id"]): raise BridgeError(401,"UNAUTHORIZED","browser token 无效或尚未绑定")
        return row

    def get_status(self,sid):
        s=self._session(sid); clients=[]; now=time.time(); any_dirty=False
        for row in self.db.execute("SELECT * FROM clients WHERE session_id=?",(sid,)):
            online=parse_time(row["last_seen"])>=now-CLIENT_ONLINE_SEC; dirty=bool(row["dirty"]) if online else None; any_dirty|=bool(dirty)
            clients.append({"client_id":row["id"],"online":online,"dirty":dirty,"active_edit":bool(row["active_edit"]) if online else False,"draft_pending":bool(row["draft_pending"]) if online else False,"revision":row["revision"],"last_seen":row["last_seen"]})
        proc=self.db.execute("SELECT id,type,attempt,status FROM intents WHERE session_id=? AND status='processing' LIMIT 1",(sid,)).fetchone(); ints=[dict(r) for r in self.db.execute("SELECT id,type,attempt,status FROM intents WHERE session_id=? AND status='interrupted'",(sid,))]
        latest=self.db.execute("SELECT COALESCE(MAX(id),0) FROM events WHERE session_id=?",(sid,)).fetchone()[0]
        stale=not s["export_source_revision"] or s["export_source_revision"]!=s["revision"]
        return {"ok":True,"session_id":sid,"phase":s["phase"],"deck_path":str(self.workdir/s["deck_path"]) if s["deck_path"] else None,"target_path":str(self.workdir/s["target_path"]),"resource_path":s["target_path"],"revision":s["revision"],"export_revision":s["export_revision"],"export_stale":stale,"agent_state":self.agent_state(sid),"page_online":self.page_online(sid),"any_dirty":any_dirty,"clients":clients,"pending_count":self._count(sid,"pending"),"processing":dict(proc) if proc else None,"interrupted":ints,"recoverable_count":self.db.execute("SELECT COUNT(*) FROM intents WHERE session_id=? AND status IN ('failed','conflict','interrupted')",(sid,)).fetchone()[0],"latest_event_id":latest,"brief_options":self._brief_options_of(s),"track":self.track_of(sid),"view_attached":self.view_attached(sid),"ui_signal_ever":self.ui_signal_ever(sid),"capabilities":{"local_convert":self.allow_convert,"local_imagegen":self.allow_imagegen,"git_ready":bool(s["git_ready"])}}

    def query_intents(self,sid,body):
        allowed={"session_id","statuses","cursor","limit","intent_id"}
        if not isinstance(body,dict) or not set(body)<=allowed or body.get("session_id")!=sid: raise BridgeError(400,"INVALID_ARGUMENT","query 字段非法")
        if "intent_id" in body:
            if set(body)!={"session_id","intent_id"} or not UUID_RE.match(str(body["intent_id"])): raise BridgeError(400,"INVALID_ARGUMENT","单条 query 非法")
            row=self.db.execute("SELECT * FROM intents WHERE session_id=? AND id=?",(sid,body["intent_id"])).fetchone()
            if not row: raise BridgeError(404,"INTENT_NOT_FOUND","请求不存在")
            return {"ok":True,"items":[self._intent_summary(row)],"next_cursor":None,"has_more":False}
        statuses=body.get("statuses")
        if statuses is not None and (not isinstance(statuses,list) or not statuses or len(statuses)!=len(set(statuses)) or not set(statuses)<=INTENT_STATUSES): raise BridgeError(400,"INVALID_ARGUMENT","statuses 非法")
        cursor=body.get("cursor",0); limit=body.get("limit",50)
        if isinstance(cursor,bool) or not isinstance(cursor,int) or cursor<0 or isinstance(limit,bool) or not isinstance(limit,int) or not 1<=limit<=100: raise BridgeError(400,"INVALID_ARGUMENT","cursor/limit 非法")
        args=[sid,cursor]; sql="SELECT * FROM intents WHERE session_id=? AND seq>?"
        if statuses: sql+=" AND status IN ("+",".join("?"*len(statuses))+")"; args+=statuses
        sql+=" ORDER BY seq LIMIT ?"; args.append(limit+1); rows=self.db.execute(sql,args).fetchall(); more=len(rows)>limit; rows=rows[:limit]
        return {"ok":True,"items":[self._intent_summary(r) for r in rows],"next_cursor":rows[-1]["seq"] if more and rows else None,"has_more":more}

    def _intent_summary(self,r):
        error=json.loads(r["error_json"]) if r["error_json"] else None; result=json.loads(r["result_json"]) if r["result_json"] else None
        summary=None
        if r["status"]=="succeeded" and result: summary={k:result.get(k) for k in ("receipt_id","revision","export_revision","message")}
        return {"id":r["id"],"seq":r["seq"],"type":r["type"],"status":r["status"],"attempt":r["attempt"],"base_revision":r["base_revision"],"created_at":r["created_at"],"updated_at":r["updated_at"],"error":error,"result_summary":summary}

    def create_draft(self,sid,client_id,html,annotations,base_revision):
        if not isinstance(html,str) or not isinstance(annotations,list): raise BridgeError(400,"INVALID_ARGUMENT","draft 非法")
        did=new_id("draft_")
        with self.db:self.db.execute("INSERT INTO drafts VALUES(?,?,?,?,?,?,?)",(did,sid,client_id,html,canonical_json(annotations).decode(),base_revision,utcnow()))
        return {"ok":True,"draft_id":did}

    def start_local_convert(self,sid,formats):
        if not self.allow_convert: raise BridgeError(403,"UNAUTHORIZED","daemon 未启用本地转换")
        if not isinstance(formats,list) or not formats or len(formats)!=len(set(formats)) or not set(formats)<={"pptx","vector","pdf"}: raise BridgeError(400,"INVALID_ARGUMENT","formats 非法")
        session=self._session(sid)
        if not session["deck_path"]: raise BridgeError(409,"RECOVERY_REQUIRED","尚无可转换 deck")
        with self._convert_lock:
            if self._convert_state["status"]=="running":
                if self._convert_state["session_id"]!=sid: raise BridgeError(409,"SESSION_BUSY","另一任务正在本地转换",True)
                return {"ok":True,"started":False,**self._convert_state}
            if self.db.execute("SELECT 1 FROM intents WHERE session_id=? AND status='processing'",(sid,)).fetchone(): raise BridgeError(409,"SESSION_BUSY","Agent 正在处理该任务",True)
            consumer="local-convert-"+str(uuid.uuid4()); now=utcnow(); iid=str(uuid.uuid4()); payload={"formats":formats,"scope":"all"}; raw=canonical_json(payload); digest=digest_json({"type":"convert.requested","base_revision":session["revision"],"payload":payload})
            with self.db:
                self.db.execute("INSERT INTO consumers(session_id,consumer_id,state,registered_at,requires_open) VALUES(?,?,?,?,0)",(sid,consumer,"registered",now)); seq=self.db.execute("SELECT COALESCE(MAX(seq),0)+1 FROM intents").fetchone()[0]; self.db.execute("INSERT INTO intents(id,session_id,seq,type,payload_json,payload_digest,payload_bytes,base_revision,status,attempt,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",(iid,sid,seq,"convert.requested",raw.decode(),digest,len(raw),session["revision"],"pending",1,now,now)); self._event(sid,"intent-status",{"session_id":sid,"intent_id":iid,"status":"pending","attempt":1})
            self._convert_state={"status":"running","session_id":sid,"intent_id":iid,"started":now,"tail":""}
            threading.Thread(target=self._local_convert_worker,args=(sid,consumer,iid),daemon=True).start()
            return {"ok":True,"started":True,**self._convert_state}

    def _run_local_process(self,argv,sid,iid,attempt,consumer,timeout=1800):
        process=subprocess.Popen(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        deadline=time.monotonic()+timeout
        try:
            while True:
                remaining=deadline-time.monotonic()
                if remaining<=0: raise subprocess.TimeoutExpired(argv,timeout)
                try:
                    stdout,stderr=process.communicate(timeout=min(30,remaining))
                    return subprocess.CompletedProcess(argv,process.returncode,stdout,stderr)
                except subprocess.TimeoutExpired:
                    self.push_update(sid,iid,attempt,consumer,"progress","local conversion running")
        except BaseException:
            if process.poll() is None:
                process.terminate()
                try:process.communicate(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill();process.communicate()
            raise

    # 兼容别名：既有测试与本地转换 worker 沿用旧名
    _run_local_convert_process = _run_local_process

    def _local_convert_worker(self,sid,consumer,iid):
        try:
            claimed=self.await_intent(sid,consumer,1); work_path=claimed["work_path"];attempt=claimed["attempt"]
            script=PROJECT_ROOT/"skills/html-pptx/scripts/export-pptx.py"
            argv=[sys.executable,str(script),work_path,"--force","--track","both"]
            run=self._run_local_convert_process(argv,sid,iid,attempt,consumer)
            tail="\n".join((run.stdout+"\n"+run.stderr).splitlines()[-30:])
            if run.returncode:
                self.push_update(sid,iid,attempt,consumer,"fail",tail or "conversion failed")
                state="failed"
            else:
                candidate=revision_cli(work_path)
                validation={"candidate_revision":candidate,"export_source_revision":candidate,"checks":[{"name":"export","argv":argv,"exit_code":0,"report_path":None}]}
                self.push_update(sid,iid,attempt,consumer,"complete","local conversion complete",validation)
                state="done"
            with self._convert_lock:self._convert_state.update({"status":state,"tail":tail})
        except Exception as exc:
            with self._convert_lock:self._convert_state.update({"status":"failed","tail":str(exc)})

    def local_convert_status(self,sid):
        with self._convert_lock:
            state=dict(self._convert_state)
        if state["session_id"] not in (None,sid): raise BridgeError(404,"SESSION_NOT_FOUND","当前任务无转换记录")
        return {"ok":True,**state}

    # ---------- G6 本地插画通道（--imagegen；imagegen-v2.md §3-G6） ----------
    # 与本地转换同构：daemon 只做编排（落 illustrate.requested intent + 后台 worker），
    # 生图与验收 100% 由技能脚本完成（imagegen-adapter.py + render/capacity/images/
    # manifest 四闸 + check-image-harmony 告警），本文件不含任何生图/校验逻辑。
    # 纪律：只补插画（页内 placeholder 槽位），禁止烙入（烙入必须过代表页审批闸门）；
    # provider 路径只来自启动配置（env/config.json），只存内存，不落 ledger/deck。

    IMAGEGEN_SLOT_RE = re.compile(r'data-image-slot="([a-z0-9][a-z0-9-]*-(\d+)x(\d+))"')
    IMAGEGEN_PAGE_SLOT_RE = re.compile(r"^page-baked-")

    def _scan_placeholder_slots(self, text):
        """扫描 deck HTML 中 state=placeholder 的页内插画槽位（页面级 page-baked-*
        属烙入流程，本地通道明确跳过）。返回 [{slot,name,w,h,intent}]，槽位去重保序。"""
        found=[]; seen=set()
        for tag in re.findall(r"<img\b[^>]*>",text):
            if 'data-editable-image' not in tag or 'data-image-state="placeholder"' not in tag: continue
            m=re.search(r'data-image-slot="([a-z0-9][a-z0-9-]*-(\d+)x(\d+))"',tag)
            if not m or self.IMAGEGEN_PAGE_SLOT_RE.match(m.group(1)): continue
            slot=m.group(1)
            if slot in seen: continue
            seen.add(slot)
            im=re.search(r'data-image-intent="([^"]*)"',tag)
            intent=_html.unescape(im.group(1)).strip() if im else ""
            found.append({"slot":slot,"name":re.sub(r"-\d+x\d+$","",slot),
                          "w":int(m.group(2)),"h":int(m.group(3)),"intent":intent})
        return found

    @staticmethod
    def _slot_expected_size(w,h):
        """由槽位声明比例推算生图像素尺寸：长边 ≥2048 且短边 ≥1024（与 G7 静态下限
        及 adapter 验收对齐；4:3 → 2048x1536，16:9 → 2048x1152），取偶数。"""
        s=max(2048/max(w,h),1024/min(w,h))
        return (int(round(w*s/2)*2),int(round(h*s/2)*2))

    def start_local_imagegen(self,sid):
        if not self.allow_imagegen: raise BridgeError(403,"UNAUTHORIZED","daemon 未启用本地插画（--imagegen）")
        if not self.imagegen_provider: raise BridgeError(503,"STORAGE_UNAVAILABLE","未配置 imagegen provider（PPTX_HTML_IMAGEGEN_PROVIDER 或 .pptx-html/config.json 的 imagegen_provider）")
        session=self._session(sid)
        if not session["deck_path"]: raise BridgeError(409,"RECOVERY_REQUIRED","尚无可补齐插画的 deck")
        with self._imagegen_lock:
            if self._imagegen_state["status"]=="running":
                if self._imagegen_state["session_id"]!=sid: raise BridgeError(409,"SESSION_BUSY","另一任务正在本地生图",True)
                state=dict(self._imagegen_state); state["started_at"]=state.pop("started")
                return {"ok":True,"started":False,**state}
            if self.db.execute("SELECT 1 FROM intents WHERE session_id=? AND status='processing'",(sid,)).fetchone(): raise BridgeError(409,"SESSION_BUSY","Agent 正在处理该任务",True)
            slots=self._scan_placeholder_slots(self.secure.read(self._work_rel(self._target_abs(session))).decode("utf-8"))
            if not slots:
                return {"ok":True,"started":False,"status":"idle","session_id":sid,"intent_id":None,"started_at":None,"tail":"当前 deck 没有 placeholder 插画槽位，无需补齐","slots":[]}
            consumer="local-imagegen-"+str(uuid.uuid4()); now=utcnow(); iid=str(uuid.uuid4())
            payload={"slots":[s["slot"] for s in slots]}; raw=canonical_json(payload)
            digest=digest_json({"type":"illustrate.requested","base_revision":session["revision"],"payload":payload})
            with self.db:
                self.db.execute("INSERT INTO consumers(session_id,consumer_id,state,registered_at,requires_open) VALUES(?,?,?,?,0)",(sid,consumer,"registered",now)); seq=self.db.execute("SELECT COALESCE(MAX(seq),0)+1 FROM intents").fetchone()[0]; self.db.execute("INSERT INTO intents(id,session_id,seq,type,payload_json,payload_digest,payload_bytes,base_revision,status,attempt,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",(iid,sid,seq,"illustrate.requested",raw.decode(),digest,len(raw),session["revision"],"pending",1,now,now)); self._event(sid,"intent-status",{"session_id":sid,"intent_id":iid,"status":"pending","attempt":1})
            self._imagegen_state={"status":"running","session_id":sid,"intent_id":iid,"started":now,"tail":"","slots":payload["slots"]}
            threading.Thread(target=self._local_imagegen_worker,args=(sid,consumer,iid),daemon=True).start()
            state=dict(self._imagegen_state); state["started_at"]=state.pop("started")
            return {"ok":True,"started":True,**state}

    def _rewrite_slot_generated(self,text,slot,name):
        """把工作副本中指定槽位的 img 标签推进到 generated：src→assets/<name>.png。
        槽位三属性其余部分（slot/intent）保持不动。"""
        pattern=re.compile(r"<img\b(?=[^>]*data-image-slot=\""+re.escape(slot)+r"\")[^>]*>")
        m=pattern.search(text)
        if not m: raise BridgeError(422,"INVALID_ARTIFACT","工作副本中找不到槽位 "+slot)
        tag=m.group(0)
        if 'src="' not in tag or 'data-image-state="' not in tag: raise BridgeError(422,"INVALID_ARTIFACT","槽位 img 缺 src/state 属性："+slot)
        tag=re.sub(r'src="[^"]*"','src="assets/'+name+'.png"',tag,count=1)
        tag=re.sub(r'data-image-state="[^"]*"','data-image-state="generated"',tag,count=1)
        return text[:m.start()]+tag+text[m.end():]

    def _local_imagegen_worker(self,sid,consumer,iid):
        tail=""
        try:
            claimed=self.await_intent(sid,consumer,1); work_path=claimed["work_path"]; attempt=claimed["attempt"]
            deck=Path(work_path); bundle=deck.parent
            scripts=PROJECT_ROOT/"skills/html-pptx/scripts"
            slots=(claimed.get("payload") or {}).get("slots") or []
            text=deck.read_text("utf-8")
            catalog={s["slot"]:s for s in self._scan_placeholder_slots(text)}
            for slot in slots:
                info=catalog.get(slot)
                if not info: continue   # 已被其他途径补齐的槽位跳过（幂等）
                ew,eh=self._slot_expected_size(info["w"],info["h"]); size="%dx%d"%(ew,eh)
                prompt=(info["intent"] or "补齐该图片槽位")+"\n\n输出尺寸 %s，画面不含文字、水印、边框。"%size
                argv=[sys.executable,str(scripts/"imagegen-adapter.py"),str(bundle),
                      "--provider-script",self.imagegen_provider,"--prompt",prompt,
                      "--name",info["name"],"--expected-size",size,"--size",size,"--format","png"]
                run=self._run_local_process(argv,sid,iid,attempt,consumer,timeout=1400)
                tail="\n".join((run.stdout+"\n"+run.stderr).splitlines()[-30:])
                if run.returncode:
                    self.push_update(sid,iid,attempt,consumer,"fail","槽位 %s 生图失败：%s"%(slot,tail or "adapter 非零退出"))
                    with self._imagegen_lock:self._imagegen_state.update({"status":"failed","tail":tail})
                    return
                text=self._rewrite_slot_generated(text,slot,info["name"])
                deck.write_text(text,"utf-8")
                self.push_update(sid,iid,attempt,consumer,"progress","槽位 %s 已生成（%s）"%(slot,size))
            # 四闸（与技能 Step 5.5 同一组命令；manifest 最后跑，--write-hashes 会改写 HTML）
            manifest_out=Path(tempfile.mkstemp(prefix=".imagegen-manifest-",suffix=".json")[1])
            gates=[("render",[sys.executable,str(scripts/"check-render.py"),str(deck)],None),
                   ("capacity",[sys.executable,str(scripts/"check-capacity.py"),str(deck),"--json",str(bundle/"capacity-report.json")],"capacity-report.json"),
                   ("images",["node",str(scripts/"check-images.mjs"),str(deck),"--mode","illustration"],None),
                   ("manifest",[sys.executable,str(scripts/"extract-manifest.py"),str(deck),"--write-hashes","--out",str(manifest_out)],None)]
            checks=[]
            try:
                for name,argv,report in gates:
                    run=self._run_local_process(argv,sid,iid,attempt,consumer,timeout=1800)
                    tail="\n".join((run.stdout+"\n"+run.stderr).splitlines()[-30:])
                    if run.returncode:
                        self.push_update(sid,iid,attempt,consumer,"fail","验收闸 %s 未通过：%s"%(name,tail))
                        with self._imagegen_lock:self._imagegen_state.update({"status":"failed","tail":tail})
                        return
                    checks.append({"name":name,"argv":[str(x) for x in argv],"exit_code":0,"report_path":report})
            finally:
                with contextlib.suppress(FileNotFoundError): manifest_out.unlink()
            # 色彩一致性后置校验（G2 告警口径）：rc0 通过/仅告警；rc1（≥50% 双触发）阻断；
            # rc2（环境/用法问题，如无浏览器）只记告警不阻断——四闸已经给出质量底线。
            harmony_tail=""
            run=self._run_local_process([sys.executable,str(scripts/"check-image-harmony.py"),str(deck)],sid,iid,attempt,consumer,timeout=900)
            harmony_tail="\n".join((run.stdout+"\n"+run.stderr).splitlines()[-10:])
            if run.returncode==1:
                self.push_update(sid,iid,attempt,consumer,"fail","色彩一致性阻断（≥50% 图双触发 A+B）："+harmony_tail)
                with self._imagegen_lock:self._imagegen_state.update({"status":"failed","tail":harmony_tail})
                return
            candidate=revision_cli(work_path)
            validation={"candidate_revision":candidate,"checks":checks}
            message="本地插画补齐完成：%d 个槽位"%len(slots)+("；色彩校验告警："+harmony_tail if run.returncode==2 else "")
            self.push_update(sid,iid,attempt,consumer,"complete",message,validation)
            with self._imagegen_lock:self._imagegen_state.update({"status":"done","tail":message})
        except Exception as exc:
            with self._imagegen_lock:self._imagegen_state.update({"status":"failed","tail":str(exc)})

    def local_imagegen_status(self,sid):
        with self._imagegen_lock:
            state=dict(self._imagegen_state)
        if state["session_id"] not in (None,sid): raise BridgeError(404,"SESSION_NOT_FOUND","当前任务无生图记录")
        return {"ok":True,**state}

    def bootstrap_issue(self,mode,path):
        if mode not in {"deck","new"}: raise BridgeError(400,"INVALID_ARGUMENT","bootstrap mode 非法")
        rel=normalize_rel(path,suffix=".html"); target=self.workdir/rel
        if mode=="deck" and not target.is_file(): raise BridgeError(400,"INVALID_ARGUMENT","deck 不存在")
        if mode=="new" and target.exists(): raise BridgeError(409,"REVISION_CONFLICT","new 目标已存在")
        raw=secrets.token_urlsafe(32); expires=future(BOOTSTRAP_TTL_SEC)
        with self.db:self.db.execute("INSERT INTO bootstrap_tokens VALUES(?,?,?,?,?,NULL)",(token_digest(raw),self.instance_id,mode,rel,expires))
        return {"ok":True,"url":f"{self.origin}/bootstrap#boot={raw}","expires_at":expires}

    def bootstrap_redeem(self,ticket,raw):
        if not hmac.compare_digest(token_digest(raw),ticket): raise BridgeError(401,"UNAUTHORIZED","bootstrap ticket 不匹配")
        with self.db:
            row=self.db.execute("SELECT * FROM bootstrap_tokens WHERE token_digest=?",(ticket,)).fetchone()
            if not row or row["used_at"] or row["instance_id"]!=self.instance_id or parse_time(row["expires_at"])<time.time(): raise BridgeError(401,"UNAUTHORIZED","bootstrap 已失效")
            self.db.execute("UPDATE bootstrap_tokens SET used_at=? WHERE token_digest=? AND used_at IS NULL",(utcnow(),ticket))
        session=self.register_session(deck_path=str(self.workdir/row["target_path"]) if row["mode"]=="deck" else None,output_path=row["target_path"],auto_git=False)
        token=self.issue_browser_token(session["id"])
        # 手动启动时 view 的唯一来源是 mode（设计 brief-page-split §6 / C8：/bootstrap 的 query
        # 被精确校验 `set(q)=={"ticket"}`，view 不能走 query）——新建目标落脑暴，打开已有 deck 落工作台。
        view="brief" if row["mode"]=="new" else "edit"
        return f"/editor.html#brt={token}&session={session['id']}&view={view}"

    def heartbeat_management(self,sid,cid): return self.heartbeat_consumer(sid,cid)

    def events_after(self,sid,after):
        return self.db.execute("SELECT * FROM events WHERE session_id=? AND id>? ORDER BY id",(sid,after)).fetchall()


LANDING = b"""<!doctype html><meta charset=utf-8><meta name=referrer content=no-referrer><title>Opening editor</title><script>const p=new URLSearchParams(location.hash.slice(1)),t=p.get('boot');history.replaceState(null,'',location.pathname);if(!t){document.body.textContent='Missing bootstrap token; rerun the launcher.'}else{crypto.subtle.digest('SHA-256',new TextEncoder().encode(t)).then(b=>{const h=[...new Uint8Array(b)].map(x=>x.toString(16).padStart(2,'0')).join('');document.cookie='pptx_bootstrap_'+h+'='+encodeURIComponent(t)+'; Path=/bootstrap; SameSite=Strict; Max-Age=300';location.replace('/bootstrap?ticket='+h)})}</script>"""


class BridgeHTTPServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self,address,core):
        super().__init__(address,BridgeHandler); self.core=core; self.workdir=core.workdir
        self._request_condition = threading.Condition()
        self._active_requests = set()

    def process_request(self,request,client_address):
        with self._request_condition:
            self._active_requests.add(request)
        try:
            super().process_request(request,client_address)
        except Exception:
            with self._request_condition:
                self._active_requests.discard(request)
                self._request_condition.notify_all()
            raise

    def process_request_thread(self,request,client_address):
        try:
            super().process_request_thread(request,client_address)
        finally:
            with self._request_condition:
                self._active_requests.discard(request)
                self._request_condition.notify_all()

    def _disconnect_requests(self):
        with self._request_condition:
            requests = list(self._active_requests)
        for request in requests:
            with contextlib.suppress(OSError):
                request.shutdown(socket.SHUT_RDWR)

    def shutdown(self):
        self.core.begin_shutdown()
        self._disconnect_requests()
        super().shutdown()
        self._disconnect_requests()

    def server_close(self):
        super().server_close()
        with self._request_condition:
            while self._active_requests:
                self._request_condition.wait()


class BridgeHandler(BaseHTTPRequestHandler):
    server_version="PptxBridge/2"
    protocol_version="HTTP/1.1"
    def log_message(self,*args): pass
    @property
    def core(self): return self.server.core
    def _json(self,obj,status=200,headers=None):
        raw=canonical_json(obj); self.send_response(status); self.send_header("Content-Type","application/json; charset=utf-8"); self.send_header("Content-Length",str(len(raw))); self.send_header("Cache-Control","no-store"); self.send_header("X-Content-Type-Options","nosniff");
        for k,v in (headers or {}).items():self.send_header(k,v)
        self.end_headers();
        if self.command!="HEAD":self.wfile.write(raw)
    def _error(self,e): self._json(e.payload(),e.status)
    def _origin(self): return self.core.origin
    def _check_host_origin(self,write=False,bootstrap_redeem=False):
        host=self.headers.get("Host")
        expected=urlsplit(self._origin()).netloc
        if host!=expected: raise BridgeError(403,"ORIGIN_DENIED","Host 不匹配")
        origin=self.headers.get("Origin")
        if origin is not None and origin!=self._origin(): raise BridgeError(403,"ORIGIN_DENIED","Origin 不匹配")
        if write and not self._is_management() and origin is not None and origin!=self._origin(): raise BridgeError(403,"ORIGIN_DENIED","浏览器写请求需要严格同源 Origin")
        if bootstrap_redeem and self.headers.get("Sec-Fetch-Site") not in ("same-origin",None): raise BridgeError(403,"ORIGIN_DENIED","bootstrap 必须同源兑换")
    def _bearer(self):
        v=self.headers.get("Authorization",""); return v[7:] if v.startswith("Bearer ") else None
    def _is_management(self):
        token=self._bearer(); return bool(token and hmac.compare_digest(token,self.core.management_token))
    def _management(self):
        if not self._is_management(): raise BridgeError(401,"UNAUTHORIZED","需要管理凭证")
    def _browser(self,sid,bound=True):
        token=self._bearer()
        if not token: raise BridgeError(401,"UNAUTHORIZED","需要 browser bearer")
        if self.command in ("GET","HEAD") and self.headers.get("Origin") is None and self.headers.get("Sec-Fetch-Site")!="same-origin":
            raise BridgeError(403,"ORIGIN_DENIED","浏览器只读请求缺少 same-origin Fetch Metadata")
        return self.core.authorize_browser(token,sid,bound)
    def _client_disconnected(self):
        try:
            readable,_,_=select.select([self.connection],[],[],0)
            if not readable:return False
            return self.connection.recv(1,socket.MSG_PEEK|socket.MSG_DONTWAIT)==b""
        except (BlockingIOError,InterruptedError):
            return False
        except OSError:
            return True
    def _read_json(self,limit):
        if self.headers.get("Content-Type","").split(";",1)[0].strip().lower()!="application/json": raise BridgeError(400,"INVALID_ARGUMENT","Content-Type 必须为 application/json")
        raw_len=self.headers.get("Content-Length")
        if not raw_len or not raw_len.isdigit(): raise BridgeError(400,"INVALID_ARGUMENT","需要明确 Content-Length")
        n=int(raw_len)
        if n<=0: raise BridgeError(400,"INVALID_ARGUMENT","请求体为空")
        if n>limit: raise BridgeError(413,"PAYLOAD_TOO_LARGE","请求体超过路由预算")
        raw=self.rfile.read(n)
        if len(raw)!=n: raise BridgeError(400,"INVALID_ARGUMENT","请求体长度不完整")
        try:return json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError,json.JSONDecodeError):raise BridgeError(400,"INVALID_ARGUMENT","请求体不是合法 UTF-8 JSON")
    def _fields(self,body,required,optional=()):
        if not isinstance(body,dict) or not set(required)<=set(body) or not set(body)<=set(required)|set(optional):
            raise BridgeError(400,"INVALID_ARGUMENT","请求字段不符合协议")
    def do_HEAD(self): self._dispatch(False)
    def do_GET(self): self._dispatch(False)
    def do_POST(self): self._dispatch(True)
    def _dispatch(self,write):
        try:
            self._check_host_origin(write=write); u=urlsplit(self.path); path=u.path
            if self.command=="GET" and path=="/api/health":
                data={"ok":True,"protocol_version":2,"bridge_available":self.core.ready,"instance_id":self.core.instance_id}
                if self._is_management():data["workdir"]=str(self.core.workdir)
                return self._json(data)
            if path=="/bootstrap": return self._bootstrap(u)
            if path.startswith("/api/"): return self._api(path,u)
            if self.command not in ("GET","HEAD"): raise BridgeError(405,"INVALID_ARGUMENT","方法不允许")
            return self._static(path)
        except BridgeError as e:self._error(e)
        except (BrokenPipeError,ConnectionResetError,ConnectionAbortedError):pass
        except Exception:self._error(BridgeError(500,"STORAGE_UNAVAILABLE","服务内部错误",True))
    def _api(self,path,u):
        if self.command=="POST":
            limits={"/api/save":DOCUMENT_BODY_MAX,"/api/bridge/draft":DOCUMENT_BODY_MAX,"/api/bridge/asset":ASSET_BODY_MAX}
            body=self._read_json(limits.get(path,CONTROL_BODY_MAX))
            if path=="/api/bridge/open":
                self._management();self._fields(body,{"consumer_id"},{"deck_path","output_path","view","open_browser","brief_options"})
                if "open_browser" in body and type(body["open_browser"]) is not bool and body["open_browser"] != "auto":raise BridgeError(400,"INVALID_ARGUMENT","open_browser 必须为 boolean 或 \"auto\"")
                return self._json(self.core.open_editor(body["consumer_id"],body.get("deck_path"),body.get("output_path","index.html"),body.get("view","edit"),body.get("open_browser",True),body.get("brief_options")))
            if path=="/api/bridge/await":
                self._management();self._fields(body,{"session_id","consumer_id"},{"timeout_sec"})
                return self._json(self.core.await_intent(
                    body["session_id"],body["consumer_id"],body.get("timeout_sec",AWAIT_TIMEOUT_DEFAULT_SEC),
                    cancelled=self._client_disconnected))
            if path=="/api/bridge/update":
                self._management();self._fields(body,{"session_id","intent_id","attempt","consumer_id","action"},{"message","validation"})
                return self._json(self.core.push_update(body["session_id"],body["intent_id"],body["attempt"],body["consumer_id"],body["action"],body.get("message",""),body.get("validation")))
            if path=="/api/bridge/close":
                self._management();self._fields(body,{"session_id","consumer_id"},{"reason"})
                return self._json(self.core.close_consumer(body["session_id"],body["consumer_id"],body.get("reason","user-ended")))
            if path=="/api/bridge/status":
                self._fields(body,{"session_id"});sid=body["session_id"]
                if not self._is_management():self._browser(sid)
                return self._json(self.core.get_status(sid))
            if path=="/api/bridge/attach":
                # app-only：View 连接后立即上报，作为轨道判定的实证信号
                self._management();self._fields(body,{"session_id"},{"client"})
                return self._json(self.core.attach_view(body["session_id"],body.get("client")))
            if path=="/api/bridge/read":
                self._management();self._fields(body,{"session_id"},{"path"})
                return self._json(self.core.read_document(body["session_id"],body.get("path")))
            if path=="/api/bridge/asset-read":
                self._management();self._fields(body,{"session_id","path"})
                return self._json(self.core.read_artifact(body["session_id"],body["path"],kind="asset"))
            if path=="/api/bridge/export-read":
                self._management();self._fields(body,{"session_id","file"})
                return self._json(self.core.read_export_file(body["session_id"],body["file"]))
            if path=="/api/bridge/heartbeat":
                if body.get("role")=="consumer":
                    self._management(); expected={"protocol_version","role","session_id","consumer_id"}
                    if set(body)!=expected or body["protocol_version"]!=2:raise BridgeError(400,"INVALID_ARGUMENT","consumer heartbeat 非法")
                    return self._json(self.core.heartbeat_consumer(body["session_id"],body["consumer_id"]))
                sid=body.get("session_id"); token=self._bearer()
                if not token:raise BridgeError(401,"UNAUTHORIZED","缺少 browser token")
                return self._json(self.core.heartbeat_browser(token,sid,body))
            # MCP Apps 轨（轨 A）的 View 没有 browser 凭证：app-only 工具经宿主的 MCP 代理
            # 到达本 daemon，带的是 management 凭证。因此这些浏览器路由改为"management 或
            # browser 二选一"——与 /api/save、/api/rollback 既有做法一致。信任边界不变：
            # management 凭证本来就是 MCP server 自己的、可经 /api/bridge/* 管理全套状态。
            # session 归属由工具层（tools/bridge_dispatch.py）自校验，不依赖宿主鉴权。
            if path=="/api/intent":
                sid=body.get("session_id")
                if not self._is_management():self._browser(sid)
                return self._json(self.core.accept_intent(sid,body))
            if path=="/api/intent/retry":
                sid=body.get("session_id")
                if not self._is_management():self._browser(sid)
                return self._json(self.core.retry_intent(sid,body))
            if path=="/api/intent/cancel":
                self._fields(body,{"session_id","intent_id"});sid=body["session_id"]
                if not self._is_management():self._browser(sid)
                return self._json(self.core.cancel_intent(sid,body["intent_id"]))
            if path=="/api/intents/query":
                sid=body.get("session_id")
                if not self._is_management():self._browser(sid)
                return self._json(self.core.query_intents(sid,body))
            if path=="/api/save":
                self._fields(body,{"session_id","path","html","base_revision"},{"init"});sid=body["session_id"]
                if "init" in body and type(body["init"]) is not bool:raise BridgeError(400,"INVALID_ARGUMENT","init 必须为 boolean")
                if not self._is_management():self._browser(sid)
                return self._json(self.core.save(sid,body["path"],body["html"],body["base_revision"],body.get("init") is True))
            if path=="/api/rollback":
                self._fields(body,{"session_id","path","hash","base_revision"});sid=body["session_id"]
                if not self._is_management():self._browser(sid)
                return self._json(self.core.rollback(sid,body["path"],body["hash"],body["base_revision"]))
            if path=="/api/bridge/asset":
                self._fields(body,{"session_id","path","data_base64","base_revision"});sid=body["session_id"]
                if not self._is_management():self._browser(sid)
                return self._json(self.core.asset(sid,body["path"],body["data_base64"],body["base_revision"]))
            if path=="/api/convert":
                self._fields(body,{"session_id"},{"formats"});sid=body["session_id"]
                if not self._is_management():self._browser(sid)
                return self._json(self.core.start_local_convert(sid,body.get("formats",["pptx","vector","pdf"])))
            if path=="/api/imagegen":
                self._fields(body,{"session_id"});sid=body["session_id"]
                if not self._is_management():self._browser(sid)
                return self._json(self.core.start_local_imagegen(sid))
            if path=="/api/bridge/draft":
                self._fields(body,{"session_id","client_id","html","annotations","base_revision"});sid=body["session_id"]
                if not self._is_management():
                    b=self._browser(sid)
                    if body["client_id"]!=b["client_id"]:raise BridgeError(403,"UNAUTHORIZED","draft client 不匹配")
                return self._json(self.core.create_draft(sid,body["client_id"],body["html"],body["annotations"],body["base_revision"]))
            if path=="/api/bridge/bootstrap":
                self._management()
                if set(body)!={"mode","path"}:raise BridgeError(400,"INVALID_ARGUMENT","bootstrap 字段非法")
                return self._json(self.core.bootstrap_issue(body["mode"],body["path"]))
            if path=="/api/bridge/stop":
                self._management()
                if body not in ({}, {"reason":"cli-stop"}):raise BridgeError(400,"INVALID_ARGUMENT","stop 字段非法")
                result={"ok":True,"instance_id":self.core.instance_id}
                self.close_connection=True
                self._json(result,headers={"Connection":"close"})
                threading.Thread(target=self.server.shutdown,daemon=True).start()
                return
            raise BridgeError(404,"INVALID_ARGUMENT","未知 API")
        if self.command=="GET":
            q=parse_qs(u.query,keep_blank_values=True)
            if path=="/api/events":
                if not set(q)<={"session_id","after"} or len(q.get("session_id",[]))!=1 or any(len(v)!=1 for v in q.values()):raise BridgeError(400,"INVALID_ARGUMENT","events query 非法")
                return self._sse(q)
            if path=="/api/versions":
                if set(q)!={"session_id","path"} or any(len(v)!=1 for v in q.values()):raise BridgeError(400,"INVALID_ARGUMENT","versions query 非法")
                sid=q["session_id"][0];session=self.core._session(sid)
                if normalize_rel(q["path"][0])!=session["target_path"]:raise BridgeError(403,"PATH_DENIED","versions path 不属于任务")
                if not self._is_management():self._browser(sid)
                return self._json(self.core.versions(sid))
            if path=="/api/convert-status":
                if set(q)!={"session_id"} or len(q["session_id"])!=1:raise BridgeError(400,"INVALID_ARGUMENT","convert-status query 非法")
                sid=q["session_id"][0]
                if not self._is_management():self._browser(sid)
                return self._json(self.core.local_convert_status(sid))
            if path=="/api/imagegen-status":
                if set(q)!={"session_id"} or len(q["session_id"])!=1:raise BridgeError(400,"INVALID_ARGUMENT","imagegen-status query 非法")
                sid=q["session_id"][0]
                if not self._is_management():self._browser(sid)
                return self._json(self.core.local_imagegen_status(sid))
            if path=="/api/bridge/drafts":
                if set(q)!={"session_id"} or len(q["session_id"])!=1:raise BridgeError(400,"INVALID_ARGUMENT","drafts query 非法")
                sid=q["session_id"][0];self._browser(sid); rows=self.core.db.execute("SELECT id,client_id,base_revision,created_at FROM drafts WHERE session_id=? ORDER BY created_at DESC LIMIT 50",(sid,)).fetchall();return self._json({"ok":True,"items":[dict(x) for x in rows]})
            if path=="/api/bridge/draft":
                if set(q)!={"id"} or len(q["id"])!=1:raise BridgeError(400,"INVALID_ARGUMENT","draft query 非法")
                did=q["id"][0]; row=self.core.db.execute("SELECT * FROM drafts WHERE id=?",(did,)).fetchone()
                if not row:raise BridgeError(404,"INTENT_NOT_FOUND","草稿不存在")
                self._browser(row["session_id"]);return self._json({"ok":True,"id":did,"session_id":row["session_id"],"client_id":row["client_id"],"html":row["html"],"annotations":json.loads(row["annotations_json"]),"base_revision":row["base_revision"],"created_at":row["created_at"]})
            raise BridgeError(404,"INVALID_ARGUMENT","未知 API")
        raise BridgeError(405,"INVALID_ARGUMENT","方法不允许")
    def _bootstrap(self,u):
        if self.command=="HEAD":raise BridgeError(405,"INVALID_ARGUMENT","HEAD 不可兑换 bootstrap")
        if self.command!="GET":raise BridgeError(405,"INVALID_ARGUMENT","方法不允许")
        q=parse_qs(u.query,keep_blank_values=True)
        if not q:
            self.send_response(200);self.send_header("Content-Type","text/html; charset=utf-8");self.send_header("Content-Length",str(len(LANDING)));self.send_header("Cache-Control","no-store");self.send_header("Content-Security-Policy","default-src 'none'; script-src 'unsafe-inline'; frame-ancestors 'none'");self.send_header("Referrer-Policy","no-referrer");self.end_headers();self.wfile.write(LANDING);return
        if set(q)!={"ticket"} or len(q["ticket"])!=1 or not re.fullmatch(r"[0-9a-f]{64}",q["ticket"][0]):raise BridgeError(400,"INVALID_ARGUMENT","bootstrap ticket 非法")
        self._check_host_origin(bootstrap_redeem=True); ticket=q["ticket"][0]; cookies={}
        for pair in self.headers.get("Cookie","").split(";"):
            if "=" in pair:k,v=pair.strip().split("=",1);cookies[k]=unquote(v)
        raw=cookies.get("pptx_bootstrap_"+ticket)
        if not raw:raise BridgeError(401,"UNAUTHORIZED","缺少 bootstrap cookie")
        loc=self.core.bootstrap_redeem(ticket,raw);self.send_response(302);self.send_header("Location",loc);self.send_header("Set-Cookie",f"pptx_bootstrap_{ticket}=; Path=/bootstrap; Max-Age=0; SameSite=Strict");self.send_header("Cache-Control","no-store");self.send_header("Referrer-Policy","no-referrer");self.send_header("Content-Length","0");self.end_headers()
    def _static(self,path):
        if self.headers.get("Sec-Fetch-Site") not in {"same-origin","none"}:raise BridgeError(403,"ORIGIN_DENIED","静态资源请求缺少可信 Fetch Metadata")
        try: decoded=unquote(path,errors="strict")
        except Exception:raise BridgeError(403,"PATH_DENIED","非法 URL 编码")
        if "%" in decoded or "\\" in decoded or "\x00" in decoded:raise BridgeError(403,"PATH_DENIED","非法静态路径")
        if decoded in ("/","/editor.html"):
            file=PROJECT_ROOT/"editor.html"
        else:
            stripped=decoded.lstrip("/")
            rel=None; artifact_class=None
            try:
                rel=normalize_rel(stripped)
            except BridgeError:
                rel=None
            if rel is not None:
                for s in self.core.db.execute("SELECT * FROM sessions"):
                    root=self.core._bundle_root(s)
                    try: br=(self.core.workdir/rel).relative_to(root).as_posix()
                    except ValueError:continue
                    row=self.core.db.execute("SELECT class FROM bundle_files WHERE session_id=? AND path=? AND present=1",(s["id"],br)).fetchone()
                    if row:artifact_class=row["class"];break
            if artifact_class is None:
                abs_path=self.core.workdir/stripped
                for s in self.core.db.execute("SELECT * FROM sessions"):
                    root=self.core._bundle_root(s)
                    try: br=abs_path.relative_to(root).as_posix()
                    except ValueError:continue
                    if ".." not in br:
                        row=self.core.db.execute("SELECT class FROM bundle_files WHERE session_id=? AND path=? AND present=1",(s["id"],br)).fetchone()
                        if row:artifact_class=row["class"];rel=stripped;break
            if artifact_class is None:raise BridgeError(403,"PATH_DENIED","静态资源未登记")
            if artifact_class=="source-legacy":raise BridgeError(403,"PATH_DENIED","legacy 源素材禁止静态读取")
            file=self.core.workdir/rel
        if file.is_relative_to(self.core.workdir):data=self.core.secure.read(self.core._work_rel(file))
        else:_safe_regular(file,PROJECT_ROOT);data=file.read_bytes()
        self.send_response(200);self.send_header("Content-Type",mimetypes.guess_type(file.name)[0] or "application/octet-stream");self.send_header("Content-Length",str(len(data)));self.send_header("Cache-Control","no-store");self.send_header("X-Content-Type-Options","nosniff");self.end_headers();
        if self.command!="HEAD":self.wfile.write(data)
    def _sse(self,q):
        sid=(q.get("session_id")or[None])[0]; after_raw=(q.get("after")or["0"])[0]
        if not after_raw.isdigit():raise BridgeError(400,"INVALID_ARGUMENT","after 非法")
        self._browser(sid); after=int(after_raw); self.close_connection=True; self.send_response(200);self.send_header("Content-Type","text/event-stream");self.send_header("Cache-Control","no-store");self.send_header("Connection","close");self.end_headers();deadline=time.monotonic()+30
        bounds=self.core.db.execute("SELECT MIN(id),MAX(id) FROM events WHERE session_id=?",(sid,)).fetchone()
        if after and bounds[0] is not None and after < bounds[0]:
            status=self.core.get_status(sid); data=canonical_json({"session_id":sid,"latest_event_id":bounds[1],"revision":status["revision"]}).decode()
            self.wfile.write(f"id: {bounds[1]}\nevent: resync-required\ndata: {data}\n\n".encode());self.wfile.flush();after=bounds[1]
        while not self.core._stop.is_set() and time.monotonic()<deadline:
            rows=self.core.events_after(sid,after)
            for row in rows:
                payload=f"id: {row['id']}\nevent: {row['type']}\ndata: {row['data_json']}\n\n".encode();self.wfile.write(payload);self.wfile.flush();after=row["id"]
            if not rows:self.wfile.write(b": ping\n\n");self.wfile.flush()
            cond=self.core._condition(sid)
            with cond:cond.wait(SSE_PING_SEC)


def write_serve(core,server):
    core.origin=f"http://127.0.0.1:{server.server_address[1]}"
    data={"protocol_version":2,"workdir":str(core.workdir),"instance_id":core.instance_id,"pid":os.getpid(),"origin":core.origin,"port":server.server_address[1],"management_token":core.management_token}
    core._atomic_json(core.internal/"serve.json",data);os.chmod(core.internal/"serve.json",0o600)


def serve(workdir,port=8926,allow_convert=False):
    core=BridgeCore(workdir,allow_convert=allow_convert,require_lock=True);server=BridgeHTTPServer(("127.0.0.1",port),core);write_serve(core,server)
    try:server.serve_forever(poll_interval=.2)
    finally:
        with contextlib.suppress(Exception):
            core._event("", "server-stop", {"instance_id":core.instance_id})
        server.server_close();core.close()


def read_discovery(workdir):
    p=Path(workdir).resolve()/INTERNAL/"serve.json"
    st=p.stat()
    if stat.S_IMODE(st.st_mode)&0o077:raise BridgeError(503,"STORAGE_UNAVAILABLE","serve.json 权限不安全")
    return json.loads(p.read_text("utf-8"))


def admin_request(discovery,path,body=None,timeout=10):
    headers={"Authorization":"Bearer "+discovery["management_token"]}
    data=None
    if body is not None:data=canonical_json(body);headers["Content-Type"]="application/json"
    req=Request(discovery["origin"]+path,data=data,headers=headers,method="POST" if body is not None else "GET")
    try:return json.loads(urlopen(req,timeout=timeout).read())
    except HTTPError as e:
        try:data=json.loads(e.read())
        except Exception:raise BridgeError(e.code,"STORAGE_UNAVAILABLE","daemon HTTP 失败")
        err=data.get("error",{});raise BridgeError(e.code,err.get("code","STORAGE_UNAVAILABLE"),err.get("message","daemon HTTP 失败"),err.get("retryable",False),err.get("details"))


def verify_discovery(workdir,d):
    if d.get("protocol_version")!=2 or Path(d.get("workdir","")).resolve()!=Path(workdir).resolve():return False
    try:h=admin_request(d,"/api/health")
    except Exception:return False
    return h.get("instance_id")==d.get("instance_id") and h.get("workdir")==str(Path(workdir).resolve())


def ensure_daemon(workdir,allow_convert=False,port=0,allow_imagegen=False):
    workdir=str(Path(workdir).resolve())
    with contextlib.suppress(Exception):
        d=read_discovery(workdir)
        if verify_discovery(workdir,d):return d
    cmd=[sys.executable,str(PROJECT_ROOT/"tools/edit.py"),workdir,"--daemon","--port",str(port)]
    if allow_convert:cmd.append("--convert")
    if allow_imagegen:cmd.append("--imagegen")
    logdir=Path(workdir)/INTERNAL;logdir.mkdir(mode=0o700,exist_ok=True);log=open(logdir/"daemon.log","ab",buffering=0)
    subprocess.Popen(cmd,stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True,close_fds=True)
    deadline=time.monotonic()+10
    while time.monotonic()<deadline:
        time.sleep(.1)
        with contextlib.suppress(Exception):
            d=read_discovery(workdir)
            if verify_discovery(workdir,d):return d
    raise BridgeError(503,"STORAGE_UNAVAILABLE","daemon 启动超时")


def revision_cli(path):
    target=Path(path).resolve(strict=True)
    if target.suffix.lower()!=".html":raise BridgeError(400,"INVALID_ARGUMENT","work_path 必须为 HTML")
    dummy=object.__new__(BridgeCore);dummy.workdir=target.parent;dummy.secure=SecureRoot(target.parent)
    try:manifest=BridgeCore.scan_bundle(dummy,target)
    finally:dummy.secure.close()
    rev,_=BridgeCore.revisions(manifest)
    if not rev:raise BridgeError(422,"INVALID_ARTIFACT","缺少源 HTML")
    return rev


def main():
    ap=argparse.ArgumentParser();sub=ap.add_subparsers(dest="cmd",required=True);p=sub.add_parser("revision");p.add_argument("work_path")
    args=ap.parse_args()
    try:
        if args.cmd=="revision":print(revision_cli(args.work_path))
    except BridgeError as e:print(f"{e.code}: {e.message}",file=sys.stderr);raise SystemExit(1)


if __name__=="__main__":main()
