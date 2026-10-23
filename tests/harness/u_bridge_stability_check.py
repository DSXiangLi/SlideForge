#!/usr/bin/env python3
from __future__ import annotations

import argparse
import contextlib
import http.client
import json
import math
import os
import platform
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import traceback
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[2]
EDIT = ROOT / "tools" / "edit.py"
RESULT_DIR = ROOT / "tests" / "harness" / "results" / "bridge-p4"

AWAIT_P95_SLACK_SEC = 2
AWAIT_MAX_SLACK_SEC = 5
CANCEL_P95_LIMIT_MS = 1000
COLD_START_P95_LIMIT_MS = 3000
STABLE_RESOURCE_GROWTH_LIMIT = 5
IDLE_RSS_GROWTH_LIMIT_MIB = 20
STOP_ACCEPT_LIMIT_SEC = 5
STOP_WAIT_LIMIT_SEC = 20
DISCOVERY_LIMIT_SEC = 10
QUIESCE_LIMIT_SEC = 3
SSE_RECLAIM_LIMIT_SEC = 33
FORMAL_CONNECTION_BATCH_SIZE = 5
FORMAL_AWAIT_CASES = ((1, 100), (25, 20), (120, 3))
FORMAL_CANCEL_COUNT = 100
FORMAL_COLD_START_COUNT = 20
FORMAL_CONNECTION_ROUNDS = 100
FORMAL_CONNECTION_WARMUP_ROUNDS = 20
FORMAL_IDLE_SEC = 30 * 60
FORMAL_HEARTBEAT_SEC = 15


@dataclass(frozen=True)
class Profile:
    mode: str
    await_cases: tuple[tuple[int, int], ...]
    cancel_count: int
    cold_start_count: int
    connection_rounds: int
    connection_warmup_rounds: int
    idle_sec: float
    heartbeat_sec: float

    @property
    def formal(self):
        return self.mode == "formal"


FORMAL_PROFILE = Profile(
    mode="formal",
    await_cases=FORMAL_AWAIT_CASES,
    cancel_count=FORMAL_CANCEL_COUNT,
    cold_start_count=FORMAL_COLD_START_COUNT,
    connection_rounds=FORMAL_CONNECTION_ROUNDS,
    connection_warmup_rounds=FORMAL_CONNECTION_WARMUP_ROUNDS,
    idle_sec=FORMAL_IDLE_SEC,
    heartbeat_sec=FORMAL_HEARTBEAT_SEC,
)


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def utc_now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def percentile(values, fraction):
    check(values, "cannot calculate a percentile for an empty sample")
    ordered = sorted(values)
    return ordered[max(0, math.ceil(fraction * len(ordered)) - 1)]


def distribution(values, unit="ms"):
    return {
        "count": len(values),
        f"p50_{unit}": round(percentile(values, .50), 3),
        f"p95_{unit}": round(percentile(values, .95), 3),
        f"max_{unit}": round(max(values), 3),
    }


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def command_version(argv):
    try:
        run = subprocess.run(argv, capture_output=True, text=True, timeout=10)
        if run.returncode == 0:
            return (run.stdout or run.stderr).splitlines()[0].strip()
    except (OSError, subprocess.SubprocessError, IndexError):
        pass
    return None


def environment(root):
    memory = {}
    with contextlib.suppress(OSError):
        memory = {
            line.split(":", 1)[0]: line.split(":", 1)[1].strip()
            for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines()
            if line.startswith(("MemTotal:", "MemAvailable:"))
        }
    usage = shutil.disk_usage(root)
    return {
        "platform": platform.platform(),
        "python": sys.version.splitlines()[0],
        "git": command_version(["git", "--version"]),
        "cpu_count": os.cpu_count(),
        "load_average": list(os.getloadavg()),
        "memory": memory,
        "disk": {
            "total_gib": round(usage.total / 1024 ** 3, 3),
            "free_gib": round(usage.free / 1024 ** 3, 3),
        },
    }


def process_resources(pid):
    result = {
        "pid": pid,
        "alive": Path(f"/proc/{pid}").exists(),
        "rss_mib": None,
        "fd_count": None,
        "thread_count": None,
        "child_pids": [],
        "child_count": None,
    }
    if not result["alive"]:
        result["child_count"] = 0
        return result
    try:
        for line in Path(f"/proc/{pid}/status").read_text(encoding="utf-8").splitlines():
            if line.startswith("VmRSS:"):
                result["rss_mib"] = round(int(line.split()[1]) / 1024, 3)
                break
        result["fd_count"] = len(list(Path(f"/proc/{pid}/fd").iterdir()))
        result["thread_count"] = len(list(Path(f"/proc/{pid}/task").iterdir()))
        children = Path(f"/proc/{pid}/task/{pid}/children").read_text(encoding="utf-8").split()
        result["child_pids"] = [int(value) for value in children]
        result["child_count"] = len(children)
    except (FileNotFoundError, PermissionError, ProcessLookupError):
        result["alive"] = False
    return result


def resource_distributions(resources):
    summaries = {}
    for field, unit in (("rss_mib", "mib"), ("fd_count", "count"),
                        ("thread_count", "count"), ("child_count", "count")):
        values = [sample[field] for sample in resources if sample.get(field) is not None]
        summaries[field] = distribution(values, unit=unit) if values else None
    return summaries


def sqlite_state(workdir):
    internal = Path(workdir) / ".pptx-html"
    database = internal / "bridge.sqlite3"
    state = {
        "path": str(database),
        "exists": database.exists(),
        "files": {},
        "quick_check": None,
        "journal_mode": None,
        "table_counts": {},
        "error": None,
    }
    for suffix in ("", "-wal", "-shm"):
        file = Path(str(database) + suffix)
        state["files"][file.name] = {"exists": file.exists(), "bytes": file.stat().st_size if file.exists() else 0}
    if not database.exists():
        return state
    try:
        uri = f"file:{database}?mode=ro"
        connection = sqlite3.connect(uri, uri=True, timeout=2)
        try:
            state["quick_check"] = connection.execute("PRAGMA quick_check").fetchone()[0]
            state["journal_mode"] = connection.execute("PRAGMA journal_mode").fetchone()[0]
            tables = [row[0] for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
            state["table_counts"] = {
                table: connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
                for table in tables
            }
        finally:
            connection.close()
    except (OSError, sqlite3.Error) as exc:
        state["error"] = f"{type(exc).__name__}: {exc}"
    return state


def request_json(origin, path, body=None, bearer=None, timeout=15, origin_header=None):
    parsed = urlsplit(origin)
    connection = http.client.HTTPConnection(parsed.hostname, parsed.port, timeout=timeout)
    headers = {}
    payload = None
    if bearer:
        headers["Authorization"] = "Bearer " + bearer
    if origin_header is not None:
        headers["Origin"] = origin_header
    if body is not None:
        payload = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        headers["Content-Type"] = "application/json"
    try:
        connection.request("POST" if body is not None else "GET", path, body=payload, headers=headers)
        response = connection.getresponse()
        raw = response.read()
        data = json.loads(raw) if raw else {}
        return response.status, data
    finally:
        connection.close()


def port_state(discovery):
    try:
        code, body = request_json(
            discovery["origin"], "/api/health", bearer=discovery["management_token"], timeout=2)
        return {
            "reachable": True,
            "authenticated_ready": code == 200 and body.get("bridge_available") is True,
            "http_status": code,
            "instance_id": body.get("instance_id"),
        }
    except (OSError, http.client.HTTPException, json.JSONDecodeError) as exc:
        return {"reachable": False, "authenticated_ready": False, "error": f"{type(exc).__name__}: {exc}"}


def port_closed(origin):
    parsed = urlsplit(origin)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    try:
        return sock.connect_ex((parsed.hostname, parsed.port)) != 0
    finally:
        sock.close()


def checkpoint(daemon, label):
    return {
        "label": label,
        "monotonic_sec": round(time.monotonic(), 6),
        "resources": process_resources(daemon.proc.pid),
        "port": port_state(daemon.discovery),
        "sqlite": sqlite_state(daemon.workdir),
    }


def minimal_deck():
    return "<!doctype html><meta charset=utf-8><title>Bridge P4 stability</title><section class=slide data-slide-id=cover><h1 data-editable>Bridge P4 stability</h1></section>"


class Daemon:
    def __init__(self, workdir):
        self.workdir = Path(workdir)
        self.proc = None
        self.discovery = None
        self.stderr = ""
        self.stdout = ""

    def start(self):
        self.proc = subprocess.Popen(
            [sys.executable, str(EDIT), str(self.workdir), "--daemon", "--port", "0"],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        discovery_path = self.workdir / ".pptx-html" / "serve.json"
        deadline = time.monotonic() + DISCOVERY_LIMIT_SEC
        while time.monotonic() < deadline:
            if self.proc.poll() is not None:
                self._collect_output()
                raise AssertionError(f"daemon exited during startup: {self.stderr or self.stdout}")
            if discovery_path.exists():
                try:
                    discovery = json.loads(discovery_path.read_text(encoding="utf-8"))
                    port = port_state(discovery)
                    if port["authenticated_ready"] and port["instance_id"] == discovery["instance_id"]:
                        self.discovery = discovery
                        return self
                except (OSError, json.JSONDecodeError, KeyError):
                    pass
            time.sleep(.02)
        raise AssertionError("daemon did not become authenticated-ready before startup deadline")

    def _collect_output(self):
        if self.proc and self.proc.poll() is not None:
            stdout, stderr = self.proc.communicate()
            self.stdout = stdout
            self.stderr = stderr

    def stop(self):
        if not self.proc:
            return {"already_stopped": True}
        started = time.monotonic()
        response = None
        error = None
        if self.proc.poll() is None and self.discovery:
            try:
                response = request_json(
                    self.discovery["origin"], "/api/bridge/stop", {"reason": "cli-stop"},
                    self.discovery["management_token"], timeout=STOP_ACCEPT_LIMIT_SEC)
            except Exception as exc:
                error = f"{type(exc).__name__}: {exc}"
        try:
            self.proc.wait(timeout=STOP_WAIT_LIMIT_SEC)
        except subprocess.TimeoutExpired:
            self.proc.terminate()
            self.proc.wait(timeout=STOP_ACCEPT_LIMIT_SEC)
            error = error or "graceful stop exceeded wait limit and required terminate"
        elapsed_ms = (time.monotonic() - started) * 1000
        self._collect_output()
        return {
            "elapsed_ms": round(elapsed_ms, 3),
            "response": response,
            "error": error,
            "returncode": self.proc.returncode,
            "stderr": self.stderr,
            "stdout": self.stdout,
            "port_closed": port_closed(self.discovery["origin"]) if self.discovery else None,
            "sqlite": sqlite_state(self.workdir),
        }

    def force_cleanup(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            with contextlib.suppress(subprocess.TimeoutExpired):
                self.proc.wait(timeout=STOP_ACCEPT_LIMIT_SEC)
            if self.proc.poll() is None:
                self.proc.kill()
                self.proc.wait(timeout=STOP_ACCEPT_LIMIT_SEC)
            self._collect_output()


class Harness:
    def __init__(self, profile):
        self.profile = profile
        self.started_at = utc_now()
        self.heartbeat_due = {}
        self.metrics = {
            "schema_version": 1,
            "mode": profile.mode,
            "formal_acceptance": profile.formal,
            "started_at": self.started_at,
            "profile": asdict(profile),
            "formal_profile": asdict(FORMAL_PROFILE),
            "environment": None,
            "phases": {},
            "checkpoints": [],
            "checks": {},
            "error": None,
        }

    def flush(self, state="RUNNING"):
        self.metrics["generated_at"] = utc_now()
        self.metrics["state"] = state
        atomic_json(RESULT_DIR / "metrics.json", self.metrics)
        report = {
            "schema_version": 1,
            "generated_at": self.metrics["generated_at"],
            "mode": self.profile.mode,
            "formal_acceptance": self.profile.formal,
            "status": state,
            "checks": self.metrics["checks"],
            "metrics_path": "tests/harness/results/bridge-p4/metrics.json",
            "notice": (
                "Formal PERF-04/05/06 acceptance run with fixed sample counts."
                if self.profile.formal else
                "Development-only reduced run. This report is not formal PERF-04/05/06 acceptance evidence."
            ),
        }
        atomic_json(RESULT_DIR / "report.json", report)

    def add_checkpoint(self, daemon, label):
        sample = checkpoint(daemon, label)
        self.metrics["checkpoints"].append(sample)
        self.flush()
        return sample

    def run(self):
        RESULT_DIR.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="bridge-p4-stability-") as tmp:
            root = Path(tmp)
            self.metrics["environment"] = environment(root)
            self.flush()
            self.run_cold_starts(root)
            self.flush()
            self.run_stability(root)
            self.flush()
            self.run_active_stop(root)
            self.evaluate()
            final_state = "PASS" if self.profile.formal and all(self.metrics["checks"].values()) else (
                "FAIL" if self.profile.formal else (
                    "DEVELOPMENT_OK" if all(self.metrics["checks"].values()) else "DEVELOPMENT_FAIL"))
            self.flush(final_state)
            check(all(self.metrics["checks"].values()), "one or more stability thresholds failed")
            return final_state

    def run_cold_starts(self, root):
        samples = []
        for index in range(self.profile.cold_start_count):
            workdir = root / f"cold-{index + 1:03d}"
            workdir.mkdir()
            daemon = Daemon(workdir)
            started = time.monotonic()
            try:
                daemon.start()
                ready_ms = (time.monotonic() - started) * 1000
                before_stop = checkpoint(daemon, "cold-ready")
                stopped = daemon.stop()
                sample = {
                    "index": index + 1,
                    "ready_ms": round(ready_ms, 3),
                    "ready": before_stop,
                    "stop": stopped,
                }
                check(stopped["returncode"] == 0 and stopped["port_closed"], f"cold start {index + 1} did not stop cleanly")
                check(stopped["sqlite"]["quick_check"] == "ok", f"cold start {index + 1} SQLite check failed")
                samples.append(sample)
                self.metrics["phases"]["cold_start"] = {
                    "samples": samples,
                    "distribution": distribution([item["ready_ms"] for item in samples]),
                }
                self.flush()
            finally:
                daemon.force_cleanup()
        self.metrics["phases"]["cold_start"]["distribution"] = distribution(
            [item["ready_ms"] for item in samples])

    def open_session(self, daemon):
        deck = daemon.workdir / "index.html"
        deck.write_text(minimal_deck(), encoding="utf-8")
        items = []
        for consumer in ("stability-a", "stability-b"):
            code, opened = request_json(
                daemon.discovery["origin"], "/api/bridge/open", {
                    "consumer_id": consumer,
                    "deck_path": str(deck),
                    "output_path": "index.html",
                    "view": "edit",
                    "open_browser": False,
                }, daemon.discovery["management_token"])
            check(code == 200 and opened.get("ok"), f"open failed for {consumer}: {code} {opened}")
            items.append(opened)
        check(items[0]["session_id"] == items[1]["session_id"], "two consumers did not share one session")
        tabs = []
        for opened in items:
            fragment = parse_qs(urlsplit(opened["url"]).fragment)
            token = fragment["brt"][0]
            body = {
                "protocol_version": 2,
                "role": "browser",
                "session_id": opened["session_id"],
                "client_id": str(uuid.uuid4()),
                "dirty": False,
                "active_edit": False,
                "draft_pending": False,
                "revision": opened["revision"],
                "last_event_id": 0,
            }
            code, response = request_json(
                daemon.discovery["origin"], "/api/bridge/heartbeat", body, token,
                origin_header=daemon.discovery["origin"])
            check(code == 200 and response.get("client_id") == body["client_id"], f"tab bind failed: {response}")
            tabs.append({"token": token, "heartbeat": body})
        return {"session_id": items[0]["session_id"], "revision": items[0]["revision"], "tabs": tabs}

    def run_stability(self, root):
        workdir = root / "stability"
        workdir.mkdir()
        daemon = Daemon(workdir)
        try:
            daemon.start()
            session = self.open_session(daemon)
            self.add_checkpoint(daemon, "stability-baseline")
            self.arm_heartbeat(daemon, session)
            self.run_await_samples(daemon, session)
            self.add_checkpoint(daemon, "after-await")
            self.run_cancel_samples(daemon, session)
            self.add_checkpoint(daemon, "after-cancel")
            self.run_connection_cycles(daemon, session)
            self.add_checkpoint(daemon, "after-connections")
            self.run_idle(daemon, session)
            self.add_checkpoint(daemon, "after-idle")
            stopped = daemon.stop()
            self.metrics["phases"]["stability_stop"] = stopped
            check(stopped["returncode"] == 0 and stopped["port_closed"], "stability daemon did not stop cleanly")
            check(stopped["sqlite"]["quick_check"] == "ok", "stability SQLite failed after stop")
        finally:
            daemon.force_cleanup()

    def run_await_samples(self, daemon, session):
        phase = {"cases": {}}
        self.metrics["phases"]["await"] = phase
        for timeout_sec, count in self.profile.await_cases:
            samples = []
            for index in range(count):
                started = time.monotonic()
                with self.heartbeat_during(daemon, session):
                    code, response = request_json(
                        daemon.discovery["origin"], "/api/bridge/await", {
                            "session_id": session["session_id"],
                            "consumer_id": "stability-a",
                            "timeout_sec": timeout_sec,
                        }, daemon.discovery["management_token"], timeout=timeout_sec + AWAIT_MAX_SLACK_SEC + 2)
                elapsed_ms = (time.monotonic() - started) * 1000
                check(code == 200 and response.get("kind") == "timeout", f"await {timeout_sec}s failed: {code} {response}")
                samples.append({
                    "index": index + 1,
                    "requested_sec": timeout_sec,
                    "elapsed_ms": round(elapsed_ms, 3),
                    "http_status": code,
                    "kind": response.get("kind"),
                    "resources_after": process_resources(daemon.proc.pid),
                })
                phase["cases"][str(timeout_sec)] = {
                    "requested_sec": timeout_sec,
                    "samples": samples,
                    "distribution": distribution([sample["elapsed_ms"] for sample in samples]),
                }
                self.flush()

    def cancel_socket(self, daemon, session, timeout_sec=120):
        parsed = urlsplit(daemon.discovery["origin"])
        body = json.dumps({
            "session_id": session["session_id"],
            "consumer_id": "stability-a",
            "timeout_sec": timeout_sec,
        }, separators=(",", ":")).encode("utf-8")
        request = (
            f"POST /api/bridge/await HTTP/1.1\r\n"
            f"Host: {parsed.netloc}\r\n"
            f"Authorization: Bearer {daemon.discovery['management_token']}\r\n"
            "Content-Type: application/json\r\n"
            f"Content-Length: {len(body)}\r\n"
            "Connection: keep-alive\r\n\r\n"
        ).encode("ascii") + body
        baseline = process_resources(daemon.proc.pid)
        sock = socket.create_connection((parsed.hostname, parsed.port), timeout=2)
        sock.sendall(request)
        deadline = time.monotonic() + 1
        observed = False
        while time.monotonic() < deadline:
            current = process_resources(daemon.proc.pid)
            if ((current["thread_count"] or 0) > (baseline["thread_count"] or 0)
                    or (current["fd_count"] or 0) > (baseline["fd_count"] or 0)):
                observed = True
                break
            time.sleep(.005)
        closed_at = time.monotonic()
        with contextlib.suppress(OSError):
            sock.shutdown(socket.SHUT_RDWR)
        sock.close()
        reclaimed = False
        final = None
        deadline = closed_at + QUIESCE_LIMIT_SEC
        while time.monotonic() < deadline:
            final = process_resources(daemon.proc.pid)
            if ((final["thread_count"] or 0) <= (baseline["thread_count"] or 0)
                    and (final["fd_count"] or 0) <= (baseline["fd_count"] or 0)):
                reclaimed = True
                break
            time.sleep(.01)
        return {
            "observed_active_request": observed,
            "requested_timeout_sec": timeout_sec,
            "reclaim_ms": round((time.monotonic() - closed_at) * 1000, 3),
            "reclaimed": reclaimed,
            "baseline": baseline,
            "final": final,
        }

    def run_cancel_samples(self, daemon, session):
        samples = []
        phase = {"request_timeout_sec": 120, "samples": samples}
        self.metrics["phases"]["cancel"] = phase
        for index in range(self.profile.cancel_count):
            self.heartbeat_if_due(daemon, session)
            sample = self.cancel_socket(daemon, session)
            sample["index"] = index + 1
            samples.append(sample)
            phase["distribution"] = distribution([item["reclaim_ms"] for item in samples])
            self.flush()
        check(all(item["observed_active_request"] for item in samples), "one or more cancellation requests were not observed active")
        check(all(item["reclaimed"] for item in samples), "one or more cancelled connections did not reclaim resources")

    def open_sse(self, daemon, session, tab_index=0):
        parsed = urlsplit(daemon.discovery["origin"])
        connection = http.client.HTTPConnection(parsed.hostname, parsed.port, timeout=2)
        tab = session["tabs"][tab_index]
        connection.request(
            "GET", f"/api/events?session_id={session['session_id']}&after=0",
            headers={"Authorization": "Bearer " + tab["token"], "Sec-Fetch-Site": "same-origin"})
        response = connection.getresponse()
        check(response.status == 200 and response.getheader("Content-Type") == "text/event-stream", "SSE connection failed")
        line = response.readline().decode("utf-8", errors="replace")
        return connection, response, line

    def keepalive_roundtrip(self, daemon, session):
        parsed = urlsplit(daemon.discovery["origin"])
        connection = http.client.HTTPConnection(parsed.hostname, parsed.port, timeout=3)
        body = json.dumps({"session_id": session["session_id"]}, separators=(",", ":")).encode("utf-8")
        headers = {
            "Authorization": "Bearer " + daemon.discovery["management_token"],
            "Content-Type": "application/json",
        }
        statuses = []
        try:
            for _ in range(2):
                connection.request("POST", "/api/bridge/status", body=body, headers=headers)
                response = connection.getresponse()
                response.read()
                statuses.append(response.status)
        finally:
            connection.close()
        return statuses

    def wait_quiescent(self, pid, baseline, timeout=QUIESCE_LIMIT_SEC):
        deadline = time.monotonic() + timeout
        current = process_resources(pid)
        while time.monotonic() < deadline:
            current = process_resources(pid)
            if ((current["thread_count"] or 0) <= (baseline["thread_count"] or 0)
                    and (current["fd_count"] or 0) <= (baseline["fd_count"] or 0)):
                return True, current
            time.sleep(.01)
        return False, current

    def run_connection_cycles(self, daemon, session):
        baseline = process_resources(daemon.proc.pid)
        rounds = []
        batch_size = FORMAL_CONNECTION_BATCH_SIZE if self.profile.formal else min(2, self.profile.connection_rounds)
        phase = {"baseline": baseline, "batch_size": batch_size, "samples": rounds}
        self.metrics["phases"]["connections"] = phase
        batch = []
        for index in range(self.profile.connection_rounds):
            started = time.monotonic()
            with self.heartbeat_during(daemon, session):
                connection, response, first_line = self.open_sse(daemon, session, index % 2)
            response.close()
            connection.close()
            statuses = self.keepalive_roundtrip(daemon, session)
            sample = {
                "index": index + 1,
                "elapsed_ms": round((time.monotonic() - started) * 1000, 3),
                "sse_first_line": first_line.rstrip("\r\n"),
                "keepalive_statuses": statuses,
                "resources_on_close": process_resources(daemon.proc.pid),
                "quiescent": None,
                "resources_after": None,
            }
            rounds.append(sample)
            batch.append(sample)
            if len(batch) == batch_size or index + 1 == self.profile.connection_rounds:
                self.heartbeat_if_due(daemon, session)
                quiescent, resources = self.wait_quiescent(daemon.proc.pid, baseline, SSE_RECLAIM_LIMIT_SEC)
                for item in batch:
                    item["quiescent"] = quiescent
                    item["resources_after"] = resources
                batch = []
            phase["distribution"] = distribution([item["elapsed_ms"] for item in rounds])
            self.flush()
        phase["resource_distributions_on_close"] = resource_distributions(
            [item["resources_on_close"] for item in rounds])
        phase["resource_distributions_after_reclaim"] = resource_distributions(
            [item["resources_after"] for item in rounds])
        check(all(item["keepalive_statuses"] == [200, 200] for item in rounds), "keep-alive cycle failed")
        check(all(item["quiescent"] for item in rounds), "connection batch did not return to baseline after an SSE ping interval")
        warmup_index = min(self.profile.connection_warmup_rounds, len(rounds)) - 1
        stable_baseline = rounds[warmup_index]["resources_after"]
        tail = rounds[-min(20, len(rounds)):]
        fd_values = [item["resources_after"]["fd_count"] for item in tail]
        thread_values = [item["resources_after"]["thread_count"] for item in tail]
        child_values = [item["resources_after"]["child_count"] for item in tail]
        phase["stable_baseline_round"] = warmup_index + 1
        phase["stable_baseline"] = stable_baseline
        phase["last_20_or_all"] = {
            "count": len(tail),
            "fd_max_growth": max(fd_values) - stable_baseline["fd_count"],
            "thread_max_growth": max(thread_values) - stable_baseline["thread_count"],
            "child_max_growth": max(child_values) - stable_baseline["child_count"],
        }

    def heartbeat_key(self, daemon, session):
        return daemon.discovery["origin"], session["session_id"]

    def arm_heartbeat(self, daemon, session):
        self.heartbeat_due[self.heartbeat_key(daemon, session)] = time.monotonic() + FORMAL_HEARTBEAT_SEC

    def heartbeat(self, daemon, session):
        for tab in session["tabs"]:
            code, response = request_json(
                daemon.discovery["origin"], "/api/bridge/heartbeat", tab["heartbeat"], tab["token"],
                origin_header=daemon.discovery["origin"])
            check(code == 200 and response.get("client_id") == tab["heartbeat"]["client_id"], "browser heartbeat failed")
        code, response = request_json(
            daemon.discovery["origin"], "/api/bridge/heartbeat", {
                "protocol_version": 2,
                "role": "consumer",
                "session_id": session["session_id"],
                "consumer_id": "stability-a",
            }, daemon.discovery["management_token"])
        check(code == 200 and response.get("ok"), "consumer heartbeat failed")
        self.arm_heartbeat(daemon, session)

    def heartbeat_if_due(self, daemon, session):
        key = self.heartbeat_key(daemon, session)
        if time.monotonic() >= self.heartbeat_due.get(key, 0):
            self.heartbeat(daemon, session)

    @contextlib.contextmanager
    def heartbeat_during(self, daemon, session):
        stop_event = threading.Event()
        heartbeat_error = []

        def worker():
            key = self.heartbeat_key(daemon, session)
            while True:
                delay = max(0, self.heartbeat_due.get(key, 0) - time.monotonic())
                if stop_event.wait(delay):
                    return
                try:
                    self.heartbeat_if_due(daemon, session)
                except BaseException as exc:
                    heartbeat_error.append(exc)
                    stop_event.set()
                    return

        thread = threading.Thread(target=worker, name="stability-heartbeat")
        thread.start()
        active_error = None
        try:
            yield
        except BaseException as exc:
            active_error = exc
            raise
        finally:
            stop_event.set()
            thread.join(timeout=20)
            stop_error = None
            if thread.is_alive():
                stop_error = AssertionError("stability heartbeat thread did not stop")
            elif heartbeat_error:
                source = heartbeat_error[0]
                stop_error = AssertionError(f"stability heartbeat failed: {type(source).__name__}: {source}")
            if stop_error is not None:
                if active_error is None:
                    raise stop_error
                active_error.add_note(str(stop_error))

    def run_idle(self, daemon, session):
        baseline = process_resources(daemon.proc.pid)
        samples = [{"elapsed_sec": 0, "resources": baseline}]
        phase = {"baseline": baseline, "samples": samples}
        self.metrics["phases"]["idle"] = phase
        started = time.monotonic()
        next_heartbeat = started
        while True:
            now = time.monotonic()
            elapsed = now - started
            if elapsed >= self.profile.idle_sec:
                break
            if now >= next_heartbeat:
                self.heartbeat(daemon, session)
                quiescent, resources = self.wait_quiescent(daemon.proc.pid, baseline)
                check(quiescent, "idle heartbeat request did not quiesce before resource sampling")
                samples.append({"elapsed_sec": round(elapsed, 3), "resources": resources})
                phase["resource_distributions"] = resource_distributions(
                    [item["resources"] for item in samples])
                self.flush()
                next_heartbeat = time.monotonic() + self.profile.heartbeat_sec
            time.sleep(min(.1, max(0, next_heartbeat - time.monotonic()), max(0, self.profile.idle_sec - elapsed)))
        self.heartbeat(daemon, session)
        quiescent, final = self.wait_quiescent(daemon.proc.pid, baseline)
        check(quiescent, "final idle heartbeat request did not quiesce before resource sampling")
        samples.append({"elapsed_sec": round(time.monotonic() - started, 3), "resources": final})
        phase["final"] = final
        phase["rss_growth_mib"] = round(final["rss_mib"] - baseline["rss_mib"], 3)
        phase["resource_distributions"] = resource_distributions(
            [item["resources"] for item in samples])

    def active_stop_worker(self, daemon, session, result):
        started = time.monotonic()
        try:
            code, response = request_json(
                daemon.discovery["origin"], "/api/bridge/await", {
                    "session_id": session["session_id"],
                    "consumer_id": "stability-a",
                    "timeout_sec": 120,
                }, daemon.discovery["management_token"], timeout=130)
            result.update({"http_status": code, "response": response})
        except Exception as exc:
            result["error"] = f"{type(exc).__name__}: {exc}"
        result["elapsed_ms"] = round((time.monotonic() - started) * 1000, 3)

    def run_active_stop(self, root):
        workdir = root / "active-stop"
        workdir.mkdir()
        daemon = Daemon(workdir)
        keepalive = None
        sse = None
        long_result = {}
        try:
            daemon.start()
            session = self.open_session(daemon)
            sse, _, sse_line = self.open_sse(daemon, session)
            parsed = urlsplit(daemon.discovery["origin"])
            keepalive = http.client.HTTPConnection(parsed.hostname, parsed.port, timeout=3)
            keepalive.request("GET", "/api/health", headers={
                "Authorization": "Bearer " + daemon.discovery["management_token"]})
            keepalive_response = keepalive.getresponse()
            keepalive_response.read()
            worker = threading.Thread(target=self.active_stop_worker, args=(daemon, session, long_result))
            worker.start()
            baseline = process_resources(daemon.proc.pid)
            deadline = time.monotonic() + 2
            active = baseline
            while time.monotonic() < deadline:
                active = process_resources(daemon.proc.pid)
                if ((active["thread_count"] or 0) >= (baseline["thread_count"] or 0) + 1):
                    break
                time.sleep(.01)
            before = checkpoint(daemon, "active-stop-before")
            stopped = daemon.stop()
            worker.join(timeout=STOP_WAIT_LIMIT_SEC)
            self.metrics["phases"]["active_stop"] = {
                "sse_first_line": sse_line.rstrip("\r\n"),
                "keepalive_status": keepalive_response.status,
                "long_poll": long_result,
                "long_poll_thread_alive": worker.is_alive(),
                "resources_before_stop": before,
                "stop": stopped,
            }
        finally:
            if sse:
                sse.close()
            if keepalive:
                keepalive.close()
            daemon.force_cleanup()

    def evaluate(self):
        checks = {}
        await_cases = self.metrics["phases"]["await"]["cases"]
        for timeout_sec, expected_count in self.profile.await_cases:
            case = await_cases[str(timeout_sec)]
            summary = case["distribution"]
            checks[f"PERF-04 await {timeout_sec}s sample count"] = summary["count"] == expected_count
            checks[f"PERF-04 await {timeout_sec}s p95"] = summary["p95_ms"] <= (timeout_sec + AWAIT_P95_SLACK_SEC) * 1000
            checks[f"PERF-04 await {timeout_sec}s max"] = summary["max_ms"] <= (timeout_sec + AWAIT_MAX_SLACK_SEC) * 1000
        cancel = self.metrics["phases"]["cancel"]
        checks["PERF-04 cancellation sample count"] = cancel["distribution"]["count"] == self.profile.cancel_count
        checks["PERF-04 cancellation p95 <=1s"] = cancel["distribution"]["p95_ms"] <= CANCEL_P95_LIMIT_MS
        checks["PERF-04 cancellation all reclaimed"] = all(item["reclaimed"] for item in cancel["samples"])
        cold = self.metrics["phases"]["cold_start"]
        checks["PERF-05 cold-start sample count"] = cold["distribution"]["count"] == self.profile.cold_start_count
        checks["PERF-05 authenticated-ready p95 <=3s"] = cold["distribution"]["p95_ms"] <= COLD_START_P95_LIMIT_MS
        connections = self.metrics["phases"]["connections"]
        tail = connections["last_20_or_all"]
        checks["PERF-06 connection sample count"] = len(connections["samples"]) == self.profile.connection_rounds
        checks["PERF-06 last20 FD growth <=5"] = tail["fd_max_growth"] <= STABLE_RESOURCE_GROWTH_LIMIT
        checks["PERF-06 last20 thread growth <=5"] = tail["thread_max_growth"] <= STABLE_RESOURCE_GROWTH_LIMIT
        checks["PERF-06 last20 child growth <=5"] = tail["child_max_growth"] <= STABLE_RESOURCE_GROWTH_LIMIT
        idle = self.metrics["phases"]["idle"]
        checks["PERF-06 idle duration reached"] = idle["samples"][-1]["elapsed_sec"] >= self.profile.idle_sec
        checks["PERF-06 idle RSS growth <=20MiB"] = idle["rss_growth_mib"] <= IDLE_RSS_GROWTH_LIMIT_MIB
        active = self.metrics["phases"]["active_stop"]
        stop = active["stop"]
        checks["stop under active SSE/keepalive/longpoll <=5s"] = stop["elapsed_ms"] <= STOP_ACCEPT_LIMIT_SEC * 1000
        checks["stop process exited cleanly"] = stop["returncode"] == 0 and stop["port_closed"]
        checks["stop reclaimed long-poll thread"] = not active["long_poll_thread_alive"]
        stop_records = [sample["stop"] for sample in cold["samples"]]
        stop_records.extend([self.metrics["phases"]["stability_stop"], stop])
        sqlite_records = [item["sqlite"] for item in self.metrics["checkpoints"]]
        sqlite_records.extend(sample["ready"]["sqlite"] for sample in cold["samples"])
        sqlite_records.extend(item["sqlite"] for item in stop_records)
        checks["authenticated port ready at every checkpoint"] = all(
            item["port"]["authenticated_ready"] for item in self.metrics["checkpoints"]
        ) and all(sample["ready"]["port"]["authenticated_ready"] for sample in cold["samples"])
        checks["all stopped ports closed"] = all(item["port_closed"] for item in stop_records)
        checks["SQLite quick_check always ok"] = all(
            item["quick_check"] == "ok" and item["error"] is None for item in sqlite_records)
        if self.profile.formal:
            checks["formal fixed profile unchanged"] = self.profile == FORMAL_PROFILE
        else:
            checks["quick report is not formal acceptance"] = not self.metrics["formal_acceptance"]
        self.metrics["checks"] = checks


def quick_profile(args):
    await_cases = ((1, args.quick_await_1), (args.quick_await_medium_sec, args.quick_await_medium_count),
                   (args.quick_await_long_sec, args.quick_await_long_count))
    return Profile(
        mode="quick",
        await_cases=await_cases,
        cancel_count=args.quick_cancel_count,
        cold_start_count=args.quick_cold_start_count,
        connection_rounds=args.quick_connection_rounds,
        connection_warmup_rounds=min(args.quick_connection_warmup_rounds, args.quick_connection_rounds),
        idle_sec=args.quick_idle_sec,
        heartbeat_sec=min(args.quick_heartbeat_sec, args.quick_idle_sec) if args.quick_idle_sec else args.quick_heartbeat_sec,
    )


def positive_int(value):
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be >= 1")
    return parsed


def positive_float(value):
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be > 0")
    return parsed


def parse_args():
    parser = argparse.ArgumentParser(
        description="Explicit long-running Bridge PERF-04/05/06 stability harness. No mode runs implicitly.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--formal", action="store_true", help="fixed acceptance counts; approximately 50-60 minutes")
    mode.add_argument("--quick", action="store_true", help="reduced development run; never reported as formal PASS")
    parser.add_argument("--quick-await-1", type=positive_int, default=3)
    parser.add_argument("--quick-await-medium-sec", type=positive_int, default=2)
    parser.add_argument("--quick-await-medium-count", type=positive_int, default=2)
    parser.add_argument("--quick-await-long-sec", type=positive_int, default=3)
    parser.add_argument("--quick-await-long-count", type=positive_int, default=1)
    parser.add_argument("--quick-cancel-count", type=positive_int, default=5)
    parser.add_argument("--quick-cold-start-count", type=positive_int, default=3)
    parser.add_argument("--quick-connection-rounds", type=positive_int, default=8)
    parser.add_argument("--quick-connection-warmup-rounds", type=positive_int, default=2)
    parser.add_argument("--quick-idle-sec", type=positive_float, default=3)
    parser.add_argument("--quick-heartbeat-sec", type=positive_float, default=.5)
    args = parser.parse_args()
    if args.formal:
        overrides = [value.split("=", 1)[0] for value in sys.argv[1:] if value.startswith("--quick-")]
        if overrides:
            parser.error("--formal has fixed acceptance counts; quick overrides are not allowed: " + ", ".join(overrides))
    for timeout in (args.quick_await_medium_sec, args.quick_await_long_sec):
        if timeout > 86400:
            parser.error("quick await timeout must remain within the production 1..86400 second contract")
    if args.quick and len({1, args.quick_await_medium_sec, args.quick_await_long_sec}) != 3:
        parser.error("quick await timeout buckets must be distinct")
    return args


def main():
    args = parse_args()
    profile = FORMAL_PROFILE if args.formal else quick_profile(args)
    harness = Harness(profile)
    try:
        state = harness.run()
    except BaseException as exc:
        harness.metrics["error"] = {
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }
        harness.flush("FAIL" if profile.formal else "DEVELOPMENT_FAIL")
        print(f"FAIL u_bridge_stability_check ({profile.mode}): {exc}", file=sys.stderr)
        return 1
    if profile.formal:
        print("PASS u_bridge_stability_check: formal PERF-04/05/06 fixed-sample acceptance")
    else:
        print("OK u_bridge_stability_check: reduced development run only; not formal acceptance")
    print(f"report: {RESULT_DIR / 'report.json'}")
    print(f"metrics: {RESULT_DIR / 'metrics.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
