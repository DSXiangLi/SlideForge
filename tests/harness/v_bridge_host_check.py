#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bridge v2 P4 real MCP-host acceptance for Kimi Code and Codex.

Real model calls are possible only with an explicit ``--host`` argument.
``--self-check`` is offline and exercises only command/config construction,
stream parsing, redaction, and conservative report classification.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import importlib.metadata
import json
import os
import platform
import queue
import re
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[2]
EDIT = (ROOT / "tools" / "edit.py").resolve()
BRIDGE_MCP = (ROOT / "tools" / "bridge_mcp.py").resolve()
FIXTURE = (ROOT / "tests" / "decks" / "bake-mix").resolve()
RESULT_DIR = ROOT / "tests" / "harness" / "results" / "bridge-p4"
EXPECTED_VERSIONS = {"kimi": "2.1.1", "codex": "0.150.1"}
SERVER_NAME = "pptx_html_bridge_host"
TOOL_NAMES = ("open_editor", "await_intent", "push_update", "get_status", "close_session")
FORMAL_DURATION_SEC = 540
DEFAULT_OBSERVATION_SEC = 600
SECRET_KEY = re.compile(
    r"(?:authorization|bearer|management[_-]?token|browser[_-]?token|bootstrap[_-]?token|"
    r"access[_-]?token|api[_-]?key|secret|password)$", re.I)
TOKEN_TEXT = [
    (re.compile(r"(?i)(authorization\s*[:=]\s*bearer\s+)[^\s\"']+"), r"\1<redacted>"),
    (re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]+"), r"\1<redacted>"),
    (re.compile(r"(?i)([#&?](?:brt|boot)=)[^&#\s\"']+"), r"\1<redacted>"),
    (re.compile(r"(?i)(\"(?:management_token|browser_token|bootstrap_token|access_token|api_key)\"\s*:\s*\")[^\"]+"), r"\1<redacted>"),
]
AUTH_FAILURE = re.compile(r"not logged in|login required|unauthorized|authentication|401|请.*登录", re.I)


class HarnessError(RuntimeError):
    pass


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def redact_text(value: str) -> str:
    result = value
    for pattern, replacement in TOKEN_TEXT:
        result = pattern.sub(replacement, result)
    return result


def redact(value: Any, key: str = "") -> Any:
    if SECRET_KEY.search(key):
        return "<redacted>"
    if isinstance(value, dict):
        return {str(k): redact(v, str(k)) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, str):
        return redact_text(value)
    return value


def public_command(command: list[str]) -> list[str]:
    return [redact_text(str(part)) for part in command]


def command_output(command: list[str], *, cwd: Path | None = None, timeout: int = 20,
                   env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=str(cwd) if cwd else None, env=env,
                          stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=timeout)


def binary_version(host: str, executable: str) -> str | None:
    try:
        result = command_output([executable, "--version"])
    except (OSError, subprocess.SubprocessError):
        return None
    text = (result.stdout or result.stderr).strip()
    if result.returncode != 0:
        return None
    match = re.search(r"(\d+\.\d+\.\d+)", text)
    return match.group(1) if match else None


def fixture_digest(root: Path) -> dict[str, Any]:
    aggregate = hashlib.sha256()
    files = []
    ignored_roots = {"export", "prompts", ".pptx-html", ".kimi-code", ".git"}
    if not root.exists():
        return {"exists": False, "file_count": 0, "aggregate_sha256": None}
    candidates = []
    for item in root.rglob("*"):
        rel = item.relative_to(root)
        if rel.parts and rel.parts[0] in ignored_roots:
            continue
        if item.is_file():
            candidates.append(item)
    for path in sorted(candidates, key=lambda item: item.relative_to(root).as_posix()):
        rel = path.relative_to(root).as_posix()
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        files.append((rel, path.stat().st_size, digest))
        aggregate.update(rel.encode() + b"\0" + str(path.stat().st_size).encode() + b"\0" + digest.encode() + b"\0")
    return {"exists": True, "file_count": len(files), "aggregate_sha256": aggregate.hexdigest()}


def copy_fixture(source: Path, destination: Path) -> None:
    if not (source / "index.html").is_file():
        raise HarnessError("existing-deck fixture is unavailable: %s" % source)
    shutil.copytree(source, destination, ignore=shutil.ignore_patterns("export", "prompts"))


def kimi_mcp_payload(workdir: Path, python: Path) -> dict[str, Any]:
    return {
        "mcpServers": {
            SERVER_NAME: {
                "command": str(python),
                "args": [str(EDIT), str(workdir.resolve()), "--mcp"],
                "cwd": str(ROOT),
                "startupTimeoutMs": 30000,
                "toolTimeoutMs": 86500000,
            }
        }
    }


def path_state(path: Path) -> dict[str, Any]:
    if not path.exists() and not path.is_symlink():
        return {"exists": False}
    if path.is_symlink():
        target = os.readlink(path)
        return {"exists": True, "kind": "symlink", "mode": oct(path.lstat().st_mode & 0o777),
                "target_sha256": hashlib.sha256(target.encode()).hexdigest()}
    if path.is_file():
        data = path.read_bytes()
        return {"exists": True, "kind": "file", "mode": oct(path.stat().st_mode & 0o777),
                "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    aggregate = hashlib.sha256()
    count = 0
    for item in sorted(path.rglob("*"), key=lambda value: value.relative_to(path).as_posix()):
        rel = item.relative_to(path).as_posix()
        mode = oct(item.lstat().st_mode & 0o777)
        if item.is_symlink():
            kind = "symlink"
            digest = hashlib.sha256(os.readlink(item).encode()).hexdigest()
        elif item.is_file():
            kind = "file"
            digest = hashlib.sha256(item.read_bytes()).hexdigest()
        else:
            kind = "directory"
            digest = "-"
        aggregate.update((rel + "\0" + kind + "\0" + mode + "\0" + digest + "\0").encode())
        count += 1
    return {"exists": True, "kind": "directory", "mode": oct(path.stat().st_mode & 0o777),
            "entries": count, "aggregate_sha256": aggregate.hexdigest()}


def user_kimi_config_state() -> dict[str, Any]:
    home = Path(os.environ.get("KIMI_CODE_HOME", str(Path.home() / ".kimi-code"))).expanduser().resolve()
    names = {"mcp.json", "config.toml", "workspace-trust"}
    if home.is_dir():
        names.update(path.name for path in home.glob("workspace-trust*"))
    return {name: path_state(home / name) for name in sorted(names)}


def atomic_write(path: Path, data: bytes, mode: int) -> None:
    fd, temporary = tempfile.mkstemp(prefix=".%s." % path.name, dir=str(path.parent))
    temp_path = Path(temporary)
    try:
        os.fchmod(fd, mode)
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
        dir_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    finally:
        with contextlib.suppress(FileNotFoundError):
            temp_path.unlink()


@contextlib.contextmanager
def temporary_kimi_project_config(project_root: Path, workdir: Path, python: Path):
    project_root = project_root.resolve()
    config_dir = project_root / ".kimi-code"
    config_path = config_dir / "mcp.json"
    before = path_state(config_dir)
    directory_existed = config_dir.exists()
    if config_dir.is_symlink() or (directory_existed and not config_dir.is_dir()):
        raise HarnessError("trusted project .kimi-code is not a real directory")
    if config_path.is_symlink() or (config_path.exists() and not config_path.is_file()):
        raise HarnessError("trusted project MCP config is not a regular file")
    original = config_path.read_bytes() if config_path.is_file() else None
    original_mode = config_path.stat().st_mode & 0o777 if config_path.is_file() else None
    config_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    payload = json.dumps(kimi_mcp_payload(workdir, python), ensure_ascii=False, indent=2).encode() + b"\n"
    atomic_write(config_path, payload, 0o600)
    try:
        yield config_path
    finally:
        if original is None:
            with contextlib.suppress(FileNotFoundError):
                config_path.unlink()
        else:
            atomic_write(config_path, original, original_mode or 0o600)
        if not directory_existed:
            with contextlib.suppress(OSError):
                config_dir.rmdir()
        after = path_state(config_dir)
        if after != before:
            raise HarnessError("trusted project .kimi-code state was not restored exactly")


def host_cwd(host: str, workdir: Path) -> Path:
    return ROOT if host == "kimi" else workdir


def toml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def codex_overrides(workdir: Path, python: Path) -> list[str]:
    prefix = "mcp_servers.%s" % SERVER_NAME
    args = [str(EDIT), str(workdir.resolve()), "--mcp"]
    return [
        "-c", "%s.command=%s" % (prefix, toml_string(str(python))),
        "-c", "%s.args=%s" % (prefix, json.dumps(args, ensure_ascii=False)),
        "-c", "%s.cwd=%s" % (prefix, toml_string(str(ROOT))),
        "-c", "%s.startup_timeout_sec=30" % prefix,
        "-c", "%s.tool_timeout_sec=150" % prefix,
    ]


def build_host_command(host: str, executable: str, workdir: Path, prompt: str,
                       python: Path) -> list[str]:
    if host == "kimi":
        return [executable, "-p", prompt, "--output-format", "stream-json"]
    return [
        executable, "exec", "--ignore-user-config", "--ignore-rules", "--ephemeral",
        "--json", "--color", "never", "-C", str(workdir.resolve()),
        "--sandbox", "workspace-write", "--ask-for-approval", "never",
        *codex_overrides(workdir, python), prompt,
    ]


def normalize_tool_name(value: str) -> str | None:
    for name in TOOL_NAMES:
        if value == name or value.endswith("__" + name) or value.endswith("/" + name):
            return name
    return None


def walk(value: Any):
    yield value
    if isinstance(value, dict):
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


@dataclass
class StreamEvidence:
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    usage_samples: list[dict[str, Any]] = field(default_factory=list)
    cost_samples: list[dict[str, Any]] = field(default_factory=list)
    parse_errors: int = 0

    def ingest(self, line: str, channel: str) -> None:
        if channel != "stdout" or not line.strip():
            return
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            self.parse_errors += 1
            return
        seen = set()
        for node in walk(event):
            if not isinstance(node, dict):
                continue
            for key in ("name", "tool_name", "tool", "method"):
                raw_name = node.get(key)
                name = normalize_tool_name(raw_name) if isinstance(raw_name, str) else None
                if not name:
                    continue
                call_id = node.get("id") or node.get("call_id") or node.get("tool_call_id")
                marker = (name, str(call_id), json.dumps(node, sort_keys=True, default=str)[:500])
                if marker in seen:
                    continue
                seen.add(marker)
                arguments = node.get("arguments") or node.get("args") or node.get("input") or {}
                if isinstance(arguments, str):
                    with contextlib.suppress(json.JSONDecodeError):
                        arguments = json.loads(arguments)
                self.tool_calls.append({
                    "name": name,
                    "call_id": str(call_id) if call_id is not None else None,
                    "arguments": arguments if isinstance(arguments, dict) else {},
                })
            usage = node.get("usage")
            if isinstance(usage, dict) and any(isinstance(v, (int, float)) for v in usage.values()):
                self.usage_samples.append(redact(usage))
            for key in ("cost", "cost_usd", "total_cost", "amount"):
                if key in node and isinstance(node[key], (int, float, str)):
                    self.cost_samples.append({key: node[key]})

    def call_count(self, name: str) -> int:
        return sum(call["name"] == name for call in self.tool_calls)

    def saw_await(self, timeout_sec: int) -> bool:
        return any(call["name"] == "await_intent" and call["arguments"].get("timeout_sec") == timeout_sec
                   for call in self.tool_calls)

    def summary(self) -> dict[str, Any]:
        counts = {name: self.call_count(name) for name in TOOL_NAMES}
        numeric: dict[str, float] = {}
        if self.usage_samples:
            latest = self.usage_samples[-1]
            for key, value in latest.items():
                if isinstance(value, (int, float)):
                    numeric[key] = value
        return {
            "tool_calls": counts,
            "tool_call_total": sum(counts.values()),
            "usage": {"visible": bool(self.usage_samples), "latest_numeric": numeric,
                      "samples": self.usage_samples[-10:]},
            "cost": {"visible": bool(self.cost_samples), "samples": self.cost_samples[-10:],
                     "value": self.cost_samples[-1] if self.cost_samples else "unknown"},
            "json_parse_errors": self.parse_errors,
        }


@dataclass(frozen=True)
class ProcessIdentity:
    pid: int
    ppid: int
    pgid: int
    session_id: int
    start_ticks: int
    state: str
    argv: tuple[str, ...]

    def public(self) -> dict[str, Any]:
        return {"pid": self.pid, "ppid": self.ppid, "pgid": self.pgid,
                "session_id": self.session_id, "start_ticks": self.start_ticks,
                "argv": public_command(list(self.argv))}


def process_identity(pid: int) -> ProcessIdentity | None:
    try:
        raw = Path("/proc/%d/stat" % pid).read_text(encoding="utf-8")
        close = raw.rfind(")")
        fields = raw[close + 2:].split()
        argv_raw = Path("/proc/%d/cmdline" % pid).read_bytes()
        argv = tuple(item.decode("utf-8", "replace") for item in argv_raw.split(b"\0") if item)
        return ProcessIdentity(pid=pid, state=fields[0], ppid=int(fields[1]),
                               pgid=int(fields[2]), session_id=int(fields[3]),
                               start_ticks=int(fields[19]), argv=argv)
    except (FileNotFoundError, PermissionError, ProcessLookupError, OSError, ValueError, IndexError):
        return None


def same_process(identity: ProcessIdentity) -> bool:
    current = process_identity(identity.pid)
    return bool(current and current.start_ticks == identity.start_ticks and current.state != "Z")


def process_group_members(pgid: int) -> list[ProcessIdentity]:
    members = []
    proc = Path("/proc")
    if not proc.is_dir():
        return members
    for item in proc.iterdir():
        if not item.name.isdigit():
            continue
        identity = process_identity(int(item.name))
        if identity and identity.pgid == pgid and identity.state != "Z":
            members.append(identity)
    return members


def wait_processes_gone(identities: list[ProcessIdentity], timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not any(same_process(identity) for identity in identities):
            return True
        time.sleep(.05)
    return not any(same_process(identity) for identity in identities)


def cleanup_process_groups(identities: list[ProcessIdentity], *, term_timeout: float = 3.0,
                           kill_timeout: float = 3.0) -> dict[str, Any]:
    unique = {(item.pid, item.start_ticks): item for item in identities if same_process(item)}
    targets = list(unique.values())
    groups = sorted({item.pgid for item in targets if item.pgid > 0})
    result = {"targets": [item.public() for item in targets], "groups": groups,
              "term_sent": [], "kill_sent": [], "remaining": []}
    for pgid in groups:
        if any(same_process(item) and item.pgid == pgid for item in targets):
            with contextlib.suppress(ProcessLookupError, PermissionError):
                os.killpg(pgid, signal.SIGTERM)
                result["term_sent"].append(pgid)
    wait_processes_gone(targets, term_timeout)
    remaining = [item for item in targets if same_process(item)]
    for pgid in sorted({item.pgid for item in remaining if item.pgid > 0}):
        if any(same_process(item) and item.pgid == pgid for item in remaining):
            with contextlib.suppress(ProcessLookupError, PermissionError):
                os.killpg(pgid, signal.SIGKILL)
                result["kill_sent"].append(pgid)
    wait_processes_gone(remaining, kill_timeout)
    result["remaining"] = [item.public() for item in targets if same_process(item)]
    result["stopped"] = not result["remaining"]
    return result


def cleanup_process_group(pgid: int) -> dict[str, Any]:
    members = process_group_members(pgid)
    result = cleanup_process_groups(members)
    result["pgid"] = pgid
    result["members_before"] = [item.public() for item in members]
    result["members_after"] = [item.public() for item in process_group_members(pgid)]
    result["stopped"] = result["stopped"] and not result["members_after"]
    return result


def matching_bridge_processes(workdir: Path) -> list[ProcessIdentity]:
    expected_edit = str(EDIT)
    expected_workdir = str(workdir.resolve())
    matches = []
    proc = Path("/proc")
    if not proc.is_dir():
        return matches
    for item in proc.iterdir():
        if not item.name.isdigit():
            continue
        identity = process_identity(int(item.name))
        if not identity or identity.state == "Z":
            continue
        argv = set(identity.argv)
        if expected_edit in argv and expected_workdir in argv and argv.intersection({"--mcp", "--daemon"}):
            matches.append(identity)
    return matches


def port_is_open(origin: str) -> bool:
    try:
        parsed = urlsplit(origin)
        with socket.create_connection((parsed.hostname or "127.0.0.1", parsed.port or 80), timeout=.3):
            return True
    except (OSError, ValueError):
        return False


def wait_port_closed(origin: str, timeout: float = 3.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not port_is_open(origin):
            return True
        time.sleep(.05)
    return not port_is_open(origin)


@dataclass
class HostInvocation:
    label: str
    command: list[str]
    returncode: int | None
    duration_sec: float
    stdout_lines: int
    stderr_lines: int
    interrupted: bool
    timed_out: bool
    evidence: StreamEvidence
    combined_text: str
    process_cleanup: dict[str, Any]

    def report(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "command": public_command(self.command),
            "returncode": self.returncode,
            "duration_sec": round(self.duration_sec, 3),
            "stdout_lines": self.stdout_lines,
            "stderr_lines": self.stderr_lines,
            "interrupted": self.interrupted,
            "timed_out": self.timed_out,
            "evidence": self.evidence.summary(),
            "process_cleanup": self.process_cleanup,
        }


class SanitizedLog:
    def __init__(self, path: Path, run_id: str):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.handle = path.open("w", encoding="utf-8")
        self.lock = threading.Lock()
        self.run_id = run_id

    def write(self, label: str, channel: str, line: str) -> None:
        stripped = line.rstrip("\n")
        try:
            parsed = json.loads(stripped)
            safe = json.dumps(redact(parsed), ensure_ascii=False, separators=(",", ":"))
        except json.JSONDecodeError:
            safe = redact_text(stripped)
        record = {"at": utc_now(), "run_id": self.run_id,
                  "case": label, "channel": channel, "line": safe}
        with self.lock:
            self.handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            self.handle.flush()

    def close(self) -> None:
        self.handle.close()


def run_streaming(command: list[str], *, cwd: Path, env: dict[str, str], label: str,
                  log: SanitizedLog, timeout_sec: int,
                  cancel_when: Callable[[StreamEvidence], bool] | None = None,
                  cancel_grace_sec: float = 5.0) -> HostInvocation:
    evidence = StreamEvidence()
    lines: queue.Queue[tuple[str, str | None]] = queue.Queue()
    started = time.monotonic()
    proc = subprocess.Popen(command, cwd=str(cwd), env=env, stdin=subprocess.DEVNULL,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                            bufsize=1, start_new_session=True)

    def reader(channel: str, stream) -> None:
        try:
            for line in iter(stream.readline, ""):
                lines.put((channel, line))
        finally:
            lines.put((channel, None))

    threads = [threading.Thread(target=reader, args=("stdout", proc.stdout), daemon=True),
               threading.Thread(target=reader, args=("stderr", proc.stderr), daemon=True)]
    for thread in threads:
        thread.start()
    closed = set()
    stdout_count = stderr_count = 0
    interrupted = timed_out = False
    text_tail: list[str] = []
    deadline = started + timeout_sec
    cancel_deadline = None
    while len(closed) < 2 or proc.poll() is None:
        now = time.monotonic()
        if now >= deadline and proc.poll() is None and not timed_out:
            timed_out = True
            os.killpg(proc.pid, signal.SIGTERM)
            cancel_deadline = now + cancel_grace_sec
        if cancel_when and not interrupted and proc.poll() is None and cancel_when(evidence):
            interrupted = True
            os.killpg(proc.pid, signal.SIGINT)
            cancel_deadline = now + cancel_grace_sec
        if cancel_deadline and now >= cancel_deadline and proc.poll() is None:
            os.killpg(proc.pid, signal.SIGKILL)
        try:
            channel, line = lines.get(timeout=.1)
        except queue.Empty:
            continue
        if line is None:
            closed.add(channel)
            continue
        if channel == "stdout":
            stdout_count += 1
        else:
            stderr_count += 1
        evidence.ingest(line, channel)
        log.write(label, channel, line)
        text_tail.append(line)
        if len(text_tail) > 200:
            text_tail.pop(0)
    for thread in threads:
        thread.join(timeout=1)
    process_cleanup = cleanup_process_group(proc.pid)
    return HostInvocation(
        label=label, command=command, returncode=proc.returncode,
        duration_sec=time.monotonic() - started, stdout_lines=stdout_count,
        stderr_lines=stderr_count, interrupted=interrupted, timed_out=timed_out,
        evidence=evidence, combined_text=redact_text("".join(text_tail)),
        process_cleanup=process_cleanup,
    )


def json_request(origin: str, path: str, body: dict[str, Any], bearer: str,
                 origin_header: str | None = None, timeout: int = 20) -> tuple[int, dict[str, Any]]:
    data = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode()
    headers = {"Authorization": "Bearer " + bearer, "Content-Type": "application/json"}
    if origin_header:
        headers["Origin"] = origin_header
    request = Request(origin + path, data=data, headers=headers, method="POST")
    try:
        response = urlopen(request, timeout=timeout)
        return response.status, json.loads(response.read())
    except HTTPError as exc:
        return exc.code, json.loads(exc.read())


def wait_discovery(workdir: Path, timeout: int = 20) -> dict[str, Any]:
    path = workdir / ".pptx-html" / "serve.json"
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if path.is_file():
            with contextlib.suppress(json.JSONDecodeError, OSError):
                return json.loads(path.read_text(encoding="utf-8"))
        time.sleep(.1)
    raise HarnessError("Bridge discovery was not created")


def controller_open(workdir: Path, deck: Path | None) -> tuple[dict[str, Any], dict[str, Any]]:
    discovery = wait_discovery(workdir)
    body = {
        "consumer_id": "host-harness-controller-" + str(uuid.uuid4()),
        "deck_path": str(deck.resolve()) if deck else None,
        "output_path": "index.html",
        "view": "brief" if deck is None else "edit",
        "open_browser": False,
    }
    code, opened = json_request(discovery["origin"], "/api/bridge/open", body,
                                discovery["management_token"])
    if code != 200 or not opened.get("ok"):
        raise HarnessError("controller open failed: %s" % redact(opened))
    return discovery, opened


def bind_browser_and_submit(workdir: Path, deck: Path | None, intent_type: str) -> dict[str, Any]:
    discovery, opened = controller_open(workdir, deck)
    fragment = parse_qs(urlsplit(opened["url"]).fragment)
    token = fragment["brt"][0]
    client_id = str(uuid.uuid4())
    heartbeat = {
        "protocol_version": 2, "role": "browser", "session_id": opened["session_id"],
        "client_id": client_id, "dirty": False, "active_edit": False,
        "draft_pending": False, "revision": opened.get("revision"), "last_event_id": 0,
    }
    code, response = json_request(discovery["origin"], "/api/bridge/heartbeat", heartbeat,
                                  token, discovery["origin"])
    if code != 200 or not response.get("ok"):
        raise HarnessError("browser bind failed: %s" % redact(response))
    payload = ({"text": "host acceptance temporary brief", "json": {"kind": "design-brief", "topic": "bridge-host"}}
               if intent_type == "brief.submitted" else
               {"version": 1, "kind": "design-intent", "deck": "index.html",
                "answers": {"note": "host acceptance; do not modify the fixture"}})
    intent = {
        "protocol_version": 2, "intent_id": str(uuid.uuid4()),
        "session_id": opened["session_id"], "type": intent_type,
        "base_revision": opened.get("revision"), "payload": payload,
        "client_ts": utc_now(),
    }
    code, accepted = json_request(discovery["origin"], "/api/intent", intent, token,
                                  discovery["origin"])
    if code != 200 or not accepted.get("accepted"):
        raise HarnessError("intent submit failed: %s" % redact(accepted))
    return {"session_id": opened["session_id"], "intent_id": intent["intent_id"],
            "revision": opened.get("revision")}


class ScenarioRuntime:
    def __init__(self, workdir: Path):
        self.workdir = workdir.resolve()
        self.discoveries: dict[str, dict[str, Any]] = {}

    def capture(self) -> None:
        path = self.workdir / ".pptx-html" / "serve.json"
        if not path.is_file():
            return
        try:
            discovery = json.loads(path.read_text(encoding="utf-8"))
            pid = int(discovery["pid"])
            identity = process_identity(pid)
            key = str(discovery.get("instance_id") or "%s:%s" % (pid, discovery.get("origin")))
            self.discoveries[key] = {"discovery": discovery, "identity": identity}
        except (OSError, ValueError, KeyError, json.JSONDecodeError):
            return

    def cleanup(self) -> dict[str, Any]:
        self.capture()
        normal_stop = []
        known_identities = []
        origins = []
        for item in self.discoveries.values():
            discovery = item["discovery"]
            identity = item.get("identity")
            if identity:
                known_identities.append(identity)
            origin = discovery.get("origin")
            if isinstance(origin, str):
                origins.append(origin)
            attempt = {"instance_id": discovery.get("instance_id"), "pid": discovery.get("pid"),
                       "origin": origin, "attempted": True, "stop_body": {"reason": "cli-stop"}}
            try:
                code, response = json_request(origin, "/api/bridge/stop", {"reason": "cli-stop"},
                                              discovery["management_token"], timeout=10)
                attempt.update({"http_status": code, "accepted": code == 200,
                                "response_instance_id": response.get("instance_id")})
            except Exception as exc:
                attempt.update({"accepted": False,
                                "error": "%s: %s" % (type(exc).__name__, redact_text(str(exc)))})
            normal_stop.append(attempt)

        if known_identities:
            wait_processes_gone(known_identities, 3.0)
        exact_before = matching_bridge_processes(self.workdir)
        fallback = cleanup_process_groups(known_identities + exact_before)
        exact_after = matching_bridge_processes(self.workdir)
        daemon_remaining = [item for item in known_identities if same_process(item)]
        ports = [{"origin": origin, "closed": wait_port_closed(origin)} for origin in sorted(set(origins))]
        stopped = (not daemon_remaining and not exact_after and
                   all(item["closed"] for item in ports) and fallback["stopped"])
        return {
            "workdir": str(self.workdir), "attempted": bool(self.discoveries),
            "normal_stop": normal_stop,
            "known_daemons": [item.public() for item in known_identities],
            "exact_matches_before_fallback": [item.public() for item in exact_before],
            "fallback": fallback,
            "daemon_remaining": [item.public() for item in daemon_remaining],
            "exact_matches_after": [item.public() for item in exact_after],
            "ports": ports, "stopped": stopped,
        }


def prompt_open(deck: Path | None, await_sec: int, *, close: bool = True) -> str:
    deck_arg = "null" if deck is None else json.dumps(str(deck.resolve()))
    close_line = "Then call close_session for that session." if close else "Leave the session open after the wait."
    return (
        "Bridge host acceptance. Use only the MCP server named %s. "
        "Call open_editor with deck_path=%s, output_path='index.html', open_browser=false; "
        "call get_status with its session_id; call await_intent with timeout_sec=%d exactly once. "
        "%s Do not use any built-in tool, shell, filesystem tool, or network tool. "
        "End with a compact JSON summary."
        % (SERVER_NAME, deck_arg, await_sec, close_line)
    )


def prompt_claim(deck: Path | None) -> str:
    deck_arg = "null" if deck is None else json.dumps(str(deck.resolve()))
    return (
        "Bridge host acceptance with one already-pending temporary intent. Use only MCP server %s. "
        "Call open_editor(deck_path=%s, output_path='index.html', open_browser=false), then await_intent "
        "with timeout_sec=25. If an intent is returned, call push_update on exactly that intent/attempt "
        "with action='fail', message='host acceptance deterministic stop', validation omitted. Then call "
        "get_status and close_session. Do not use any built-in tool, shell, filesystem tool, or network tool."
        % (SERVER_NAME, deck_arg)
    )


def prompt_close_reopen(deck: Path | None) -> str:
    deck_arg = "null" if deck is None else json.dumps(str(deck.resolve()))
    return (
        "Use only MCP server %s. Call open_editor(deck_path=%s, output_path='index.html', "
        "open_browser=false), close_session, then call await_intent(timeout_sec=1) and preserve its "
        "expected recovery error. Call open_editor again for the same target, get_status, then "
        "close_session again. Do not use any built-in or non-MCP tool." % (SERVER_NAME, deck_arg)
    )


def prompt_reattach(deck: Path | None) -> str:
    deck_arg = "null" if deck is None else json.dumps(str(deck.resolve()))
    return (
        "Use only MCP server %s. Reattach by calling open_editor(deck_path=%s, output_path='index.html', "
        "open_browser=false), then get_status and close_session. Do not use any built-in or non-MCP tool."
        % (SERVER_NAME, deck_arg)
    )


def classify_invocation(invocation: HostInvocation, required: dict[str, int], *,
                        cancellation: bool = False) -> tuple[str, list[str]]:
    failures = []
    for name, minimum in required.items():
        actual = invocation.evidence.call_count(name)
        if actual < minimum:
            failures.append("%s calls %d < %d" % (name, actual, minimum))
    if invocation.timed_out:
        failures.append("host subprocess timed out")
    if not invocation.process_cleanup.get("stopped"):
        failures.append("host/MCP process group cleanup failed")
    if cancellation:
        if not invocation.interrupted:
            failures.append("SIGINT was not sent after observing await_intent(120)")
    elif invocation.returncode != 0:
        failures.append("host exited %s" % invocation.returncode)
    return ("PASS" if not failures else "FAIL"), failures


def host_environment(host: str, executable: str, python: Path) -> dict[str, Any]:
    try:
        sdk = importlib.metadata.version("mcp")
    except importlib.metadata.PackageNotFoundError:
        sdk = None
    return {
        "host": host, "binary": executable, "version": binary_version(host, executable),
        "expected_version": EXPECTED_VERSIONS[host], "python": sys.version.splitlines()[0],
        "python_executable": str(python), "mcp_sdk": sdk, "platform": platform.platform(),
    }


def preflight(host: str, executable: str, python: Path) -> tuple[dict[str, Any], list[str]]:
    environment = host_environment(host, executable, python)
    blocked = []
    if not executable:
        blocked.append("host executable not found")
    if environment["version"] != EXPECTED_VERSIONS[host]:
        blocked.append("expected %s, found %s" % (EXPECTED_VERSIONS[host], environment["version"] or "unknown"))
    if environment["mcp_sdk"] is None:
        blocked.append("official Python MCP SDK is not installed")
    if not EDIT.is_file() or not BRIDGE_MCP.is_file():
        blocked.append("Bridge MCP entry files are missing")
    if host == "codex" and executable:
        try:
            login = command_output([executable, "login", "status"], timeout=20)
            environment["login_status"] = redact_text((login.stdout + login.stderr).strip())
            environment["login_status_exit_code"] = login.returncode
            if login.returncode != 0:
                blocked.append("Codex login state unavailable: %s" % (environment["login_status"] or "not logged in"))
        except (OSError, subprocess.SubprocessError) as exc:
            blocked.append("Codex login preflight failed: %s" % exc)
    return environment, blocked


def aggregate_evidence(invocations: list[HostInvocation]) -> dict[str, Any]:
    calls = {name: 0 for name in TOOL_NAMES}
    usage_visible = False
    cost_visible = False
    usage_samples = []
    cost_samples = []
    for invocation in invocations:
        summary = invocation.evidence.summary()
        for name, value in summary["tool_calls"].items():
            calls[name] += value
        usage_visible = usage_visible or summary["usage"]["visible"]
        cost_visible = cost_visible or summary["cost"]["visible"]
        usage_samples.extend(summary["usage"]["samples"])
        cost_samples.extend(summary["cost"]["samples"])
    return {
        "tool_calls": calls,
        "tool_call_total": sum(calls.values()),
        "model_processes": len(invocations),
        "usage": {"visible": usage_visible, "samples": usage_samples[-20:],
                  "note": None if usage_visible else "unknown: host stream exposed no parseable usage"},
        "cost": {"visible": cost_visible, "samples": cost_samples[-20:],
                 "value": cost_samples[-1] if cost_samples else "unknown"},
    }


def cleanup_gate(invocations: list[HostInvocation], cleanup: list[dict[str, Any]],
                 expected_scenarios: int) -> tuple[bool, bool, bool]:
    invocation_ok = all(item.process_cleanup.get("stopped") for item in invocations)
    scenarios_ok = (len(cleanup) == expected_scenarios
                    and all(item.get("attempted") and item.get("stopped") for item in cleanup))
    return invocation_ok, scenarios_ok, invocation_ok and scenarios_ok


def run_real_host(host: str, observation_sec: int) -> tuple[int, dict[str, Any]]:
    executable = shutil.which(host)
    python = Path(sys.executable).resolve()
    run_id = "%s-%s-%s" % (host, time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()), uuid.uuid4().hex[:8])
    report_path = RESULT_DIR / ("host-%s.json" % host)
    log_path = RESULT_DIR / ("host-%s.log" % host)
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    config_before = {
        "trusted_project": path_state(ROOT / ".kimi-code"),
        "user_kimi": user_kimi_config_state(),
    }
    environment, blocked = preflight(host, executable or "", python)
    if blocked:
        config_after = {
            "trusted_project": path_state(ROOT / ".kimi-code"),
            "user_kimi": user_kimi_config_state(),
        }
        report = {
            "schema_version": 1, "run_id": run_id, "report_scope": "this invocation only",
            "generated_at": utc_now(), "host": host,
            "status": "BLOCKED", "formal_acceptance": False,
            "real_model_invocations": 0, "environment": environment,
            "blocked": blocked, "not_run": ["all real host scenarios"],
            "isolation": {"user_config_modified": config_before != config_after,
                          "config_before": config_before, "config_after": config_after},
        }
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        log_path.write_text(json.dumps({"at": utc_now(), "run_id": run_id, "status": "BLOCKED",
                                        "reasons": blocked}, ensure_ascii=False) + "\n", encoding="utf-8")
        print("%s BLOCKED: %s" % (host, "; ".join(blocked)))
        print("REPORT:", report_path)
        return 2, report

    source_before = fixture_digest(FIXTURE)
    started = time.monotonic()
    invocations: list[HostInvocation] = []
    cases: list[dict[str, Any]] = []
    cleanup: list[dict[str, Any]] = []
    log = SanitizedLog(log_path, run_id)
    auth_blocked = False
    try:
        with contextlib.ExitStack() as stack:
            temp_root = Path(stack.enter_context(
                tempfile.TemporaryDirectory(prefix="bridge-host-%s-" % host)))
            scenarios = []
            empty = temp_root / "no-deck"
            existing = temp_root / "existing-deck"
            empty.mkdir()
            copy_fixture(FIXTURE, existing)
            scenarios.extend([(empty, None), (existing, existing / "index.html")])
            runtimes = {str(workdir): ScenarioRuntime(workdir) for workdir, _deck in scenarios}

            def cleanup_scenario(runtime: ScenarioRuntime) -> None:
                cleanup.append(runtime.cleanup())

            stack.callback(cleanup_scenario, runtimes[str(existing)])
            stack.callback(cleanup_scenario, runtimes[str(empty)])

            def invoke(label: str, workdir: Path, prompt: str, timeout_sec: int = 240,
                       cancel_when=None) -> HostInvocation:
                command = build_host_command(host, executable, workdir, prompt, python)
                env = os.environ.copy()
                config_context = (temporary_kimi_project_config(ROOT, workdir, python)
                                  if host == "kimi" else contextlib.nullcontext())
                with config_context:
                    invocation = run_streaming(
                        command, cwd=host_cwd(host, workdir), env=env, label=label, log=log,
                        timeout_sec=timeout_sec, cancel_when=cancel_when)
                    runtimes[str(workdir)].capture()
                    invocations.append(invocation)
                return invocation

            first = invoke("no-deck-await-25", empty, prompt_open(None, 25), timeout_sec=180)
            status, failures = classify_invocation(first, {"open_editor": 1, "get_status": 1,
                                                            "await_intent": 1, "close_session": 1})
            if first.duration_sec < 24 or not first.evidence.saw_await(25):
                failures.append("25-second await was not evidenced with bounded wall time")
                status = "FAIL"
            cases.append({"id": "no-deck-await-25", "status": status, "failures": failures,
                          "invocation": first.report()})
            if AUTH_FAILURE.search(first.combined_text) and first.evidence.call_count("open_editor") == 0:
                auth_blocked = True
                raise HarnessError("host authentication unavailable")
            if status != "PASS":
                raise HarnessError("host could not complete the initial MCP scenario")

            long_wait = invoke("no-deck-await-120", empty, prompt_open(None, 120), timeout_sec=260)
            status, failures = classify_invocation(long_wait, {"open_editor": 1, "get_status": 1,
                                                                "await_intent": 1, "close_session": 1})
            if long_wait.duration_sec < 118 or not long_wait.evidence.saw_await(120):
                failures.append("120-second await was not evidenced with bounded wall time")
                status = "FAIL"
            cases.append({"id": "no-deck-await-120", "status": status, "failures": failures,
                          "invocation": long_wait.report()})

            bind_browser_and_submit(empty, None, "brief.submitted")
            claim = invoke("no-deck-claim-fail", empty, prompt_claim(None), timeout_sec=180)
            status, failures = classify_invocation(claim, {name: 1 for name in TOOL_NAMES})
            cases.append({"id": "no-deck-claim-fail", "status": status, "failures": failures,
                          "invocation": claim.report()})

            lifecycle = invoke("close-reopen", empty, prompt_close_reopen(None), timeout_sec=180)
            status, failures = classify_invocation(lifecycle, {"open_editor": 2, "await_intent": 1,
                                                                "get_status": 1, "close_session": 2})
            cases.append({"id": "close-reopen", "status": status, "failures": failures,
                          "invocation": lifecycle.report()})

            cancelled = invoke(
                "cancel-await-120", empty, prompt_open(None, 120, close=False), timeout_sec=180,
                cancel_when=lambda evidence: evidence.saw_await(120))
            status, failures = classify_invocation(cancelled, {"open_editor": 1, "await_intent": 1},
                                                    cancellation=True)
            cases.append({"id": "cancel-await-120", "status": status, "failures": failures,
                          "invocation": cancelled.report()})
            reattach = invoke("reattach-after-cancel", empty, prompt_reattach(None), timeout_sec=180)
            status, failures = classify_invocation(reattach, {"open_editor": 1, "get_status": 1,
                                                               "close_session": 1})
            cases.append({"id": "reattach-after-cancel", "status": status, "failures": failures,
                          "invocation": reattach.report()})

            existing_open = invoke("existing-deck-open", existing, prompt_open(existing / "index.html", 25), timeout_sec=180)
            status, failures = classify_invocation(existing_open, {"open_editor": 1, "get_status": 1,
                                                                    "await_intent": 1, "close_session": 1})
            cases.append({"id": "existing-deck-open", "status": status, "failures": failures,
                          "invocation": existing_open.report()})
            bind_browser_and_submit(existing, existing / "index.html", "design.submitted")
            existing_claim = invoke("existing-deck-claim-fail", existing,
                                    prompt_claim(existing / "index.html"), timeout_sec=180)
            status, failures = classify_invocation(existing_claim, {name: 1 for name in TOOL_NAMES})
            cases.append({"id": "existing-deck-claim-fail", "status": status, "failures": failures,
                          "invocation": existing_claim.report()})

            soak_index = 0
            while time.monotonic() - started < observation_sec:
                soak_index += 1
                soak = invoke("observation-%02d" % soak_index, existing,
                              prompt_open(existing / "index.html", 25), timeout_sec=180)
                status, failures = classify_invocation(soak, {"open_editor": 1, "get_status": 1,
                                                              "await_intent": 1, "close_session": 1})
                cases.append({"id": "observation-%02d" % soak_index, "status": status,
                              "failures": failures, "invocation": soak.report()})
                if soak_index >= 20:
                    break

            temp_existing_digest = fixture_digest(existing)
            copied_fixture_unchanged = temp_existing_digest == source_before
    except HarnessError as exc:
        cases.append({"id": "harness", "status": "BLOCKED" if auth_blocked else "FAIL",
                      "reason": redact_text(str(exc))})
    except Exception as exc:
        cases.append({"id": "harness", "status": "FAIL",
                      "reason": "%s: %s" % (type(exc).__name__, redact_text(str(exc)))})
    finally:
        log.close()

    source_after = fixture_digest(FIXTURE)
    config_after = {
        "trusted_project": path_state(ROOT / ".kimi-code"),
        "user_kimi": user_kimi_config_state(),
    }
    duration = time.monotonic() - started
    evidence = aggregate_evidence(invocations)
    statuses = [case["status"] for case in cases]
    all_tools = all(evidence["tool_calls"][name] > 0 for name in TOOL_NAMES)
    fixture_unchanged = source_before == source_after
    copied_unchanged = locals().get("copied_fixture_unchanged", False)
    config_unchanged = config_before == config_after
    invocation_cleanup_ok, scenario_cleanup_ok, cleanup_ok = cleanup_gate(
        invocations, cleanup, expected_scenarios=2)
    formal = (duration >= FORMAL_DURATION_SEC and all_tools and fixture_unchanged and copied_unchanged
              and config_unchanged and cleanup_ok and statuses
              and all(status == "PASS" for status in statuses))
    if auth_blocked:
        overall = "BLOCKED"
    elif ("FAIL" in statuses or not fixture_unchanged or not copied_unchanged
          or not config_unchanged or not cleanup_ok):
        overall = "FAIL"
    elif formal:
        overall = "PASS"
    else:
        overall = "NOT_RUN"
    report = {
        "schema_version": 1, "run_id": run_id, "report_scope": "this invocation only",
        "generated_at": utc_now(), "host": host,
        "status": overall, "formal_acceptance": formal,
        "real_model_invocations": len(invocations), "duration_sec": round(duration, 3),
        "required_observation_sec": observation_sec, "formal_minimum_sec": FORMAL_DURATION_SEC,
        "environment": environment,
        "isolation": {
            "temporary_workdirs": True, "fixture_copy": str(FIXTURE.relative_to(ROOT)),
            "source_fixture_before": source_before, "source_fixture_after": source_after,
            "source_fixture_unchanged": fixture_unchanged,
            "copied_fixture_unchanged": copied_unchanged,
            "config_before": config_before, "config_after": config_after,
            "project_and_user_config_unchanged": config_unchanged,
            "user_config_modified": config_before["user_kimi"] != config_after["user_kimi"],
            "kimi_trusted_root_cwd": str(ROOT) if host == "kimi" else None,
            "kimi_root_project_config_atomic_restore": host == "kimi",
            "codex_ignore_user_config_ephemeral": host == "codex",
        },
        "evidence": evidence, "cases": cases,
        "cleanup": {"ok": cleanup_ok, "invocation_process_groups_ok": invocation_cleanup_ok,
                    "scenarios_ok": scenario_cleanup_ok, "scenarios": cleanup},
        "limitations": [
            "push_update is exercised with action=fail; deterministic host acceptance does not publish or fabricate validation",
            "cost remains unknown unless the host stream exposes an explicit cost field",
            "Kimi 2.1.1 has no ephemeral flag; a real run may persist session metadata under the existing Kimi home",
        ],
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("REPORT:", report_path)
    print("RESULT:", host, overall, "formal_acceptance=%s" % str(formal).lower())
    return (0 if overall == "PASS" else 2 if overall in ("BLOCKED", "NOT_RUN") else 1), report


def self_check() -> int:
    checks: dict[str, bool] = {}
    with tempfile.TemporaryDirectory(prefix="bridge-host-self-check-") as tmp_name:
        workdir = Path(tmp_name).resolve()
        python = Path(sys.executable).resolve()
        trusted_root = workdir / "trusted-root"
        scenario = workdir / "scenario"
        trusted_config_dir = trusted_root / ".kimi-code"
        trusted_config_dir.mkdir(parents=True)
        original = b'{"mcpServers":{"preserved":{"command":"before"}}}\n'
        config_path = trusted_config_dir / "mcp.json"
        config_path.write_bytes(original)
        config_path.chmod(0o640)
        trusted_before = path_state(trusted_config_dir)
        with temporary_kimi_project_config(trusted_root, scenario, python) as installed:
            config = json.loads(installed.read_text(encoding="utf-8"))
            server = config["mcpServers"][SERVER_NAME]
            checks["kimi_project_config"] = installed == trusted_root / ".kimi-code" / "mcp.json"
            checks["kimi_absolute_command"] = Path(server["command"]).is_absolute()
            checks["kimi_absolute_edit_workdir"] = (Path(server["args"][0]).is_absolute()
                                                        and Path(server["args"][1]).is_absolute()
                                                        and server["args"][2] == "--mcp")
            checks["kimi_timeout_covers_86400s"] = server["toolTimeoutMs"] == 86500000
            checks["kimi_config_no_secret"] = "token" not in json.dumps(config).lower()
        checks["kimi_existing_config_restored"] = (config_path.read_bytes() == original
                                                    and config_path.stat().st_mode & 0o777 == 0o640
                                                    and path_state(trusted_config_dir) == trusted_before)
        absent_root = workdir / "trusted-root-absent"
        with temporary_kimi_project_config(absent_root, scenario, python):
            checks["kimi_absent_config_created"] = (absent_root / ".kimi-code/mcp.json").is_file()
        checks["kimi_empty_directory_removed"] = not (absent_root / ".kimi-code").exists()
        kimi_command = build_host_command("kimi", "/abs/kimi", scenario, "synthetic", python)
        checks["kimi_stream_json"] = kimi_command[-2:] == ["--output-format", "stream-json"]
        checks["kimi_trusted_root_cwd"] = host_cwd("kimi", scenario) == ROOT

        codex_command = build_host_command("codex", "/abs/codex", workdir, "synthetic", python)
        joined = " ".join(codex_command)
        checks["codex_safe_isolation"] = all(flag in codex_command for flag in (
            "--ignore-user-config", "--ignore-rules", "--ephemeral", "--json"))
        checks["codex_cli_mcp_override"] = ("mcp_servers.%s.command" % SERVER_NAME) in joined and str(EDIT) in joined
        checks["codex_no_global_mutation"] = "mcp add" not in joined and "mcp remove" not in joined
        checks["codex_workspace_write"] = "workspace-write" in codex_command and str(workdir) in codex_command

        orphan_parent = subprocess.Popen([
            str(python), "-c",
            "import subprocess,sys; subprocess.Popen([sys.executable,'-c','import time; time.sleep(300)'],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)",
        ], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=True)
        orphan_parent.wait(timeout=10)
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and not process_group_members(orphan_parent.pid):
            time.sleep(.05)
        group_cleanup = cleanup_process_group(orphan_parent.pid)
        checks["orphan_mcp_process_group_removed"] = (
            group_cleanup["stopped"] and not process_group_members(orphan_parent.pid))

        fake_workdir = workdir / "fake-daemon-workdir"
        (fake_workdir / ".pptx-html").mkdir(parents=True)
        probe = socket.socket()
        probe.bind(("127.0.0.1", 0))
        unused_port = probe.getsockname()[1]
        probe.close()
        fake_daemon = subprocess.Popen([
            str(python), "-c", "import time; time.sleep(300)",
            str(EDIT), str(fake_workdir), "--daemon",
        ], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=True)
        fake_identity = process_identity(fake_daemon.pid)
        fake_discovery = {
            "protocol_version": 2, "workdir": str(fake_workdir), "instance_id": "self-check-fake",
            "pid": fake_daemon.pid, "origin": "http://127.0.0.1:%d" % unused_port,
            "port": unused_port, "management_token": "self-check-token",
        }
        (fake_workdir / ".pptx-html/serve.json").write_text(
            json.dumps(fake_discovery), encoding="utf-8")
        runtime = ScenarioRuntime(fake_workdir)
        runtime.capture()
        fake_cleanup = runtime.cleanup()
        with contextlib.suppress(subprocess.TimeoutExpired):
            fake_daemon.wait(timeout=5)
        if fake_daemon.poll() is None:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(fake_daemon.pid, signal.SIGKILL)
            fake_daemon.wait(timeout=5)
        shutil.rmtree(fake_workdir)
        checks["live_daemon_before_workdir_delete_removed"] = (
            fake_identity is not None and fake_cleanup["stopped"] and not same_process(fake_identity))
        checks["fake_workdir_deleted_after_cleanup"] = not fake_workdir.exists()
        checks["stop_body_uses_cli_stop"] = (
            fake_cleanup["normal_stop"][0]["stop_body"] == {"reason": "cli-stop"})
        checks["cleanup_failure_blocks_formal"] = not cleanup_gate(
            [], [{"stopped": False}], expected_scenarios=1)[2]

        evidence = StreamEvidence()
        synthetic = [
            {"type": "assistant", "tool_calls": [{"id": "1", "name": "mcp__%s__open_editor" % SERVER_NAME,
                                                     "arguments": {"deck_path": None}}]},
            {"type": "item.started", "item": {"id": "2", "type": "mcp_tool_call",
                                                  "server": SERVER_NAME, "tool": "await_intent",
                                                  "arguments": "{\"timeout_sec\":120}"}},
            {"type": "assistant", "tool_calls": [{"id": "3", "name": "push_update", "args": {"action": "fail"}},
                                                     {"id": "4", "name": "get_status", "args": {}},
                                                     {"id": "5", "name": "close_session", "args": {}}],
             "usage": {"input_tokens": 10, "output_tokens": 5}, "cost_usd": 0.01},
        ]
        for event in synthetic:
            evidence.ingest(json.dumps(event), "stdout")
        checks["stream_five_tools"] = all(evidence.call_count(name) == 1 for name in TOOL_NAMES)
        checks["stream_await_120"] = evidence.saw_await(120)
        checks["stream_usage_cost"] = (evidence.summary()["usage"]["visible"]
                                                and evidence.summary()["cost"]["visible"])

        secret = "https://127.0.0.1/editor.html#brt=abc123&session=s Authorization: Bearer xyz"
        safe = redact_text(secret)
        checks["redact_url_and_bearer"] = "abc123" not in safe and "xyz" not in safe
        safe_obj = redact({"management_token": "secret", "nested": {"api_key": "key"}})
        checks["redact_secret_keys"] = (safe_obj["management_token"] == "<redacted>"
                                        and safe_obj["nested"]["api_key"] == "<redacted>")
        prompts = [prompt_open(None, 25), prompt_claim(None),
                   prompt_close_reopen(None), prompt_reattach(None)]
        checks["prompts_forbid_builtin_tools"] = all("built-in" in prompt for prompt in prompts)
        checks["formal_duration_guard"] = 539 < FORMAL_DURATION_SEC <= DEFAULT_OBSERVATION_SEC
        checks["result_paths_gitignored_scope"] = str(RESULT_DIR).endswith("tests/harness/results/bridge-p4")

    report = {
        "schema_version": 1, "generated_at": utc_now(), "mode": "self-check",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "real_model_invocations": 0, "network_calls": 0, "checks": checks,
        "sample_commands": {"kimi": public_command(kimi_command), "codex": public_command(codex_command)},
    }
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    path = RESULT_DIR / "host-self-check.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("REPORT:", path)
    print("RESULT:", report["status"], "real model invocations: 0")
    return 0 if report["status"] == "PASS" else 1


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bridge v2 P4 real Kimi/Codex MCP host acceptance; real model calls require --host")
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--self-check", action="store_true",
                       help="offline command/config/parser/redaction checks; never starts a host or model")
    modes.add_argument("--host", choices=("kimi", "codex", "all"),
                       help="EXPLICIT REAL MODE: starts the selected host and incurs model usage/cost")
    parser.add_argument("--observation-sec", type=int, default=DEFAULT_OBSERVATION_SEC,
                        help="real-mode target wall time per host (default 600; below 540 cannot formally pass)")
    args = parser.parse_args(argv)
    if args.observation_sec < 1:
        parser.error("--observation-sec must be >= 1")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.self_check:
        return self_check()
    hosts = ("kimi", "codex") if args.host == "all" else (args.host,)
    results = []
    codes = []
    for host in hosts:
        code, report = run_real_host(host, args.observation_sec)
        codes.append(code)
        results.append({"host": host, "status": report["status"],
                        "formal_acceptance": report["formal_acceptance"]})
    if args.host == "all":
        aggregate = {
            "schema_version": 1, "generated_at": utc_now(), "status": (
                "PASS" if all(item["status"] == "PASS" for item in results) else
                "FAIL" if any(item["status"] == "FAIL" for item in results) else "BLOCKED"),
            "hosts": results,
        }
        RESULT_DIR.mkdir(parents=True, exist_ok=True)
        (RESULT_DIR / "host-all.json").write_text(
            json.dumps(aggregate, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 1 if 1 in codes else 2 if 2 in codes else 0


if __name__ == "__main__":
    sys.exit(main())
