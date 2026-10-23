#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import contextlib
import hashlib
import json
import math
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
EDIT = ROOT / "tools" / "edit.py"
BRIDGE_CORE = ROOT / "tools" / "bridge_core.py"
J_RENDER = ROOT / "skills" / "html-pptx" / "scripts" / "check-render.py"
CAPACITY = ROOT / "skills" / "html-pptx" / "scripts" / "check-capacity.py"
CHECK_IMAGES = ROOT / "skills" / "html-pptx" / "scripts" / "check-images.mjs"
EXTRACT = ROOT / "skills" / "html-pptx" / "scripts" / "extract-manifest.py"
FIXTURES = {
    "bake-mix": ROOT / "tests" / "decks" / "bake-mix",
    "cmb-retail": ROOT / "tests" / "decks" / "cmb-retail",
}
RESULT_DIR = ROOT / "tests" / "harness" / "results" / "bridge-p4"
BUNDLE_MAX = 2 * 1024 ** 3
BUNDLE_FILE_MAX = 20_000
INTERNAL_STORAGE_MAX = 10 * 1024 ** 3
MIN_FREE_BYTES = 512 * 1024 ** 2
LEASE_PROGRESS_INTERVAL_SEC = 30
LEASE_PROGRESS_REQUEST_TIMEOUT_SEC = 30
PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


class Blocked(RuntimeError):
    pass


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def utc_stamp():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def percentile(samples, fraction):
    ordered = sorted(samples)
    return ordered[max(0, math.ceil(fraction * len(ordered)) - 1)]


def distribution(samples):
    check(bool(samples), "empty metric sample")
    return {
        "count": len(samples),
        "p50_ms": round(percentile(samples, .50), 3),
        "p95_ms": round(percentile(samples, .95), 3),
        "max_ms": round(max(samples), 3),
        "samples_ms": [round(value, 3) for value in samples],
    }


def process_resources(pid):
    result = {"rss_mib": None, "fd_count": None, "thread_count": None}
    try:
        for line in Path(f"/proc/{pid}/status").read_text(encoding="utf-8").splitlines():
            if line.startswith("VmRSS:"):
                result["rss_mib"] = round(int(line.split()[1]) / 1024, 3)
            elif line.startswith("Threads:"):
                result["thread_count"] = int(line.split()[1])
        result["fd_count"] = len(list(Path(f"/proc/{pid}/fd").iterdir()))
    except (FileNotFoundError, PermissionError, ProcessLookupError):
        pass
    return result


def environment(path):
    usage = shutil.disk_usage(path)
    return {
        "platform": platform.platform(),
        "python": sys.version.splitlines()[0],
        "cpu_count": os.cpu_count(),
        "load_average": list(os.getloadavg()),
        "disk": {
            "total_bytes": usage.total,
            "used_bytes": usage.used,
            "free_bytes": usage.free,
        },
    }


def fixture_summary(root):
    root = Path(root)
    entries = []
    total = 0
    aggregate = hashlib.sha256()
    for path in sorted((p for p in root.rglob("*") if p.is_file()), key=lambda p: p.relative_to(root).as_posix().encode()):
        rel = path.relative_to(root).as_posix()
        digest = hashlib.sha256()
        size = 0
        with path.open("rb") as source:
            while True:
                chunk = source.read(1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
                size += len(chunk)
        total += size
        aggregate.update(rel.encode("utf-8") + b"\0" + str(size).encode() + b"\0" + digest.digest())
        entries.append({"path": rel, "bytes": size, "sha256": digest.hexdigest()})
    return {
        "path": str(root),
        "file_count": len(entries),
        "bytes": total,
        "aggregate_sha256": aggregate.hexdigest(),
        "files": entries,
    }


def compact_summary(summary):
    return {key: summary[key] for key in ("path", "file_count", "bytes", "aggregate_sha256")}


def assert_fixture_unchanged(before, after, name):
    check(before["file_count"] == after["file_count"], f"{name} fixture file count changed")
    check(before["bytes"] == after["bytes"], f"{name} fixture byte count changed")
    check(before["aggregate_sha256"] == after["aggregate_sha256"], f"{name} fixture bytes changed")


def copy_fixture(source, destination):
    shutil.copytree(source, destination, ignore=shutil.ignore_patterns("export", "prompts"))


def bridge_fixture_blockers(source):
    allowed = {
        "assets": {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg", ".wmf", ".emf"},
        "fonts": {".woff2", ".woff", ".ttf", ".otf"},
    }
    blockers = []
    for folder, extensions in allowed.items():
        root = Path(source) / folder
        if not root.is_dir():
            continue
        for path in sorted((item for item in root.rglob("*") if item.is_file())):
            if path.suffix.lower() not in extensions:
                blockers.append({
                    "path": path.relative_to(source).as_posix(),
                    "reason": "Bridge managed directory rejects this extension",
                })
    return blockers


def write_group_report(name, report):
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    report = {"schema_version": 1, "generated_at": utc_stamp(), **report}
    (RESULT_DIR / f"{name}.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def one_request(origin, path, body=None, bearer=None, origin_header=None, timeout=60):
    headers = {}
    data = None
    if bearer:
        headers["Authorization"] = "Bearer " + bearer
        if body is None:
            headers["Sec-Fetch-Site"] = "same-origin"
    if origin_header is not None:
        headers["Origin"] = origin_header
    if body is not None:
        data = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = Request(origin + path, data=data, headers=headers, method="POST" if body is not None else "GET")
    try:
        response = urlopen(request, timeout=timeout)
        raw = response.read()
        return response.status, json.loads(raw) if raw else {}
    except HTTPError as exc:
        return exc.code, json.loads(exc.read())


def static_get(origin, path):
    request = Request(origin + "/" + path.lstrip("/"), headers={"Sec-Fetch-Site": "same-origin"})
    with urlopen(request, timeout=30) as response:
        return response.read()


def managed_post(daemon, path, body, timeout=60):
    code, result = one_request(daemon.origin, path, body, daemon.management, timeout=timeout)
    check(code == 200 and result.get("ok"), f"management {path} failed: {code} {result}")
    return result


class IntentProgressLease:
    def __init__(self, daemon, session_id, intent_id, attempt, consumer_id, message):
        self.daemon = daemon
        self.body = {
            "session_id": session_id,
            "intent_id": intent_id,
            "attempt": attempt,
            "consumer_id": consumer_id,
            "action": "progress",
            "message": message,
        }
        self.stop_event = threading.Event()
        self.thread = None
        self.error = None

    def _progress(self):
        managed_post(
            self.daemon,
            "/api/bridge/update",
            self.body,
            timeout=LEASE_PROGRESS_REQUEST_TIMEOUT_SEC,
        )

    def _run(self):
        while not self.stop_event.wait(LEASE_PROGRESS_INTERVAL_SEC):
            try:
                self._progress()
            except BaseException as exc:
                self.error = exc
                self.stop_event.set()
                return

    def __enter__(self):
        self._progress()
        self.thread = threading.Thread(target=self._run, name=f"lease-{self.body['intent_id']}")
        self.thread.start()
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.stop_event.set()
        self.thread.join(timeout=LEASE_PROGRESS_REQUEST_TIMEOUT_SEC + 5)
        stop_error = None
        if self.thread.is_alive():
            stop_error = AssertionError("intent progress lease thread did not stop")
        elif self.error is not None:
            stop_error = AssertionError(f"intent progress lease failed: {type(self.error).__name__}: {self.error}")
        if stop_error is not None:
            if exc is None:
                raise stop_error
            exc.add_note(str(stop_error))
        return False


class Daemon:
    def __init__(self, workdir, allow_convert=False, startup_timeout=15, allow_imagegen=False):
        self.workdir = Path(workdir)
        self.allow_convert = allow_convert
        self.allow_imagegen = allow_imagegen
        self.startup_timeout = startup_timeout
        self.proc = None
        self.origin = None
        self.management = None

    def __enter__(self):
        command = [sys.executable, str(EDIT), str(self.workdir), "--daemon", "--port", "0"]
        if self.allow_convert:
            command.append("--convert")
        if self.allow_imagegen:
            command.append("--imagegen")
        self.proc = subprocess.Popen(
            command, cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        discovery_path = self.workdir / ".pptx-html" / "serve.json"
        deadline = time.monotonic() + self.startup_timeout
        while time.monotonic() < deadline:
            if self.proc.poll() is not None:
                raise AssertionError("bridge daemon exited: " + (self.proc.stderr.read() if self.proc.stderr else ""))
            if discovery_path.is_file():
                try:
                    discovery = json.loads(discovery_path.read_text(encoding="utf-8"))
                    code, health = one_request(discovery["origin"], "/api/health", bearer=discovery["management_token"])
                    if code == 200 and health.get("bridge_available"):
                        self.origin = discovery["origin"]
                        self.management = discovery["management_token"]
                        return self
                except (OSError, KeyError, json.JSONDecodeError):
                    pass
            time.sleep(.05)
        raise AssertionError("bridge daemon did not become ready")

    def __exit__(self, *_):
        if self.proc and self.proc.poll() is None and self.origin and self.management:
            with contextlib.suppress(Exception):
                one_request(self.origin, "/api/bridge/stop", {"reason": "cli-stop"}, self.management)
            with contextlib.suppress(subprocess.TimeoutExpired):
                self.proc.wait(timeout=10)
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            with contextlib.suppress(subprocess.TimeoutExpired):
                self.proc.wait(timeout=5)
        if self.proc and self.proc.poll() is None:
            self.proc.kill()
            self.proc.wait(timeout=5)


def browser_token(opened):
    return parse_qs(urlsplit(opened["url"]).fragment)["brt"][0]


def open_deck(daemon, deck_path, consumer):
    return managed_post(daemon, "/api/bridge/open", {
        "consumer_id": consumer,
        "deck_path": str(Path(deck_path).resolve()),
        "output_path": "index.html",
        "view": "edit",
        "open_browser": False,
    })


def submit_intent(daemon, token, opened, intent_type, payload):
    intent_id = str(uuid.uuid4())
    body = {
        "protocol_version": 2,
        "intent_id": intent_id,
        "session_id": opened["session_id"],
        "type": intent_type,
        "base_revision": opened["revision"],
        "payload": payload,
        "client_ts": "2026-10-03T00:00:00Z",
    }
    code, result = one_request(daemon.origin, "/api/intent", body, token, daemon.origin)
    check(code == 200 and result.get("accepted"), f"intent submit failed: {code} {result}")
    return intent_id


def run_command(argv, timeout=600):
    started = time.monotonic()
    run = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
    return run, (time.monotonic() - started) * 1000


def run_real_gates(work_path):
    work_path = Path(work_path)
    manifest_out = work_path.parent / ".p4-manifest-check.json"
    commands = [
        ("render", [sys.executable, str(J_RENDER), str(work_path)]),
        ("capacity", [sys.executable, str(CAPACITY), str(work_path), "--json", str(work_path.parent / "capacity-report.json")]),
        ("images", ["node", str(CHECK_IMAGES), str(work_path)]),
        ("manifest", [sys.executable, str(EXTRACT), str(work_path), "--out", str(manifest_out)]),
    ]
    checks = []
    metrics = []
    for name, argv in commands:
        run, elapsed = run_command(argv)
        metrics.append({
            "name": name,
            "argv": argv,
            "exit_code": run.returncode,
            "duration_ms": round(elapsed, 3),
            "stdout_tail": run.stdout[-1000:],
            "stderr_tail": run.stderr[-1000:],
        })
        check(run.returncode == 0, f"real {name} gate failed: {(run.stdout + run.stderr)[-1200:]}")
        checks.append({"name": name, "argv": argv, "exit_code": 0, "report_path": None})
    run, elapsed = run_command([sys.executable, str(BRIDGE_CORE), "revision", str(work_path)])
    candidate = run.stdout.strip()
    check(run.returncode == 0 and candidate.startswith("sha256:") and len(candidate) == 71,
          f"revision CLI failed: {run.stderr or candidate}")
    metrics.append({"name": "revision", "duration_ms": round(elapsed, 3), "exit_code": run.returncode})
    with contextlib.suppress(FileNotFoundError):
        manifest_out.unlink()
    return checks, candidate, metrics


def mutate_root_attribute(path, value, *, write=True):
    text = Path(path).read_text(encoding="utf-8")
    if "data-p4-seq=" in text:
        import re
        text = re.sub(r' data-p4-seq="[^"]*"', f' data-p4-seq="{value}"', text, count=1)
    else:
        text = text.replace("<html", f'<html data-p4-seq="{value}"', 1)
    if write:
        Path(path).write_text(text, encoding="utf-8")
    return text


def bind_browser_token(daemon, opened):
    token = browser_token(opened)
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
    code, result = one_request(daemon.origin, "/api/bridge/heartbeat", body, token, daemon.origin)
    check(code == 200 and result.get("client_id") == body["client_id"],
          f"browser token bind failed: {code} {result}")
    return token


def bind_and_wait_page(browser, opened, expected_slides, timeout=60000):
    context = browser.new_context(viewport={"width": 1440, "height": 900})
    page = context.new_page()
    telemetry = {"console": [], "page_errors": [], "request_failed": []}
    page.on("console", lambda message: telemetry["console"].append(f"{message.type}: {message.text}"))
    page.on("pageerror", lambda error: telemetry["page_errors"].append(str(error)))
    page.on("requestfailed", lambda request: telemetry["request_failed"].append({
        "url": request.url,
        "failure": request.failure,
    }))
    page.goto(opened["url"], wait_until="domcontentloaded", timeout=timeout)
    page.wait_for_function(
        "([rev,n]) => window.bridge && bridge.bound && state.loaded && bridge.loadedRevision === rev "
        "&& frame.contentDocument.querySelectorAll('.slide[data-slide-id]').length === n "
        "&& registry.some(x => x.kind === 'text')",
        arg=[opened["revision"], expected_slides], timeout=timeout)
    return context, page, telemetry


def page_bridge_diagnostics(page, telemetry):
    snapshot = page.evaluate("""() => ({
      state:{loaded:state.loaded,dirty:state.dirty,deckPath:state.deckPath},
      edit:{active:!!editEl,selected:!!selEl,annotationsPending:!!pendingAnno,annotationsUnexported:!!annoUnexported},
      bridge:{bound:bridge.bound,connected:bridge.connected,stopped:bridge.stopped,
        loadedRevision:bridge.loadedRevision,latestServerRevision:bridge.latestServerRevision,
        lastAppliedEventId:bridge.lastAppliedEventId,loadEpoch:bridge.loadEpoch,
        formDirty:bridge.formDirty,draftPending:bridge.draftPending,saveInFlight:bridge.saveInFlight,
        pendingAssetWrites:bridge.pendingAssetWrites,pendingRemoteChange:bridge.pendingRemoteChange,
        heartbeatInFlight:bridge.heartbeatInFlight,sseBackoff:bridge.sseBackoff,lastNotice:bridge.lastNotice,
        intentRisk:bridgeHasIntentRisk(),draftRisk:bridgeHasDraftRisk(),autoReloadRisk:bridgeAutoReloadRisk()},
      ui:{bridgeState:document.getElementById('bridgeState').textContent,
        bridgeNotice:document.getElementById('bridgeNotice').textContent,
        warningVisible:document.getElementById('warnBanner').classList.contains('show'),
        warningText:document.getElementById('warnText').textContent,
        tasks:document.getElementById('bridgeTasks').innerText}
    })""")
    snapshot["telemetry"] = {key: value[-30:] for key, value in telemetry.items()}
    return snapshot


def wait_for_editor_revision(daemon, page, telemetry, opened, revision, timeout=60000):
    try:
        page.wait_for_function("rev => bridge.loadedRevision === rev", arg=revision, timeout=timeout)
    except Exception as exc:
        status = managed_post(daemon, "/api/bridge/status", {"session_id": opened["session_id"]})
        diagnostics = page_bridge_diagnostics(page, telemetry)
        raise AssertionError(
            "editor did not apply revision " + revision + ": "
            + json.dumps({"page": diagnostics, "server": status}, ensure_ascii=False)
        ) from exc


def verify_editable(page):
    result = page.evaluate("""() => {
      const item = registry.find(x => x.kind === 'text' && x.el && x.el.isConnected);
      if (!item || editableTarget({target:item.el}) !== item.el) return {ok:false, registry:registry.length};
      enterEdit(item.el);
      const editable = item.el.contentEditable === 'plaintext-only' || item.el.contentEditable === 'true';
      commitEdit();
      return {ok:editable, registry:registry.length, slide:item.slideId};
    }""")
    check(result["ok"], f"loaded DOM is not editable: {result}")
    return result


def integration_fixture(name, browser):
    source = FIXTURES[name]
    if not (source / "index.html").is_file():
        raise Blocked(f"required real fixture missing: {source}")
    before = fixture_summary(source)
    with tempfile.TemporaryDirectory(prefix=f"bridge-p4-{name}-") as tmp:
        workdir = Path(tmp)
        deck_dir = workdir / name
        copy_fixture(source, deck_dir)
        deck = deck_dir / "index.html"
        expected_slides = 4 if name == "bake-mix" else 54
        with Daemon(workdir) as daemon:
            consumer = f"p4-{name}"
            opened = open_deck(daemon, deck, consumer)
            context, page, telemetry = bind_and_wait_page(browser, opened, expected_slides)
            try:
                token = browser_token(opened)
                timings = {}
                resources = {"baseline": process_resources(daemon.proc.pid)}
                checks = {"initial_editable": verify_editable(page)}
                initial_state = page_bridge_diagnostics(page, telemetry)
                checks["verify_editable_clean"] = not initial_state["bridge"]["autoReloadRisk"]
                check(checks["verify_editable_clean"],
                      "verify_editable introduced reload risk: " + json.dumps(initial_state, ensure_ascii=False))
                if name == "bake-mix":
                    intent_id = submit_intent(daemon, token, opened, "design.submitted", {
                        "version": 1, "kind": "design-intent", "deck": name,
                        "answers": {"p4": "source-layer deterministic edit"},
                    })
                    started = time.monotonic()
                    claimed = managed_post(daemon, "/api/bridge/await", {
                        "session_id": opened["session_id"], "consumer_id": consumer, "timeout_sec": 1})
                    timings["claim_ms"] = round((time.monotonic() - started) * 1000, 3)
                    check(claimed["intent_id"] == intent_id and Path(claimed["work_path"]) != deck,
                          f"bake-mix attempt isolation failed: {claimed}")
                    attempt = Path(claimed["work_path"])
                    html = attempt.read_text(encoding="utf-8")
                    check(html.count("整页烙入示例") >= 1, "bake-mix source-layer marker missing")
                    attempt.write_text(html.replace("整页烙入示例", "整页烙入示例 P4", 1), encoding="utf-8")
                    with IntentProgressLease(
                        daemon, opened["session_id"], intent_id, claimed["attempt"], consumer,
                        f"P4 {name} real gates running",
                    ):
                        validation, candidate, gate_metrics = run_real_gates(attempt)
                    started = time.monotonic()
                    completed = managed_post(daemon, "/api/bridge/update", {
                        "session_id": opened["session_id"], "intent_id": intent_id,
                        "attempt": claimed["attempt"], "consumer_id": consumer,
                        "action": "complete", "message": "P4 bake-mix real-gate publication",
                        "validation": {"candidate_revision": candidate, "checks": validation},
                    })
                    timings["publication_ms"] = round((time.monotonic() - started) * 1000, 3)
                    check(completed["status"] == "succeeded" and completed["revision"] == candidate, completed)
                    page.wait_for_function(
                        "rev => bridge.loadedRevision === rev && frame.contentDocument.documentElement.outerHTML.includes('整页烙入示例 P4')",
                        arg=candidate, timeout=30000)
                    checks["published_editable"] = verify_editable(page)
                    checks["http_reread_matches"] = static_get(daemon.origin, f"{name}/index.html") == deck.read_bytes()
                    check(checks["http_reread_matches"], "HTTP reread differs from published bake-mix")
                    record = {"gate_metrics": gate_metrics, "timings": timings, "checks": checks,
                              "revision": completed["revision"], "receipt_id": completed["receipt_id"]}
                else:
                    original = deck.read_text(encoding="utf-8")
                    saved_html = original.replace("<html", '<html data-p4-integration="saved"', 1)
                    started = time.monotonic()
                    code, saved = one_request(daemon.origin, "/api/save", {
                        "session_id": opened["session_id"], "path": f"{name}/index.html",
                        "html": saved_html, "base_revision": opened["revision"]}, token, daemon.origin, timeout=180)
                    timings["save_publication_ms"] = round((time.monotonic() - started) * 1000, 3)
                    check(code == 200 and saved.get("committed"), f"cmb save failed: {code} {saved}")
                    wait_for_editor_revision(daemon, page, telemetry, opened, saved["revision"])
                    checks["save_applied"] = True
                    stale_html = saved_html.replace('data-p4-integration="saved"', 'data-p4-integration="stale"', 1)
                    code, stale = one_request(daemon.origin, "/api/save", {
                        "session_id": opened["session_id"], "path": f"{name}/index.html",
                        "html": stale_html, "base_revision": opened["revision"]}, token, daemon.origin, timeout=180)
                    check(code == 409 and stale["error"]["code"] == "REVISION_CONFLICT", f"CAS stale save passed: {code} {stale}")
                    code, replay = one_request(daemon.origin, "/api/save", {
                        "session_id": opened["session_id"], "path": f"{name}/index.html",
                        "html": saved_html, "base_revision": opened["revision"]}, token, daemon.origin, timeout=180)
                    check(code == 200 and replay["receipt_id"] == saved["receipt_id"],
                          f"save receipt replay changed identity: {code} {replay}")
                    started = time.monotonic()
                    code, asset = one_request(daemon.origin, "/api/bridge/asset", {
                        "session_id": opened["session_id"], "path": "assets/p4-integration.png",
                        "data_base64": base64.b64encode(PNG_1X1).decode("ascii"),
                        "base_revision": saved["revision"]}, token, daemon.origin, timeout=180)
                    timings["asset_publication_ms"] = round((time.monotonic() - started) * 1000, 3)
                    check(code == 200 and asset.get("committed") and (deck_dir / "assets/p4-integration.png").is_file(),
                          f"asset publication failed: {code} {asset}")
                    wait_for_editor_revision(daemon, page, telemetry, opened, asset["revision"])
                    checks["asset_applied"] = True
                    opened = {**opened, "revision": asset["revision"]}
                    intent_id = submit_intent(daemon, token, opened, "design.submitted", {
                        "version": 1, "kind": "design-intent", "deck": name,
                        "answers": {"p4": "validation publication"},
                    })
                    started = time.monotonic()
                    claimed = managed_post(daemon, "/api/bridge/await", {
                        "session_id": opened["session_id"], "consumer_id": consumer, "timeout_sec": 1})
                    timings["attempt_copy_ms"] = round((time.monotonic() - started) * 1000, 3)
                    attempt = Path(claimed["work_path"])
                    mutate_root_attribute(attempt, "integration-complete")
                    with IntentProgressLease(
                        daemon, opened["session_id"], intent_id, claimed["attempt"], consumer,
                        f"P4 {name} real gates running",
                    ):
                        validation, candidate, gate_metrics = run_real_gates(attempt)
                    started = time.monotonic()
                    completed = managed_post(daemon, "/api/bridge/update", {
                        "session_id": opened["session_id"], "intent_id": intent_id,
                        "attempt": claimed["attempt"], "consumer_id": consumer,
                        "action": "complete", "message": "P4 cmb-retail real-gate publication",
                        "validation": {"candidate_revision": candidate, "checks": validation},
                    }, timeout=300)
                    timings["agent_publication_ms"] = round((time.monotonic() - started) * 1000, 3)
                    check(completed["status"] == "succeeded", completed)
                    wait_for_editor_revision(daemon, page, telemetry, opened, completed["revision"])
                    checks["published_editable"] = verify_editable(page)
                    checks["cas_rejected"] = True
                    checks["asset_registered"] = True
                    checks["http_reread_matches"] = static_get(daemon.origin, f"{name}/index.html") == deck.read_bytes()
                    check(checks["http_reread_matches"], "HTTP reread differs from published cmb-retail")

                    convert_opened = {**opened, "revision": completed["revision"]}
                    convert_id = submit_intent(daemon, token, convert_opened, "convert.requested", {
                        "formats": ["pptx", "vector", "pdf"], "scope": "all"})
                    convert_claim = managed_post(daemon, "/api/bridge/await", {
                        "session_id": opened["session_id"], "consumer_id": consumer, "timeout_sec": 1})
                    check(convert_claim["intent_id"] == convert_id, "convert interface claimed wrong intent")
                    export_dir = Path(convert_claim["work_path"]).parent / "export"
                    check(export_dir.is_dir() and not any(export_dir.iterdir()),
                          "convert attempt inherited stale export artifacts")
                    failed = managed_post(daemon, "/api/bridge/update", {
                        "session_id": opened["session_id"], "intent_id": convert_id,
                        "attempt": convert_claim["attempt"], "consumer_id": consumer,
                        "action": "fail", "message": "conversion intentionally delegated to explicit convert group"})
                    check(failed["status"] == "failed", failed)
                    status = managed_post(daemon, "/api/bridge/status", {"session_id": opened["session_id"]})
                    checks["dual_track_interface"] = {
                        "status": "SKIPPED_BY_GROUP",
                        "reason": "real 54-page conversion runs only under --group convert",
                        "capability": status["capabilities"]["local_convert"],
                        "stale_export_not_published": status["export_stale"],
                    }
                    check(status["export_stale"], "failed convert falsely marked export fresh")
                    record = {"gate_metrics": gate_metrics, "timings": timings, "checks": checks,
                              "revision": completed["revision"], "receipt_id": completed["receipt_id"]}
                resources["final"] = process_resources(daemon.proc.pid)
                record["resources"] = resources
                record["timing_distributions"] = {
                    key: distribution([value]) for key, value in timings.items()
                }
            finally:
                context.close()
    after = fixture_summary(source)
    assert_fixture_unchanged(before, after, name)
    return {**record, "fixture_before": compact_summary(before), "fixture_after": compact_summary(after)}


def integration_group():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise Blocked("Playwright is required for integration") from exc
    fixture_before = {name: fixture_summary(path) for name, path in FIXTURES.items()}
    blockers = {name: bridge_fixture_blockers(path) for name, path in FIXTURES.items()}
    cases = {}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            for name in ("bake-mix", "cmb-retail"):
                if blockers[name]:
                    cases[name] = {
                        "status": "BLOCKED",
                        "reason": "real fixture is rejected by the production managed-file allowlist",
                        "blockers": blockers[name],
                    }
                else:
                    cases[name] = {"status": "PASS", **integration_fixture(name, browser)}
        finally:
            browser.close()
    fixture_after = {name: fixture_summary(path) for name, path in FIXTURES.items()}
    for name in FIXTURES:
        assert_fixture_unchanged(fixture_before[name], fixture_after[name], name)
    blocked = [name for name, case in cases.items() if case["status"] == "BLOCKED"]
    report = {
        "status": "BLOCKED" if blocked else "PASS",
        "scope": "real fixture copies + real daemon/browser/attempt/gates/publication; conversion delegated to explicit group",
        "environment": environment(ROOT),
        "cases": cases,
        "fixture_before": {name: compact_summary(value) for name, value in fixture_before.items()},
        "fixture_after": {name: compact_summary(value) for name, value in fixture_after.items()},
    }
    write_group_report("integration", report)
    if blocked:
        raise Blocked("integration fixture rejected by production contract: " + ",".join(blocked))
    print("PASS integration: real bake-mix/cmb-retail Bridge orchestration, gates, CAS, asset, publication and editable UI")


def perf03_case(name, sample_count, browser):
    source = FIXTURES[name]
    before = fixture_summary(source)
    with tempfile.TemporaryDirectory(prefix=f"bridge-perf03-{name}-") as tmp:
        workdir = Path(tmp)
        deck_dir = workdir / name
        copy_fixture(source, deck_dir)
        deck = deck_dir / "index.html"
        slides = 4 if name == "bake-mix" else 54
        with Daemon(workdir) as daemon:
            opened = open_deck(daemon, deck, f"perf03-{name}")
            context, page, telemetry = bind_and_wait_page(browser, opened, slides, timeout=90000)
            try:
                initial = verify_editable(page)
                token = browser_token(opened)
                samples = []
                resources = {"baseline": process_resources(daemon.proc.pid)}
                revision = opened["revision"]
                for index in range(sample_count):
                    html = mutate_root_attribute(deck, f"{index:03d}", write=False)
                    started = time.monotonic()
                    code, saved = one_request(daemon.origin, "/api/save", {
                        "session_id": opened["session_id"], "path": f"{name}/index.html",
                        "html": html, "base_revision": revision}, token, daemon.origin, timeout=300)
                    check(code == 200 and saved.get("committed"), f"PERF-03 {name} save {index} failed: {code} {saved}")
                    revision = saved["revision"]
                    page.wait_for_function(
                        "([rev,n]) => bridge.loadedRevision === rev && state.loaded && registry.some(x => x.kind === 'text') "
                        "&& frame.contentDocument.querySelectorAll('.slide[data-slide-id]').length === n",
                        arg=[revision, slides], timeout=90000)
                    editable = verify_editable(page)
                    samples.append((time.monotonic() - started) * 1000)
                    check(editable["registry"] == initial["registry"],
                          f"PERF-03 {name} registry changed at sample {index}")
                resources["final"] = process_resources(daemon.proc.pid)
            finally:
                context.close()
    after = fixture_summary(source)
    assert_fixture_unchanged(before, after, name)
    metrics = distribution(samples)
    limit = 2000 if name == "bake-mix" else 5000
    return {
        "status": "PASS" if metrics["p95_ms"] <= limit else "FAIL",
        "threshold_ms": limit,
        "latency": metrics,
        "resources": resources,
        "slides": slides,
        "editable_probe": initial,
        "fixture_before": compact_summary(before),
        "fixture_after": compact_summary(after),
    }


def perf03_group():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise Blocked("Playwright is required for PERF-03") from exc
    blockers = {name: bridge_fixture_blockers(path) for name, path in FIXTURES.items()}
    cases = {}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            for name, count in (("bake-mix", 50), ("cmb-retail", 30)):
                if blockers[name]:
                    fixture_before = fixture_summary(FIXTURES[name])
                    fixture_after = fixture_summary(FIXTURES[name])
                    assert_fixture_unchanged(fixture_before, fixture_after, name)
                    cases[name] = {
                        "status": "BLOCKED",
                        "required_samples": count,
                        "completed_samples": 0,
                        "reason": "real fixture is rejected by the production managed-file allowlist",
                        "blockers": blockers[name],
                        "resources": {"status": "NOT_STARTED"},
                        "fixture_before": compact_summary(fixture_before),
                        "fixture_after": compact_summary(fixture_after),
                    }
                else:
                    cases[name] = perf03_case(name, count, browser)
        finally:
            browser.close()
    blocked = [name for name, case in cases.items() if case["status"] == "BLOCKED"]
    failed = [name for name, case in cases.items() if case["status"] == "FAIL"]
    report = {
        "status": "BLOCKED" if blocked else ("FAIL" if failed else "PASS"),
        "metric": "HTTP persisted save start through clean editor reload and successful enterEdit/commitEdit",
        "environment": environment(ROOT),
        "cases": cases,
    }
    write_group_report("perf03", report)
    if blocked:
        raise Blocked("PERF-03 fixed sample set incomplete: " + ",".join(blocked))
    check(not failed, "PERF-03 threshold failed; see results/bridge-p4/perf03.json")
    print("PASS perf03: bake-mix 50 and cmb-retail 30 persisted-event-to-editable samples")


def scale_payload_files(root):
    files = []
    for folder in ("assets", "fonts"):
        base = Path(root) / folder
        if base.is_dir():
            files.extend(path for path in base.rglob("*") if path.is_file())
    return sorted(files, key=lambda path: path.relative_to(root).as_posix().encode())


def scale_plan(source, multiplier=10):
    payload = scale_payload_files(source)
    payload_bytes = sum(path.stat().st_size for path in payload)
    base_files = 1 + len(payload)
    base_bytes = (Path(source) / "index.html").stat().st_size + payload_bytes
    added_files = len(payload) * (multiplier - 1)
    added_bytes = payload_bytes * (multiplier - 1)
    return {
        "multiplier": multiplier,
        "payload_file_count": len(payload),
        "payload_bytes": payload_bytes,
        "projected_bundle_file_count": base_files + added_files,
        "projected_bundle_bytes": base_bytes + added_bytes,
        "added_file_count": added_files,
        "added_bytes": added_bytes,
    }


def preflight_scale(plan, free_bytes, *, bundle_max=BUNDLE_MAX, file_max=BUNDLE_FILE_MAX,
                    reserve_bytes=MIN_FREE_BYTES, workspace_max=INTERNAL_STORAGE_MAX,
                    workspace_amplification=12):
    projected_workspace = plan["projected_bundle_bytes"] * workspace_amplification
    reasons = []
    if plan["projected_bundle_bytes"] > bundle_max:
        reasons.append("bundle_bytes")
    if plan["projected_bundle_file_count"] > file_max:
        reasons.append("bundle_files")
    if projected_workspace > workspace_max:
        reasons.append("internal_storage")
    if free_bytes - projected_workspace < reserve_bytes:
        reasons.append("disk_reserve")
    return {
        "accepted": not reasons,
        "reasons": reasons,
        "projected_workspace_bytes": projected_workspace,
        "free_bytes": free_bytes,
        "limits": {
            "bundle_max": bundle_max,
            "file_max": file_max,
            "reserve_bytes": reserve_bytes,
            "workspace_max": workspace_max,
            "workspace_amplification": workspace_amplification,
        },
    }


def injected_budget_checks(plan):
    projected = plan["projected_bundle_bytes"]
    files = plan["projected_bundle_file_count"]
    workspace = projected * 2
    reserve = 4096
    exact = preflight_scale(plan, workspace + reserve, bundle_max=projected,
                            file_max=files, reserve_bytes=reserve,
                            workspace_max=workspace, workspace_amplification=2)
    over_bytes = preflight_scale(plan, workspace + reserve, bundle_max=projected - 1,
                                 file_max=files, reserve_bytes=reserve,
                                 workspace_max=workspace, workspace_amplification=2)
    over_files = preflight_scale(plan, workspace + reserve, bundle_max=projected,
                                 file_max=files - 1, reserve_bytes=reserve,
                                 workspace_max=workspace, workspace_amplification=2)
    low_disk = preflight_scale(plan, workspace + reserve - 1, bundle_max=projected,
                               file_max=files, reserve_bytes=reserve,
                               workspace_max=workspace, workspace_amplification=2)
    check(exact["accepted"], f"injected exact boundary rejected: {exact}")
    check(over_bytes["reasons"] == ["bundle_bytes"], f"byte overflow not rejected before copy: {over_bytes}")
    check(over_files["reasons"] == ["bundle_files"], f"file overflow not rejected before copy: {over_files}")
    check(low_disk["reasons"] == ["disk_reserve"], f"disk reserve boundary not rejected: {low_disk}")
    return {"exact_boundary": exact, "over_bytes": over_bytes, "over_files": over_files, "low_disk": low_disk}


def clone_file(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        import fcntl
        with source.open("rb") as src, destination.open("xb") as dst:
            fcntl.ioctl(dst.fileno(), 0x40049409, src.fileno())
        shutil.copystat(source, destination)
    except (OSError, AttributeError):
        with contextlib.suppress(FileNotFoundError):
            destination.unlink()
        shutil.copy2(source, destination)


def build_scale_corpus(deck_dir, multiplier=10):
    originals = scale_payload_files(deck_dir)
    original_bytes = sum(path.stat().st_size for path in originals)
    started = time.monotonic()
    for copy_index in range(1, multiplier):
        for source in originals:
            rel = source.relative_to(deck_dir)
            destination = deck_dir / rel.parts[0] / ".p4-scale" / f"copy-{copy_index:02d}" / Path(*rel.parts[1:])
            clone_file(source, destination)
    elapsed = (time.monotonic() - started) * 1000
    scaled = scale_payload_files(deck_dir)
    check(len(scaled) == len(originals) * multiplier, "10x payload file count mismatch")
    check(sum(path.stat().st_size for path in scaled) == original_bytes * multiplier,
          "10x payload bytes mismatch")
    return elapsed


def cns08_group():
    source = FIXTURES["cmb-retail"]
    sample_count = 5
    if not (source / "index.html").is_file():
        raise Blocked(f"required real fixture missing: {source}")
    before = fixture_summary(source)
    plan = scale_plan(source, 10)
    boundary = injected_budget_checks(plan)
    initial_preflight = preflight_scale(plan, shutil.disk_usage(ROOT).free)
    blockers = bridge_fixture_blockers(source)
    report = {
        "status": "RUNNING",
        "environment": environment(ROOT),
        "fixture_before": compact_summary(before),
        "plan": plan,
        "required_samples": sample_count,
        "completed_samples": 0,
        "initial_preflight": initial_preflight,
        "injected_budget_checks": boundary,
        "fixture_contract_blockers": blockers,
    }
    write_group_report("cns08", report)
    if not initial_preflight["accepted"]:
        report.update({"status": "BLOCKED", "reason": "preflight rejected scale construction before any temporary copy"})
        write_group_report("cns08", report)
        raise Blocked("CNS-08 preflight rejected: " + ",".join(initial_preflight["reasons"]))
    if blockers:
        report.update({
            "status": "BLOCKED",
            "reason": "real cmb-retail is rejected by the production managed-file allowlist; no 10x copy was started",
            "fixture_after": compact_summary(fixture_summary(source)),
        })
        write_group_report("cns08", report)
        raise Blocked("CNS-08 fixture contract blocker: " + ",".join(item["path"] for item in blockers))

    metrics = {name: [] for name in (
        "fixture_copy", "scale_build", "hash", "open", "attempt_copy",
        "publication", "save", "rollback", "recovery",
    )}
    gate_samples = []
    resource_samples = []
    preflights = []
    actual_samples = []
    recovery_samples = []

    class ResourceMonitor:
        def __init__(self, daemon):
            self.daemon = daemon
            self.session_id = None
            self.stop_event = threading.Event()
            self.thread = threading.Thread(
                target=self._run, name="cns08-resource-monitor", daemon=True)
            self.samples = []
            self.status_probe_ms = []
            self.errors = []

        def _run(self):
            next_probe = 0.0
            while not self.stop_event.wait(.05):
                sample = process_resources(self.daemon.proc.pid)
                sample["monotonic"] = time.monotonic()
                self.samples.append(sample)
                now = time.monotonic()
                if self.session_id and now >= next_probe:
                    started = time.monotonic()
                    try:
                        code, result = one_request(
                            self.daemon.origin, "/api/bridge/status",
                            {"session_id": self.session_id}, self.daemon.management, timeout=30)
                        if code != 200 or not result.get("ok"):
                            self.errors.append(f"status {code}: {result}")
                        else:
                            self.status_probe_ms.append((time.monotonic() - started) * 1000)
                    except BaseException as exc:
                        self.errors.append(f"{type(exc).__name__}: {exc}")
                    next_probe = time.monotonic() + .2

        def start(self):
            self.samples.append({**process_resources(self.daemon.proc.pid), "monotonic": time.monotonic()})
            self.thread.start()

        def stop(self):
            self.stop_event.set()
            self.thread.join(timeout=35)
            check(not self.thread.is_alive(), "CNS-08 resource monitor did not stop")
            check(not self.errors, "CNS-08 status probe failed: " + "; ".join(self.errors))
            values = lambda key: [sample[key] for sample in self.samples if sample[key] is not None]
            rss = values("rss_mib")
            fds = values("fd_count")
            threads = values("thread_count")
            return {
                "sample_count": len(self.samples),
                "rss_mib": {"baseline": rss[0], "peak": max(rss), "final": rss[-1]} if rss else None,
                "fd_count": {"baseline": fds[0], "peak": max(fds), "final": fds[-1]} if fds else None,
                "thread_count": {"baseline": threads[0], "peak": max(threads), "final": threads[-1]} if threads else None,
                "sqlite_status_probe_latency": distribution(self.status_probe_ms),
                "sqlite_status_probe_note": "HTTP status latency while publication work runs; this is the harness lock-wait proxy, not SQLite engine timing",
            }

    def force_committed_recovery(workdir, receipt_id, target):
        transactions = Path(workdir) / ".pptx-html" / "transactions"
        match = None
        for path in transactions.glob("*.json"):
            data = json.loads(path.read_text(encoding="utf-8"))
            if data.get("receipt_id") == receipt_id:
                match = (path, data)
                break
        check(match is not None, f"CNS-08 recovery journal missing for receipt {receipt_id}")
        path, data = match
        check(data.get("stage") == "COMMITTED", f"CNS-08 journal is not committed: {data.get('stage')}")
        old_snapshot = Path(workdir) / ".pptx-html" / "snapshots" / data["old_snapshot_id"] / "bundle" / target.name
        check(old_snapshot.is_file(), f"CNS-08 old recovery snapshot missing: {old_snapshot}")
        shutil.copy2(old_snapshot, target)
        data["stage"] = "PREPARED"
        path.write_text(json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")), encoding="utf-8")
        return path, data["source_revision"]

    for sample_index in range(sample_count):
        sample_preflight = preflight_scale(plan, shutil.disk_usage(ROOT).free)
        preflights.append(sample_preflight)
        if not sample_preflight["accepted"]:
            report.update({
                "status": "BLOCKED",
                "completed_samples": sample_index,
                "reason": f"sample {sample_index + 1} preflight rejected before temporary copy",
                "sample_preflights": preflights,
                "fixture_after": compact_summary(fixture_summary(source)),
            })
            write_group_report("cns08", report)
            raise Blocked("CNS-08 sample preflight rejected: " + ",".join(sample_preflight["reasons"]))

        with tempfile.TemporaryDirectory(prefix=f"bridge-cns08-{sample_index + 1:02d}-") as tmp:
            workdir = Path(tmp)
            deck_dir = workdir / "cmb-retail"
            started = time.monotonic()
            copy_fixture(source, deck_dir)
            metrics["fixture_copy"].append((time.monotonic() - started) * 1000)
            metrics["scale_build"].append(build_scale_corpus(deck_dir, 10))
            deck = deck_dir / "index.html"
            actual_payload = scale_payload_files(deck_dir)
            actual = {
                "payload_file_count": len(actual_payload),
                "payload_bytes": sum(path.stat().st_size for path in actual_payload),
                "deck_bytes": deck.stat().st_size,
            }
            check(actual["payload_file_count"] == plan["payload_file_count"] * 10,
                  "CNS-08 actual files are not 10x")
            check(actual["payload_bytes"] == plan["payload_bytes"] * 10,
                  "CNS-08 actual bytes are not 10x")
            actual_samples.append(actual)

            run, elapsed = run_command(
                [sys.executable, str(BRIDGE_CORE), "revision", str(deck)], timeout=600)
            check(run.returncode == 0, f"CNS-08 revision failed: {run.stderr}")
            metrics["hash"].append(elapsed)

            with Daemon(workdir) as daemon:
                monitor = ResourceMonitor(daemon)
                monitor.start()
                started = time.monotonic()
                opened = open_deck(daemon, deck, f"cns08-{sample_index}")
                metrics["open"].append((time.monotonic() - started) * 1000)
                monitor.session_id = opened["session_id"]
                token = bind_browser_token(daemon, opened)
                consumer = f"cns08-{sample_index}"
                intent_id = submit_intent(daemon, token, opened, "design.submitted", {
                    "version": 1, "kind": "design-intent", "deck": "cmb-retail",
                    "answers": {"scale_sample": sample_index},
                })
                started = time.monotonic()
                claimed = managed_post(daemon, "/api/bridge/await", {
                    "session_id": opened["session_id"], "consumer_id": consumer,
                    "timeout_sec": 1,
                }, timeout=600)
                metrics["attempt_copy"].append((time.monotonic() - started) * 1000)
                attempt = Path(claimed["work_path"])
                check(claimed["intent_id"] == intent_id and attempt.is_file(),
                      "CNS-08 scaled attempt copy failed")
                mutate_root_attribute(attempt, f"cns08-publication-{sample_index}")
                with IntentProgressLease(
                    daemon, opened["session_id"], intent_id, claimed["attempt"], consumer,
                    f"CNS-08 sample {sample_index + 1} real gates running",
                ):
                    validation, candidate, gate_metrics = run_real_gates(attempt)
                gate_samples.append(gate_metrics)
                started = time.monotonic()
                completed = managed_post(daemon, "/api/bridge/update", {
                    "session_id": opened["session_id"], "intent_id": intent_id,
                    "attempt": claimed["attempt"], "consumer_id": consumer,
                    "action": "complete", "message": f"CNS-08 publication sample {sample_index + 1}",
                    "validation": {"candidate_revision": candidate, "checks": validation},
                }, timeout=900)
                metrics["publication"].append((time.monotonic() - started) * 1000)
                check(completed["status"] == "succeeded" and completed["revision"] == candidate,
                      f"CNS-08 publication failed: {completed}")

                saved_html = mutate_root_attribute(deck, f"cns08-save-{sample_index}", write=False)
                started = time.monotonic()
                code, saved = one_request(daemon.origin, "/api/save", {
                    "session_id": opened["session_id"], "path": "cmb-retail/index.html",
                    "html": saved_html, "base_revision": completed["revision"],
                }, token, daemon.origin, timeout=900)
                metrics["save"].append((time.monotonic() - started) * 1000)
                check(code == 200 and saved.get("committed"), f"CNS-08 save failed: {code} {saved}")

                started = time.monotonic()
                code, rolled = one_request(daemon.origin, "/api/rollback", {
                    "session_id": opened["session_id"], "path": "cmb-retail/index.html",
                    "hash": completed["snapshot_id"], "base_revision": saved["revision"],
                }, token, daemon.origin, timeout=900)
                metrics["rollback"].append((time.monotonic() - started) * 1000)
                check(code == 200 and rolled.get("committed") and rolled["revision"] == completed["revision"],
                      f"CNS-08 rollback failed: {code} {rolled}")
                status = managed_post(daemon, "/api/bridge/status", {"session_id": opened["session_id"]})
                check(status["revision"] == rolled["revision"], "CNS-08 status lost rollback revision")
                resource_samples.append(monitor.stop())
                session_id = opened["session_id"]
                rollback_receipt = rolled["receipt_id"]

            journal_path, expected_revision = force_committed_recovery(workdir, rollback_receipt, deck)
            started = time.monotonic()
            with Daemon(workdir, startup_timeout=900) as recovered_daemon:
                metrics["recovery"].append((time.monotonic() - started) * 1000)
                recovered = managed_post(
                    recovered_daemon, "/api/bridge/status", {"session_id": session_id}, timeout=600)
                check(recovered["revision"] == expected_revision == rolled["revision"],
                      f"CNS-08 recovery revision mismatch: {recovered}")
                journal = json.loads(journal_path.read_text(encoding="utf-8"))
                check(journal.get("stage") == "COMMITTED", "CNS-08 recovery did not finalize journal")
                recovery_samples.append({
                    "mode": "committed DB + pre-commit journal + old target bytes",
                    "revision": recovered["revision"],
                    "journal": journal_path.name,
                })

        report["completed_samples"] = sample_index + 1
        report["sample_preflights"] = preflights
        report["actual_samples"] = actual_samples
        report["partial_metrics"] = {
            name: distribution(values) for name, values in metrics.items() if values
        }
        report["partial_metrics_status"] = "MEASURED_NOT_FINAL"
        write_group_report("cns08", report)

    after = fixture_summary(source)
    assert_fixture_unchanged(before, after, "cmb-retail")
    report.update({
        "status": "PASS",
        "completed_samples": sample_count,
        "fixture_after": compact_summary(after),
        "metrics": {name: distribution(values) for name, values in metrics.items()},
        "gate_samples": gate_samples,
        "resources": resource_samples,
        "recovery_samples": recovery_samples,
        "limitations": [
            "sqlite_status_probe_latency is an HTTP status latency proxy observed during publication work, not an internal SQLite timer",
            "hardware power-loss durability and host-disk near-full behavior remain outside this non-destructive group",
        ],
    })
    report.pop("partial_metrics", None)
    report.pop("partial_metrics_status", None)
    write_group_report("cns08", report)
    print("PASS cns08: real 54-page 10x cmb-retail completed 5 hash/open/attempt/publication/save/rollback/recovery samples")


def convert_group():
    source = FIXTURES["cmb-retail"]
    if not (source / "index.html").is_file():
        raise Blocked(f"required real fixture missing: {source}")
    before = fixture_summary(source)
    blockers = bridge_fixture_blockers(source)
    if blockers:
        write_group_report("convert", {
            "status": "BLOCKED",
            "reason": "real cmb-retail is rejected by the production managed-file allowlist",
            "blockers": blockers,
            "fixture_before": compact_summary(before),
            "fixture_after": compact_summary(fixture_summary(source)),
        })
        raise Blocked("convert fixture contract blocker: " + ",".join(item["path"] for item in blockers))
    with tempfile.TemporaryDirectory(prefix="bridge-p4-convert-") as tmp:
        workdir = Path(tmp)
        deck_dir = workdir / "cmb-retail"
        copy_fixture(source, deck_dir)
        with Daemon(workdir, allow_convert=True) as daemon:
            opened = open_deck(daemon, deck_dir / "index.html", "p4-convert")
            started = time.monotonic()
            result = managed_post(daemon, "/api/convert", {
                "session_id": opened["session_id"], "formats": ["pptx", "vector", "pdf"]})
            check(result["started"], result)
            deadline = time.monotonic() + 1800
            status = None
            while time.monotonic() < deadline:
                code, status = one_request(
                    daemon.origin, f"/api/convert-status?session_id={opened['session_id']}",
                    bearer=daemon.management, timeout=30)
                check(code == 200, status)
                if status["status"] != "running":
                    break
                time.sleep(2)
            check(status and status["status"] == "done", f"real conversion failed or timed out: {status}")
            export = deck_dir / "export"
            required = [export / "deck.pptx", export / "deck-vector.pptx", export / "deck.pdf", export / "manifest.json"]
            check(all(path.is_file() for path in required), "dual-track export files incomplete")
            native = list((export / "native").glob("page-*.png"))
            check(len(native) >= 54, f"native preview pages incomplete: {len(native)}")
            final_status = managed_post(daemon, "/api/bridge/status", {"session_id": opened["session_id"]})
            check(not final_status["export_stale"], "completed conversion published stale export")
            duration = (time.monotonic() - started) * 1000
    after = fixture_summary(source)
    assert_fixture_unchanged(before, after, "cmb-retail")
    write_group_report("convert", {
        "status": "PASS",
        "duration": distribution([duration]),
        "native_pages": len(native),
        "fixture_before": compact_summary(before),
        "fixture_after": compact_summary(after),
        "environment": environment(ROOT),
    })
    print("PASS convert: real 54-page Bridge-triggered complete dual-track export")


def run_group(name):
    functions = {
        "integration": integration_group,
        "perf03": perf03_group,
        "cns08": cns08_group,
        "convert": convert_group,
    }
    path = RESULT_DIR / f"{name}.json"
    with contextlib.suppress(FileNotFoundError):
        path.unlink()
    try:
        functions[name]()
        return True
    except Blocked as exc:
        if not path.exists():
            write_group_report(name, {"status": "BLOCKED", "reason": str(exc), "environment": environment(ROOT)})
        print(f"BLOCKED {name}: {exc}", file=sys.stderr)
        return False
    except Exception as exc:
        existing = {}
        if path.exists():
            with contextlib.suppress(OSError, json.JSONDecodeError):
                existing = json.loads(path.read_text(encoding="utf-8"))
                existing.pop("schema_version", None)
                existing.pop("generated_at", None)
        write_group_report(name, {
            **existing,
            "status": "FAIL",
            "error": f"{type(exc).__name__}: {exc}",
            "environment": environment(ROOT),
        })
        print(f"FAIL {name}: {type(exc).__name__}: {exc}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(
        description="P4 real-deck Bridge integration, PERF-03 and CNS-08 scale harness")
    parser.add_argument("--group", action="append",
                        choices=["integration", "perf03", "cns08", "convert"],
                        help="select one or more groups; default is bounded integration only")
    args = parser.parse_args()
    groups = args.group or ["integration"]
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    summary = {
        "schema_version": 1,
        "generated_at": utc_stamp(),
        "selected_groups": groups,
        "results": {},
    }
    ok = True
    for name in groups:
        passed = run_group(name)
        summary["results"][name] = "PASS" if passed else "FAIL_OR_BLOCKED"
        ok = passed and ok
    (RESULT_DIR / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if ok:
        print("PASS s_bridge_scale_check selected groups: " + ",".join(groups))
        return 0
    print("RESULT: selected group failed or is BLOCKED; reports are under tests/harness/results/bridge-p4", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
