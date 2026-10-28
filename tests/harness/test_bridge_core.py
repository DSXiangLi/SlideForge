#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import http.client
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import uuid
from pathlib import Path
from unittest import mock
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from bridge_core import (  # noqa: E402
    ASSET_RAW_MAX, AWAIT_TIMEOUT_DEFAULT_SEC, AWAIT_TIMEOUT_MAX_SEC,
    AWAIT_TIMEOUT_MIN_SEC, BOOTSTRAP_TTL_SEC, BridgeCore, BridgeError,
    BridgeHTTPServer, CLIENT_ONLINE_SEC, CONSUMER_LEASE_SEC, CONTROL_BODY_MAX,
    DOCUMENT_BODY_MAX, INTENT_INLINE_MAX, INTENT_PAYLOAD_MAX,
    PROTOCOL_VERSION, revision_cli,
)


def golden_revision(root: Path, names):
    records = []
    for name in sorted(names, key=lambda x: x.encode("utf-8")):
        raw = (root / name).read_bytes()
        records.append([name, len(raw), hashlib.sha256(raw).hexdigest()])
    encoded = json.dumps(records, ensure_ascii=False, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(b"pptx-html-source-v1\n" + encoded).hexdigest()


class CoreCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="bridge-core-")
        self.root = Path(self.tmp.name)
        self.core = BridgeCore(self.root)
        self.core.origin = "http://127.0.0.1:9999"

    def tearDown(self):
        self.core.close()
        self.tmp.cleanup()

    def make_deck(self):
        (self.root / "assets").mkdir(exist_ok=True)
        (self.root / "fonts").mkdir(exist_ok=True)
        (self.root / "index.html").write_bytes(b"<!doctype html><title>A</title>")
        (self.root / "assets" / "a.png").write_bytes(b"\x89PNG\r\n\x1a\nA")
        (self.root / "fonts" / "a.woff2").write_bytes(b"font")

    def open(self, consumer="consumer-a"):
        self.make_deck()
        return self.core.open_editor(consumer, str(self.root / "index.html"), open_browser=False)

    def submit(self, opened, intent_id=None, payload=None):
        intent_id = intent_id or str(uuid.uuid4())
        payload = payload or {"formats": ["pptx"], "scope": "all"}
        return self.core.accept_intent(opened["session_id"], {
            "protocol_version": 2, "intent_id": intent_id,
            "session_id": opened["session_id"], "type": "convert.requested",
            "base_revision": opened["revision"], "payload": payload,
            "client_ts": "2026-10-02T00:00:00Z",
        })

    def test_constants_match_frozen_contract(self):
        self.assertEqual(PROTOCOL_VERSION, 2)
        self.assertEqual(CONTROL_BODY_MAX, 2 * 1024 * 1024)
        self.assertEqual(DOCUMENT_BODY_MAX, 64 * 1024 * 1024)
        self.assertEqual(INTENT_PAYLOAD_MAX, 1024 * 1024)
        self.assertEqual(INTENT_INLINE_MAX, 16 * 1024)
        self.assertEqual(ASSET_RAW_MAX, 32 * 1024 * 1024)
        self.assertEqual((CONSUMER_LEASE_SEC, CLIENT_ONLINE_SEC, BOOTSTRAP_TTL_SEC), (90, 45, 300))
        self.assertEqual((AWAIT_TIMEOUT_MIN_SEC, AWAIT_TIMEOUT_DEFAULT_SEC, AWAIT_TIMEOUT_MAX_SEC),
                         (1, 86400, 86400))

    def test_await_timeout_bounds_without_sleeping_a_day(self):
        opened = self.open()
        with self.assertRaises(BridgeError) as raised:
            self.core.await_intent(opened["session_id"], "consumer-a", 86401)
        self.assertEqual((raised.exception.status, raised.exception.code), (400, "INVALID_ARGUMENT"))
        self.submit(opened)
        claimed = self.core.await_intent(opened["session_id"], "consumer-a")
        self.assertEqual(claimed["kind"], "intent")

    def test_http_await_disconnect_cancels_wait_but_preserves_claim_state(self):
        opened = self.open()
        session_id = opened["session_id"]
        server = BridgeHTTPServer(("127.0.0.1", 0), self.core)
        self.core.origin = f"http://127.0.0.1:{server.server_address[1]}"
        server_thread = threading.Thread(
            target=server.serve_forever, kwargs={"poll_interval": .02}, daemon=True)
        server_thread.start()
        host, port = server.server_address

        def start_await():
            body = json.dumps({
                "session_id": session_id,
                "consumer_id": "consumer-a",
                "timeout_sec": 120,
            }, separators=(",", ":")).encode("utf-8")
            request = (
                f"POST /api/bridge/await HTTP/1.1\r\n"
                f"Host: {host}:{port}\r\n"
                f"Authorization: Bearer {self.core.management_token}\r\n"
                "Content-Type: application/json\r\n"
                f"Content-Length: {len(body)}\r\n"
                "Connection: keep-alive\r\n\r\n"
            ).encode("ascii") + body
            client = socket.create_connection((host, port), timeout=2)
            client.sendall(request)
            return client

        def active_count():
            with server._request_condition:
                return len(server._active_requests)

        try:
            empty_client = start_await()
            deadline = time.monotonic() + 2
            while time.monotonic() < deadline:
                row = self.core.db.execute(
                    "SELECT state FROM consumers WHERE session_id=? AND consumer_id=?",
                    (session_id, "consumer-a")).fetchone()
                if row and row["state"] == "waiting" and active_count() == 1:
                    break
                time.sleep(.01)
            self.assertEqual(row["state"], "waiting")
            closed_at = time.monotonic()
            empty_client.shutdown(socket.SHUT_RDWR)
            empty_client.close()
            deadline = closed_at + 1
            while time.monotonic() < deadline and active_count():
                time.sleep(.005)
            self.assertFalse(active_count(), "disconnected empty await handler was not reclaimed")
            self.assertLessEqual(time.monotonic() - closed_at, 1)
            session = self.core._session(session_id)
            consumer = self.core.db.execute(
                "SELECT state,requires_open,lease_until FROM consumers WHERE session_id=? AND consumer_id=?",
                (session_id, "consumer-a")).fetchone()
            self.assertEqual(session["owner_consumer_id"], "consumer-a")
            self.assertEqual((consumer["state"], consumer["requires_open"]), ("waiting", 0))
            self.assertIsNotNone(consumer["lease_until"])

            intent_id = str(uuid.uuid4())
            self.submit(opened, intent_id)
            claimed_client = start_await()
            deadline = time.monotonic() + 2
            while time.monotonic() < deadline:
                intent = self.core.db.execute(
                    "SELECT status,attempt FROM intents WHERE id=?", (intent_id,)).fetchone()
                if intent and intent["status"] == "processing":
                    break
                time.sleep(.005)
            self.assertEqual((intent["status"], intent["attempt"]), ("processing", 1))
            claimed_client.shutdown(socket.SHUT_RDWR)
            claimed_client.close()
            deadline = time.monotonic() + 1
            while time.monotonic() < deadline and active_count():
                time.sleep(.005)
            self.assertFalse(active_count(), "lost claim response handler was not reclaimed")
            replay = self.core.await_intent(session_id, "consumer-a", 1)
            self.assertEqual((replay["intent_id"], replay["attempt"]), (intent_id, 1))
            self.assertTrue(replay["redelivered"])
            self.assertEqual(self.core.db.execute(
                "SELECT status FROM intents WHERE id=?", (intent_id,)).fetchone()["status"], "processing")
        finally:
            server.shutdown()
            server_thread.join(timeout=5)
            server.server_close()

    def test_http_stop_reclaims_active_sse_keepalive_and_longpoll(self):
        opened = self.open()
        session_id = opened["session_id"]
        token = parse_qs(urlsplit(opened["url"]).fragment)["brt"][0]
        client_id = str(uuid.uuid4())
        self.core.heartbeat_browser(token, session_id, {
            "protocol_version": 2,
            "role": "browser",
            "session_id": session_id,
            "client_id": client_id,
            "dirty": False,
            "active_edit": False,
            "draft_pending": False,
            "revision": opened["revision"],
            "last_event_id": 0,
        })

        server = BridgeHTTPServer(("127.0.0.1", 0), self.core)
        self.core.origin = f"http://127.0.0.1:{server.server_address[1]}"
        server_stopped = threading.Event()

        def serve_until_stopped():
            try:
                server.serve_forever(poll_interval=.02)
            finally:
                server.server_close()
                server_stopped.set()

        server_thread = threading.Thread(target=serve_until_stopped, daemon=True)
        server_thread.start()
        host, port = server.server_address
        sse = keepalive = stop_connection = None
        long_result = {}

        def long_poll():
            connection = http.client.HTTPConnection(host, port, timeout=130)
            body = json.dumps({
                "session_id": session_id,
                "consumer_id": "consumer-a",
                "timeout_sec": 120,
            }).encode("utf-8")
            try:
                connection.request("POST", "/api/bridge/await", body=body, headers={
                    "Authorization": "Bearer " + self.core.management_token,
                    "Content-Type": "application/json",
                })
                response = connection.getresponse()
                long_result["status"] = response.status
                long_result["body"] = response.read()
            except Exception as exc:
                long_result["error"] = f"{type(exc).__name__}: {exc}"
            finally:
                connection.close()

        worker = threading.Thread(target=long_poll)
        try:
            sse = http.client.HTTPConnection(host, port, timeout=5)
            sse.request("GET", f"/api/events?session_id={session_id}&after=0", headers={
                "Authorization": "Bearer " + token,
                "Sec-Fetch-Site": "same-origin",
            })
            sse_response = sse.getresponse()
            self.assertEqual(sse_response.status, 200)
            self.assertEqual(sse_response.getheader("Connection"), "close")
            self.assertEqual(sse_response.readline().strip(), b": ping")

            keepalive = http.client.HTTPConnection(host, port, timeout=5)
            keepalive.request("GET", "/api/health", headers={
                "Authorization": "Bearer " + self.core.management_token,
            })
            keepalive_response = keepalive.getresponse()
            keepalive_response.read()
            self.assertEqual(keepalive_response.status, 200)

            worker.start()
            deadline = time.monotonic() + 2
            while time.monotonic() < deadline:
                with server._request_condition:
                    if len(server._active_requests) >= 3:
                        break
                time.sleep(.01)

            stop_connection = http.client.HTTPConnection(host, port, timeout=5)
            stop_body = b'{"reason":"cli-stop"}'
            started = time.monotonic()
            stop_connection.request("POST", "/api/bridge/stop", body=stop_body, headers={
                "Authorization": "Bearer " + self.core.management_token,
                "Content-Type": "application/json",
            })
            stop_response = stop_connection.getresponse()
            stop_payload = json.loads(stop_response.read())
            self.assertEqual(stop_response.status, 200)
            self.assertTrue(stop_payload["ok"])
            self.assertEqual(stop_response.getheader("Connection"), "close")
            exited = server_stopped.wait(5)
            elapsed = time.monotonic() - started
        finally:
            for connection in (sse, keepalive, stop_connection):
                if connection is not None:
                    connection.close()
            if server_thread.is_alive():
                server.shutdown()
            server_thread.join(timeout=5)
            if worker.ident is not None:
                worker.join(timeout=5)

        self.assertTrue(exited, "server did not actively reclaim open HTTP handlers")
        self.assertLessEqual(elapsed, 5)
        self.assertFalse(server_thread.is_alive())
        self.assertFalse(worker.is_alive())
        with server._request_condition:
            self.assertFalse(server._active_requests)
        self.assertNotIn("closed database", long_result.get("error", "").lower())

    def test_schema_wal_and_required_tables(self):
        names = {r[0] for r in self.core.db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        for name in {"sessions", "consumers", "bootstrap_tokens", "intents", "attempts",
                     "retry_receipts", "write_receipts", "events", "clients", "bundle_files",
                     "snapshots", "publications"}:
            self.assertIn(name, names)
        self.assertEqual(self.core.db.execute("PRAGMA journal_mode").fetchone()[0], "wal")
        self.assertEqual(self.core.db.execute("PRAGMA foreign_keys").fetchone()[0], 1)

    def test_source_revision_golden_raw_bytes(self):
        self.make_deck()
        session = self.core.register_session(deck_path=str(self.root / "index.html"))
        expected = golden_revision(self.root, ["assets/a.png", "fonts/a.woff2", "index.html"])
        self.assertEqual(session["revision"], expected)
        self.assertEqual(revision_cli(self.root / "index.html"), expected)
        (self.root / "assets" / "a.png").write_bytes(b"\x89PNG\r\n\x1a\nB")
        self.assertNotEqual(self.core.observe_revision(session["id"]), expected)

    def test_legacy_wmf_emf_are_preserved_but_never_statically_served(self):
        self.make_deck()
        legacy = {
            "assets/s20_03.wmf": b"\xd7\xcd\xc6\x9a\x00\x00legacy-wmf\x00\xff",
            "assets/vector.EMF": b"\x01\x00\x00\x00legacy-emf\x00\xfe",
        }
        for rel, raw in legacy.items():
            (self.root / rel).write_bytes(raw)
        opened = self.core.open_editor("consumer-a", str(self.root / "index.html"), open_browser=False)
        classes = {row["path"]: row["class"] for row in self.core.db.execute(
            "SELECT path,class FROM bundle_files WHERE session_id=?", (opened["session_id"],))}
        self.assertEqual({rel: classes[rel] for rel in legacy}, {rel: "source-legacy" for rel in legacy})
        self.assertEqual(opened["revision"], golden_revision(
            self.root, ["assets/a.png", *legacy, "fonts/a.woff2", "index.html"]))

        iid = str(uuid.uuid4())
        self.core.accept_intent(opened["session_id"], {
            "protocol_version": 2, "intent_id": iid, "session_id": opened["session_id"],
            "type": "design.submitted", "base_revision": opened["revision"],
            "payload": {"version": 1, "kind": "design-intent", "deck": "index.html", "answers": {}},
            "client_ts": "2026-10-03T00:00:00Z",
        })
        claimed = self.core.await_intent(opened["session_id"], "consumer-a", 1)
        work_path = Path(claimed["work_path"])
        for rel, raw in legacy.items():
            self.assertEqual((work_path.parent / rel).read_bytes(), raw)
        work_path.write_text("<!doctype html><title>legacy-published</title>", encoding="utf-8")
        candidate = revision_cli(work_path)
        validation = {"candidate_revision": candidate, "checks": [
            {"name": name, "argv": ["test", name], "exit_code": 0, "report_path": None}
            for name in ("render", "capacity", "images", "manifest")]}
        completed = self.core.push_update(
            opened["session_id"], iid, 1, "consumer-a", "complete", "done", validation)
        self.assertEqual(completed["revision"], candidate)
        for rel, raw in legacy.items():
            self.assertEqual((self.root / rel).read_bytes(), raw)
        snapshot_id = self.core.db.execute(
            "SELECT id FROM snapshots WHERE session_id=? AND action='agent-complete' ORDER BY created_at DESC LIMIT 1",
            (opened["session_id"],)).fetchone()[0]
        for rel, raw in legacy.items():
            self.assertEqual((self.root / ".pptx-html" / "snapshots" / snapshot_id / "bundle" / rel).read_bytes(), raw)

        server = BridgeHTTPServer(("127.0.0.1", 0), self.core)
        self.core.origin = f"http://127.0.0.1:{server.server_address[1]}"
        thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": .05}, daemon=True)
        thread.start()
        try:
            for rel in legacy:
                request = Request(self.core.origin + "/" + rel, headers={"Sec-Fetch-Site": "same-origin"})
                with self.assertRaises(HTTPError) as denied:
                    urlopen(request, timeout=5)
                self.assertEqual(denied.exception.code, 403)
                self.assertEqual(json.loads(denied.exception.read())["error"]["code"], "PATH_DENIED")
        finally:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()
        with self.assertRaises(BridgeError) as upload:
            self.core.asset(opened["session_id"], "assets/upload.wmf", "", completed["revision"])
        self.assertEqual(upload.exception.code, "PATH_DENIED")

    def test_open_registers_without_acquiring_and_close_requires_reopen(self):
        opened = self.open()
        self.assertEqual(opened["consumer_state"], "registered")
        self.assertEqual(opened["agent_state"], "offline")
        timeout = self.core.await_intent(opened["session_id"], "consumer-a", 1)
        self.assertEqual(timeout["kind"], "timeout")
        closed = self.core.close_consumer(opened["session_id"], "consumer-a")
        self.assertEqual(closed["consumer_state"], "paused")
        with self.assertRaises(BridgeError) as caught:
            self.core.await_intent(opened["session_id"], "consumer-a", 1)
        self.assertEqual(caught.exception.code, "RECOVERY_REQUIRED")
        reopened = self.core.open_editor("consumer-a", str(self.root / "index.html"), open_browser=False)
        self.assertEqual(reopened["session_id"], opened["session_id"])
        self.assertEqual(reopened["consumer_state"], "registered")

    def test_intent_uuid_idempotency_claim_redelivery_and_attempt_path(self):
        opened = self.open()
        iid = str(uuid.uuid4())
        first = self.submit(opened, iid)
        second = self.submit(opened, iid)
        self.assertEqual((first["seq"], first["status"]), (second["seq"], second["status"]))
        with self.assertRaises(BridgeError) as caught:
            self.submit(opened, iid, {"formats": ["pdf"], "scope": "all"})
        self.assertEqual(caught.exception.code, "IDEMPOTENCY_CONFLICT")
        claimed = self.core.await_intent(opened["session_id"], "consumer-a", 1)
        self.assertIn(f"jobs/{iid}/attempt-1/work/index.html", claimed["work_path"])
        Path(claimed["work_path"]).write_text("producer marker", encoding="utf-8")
        again = self.core.await_intent(opened["session_id"], "consumer-a", 1)
        self.assertTrue(again["redelivered"])
        self.assertEqual(Path(again["work_path"]).read_text(), "producer marker")

    def test_fail_retry_receipt_and_independent_attempt(self):
        opened = self.open()
        iid = str(uuid.uuid4())
        self.submit(opened, iid)
        claimed = self.core.await_intent(opened["session_id"], "consumer-a", 1)
        self.core.push_update(opened["session_id"], iid, 1, "consumer-a", "fail", "failed")
        retry_id = str(uuid.uuid4())
        body = {"session_id": opened["session_id"], "intent_id": iid,
                "retry_id": retry_id, "expected_attempt": 1, "mode": "rebuild",
                "base_revision": opened["revision"], "confirmed": True}
        one = self.core.retry_intent(opened["session_id"], body)
        two = self.core.retry_intent(opened["session_id"], body)
        self.assertEqual(one, two)
        self.assertEqual(one["attempt"], 2)
        next_claim = self.core.await_intent(opened["session_id"], "consumer-a", 1)
        self.assertIn("attempt-2", next_claim["work_path"])
        self.assertNotEqual(next_claim["work_path"], claimed["work_path"])
        self.assertTrue(Path(claimed["work_path"]).exists())

    def test_waiting_expiration_does_not_interrupt_intents(self):
        opened = self.open()
        sid = opened["session_id"]
        self.core.open_editor("consumer-b", str(self.root / "index.html"), open_browser=False)
        self.core.await_intent(sid, "consumer-a", 1)
        before = self.core.db.execute(
            "SELECT COUNT(*) FROM events WHERE session_id=? AND type='intent-status'", (sid,)).fetchone()[0]
        with self.core.db:
            self.core.db.execute(
                "UPDATE consumers SET lease_until='2000-01-01T00:00:00.000Z' WHERE session_id=? AND consumer_id='consumer-a'",
                (sid,))
        timeout = self.core.await_intent(sid, "consumer-b", 1)
        self.assertEqual(timeout["kind"], "timeout")
        self.assertEqual(self.core._session(sid)["owner_consumer_id"], "consumer-b")
        after = self.core.db.execute(
            "SELECT COUNT(*) FROM events WHERE session_id=? AND type='intent-status'", (sid,)).fetchone()[0]
        self.assertEqual(after, before)

    def test_processing_owner_survives_stale_telemetry_and_blocks_second_owner(self):
        opened = self.open()
        sid = opened["session_id"]
        iid = str(uuid.uuid4())
        self.submit(opened, iid)
        claimed = self.core.await_intent(sid, "consumer-a", 1)
        self.core.open_editor("consumer-b", str(self.root / "index.html"), open_browser=False)
        with self.core.db:
            self.core.db.execute("UPDATE consumers SET lease_until='2000-01-01T00:00:00.000Z' WHERE session_id=? AND consumer_id='consumer-a'", (sid,))
            self.core.db.execute("UPDATE intents SET lease_until='2000-01-01T00:00:00.000Z' WHERE id=?", (iid,))
        with self.assertRaises(BridgeError) as busy:
            self.core.await_intent(sid, "consumer-b", 1)
        self.assertEqual(busy.exception.code, "SESSION_BUSY")
        heartbeat = self.core.heartbeat_consumer(sid, "consumer-a")
        self.assertEqual(heartbeat["agent_state"], "working")
        progress = self.core.push_update(sid, iid, claimed["attempt"], "consumer-a", "progress", "late owner is alive")
        self.assertEqual(progress["status"], "processing")
        self.assertEqual(self.core.get_status(sid)["processing"]["id"], iid)
        failed = self.core.push_update(sid, iid, claimed["attempt"], "consumer-a", "fail", "late owner failed")
        self.assertEqual(failed["status"], "failed")

    def test_processing_owner_can_complete_after_stale_telemetry(self):
        opened = self.open()
        sid = opened["session_id"]
        iid = str(uuid.uuid4())
        self.core.accept_intent(sid, {
            "protocol_version": 2, "intent_id": iid, "session_id": sid,
            "type": "brief.submitted", "base_revision": opened["revision"],
            "payload": {"text": "late complete", "json": {"kind": "design-brief"}},
            "client_ts": "2026-10-04T00:00:00Z",
        })
        claimed = self.core.await_intent(sid, "consumer-a", 1)
        work_path = Path(claimed["work_path"])
        work_path.write_text("<!doctype html><title>late complete</title>", encoding="utf-8")
        with self.core.db:
            self.core.db.execute("UPDATE consumers SET lease_until='2000-01-01T00:00:00.000Z' WHERE session_id=? AND consumer_id='consumer-a'", (sid,))
            self.core.db.execute("UPDATE intents SET lease_until='2000-01-01T00:00:00.000Z' WHERE id=?", (iid,))
        candidate = revision_cli(work_path)
        validation = {"candidate_revision": candidate, "checks": [
            {"name": name, "argv": ["test", name], "exit_code": 0, "report_path": None}
            for name in ("render", "capacity", "images", "manifest")]}
        completed = self.core.push_update(sid, iid, 1, "consumer-a", "complete", "late complete", validation)
        self.assertEqual(completed["status"], "succeeded")
        self.assertEqual(self.core.get_status(sid)["revision"], candidate)

    def test_resume_reuses_registered_work_path_with_new_attempt_fence(self):
        opened = self.open()
        sid = opened["session_id"]
        iid = str(uuid.uuid4())
        self.submit(opened, iid)
        claimed = self.core.await_intent(sid, "consumer-a", 1)
        work_path = Path(claimed["work_path"])
        work_path.write_text("<!doctype html><title>resume marker</title>", encoding="utf-8")
        self.core.close_consumer(sid, "consumer-a", "explicit close")
        self.core.open_editor("consumer-a", str(self.root / "index.html"), open_browser=False)
        retry = self.core.retry_intent(sid, {
            "session_id": sid, "intent_id": iid, "retry_id": str(uuid.uuid4()),
            "expected_attempt": 1, "mode": "resume", "base_revision": opened["revision"],
            "confirmed": True,
        })
        self.assertTrue(retry["reused_work_path"])
        self.assertEqual(retry["attempt"], 2)
        resumed = self.core.await_intent(sid, "consumer-a", 1)
        self.assertEqual(resumed["work_path"], str(work_path))
        self.assertTrue(resumed["resumed"])
        self.assertIn("resume marker", work_path.read_text(encoding="utf-8"))
        with self.assertRaises(BridgeError) as stale:
            self.core.push_update(sid, iid, 1, "consumer-a", "progress", "old producer")
        self.assertEqual(stale.exception.code, "RECOVERY_REQUIRED")
        self.core.push_update(sid, iid, 2, "consumer-a", "fail", "new attempt fenced")

    def test_concurrent_old_attempt_updates_cannot_override_resumed_owner(self):
        opened = self.open()
        sid = opened["session_id"]
        iid = str(uuid.uuid4())
        self.submit(opened, iid)
        claimed = self.core.await_intent(sid, "consumer-a", 1)
        Path(claimed["work_path"]).write_text("<!doctype html><title>resume race</title>", encoding="utf-8")
        started = {action: threading.Event() for action in ("progress", "fail", "complete")}
        outcomes = {}

        def late_update(action):
            started[action].set()
            try:
                self.core.push_update(sid, iid, 1, "consumer-a", action, "stale " + action)
            except BridgeError as exc:
                outcomes[action] = exc.code
            else:
                outcomes[action] = "unexpected-success"

        lock = self.core._session_lock(sid)
        with lock:
            workers = [threading.Thread(target=late_update, args=(action,)) for action in started]
            for worker in workers:
                worker.start()
            for signal in started.values():
                self.assertTrue(signal.wait(1))
            self.assertTrue(all(worker.is_alive() for worker in workers))
            self.core.cancel_intent(sid, iid)
            retry = self.core.retry_intent(sid, {
                "session_id": sid, "intent_id": iid, "retry_id": str(uuid.uuid4()),
                "expected_attempt": 1, "mode": "resume", "base_revision": opened["revision"],
                "confirmed": True,
            })
            self.assertEqual(retry["attempt"], 2)
            self.core.await_intent(sid, "consumer-a", 1)
        for worker in workers:
            worker.join(2)
            self.assertFalse(worker.is_alive())
        self.assertEqual(outcomes, {"progress": "RECOVERY_REQUIRED", "fail": "RECOVERY_REQUIRED", "complete": "RECOVERY_REQUIRED"})
        current = self.core.db.execute(
            "SELECT status,attempt,consumer_id FROM intents WHERE id=?", (iid,)).fetchone()
        self.assertEqual((current["status"], current["attempt"], current["consumer_id"]),
                         ("processing", 2, "consumer-a"))
        self.assertEqual(self.core._session(sid)["owner_consumer_id"], "consumer-a")
        self.assertEqual(self.core.db.execute(
            "SELECT state FROM consumers WHERE session_id=? AND consumer_id='consumer-a'", (sid,)).fetchone()[0],
            "working")
        self.core.push_update(sid, iid, 2, "consumer-a", "fail", "cleanup current attempt")

    def test_processing_cancel_interrupts_releases_owner_and_warns_external_work(self):
        opened = self.open()
        sid = opened["session_id"]
        iid = str(uuid.uuid4())
        self.submit(opened, iid)
        self.core.await_intent(sid, "consumer-a", 1)
        stopped = self.core.cancel_intent(sid, iid)
        self.assertEqual(stopped["status"], "interrupted")
        self.assertTrue(stopped["external_work_may_continue"])
        self.assertIsNone(self.core._session(sid)["owner_consumer_id"])
        attempt = self.core.db.execute(
            "SELECT status FROM attempts WHERE intent_id=? AND attempt=1", (iid,)).fetchone()[0]
        self.assertEqual(attempt, "interrupted")
        # P4.1（2026-10-27）：对 interrupted 再取消 = 放弃（此前是 no-op，被中断的请求
        # 既不能取消、也无法让状态机前进）。
        repeated = self.core.cancel_intent(sid, iid)
        self.assertEqual(repeated["status"], "cancelled")
        self.assertTrue(repeated["external_work_may_continue"])
        self.assertEqual(self.core.db.execute(
            "SELECT status FROM attempts WHERE intent_id=? AND attempt=1", (iid,)).fetchone()[0],
            "cancelled")
        events = self.core.db.execute(
            "SELECT data_json FROM events WHERE session_id=? AND type='intent-status' ORDER BY id",
            (sid,)).fetchall()
        self.assertEqual([json.loads(event[0])["status"] for event in events],
                         ["pending", "processing", "interrupted", "cancelled"])

    def test_per_intent_gate_lets_an_interrupted_intent_stop_blocking_the_queue(self):
        """P4.3：一条卡住的 interrupted 请求不再锁死同会话的其它请求。"""
        opened = self.open()
        sid = opened["session_id"]
        blocked = str(uuid.uuid4())
        self.submit(opened, blocked)
        self.core.await_intent(sid, "consumer-a", 1)
        self.core.cancel_intent(sid, blocked)          # processing → interrupted
        self.assertEqual(self.core.db.execute(
            "SELECT status FROM intents WHERE id=?", (blocked,)).fetchone()[0], "interrupted")
        self.assertEqual(self.core.agent_state(sid), "recovering")
        # 旧实现会在 _acquire_owner 对**整个会话**抛 RECOVERY_REQUIRED；现在新请求可被认领。
        fresh = str(uuid.uuid4())
        self.submit(opened, fresh)
        claimed = self.core.await_intent(sid, "consumer-a", 1)
        self.assertEqual(claimed["intent_id"], fresh)
        self.assertEqual(self.core.agent_state(sid), "working")

    def test_stale_interrupted_intent_is_auto_cancelled_before_claim(self):
        """P4.2：无 lease 且超过宽限期的 interrupted 请求由 daemon 自动作废（并发事件）。"""
        opened = self.open()
        sid = opened["session_id"]
        stale = str(uuid.uuid4())
        self.submit(opened, stale)
        self.core.await_intent(sid, "consumer-a", 1)
        self.core.cancel_intent(sid, stale)            # → interrupted
        self.core.db.execute("UPDATE intents SET updated_at=? WHERE id=?",
                             ("2000-01-01T00:00:00.000Z", stale))
        self.core.db.commit()
        healed = self.core._heal_stale_recoverables(sid)
        self.assertEqual(healed, 1)
        self.assertEqual(self.core.db.execute(
            "SELECT status FROM intents WHERE id=?", (stale,)).fetchone()[0], "cancelled")
        self.assertEqual(self.core.agent_state(sid), "offline")
        # 持久投影 sessions.agent_state 也必须同步刷新（不能停在 recovering）
        self.assertEqual(self.core.db.execute(
            "SELECT agent_state FROM sessions WHERE id=?", (sid,)).fetchone()[0], "offline")
        events = [json.loads(row[0]) for row in self.core.db.execute(
            "SELECT data_json FROM events WHERE session_id=? AND type='intent-status' ORDER BY id", (sid,))]
        self.assertEqual(events[-1]["intent_id"], stale)
        self.assertEqual(events[-1]["status"], "cancelled")
        # 对照组：宽限期内的 interrupted 不会被误伤。
        fresh = str(uuid.uuid4())
        self.submit(opened, fresh)
        self.core.await_intent(sid, "consumer-a", 1)
        self.core.cancel_intent(sid, fresh)
        self.assertEqual(self.core._heal_stale_recoverables(sid), 0)
        self.assertEqual(self.core.db.execute(
            "SELECT status FROM intents WHERE id=?", (fresh,)).fetchone()[0], "interrupted")

    def test_stale_conflict_intent_is_not_self_healed(self):
        """P4.2 边界：conflict 必须由用户在页面上决定，不在自愈范围。"""
        opened = self.open()
        sid = opened["session_id"]
        iid = str(uuid.uuid4())
        self.submit(opened, iid)
        self.bump_revision(opened)                     # 让 base_revision 过期
        with self.assertRaises(BridgeError) as caught:
            self.core.await_intent(sid, "consumer-a", 1)
        self.assertEqual(caught.exception.code, "RECOVERY_REQUIRED")
        self.assertEqual(self.core.db.execute(
            "SELECT status FROM intents WHERE id=?", (iid,)).fetchone()[0], "conflict")
        self.core.db.execute("UPDATE intents SET updated_at=? WHERE id=?",
                             ("2000-01-01T00:00:00.000Z", iid))
        self.core.db.commit()
        self.assertEqual(self.core._heal_stale_recoverables(sid), 0)
        self.assertEqual(self.core.db.execute(
            "SELECT status FROM intents WHERE id=?", (iid,)).fetchone()[0], "conflict")

    def test_get_status_exposes_intent_summary_for_track_a(self):
        """R3-a：轨 A 没有 query 通道，状态必须带轻量意图摘要（含小载荷）供页面展示。"""
        opened = self.open()
        sid = opened["session_id"]
        iid = str(uuid.uuid4())
        self.submit(opened, iid)
        st = self.core.get_status(sid)
        self.assertIn("intents", st)
        row = [x for x in st["intents"] if x["id"] == iid][0]
        self.assertEqual((row["status"], row["seq"], row["type"]),
                         ("pending", 1, "convert.requested"))
        self.assertEqual(row["payload"], {"formats": ["pptx"], "scope": "all"})
        # recoverable 也出现在摘要里（页面据此给"重新提交"入口）
        self.core.await_intent(sid, "consumer-a", 1)
        self.core.cancel_intent(sid, iid)
        st2 = self.core.get_status(sid)
        self.assertEqual([x["status"] for x in st2["intents"] if x["id"] == iid], ["interrupted"])

    def test_new_view_client_discards_previous_unfinished_requests(self):
        """**新 View client attach**（= 用户重开页面）才丢弃先前排队的请求；
        同一 client 的重复上报（轮询期）不丢弃；processing 不动。
        `interrupted` 的保留由既有 resume 测试保护。"""
        opened = self.open()
        sid = opened["session_id"]
        self.core.attach_view(sid, "page-1")                     # 首次挂载：prev 为空 → 不丢弃
        running_id = str(uuid.uuid4())
        self.submit(opened, running_id, {"formats": ["pdf"], "scope": "all"})
        self.core.await_intent(sid, "consumer-a", 1)             # → processing
        queued_id = str(uuid.uuid4())
        self.submit(opened, queued_id)                           # → pending
        # 同一页面轮询期重复上报：**不该**丢弃
        same = self.core.attach_view(sid, "page-1")
        self.assertEqual(same["discarded"], [])
        self.assertEqual(self.core.db.execute(
            "SELECT status FROM intents WHERE id=?", (queued_id,)).fetchone()[0], "pending")
        # 新 client = 用户重新打开了编辑器 → 丢弃排队中的，保留 processing
        reopened = self.core.attach_view(sid, "page-2")
        after = {r["id"]: r["status"] for r in self.core.db.execute(
            "SELECT id,status FROM intents WHERE session_id=?", (sid,))}
        self.assertEqual(after[queued_id], "cancelled", "重开页面应丢弃还在排队的旧请求")
        self.assertEqual(after[running_id], "processing", "重开页面不得动正在处理中的请求")
        self.assertEqual([d["seq"] for d in reopened["discarded"]], [2])
        event = self.core.db.execute(
            "SELECT data_json FROM events WHERE session_id=? AND type='notice' ORDER BY id DESC LIMIT 1",
            (sid,)).fetchone()
        self.assertEqual(json.loads(event[0])["kind"], "reopen-discard")

    def test_duplicate_request_is_deduplicated(self):
        """同一 (type, payload, base) 的未终结请求不重复入队；换基线或换载荷算新请求。"""
        opened = self.open()
        sid = opened["session_id"]
        first = self.submit(opened, str(uuid.uuid4()))
        second = self.submit(opened, str(uuid.uuid4()))
        self.assertTrue(second.get("deduplicated"), "同载荷同基线应被去重")
        self.assertEqual(second["seq"], first["seq"])
        third = self.submit(opened, str(uuid.uuid4()), {"formats": ["pdf"], "scope": "all"})
        self.assertFalse(third.get("deduplicated"), "不同载荷必须是新请求")
        self.assertNotEqual(third["seq"], first["seq"])
        self.assertEqual(self.core.db.execute(
            "SELECT COUNT(*) FROM intents WHERE session_id=?", (sid,)).fetchone()[0], 2)

    def test_intent_state_transitions_persist_events_and_notify_waiters(self):
        opened = self.open()
        sid = opened["session_id"]
        iid = str(uuid.uuid4())
        with mock.patch.object(self.core, "_notify", wraps=self.core._notify) as notified:
            self.submit(opened, iid)
            self.core.await_intent(sid, "consumer-a", 1)
            self.core.cancel_intent(sid, iid)
            self.core.retry_intent(sid, {
                "session_id": sid, "intent_id": iid, "retry_id": str(uuid.uuid4()),
                "expected_attempt": 1, "mode": "rebuild", "base_revision": opened["revision"],
                "confirmed": True,
            })
        statuses = [json.loads(row[0])["status"] for row in self.core.db.execute(
            "SELECT data_json FROM events WHERE session_id=? AND type='intent-status' ORDER BY id", (sid,))]
        self.assertEqual(statuses, ["pending", "processing", "interrupted", "pending"])
        self.assertGreaterEqual(notified.call_count, 4)

    def test_convert_claim_clears_inherited_export_and_records_baseline(self):
        self.make_deck();export=self.root/"export";native=export/"native";native.mkdir(parents=True)
        for rel,data in [("deck.pptx",b"old-editable"),("deck-vector.pptx",b"old-vector"),("deck.pdf",b"old-pdf"),("manifest.json",b"{}")]:
            (export/rel).write_bytes(data)
        (native/"page-01.png").write_bytes(b"old-native")
        opened=self.core.open_editor("consumer-a",str(self.root/"index.html"),open_browser=False);iid=str(uuid.uuid4());self.submit(opened,iid)
        claimed=self.core.await_intent(opened["session_id"],"consumer-a",1);work_export=Path(claimed["work_path"]).parent/"export"
        self.assertTrue(work_export.is_dir());self.assertEqual(list(work_export.iterdir()),[])
        baseline=json.loads(self.core.db.execute("SELECT export_baseline_json FROM attempts WHERE intent_id=?",(iid,)).fetchone()[0])
        self.assertGreaterEqual(len(baseline),5)

    def test_export_validation_uses_producer_tracks_ok_contract(self):
        self.make_deck();work_path=self.root/"index.html";export=self.root/"export";native=export/"native"
        native.mkdir(parents=True)
        for name in ("deck.pptx","deck-vector.pptx","deck.pdf"):(export/name).write_bytes(b"artifact")
        (native/"page-01.png").write_bytes(b"preview")
        manifest=export/"manifest.json"
        manifest.write_text(json.dumps({"export":{"tracks":{"editable":{"ok":True},"vector":{"ok":True}}}}))
        self.core._validate_export(work_path,[])
        for tracks in (
            {"editable":{"ok":False},"vector":{"ok":True}},
            {"editable":{"status":"ok"},"vector":{"status":"ok"}},
        ):
            manifest.write_text(json.dumps({"export":{"tracks":tracks}}))
            with self.subTest(tracks=tracks), self.assertRaises(BridgeError) as invalid:
                self.core._validate_export(work_path,[])
            self.assertEqual(invalid.exception.code,"INVALID_ARTIFACT")

    def test_local_convert_process_renews_lease_while_export_is_running(self):
        opened=self.open();iid=str(uuid.uuid4());self.submit(opened,iid)
        claimed=self.core.await_intent(opened["session_id"],"consumer-a",1)
        process=mock.Mock(returncode=0)
        process.communicate.side_effect=[subprocess.TimeoutExpired(["fake-export"],30),("done","warn")]
        with mock.patch("bridge_core.subprocess.Popen",return_value=process):
            result=self.core._run_local_convert_process(
                ["fake-export"],opened["session_id"],iid,claimed["attempt"],"consumer-a",timeout=60)
        self.assertEqual((result.returncode,result.stdout,result.stderr),(0,"done","warn"))
        notices=[json.loads(row[0]) for row in self.core.db.execute(
            "SELECT data_json FROM events WHERE session_id=? AND type='notice'",(opened["session_id"],))]
        self.assertTrue(any(item.get("message")=="local conversion running" for item in notices))
        self.assertEqual(self.core.db.execute(
            "SELECT status FROM intents WHERE id=?",(iid,)).fetchone()[0],"processing")

        abandoned=mock.Mock(returncode=None)
        abandoned.communicate.side_effect=[subprocess.TimeoutExpired(["fake-export"],30),("","")]
        abandoned.poll.return_value=None
        with mock.patch("bridge_core.subprocess.Popen",return_value=abandoned), mock.patch.object(
                self.core,"push_update",side_effect=BridgeError(409,"RECOVERY_REQUIRED","lost")):
            with self.assertRaises(BridgeError):
                self.core._run_local_convert_process(
                    ["fake-export"],opened["session_id"],iid,claimed["attempt"],"consumer-a",timeout=60)
        abandoned.terminate.assert_called_once_with()

    def test_save_receipt_replay_cas_and_git_index_isolation(self):
        self.make_deck()
        subprocess.run(["git", "init"], cwd=self.root, check=True, capture_output=True)
        (self.root / "unrelated.txt").write_text("staged")
        subprocess.run(["git", "add", "unrelated.txt"], cwd=self.root, check=True)
        index = self.root / ".git" / "index"
        before = hashlib.sha256(index.read_bytes()).hexdigest()
        opened = self.core.open_editor("consumer-a", str(self.root / "index.html"), open_browser=False)
        html = "<!doctype html><title>saved</title>"
        r1 = self.core.save(opened["session_id"], "index.html", html, opened["revision"])
        r2 = self.core.save(opened["session_id"], "index.html", html, opened["revision"])
        self.assertEqual(r1["receipt_id"], r2["receipt_id"])
        self.assertEqual((self.root / "index.html").read_text(), html)
        self.assertEqual(hashlib.sha256(index.read_bytes()).hexdigest(), before)
        self.assertEqual(subprocess.run(["git", "rev-parse", "--verify", "HEAD"], cwd=self.root, capture_output=True).returncode, 128)
        self.assertEqual(self.core.db.execute("SELECT COUNT(*) FROM write_receipts").fetchone()[0], 1)

    def test_briefing_has_no_fake_html(self):
        opened = self.core.open_editor("consumer-a", None, "nested/new.html", open_browser=False)
        self.assertIsNone(opened["deck_path"])
        self.assertIsNone(opened["revision"])
        self.assertEqual(opened["phase"], "briefing")
        self.assertEqual(opened["resource_path"], "nested/new.html")
        self.assertFalse((self.root / "nested" / "new.html").exists())

    def test_complete_validation_publication_and_receipt_replay(self):
        opened = self.open()
        iid = str(uuid.uuid4())
        payload = {"text": "brief", "json": {"kind": "design-brief"}}
        accepted = self.core.accept_intent(opened["session_id"], {
            "protocol_version": 2, "intent_id": iid, "session_id": opened["session_id"],
            "type": "brief.submitted", "base_revision": opened["revision"],
            "payload": payload, "client_ts": "2026-10-02T00:00:00Z",
        })
        claimed = self.core.await_intent(opened["session_id"], "consumer-a", 1)
        work_path = Path(claimed["work_path"])
        work_path.write_text("<!doctype html><title>published</title>", encoding="utf-8")
        candidate = revision_cli(work_path)
        checks = [{"name": name, "argv": ["test", name], "exit_code": 0, "report_path": None}
                  for name in ("render", "capacity", "images", "manifest")]
        validation = {"candidate_revision": candidate, "checks": checks}
        first = self.core.push_update(opened["session_id"], iid, 1, "consumer-a", "complete", "done", validation)
        event_count = self.core.db.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        second = self.core.push_update(opened["session_id"], iid, 1, "consumer-a", "complete", "ignored", {"bad": True})
        self.assertEqual(first["receipt_id"], second["receipt_id"])
        self.assertEqual(self.core.db.execute("SELECT COUNT(*) FROM events").fetchone()[0], event_count)
        self.assertIn("published", (self.root / "index.html").read_text())
        self.assertEqual(self.core.db.execute("SELECT status FROM publications ORDER BY created_at DESC LIMIT 1").fetchone()[0], "COMMITTED")
        self.assertEqual(self.core.db.execute("SELECT status FROM intents WHERE id=?", (iid,)).fetchone()[0], "succeeded")

    def test_response_loss_intent_claim_open_close_and_retry(self):
        opened = self.open()
        sid = opened["session_id"]
        iid = str(uuid.uuid4())
        accepted = self.submit(opened, iid)
        accepted_replay = self.submit(opened, iid)
        self.assertEqual(accepted, accepted_replay)
        claimed = self.core.await_intent(sid, "consumer-a", 1)
        claim_replay = self.core.await_intent(sid, "consumer-a", 1)
        self.assertTrue(claim_replay["redelivered"])
        self.assertEqual((claimed["intent_id"], claimed["attempt"], claimed["work_path"]),
                         (claim_replay["intent_id"], claim_replay["attempt"], claim_replay["work_path"]))
        self.core.push_update(sid, iid, 1, "consumer-a", "fail", "deterministic failure")
        retry_id = str(uuid.uuid4())
        retry = {"session_id": sid, "intent_id": iid, "retry_id": retry_id,
                 "expected_attempt": 1, "mode": "rebuild", "base_revision": opened["revision"],
                 "confirmed": True}
        retry_result = self.core.retry_intent(sid, retry)
        self.assertEqual(retry_result, self.core.retry_intent(sid, retry))
        self.core.close()
        self.core = BridgeCore(self.root)
        self.core.origin = "http://127.0.0.1:9999"
        self.assertEqual(retry_result, self.core.retry_intent(sid, retry))
        reopened = self.core.open_editor("consumer-a", str(self.root / "index.html"), open_browser=False)
        self.assertEqual(reopened["session_id"], sid)
        close_one = self.core.close_consumer(sid, "consumer-a")
        close_two = self.core.close_consumer(sid, "consumer-a")
        self.assertEqual(close_one, close_two)
        self.assertEqual(self.core.db.execute("SELECT COUNT(*) FROM retry_receipts WHERE retry_id=?", (retry_id,)).fetchone()[0], 1)

    def test_complete_response_loss_replays_after_restart_without_republish(self):
        opened = self.open()
        sid = opened["session_id"]
        iid = str(uuid.uuid4())
        self.core.accept_intent(sid, {
            "protocol_version": 2, "intent_id": iid, "session_id": sid,
            "type": "brief.submitted", "base_revision": opened["revision"],
            "payload": {"text": "response loss", "json": {"kind": "design-brief"}},
            "client_ts": "2026-10-03T00:00:00Z",
        })
        claimed = self.core.await_intent(sid, "consumer-a", 1)
        work_path = Path(claimed["work_path"])
        work_path.write_text("<!doctype html><title>response-loss-complete</title>", encoding="utf-8")
        candidate = revision_cli(work_path)
        validation = {"candidate_revision": candidate, "checks": [
            {"name": name, "argv": ["test", name], "exit_code": 0, "report_path": None}
            for name in ("render", "capacity", "images", "manifest")]}
        complete_args = (sid, iid, 1, "consumer-a", "complete", "persisted before lost response", validation)
        first = self.core.push_update(*complete_args)
        counts = tuple(self.core.db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                       for table in ("publications", "events", "snapshots", "facts"))
        self.core.close()
        self.core = BridgeCore(self.root)
        replay = self.core.push_update(*complete_args)
        self.assertEqual((replay["receipt_id"], replay["revision"], replay["events"]),
                         (first["receipt_id"], first["revision"], first["events"]))
        self.assertEqual(tuple(self.core.db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                               for table in ("publications", "events", "snapshots", "facts")), counts)
        self.assertEqual(self.core.get_status(sid)["revision"], candidate)

    def test_two_consumers_and_two_daemon_lock_are_exclusive(self):
        opened = self.open()
        sid = opened["session_id"]
        self.core.open_editor("consumer-b", str(self.root / "index.html"), open_browser=False)
        self.core.await_intent(sid, "consumer-a", 1)
        with self.assertRaises(BridgeError) as busy:
            self.core.await_intent(sid, "consumer-b", 1)
        self.assertEqual(busy.exception.code, "SESSION_BUSY")
        with tempfile.TemporaryDirectory(prefix="bridge-lock-") as tmp:
            first = BridgeCore(tmp, require_lock=True)
            try:
                with self.assertRaises(BridgeError) as locked:
                    BridgeCore(tmp, require_lock=True)
                self.assertEqual(locked.exception.code, "SESSION_BUSY")
            finally:
                first.close()

    def test_a_class_save_asset_rollback_response_loss_receipts(self):
        opened = self.open()
        sid = opened["session_id"]
        baseline = next(v for v in self.core.versions(sid)["versions"] if v["message"] == "baseline")
        save_args = (sid, "index.html", "<!doctype html><title>saved-loss</title>", opened["revision"])
        saved = self.core.save(*save_args)
        save_counts = tuple(self.core.db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                            for table in ("write_receipts", "publications", "events"))
        self.assertEqual(self.core.save(*save_args)["receipt_id"], saved["receipt_id"])
        self.assertEqual(tuple(self.core.db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                               for table in ("write_receipts", "publications", "events")), save_counts)
        raw = b"\x89PNG\r\n\x1a\nresponse-loss"
        encoded = __import__("base64").b64encode(raw).decode()
        asset_args = (sid, "assets/lost.png", encoded, saved["revision"])
        asset = self.core.asset(*asset_args)
        asset_counts = tuple(self.core.db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                             for table in ("write_receipts", "publications", "events"))
        self.assertEqual(self.core.asset(*asset_args)["receipt_id"], asset["receipt_id"])
        self.assertEqual(tuple(self.core.db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                               for table in ("write_receipts", "publications", "events")), asset_counts)
        rollback_args = (sid, "index.html", baseline["snapshot_id"], asset["revision"])
        rolled = self.core.rollback(*rollback_args)
        rollback_counts = tuple(self.core.db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                                for table in ("write_receipts", "publications", "events"))
        self.assertEqual(self.core.rollback(*rollback_args)["receipt_id"], rolled["receipt_id"])
        self.assertEqual(tuple(self.core.db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                               for table in ("write_receipts", "publications", "events")), rollback_counts)
        with self.assertRaises(BridgeError) as stale:
            self.core.save(*save_args)
        self.assertEqual(stale.exception.code, "REVISION_CONFLICT")
        self.assertEqual(stale.exception.details["receipt_id"], saved["receipt_id"])

    def test_external_side_effect_is_not_automatically_replayed(self):
        opened = self.open()
        iid = str(uuid.uuid4())
        self.submit(opened, iid)
        claimed = self.core.await_intent(opened["session_id"], "consumer-a", 1)
        paid_calls = [claimed["intent_id"]]
        self.core.close()
        self.core = BridgeCore(self.root)
        self.assertEqual(paid_calls, [iid])
        self.assertEqual(self.core.db.execute("SELECT status FROM intents WHERE id=?", (iid,)).fetchone()[0], "interrupted")
        self.assertEqual(self.core.db.execute("SELECT COUNT(*) FROM attempts WHERE intent_id=?", (iid,)).fetchone()[0], 1)
        event = self.core.db.execute(
            "SELECT data_json FROM events WHERE session_id=? AND type='intent-status' ORDER BY id DESC LIMIT 1",
            (opened["session_id"],)).fetchone()
        self.assertIsNotNone(event)
        self.assertEqual(json.loads(event[0])["status"], "interrupted")

    def instruction_body(self, opened, typ, payload, intent_id=None, base_revision=None):
        return {"protocol_version": 2, "intent_id": intent_id or str(uuid.uuid4()),
                "session_id": opened["session_id"], "type": typ,
                "base_revision": opened["revision"] if base_revision is None else base_revision,
                "payload": payload, "client_ts": "2026-10-05T00:00:00Z"}

    def anno_payload(self, anchor=None):
        payload = {"version": 1, "kind": "annotation", "deck": "index.html",
                   "annotations": [{"slide": "slide-01", "quote": "x"}]}
        if anchor is not None:
            payload["anchor"] = anchor
        return payload

    def bump_revision(self, opened, title="bumped"):
        return self.core.save(opened["session_id"], "index.html",
                              f"<!doctype html><title>{title}</title>", opened["revision"])["revision"]

    def test_instruction_intent_stale_base_revision_is_accepted_and_normalized(self):
        opened = self.open()
        advanced = self.bump_revision(opened)
        self.assertNotEqual(advanced, opened["revision"])
        iid = str(uuid.uuid4())
        accepted = self.core.accept_intent(opened["session_id"], self.instruction_body(
            opened, "anno.submitted", self.anno_payload(), intent_id=iid))
        self.assertEqual((accepted["accepted"], accepted["status"]), (True, "pending"))
        self.assertEqual(self.core.db.execute(
            "SELECT base_revision FROM intents WHERE id=?", (iid,)).fetchone()[0], advanced)
        design = self.core.accept_intent(opened["session_id"], self.instruction_body(
            opened, "design.submitted", {"version": 1, "kind": "design-intent",
                                         "deck": "index.html", "answers": {}},
            base_revision=opened["revision"]))
        self.assertEqual(design["status"], "pending")

    def test_write_coupled_intent_stale_base_revision_still_conflicts(self):
        opened = self.open()
        self.bump_revision(opened)
        with self.assertRaises(BridgeError) as raised:
            self.submit(opened)
        self.assertEqual((raised.exception.status, raised.exception.code),
                         (409, "REVISION_CONFLICT"))
        self.assertEqual(self.core.db.execute("SELECT COUNT(*) FROM intents").fetchone()[0], 0)

    def test_instruction_intent_claim_after_publish_rebases_instead_of_poisoning(self):
        opened = self.open()
        iid = str(uuid.uuid4())
        self.core.accept_intent(opened["session_id"], self.instruction_body(
            opened, "anno.submitted", self.anno_payload(), intent_id=iid))
        advanced = self.bump_revision(opened)
        claimed = self.core.await_intent(opened["session_id"], "consumer-a", 1)
        self.assertEqual(claimed["kind"], "intent")
        self.assertEqual((claimed["intent_id"], claimed["base_revision"]), (iid, advanced))
        self.assertEqual(self.core.db.execute(
            "SELECT status FROM intents WHERE id=?", (iid,)).fetchone()[0], "processing")
        attempt_base = self.core.db.execute(
            "SELECT base_revision FROM attempts WHERE intent_id=? AND attempt=1", (iid,)).fetchone()[0]
        self.assertEqual(attempt_base, advanced)
        self.assertEqual(json.loads(Path(claimed["intent_file"]).read_text())["base_revision"], advanced)

    def test_write_coupled_intent_claim_after_publish_is_poisoned(self):
        opened = self.open()
        iid = str(uuid.uuid4())
        self.submit(opened, iid)
        self.bump_revision(opened)
        with self.assertRaises(BridgeError) as raised:
            self.core.await_intent(opened["session_id"], "consumer-a", 1)
        self.assertEqual((raised.exception.status, raised.exception.code),
                         (409, "RECOVERY_REQUIRED"))
        self.assertEqual(self.core.db.execute(
            "SELECT status FROM intents WHERE id=?", (iid,)).fetchone()[0], "conflict")
        self.assertEqual(self.core.db.execute(
            "SELECT COUNT(*) FROM attempts WHERE intent_id=?", (iid,)).fetchone()[0], 0)

    def test_anchor_payload_shape_is_validated_only_for_instruction_intents(self):
        opened = self.open()
        sid = opened["session_id"]
        for anchor in ({"revision": opened["revision"], "dirty": True},
                       {"revision": None, "dirty": False}):
            accepted = self.core.accept_intent(sid, self.instruction_body(
                opened, "anno.submitted", self.anno_payload(anchor)))
            self.assertTrue(accepted["accepted"])
        accepted = self.core.accept_intent(sid, self.instruction_body(
            opened, "design.submitted", {"version": 1, "kind": "design-intent",
                                         "deck": "index.html", "answers": {},
                                         "anchor": {"revision": None, "dirty": True}}))
        self.assertTrue(accepted["accepted"])
        for anchor in (["not-a-dict"], "text", 1, {"revision": opened["revision"], "dirty": "yes"},
                       {"revision": 7, "dirty": False},
                       {"revision": opened["revision"], "dirty": False, "extra": 1},
                       {"revision": opened["revision"]}, {"dirty": False}):
            with self.assertRaises(BridgeError) as raised:
                self.core.accept_intent(sid, self.instruction_body(
                    opened, "anno.submitted", self.anno_payload(anchor)))
            self.assertEqual((raised.exception.status, raised.exception.code,
                              raised.exception.message), (400, "INVALID_ARGUMENT", "anchor 字段非法"))
        with self.assertRaises(BridgeError) as brief_anchor:
            self.core.accept_intent(sid, self.instruction_body(
                opened, "brief.submitted", {"text": "x", "json": {"kind": "design-brief"},
                                            "anchor": {"revision": None, "dirty": False}}))
        self.assertEqual((brief_anchor.exception.status, brief_anchor.exception.code),
                         (400, "INVALID_ARGUMENT"))
        with self.assertRaises(BridgeError) as coupled_anchor:
            self.core.accept_intent(sid, {
                "protocol_version": 2, "intent_id": str(uuid.uuid4()), "session_id": sid,
                "type": "convert.requested", "base_revision": opened["revision"],
                "payload": {"formats": ["pptx"], "scope": "all",
                            "anchor": {"revision": None, "dirty": False}},
                "client_ts": "2026-10-05T00:00:00Z"})
        self.assertEqual((coupled_anchor.exception.status, coupled_anchor.exception.code),
                         (400, "INVALID_ARGUMENT"))

    def test_instruction_intent_completes_with_publish_after_late_claim(self):
        opened = self.open()
        sid = opened["session_id"]
        iid = str(uuid.uuid4())
        self.core.accept_intent(sid, self.instruction_body(
            opened, "anno.submitted", self.anno_payload(), intent_id=iid))
        self.bump_revision(opened)
        claimed = self.core.await_intent(sid, "consumer-a", 1)
        work_path = Path(claimed["work_path"])
        work_path.write_text("<!doctype html><title>anno-complete</title>", encoding="utf-8")
        candidate = revision_cli(work_path)
        validation = {"candidate_revision": candidate, "checks": [
            {"name": name, "argv": ["test", name], "exit_code": 0, "report_path": None}
            for name in ("render", "capacity", "images", "manifest")]}
        completed = self.core.push_update(sid, iid, claimed["attempt"], "consumer-a",
                                          "complete", "anno done", validation)
        self.assertEqual((completed["status"], completed["revision"]), ("succeeded", candidate))
        self.assertEqual(self.core.get_status(sid)["revision"], candidate)
        self.assertIn("anno-complete", (self.root / "index.html").read_text())


class InjectedCrash(BaseException):
    pass


class PublicationRecoveryCase(unittest.TestCase):
    def _prepare(self, root, point, index=None):
        (root / "assets").mkdir();(root / "index.html").write_text("<html>old</html>");(root / "assets/a.png").write_bytes(b"\x89PNG\r\n\x1a\nold")
        def inject(actual, context):
            if actual == point and (index is None or context.get("index") == index):
                raise InjectedCrash(actual)
        core=BridgeCore(root,fault_injector=inject);core.origin="http://127.0.0.1:9"
        opened=core.open_editor("consumer",str(root/"index.html"),open_browser=False)
        return core,opened

    def _crash_save(self,root,point,index=None):
        core,opened=self._prepare(root,point,index)
        with self.assertRaises(InjectedCrash):core.save(opened["session_id"],"index.html","<html>new</html>",opened["revision"])
        core.close();return opened

    def test_prepared_applying_each_file_and_git_ref_recover_old(self):
        for repeat in range(3):
            for point,index in [("publication.prepared",None),("publication.applying",None),("publication.file_applied",0),("publication.file_applied",1),("publication.git_ref_updated",None)]:
                with self.subTest(repeat=repeat,point=point,index=index),tempfile.TemporaryDirectory(prefix="bridge-fault-") as tmp:
                    root=Path(tmp);opened=self._crash_save(root,point,index);recovered=BridgeCore(root)
                    try:
                        self.assertEqual((root/"index.html").read_text(),"<html>old</html>")
                        self.assertEqual((root/"assets/a.png").read_bytes(),b"\x89PNG\r\n\x1a\nold")
                        self.assertEqual(recovered.db.execute("SELECT status FROM publications ORDER BY created_at DESC LIMIT 1").fetchone()[0],"ROLLED_BACK")
                        self.assertEqual(recovered.db.execute("SELECT COUNT(*) FROM write_receipts").fetchone()[0],0)
                    finally:recovered.close()

    def test_db_committed_repairs_old_target_without_duplicate_receipt_or_events(self):
        for point in ("publication.db_committed", "publication.before_response"):
            with self.subTest(point=point), tempfile.TemporaryDirectory(prefix="bridge-commit-") as tmp:
                root=Path(tmp);opened=self._crash_save(root,point)
                if point == "publication.db_committed":
                    (root/"index.html").write_text("<html>old</html>")
                recovered=BridgeCore(root)
                try:
                    self.assertEqual((root/"index.html").read_text(),"<html>new</html>")
                    counts=(recovered.db.execute("SELECT COUNT(*) FROM write_receipts").fetchone()[0],recovered.db.execute("SELECT COUNT(*) FROM events").fetchone()[0],recovered.db.execute("SELECT COUNT(*) FROM publications").fetchone()[0])
                    receipt=json.loads(recovered.db.execute("SELECT result_json FROM write_receipts").fetchone()[0])
                    replay=recovered.save(opened["session_id"],"index.html","<html>new</html>",opened["revision"])
                    self.assertEqual(replay["receipt_id"],receipt["receipt_id"])
                    self.assertEqual((recovered.db.execute("SELECT COUNT(*) FROM write_receipts").fetchone()[0],recovered.db.execute("SELECT COUNT(*) FROM events").fetchone()[0],recovered.db.execute("SELECT COUNT(*) FROM publications").fetchone()[0]),counts)
                finally:recovered.close()
                again=BridgeCore(root)
                try:self.assertEqual((again.db.execute("SELECT COUNT(*) FROM write_receipts").fetchone()[0],again.db.execute("SELECT COUNT(*) FROM events").fetchone()[0],again.db.execute("SELECT COUNT(*) FROM publications").fetchone()[0]),counts)
                finally:again.close()

    def test_third_party_bytes_freeze_recovery(self):
        with tempfile.TemporaryDirectory(prefix="bridge-third-") as tmp:
            root=Path(tmp);self._crash_save(root,"publication.file_applied",0);(root/"index.html").write_text("<html>third-party</html>")
            with self.assertRaises(BridgeError) as caught:BridgeCore(root)
            self.assertEqual(caught.exception.code,"RECOVERY_FAILED")
            self.assertEqual((root/"index.html").read_text(),"<html>third-party</html>")


def valid_brief_options():
    return {
        "version": 2,
        "kind": "brief-options",
        "context_summary": "季度经营汇报，面向管理层，数据密集",
        "profile": {"signals": ["data-heavy", "brand-color", "audience:management"]},
        "groups": [
            {"id": "scene", "title": "使用场景", "impact": "决定密度与动效锚点",
             "state": "ask", "multi": False,
             "options": [
                 {"id": "report", "label": "汇报答辩", "desc": "限时讲完，结论先行",
                  "recommended": True, "reason": "素材为季度经营数据"},
                 {"id": "read", "label": "阅读分发", "desc": "会后自读", "default": True},
             ]},
            {"id": "audience", "title": "受众", "impact": "影响口吻与详略",
             "state": "prefilled", "prefill_reason": "素材明确写给管理层",
             "multi": False, "options": []},
            {"id": "x-data", "title": "数据呈现偏好", "impact": "影响图表密度",
             "state": "skipped", "prefill_reason": "素材已含完整图表",
             "multi": False, "options": []},
        ],
        "theme_pick": {"recommended": ["e3/red", "c3"], "reason": "经营汇报 + 品牌红 → 号外红变体",
                       "library_open": True},
        "static_fallback": False,
    }


class BriefOptionsCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="bridge-brief-")
        self.root = Path(self.tmp.name)
        self.core = BridgeCore(self.root)
        self.core.origin = "http://127.0.0.1:9999"

    def tearDown(self):
        self.core.close()
        self.tmp.cleanup()

    def open_brief(self, options="__absent__"):
        kwargs = {} if options == "__absent__" else {"brief_options": options}
        return self.core.open_editor("consumer-a", None, "index.html", "brief", False, **kwargs)

    def test_valid_options_roundtrip_through_open_and_status(self):
        opened = self.open_brief()
        self.assertIsNone(opened["brief_options"])
        self.assertIsNone(self.core.get_status(opened["session_id"])["brief_options"])
        options = valid_brief_options()
        opened = self.open_brief(options)
        self.assertEqual(opened["brief_options"], options)
        status = self.core.get_status(opened["session_id"])
        self.assertEqual(status["brief_options"], options)

    def test_overwrite_and_keep_semantics(self):
        options_a = valid_brief_options()
        opened = self.open_brief(options_a)
        self.assertEqual(opened["brief_options"], options_a)
        options_b = valid_brief_options()
        options_b["context_summary"] = "重新定制后的输入"
        options_b["groups"] = options_b["groups"][:1]
        opened = self.open_brief(options_b)
        self.assertEqual(opened["brief_options"], options_b)
        self.assertEqual(self.core.get_status(opened["session_id"])["brief_options"], options_b)
        opened = self.open_brief()
        self.assertEqual(opened["brief_options"], options_b)
        self.assertEqual(self.core.get_status(opened["session_id"])["brief_options"], options_b)

    def test_invalid_options_rejected_and_stored_value_kept(self):
        options = valid_brief_options()
        session_id = self.open_brief(options)["session_id"]

        def broken(mutate):
            import copy
            candidate = copy.deepcopy(valid_brief_options())
            mutate(candidate)
            return candidate

        cases = {
            "bad-group-id": lambda c: c["groups"][0].update({"id": "unknown-dim"}),
            "prefilled-missing-reason": lambda c: c["groups"][1].pop("prefill_reason"),
            "prefilled-empty-reason": lambda c: c["groups"][1].update({"prefill_reason": "  "}),
            "label-too-long": lambda c: c["groups"][0]["options"][0].update({"label": "长" * 31}),
            "desc-too-long": lambda c: c["groups"][0]["options"][0].update({"desc": "长" * 121}),
            "ask-empty-options": lambda c: c["groups"][0].update({"options": []}),
            "ask-single-option": lambda c: c["groups"][0].update({"options": c["groups"][0]["options"][:1]}),
            "too-many-options": lambda c: c["groups"][0].update(
                {"options": [{"id": f"o{i}", "label": f"选项{i}", "desc": "d"} for i in range(7)]}),
            "bad-version": lambda c: c.update({"version": 1}),
            "bad-kind": lambda c: c.update({"kind": "brief"}),
            "unknown-top-field": lambda c: c.update({"extra": 1}),
            "missing-state": lambda c: c["groups"][0].pop("state"),
            "bad-theme-id": lambda c: c["theme_pick"].update({"recommended": ["E3/Red"]}),
            "too-many-themes": lambda c: c["theme_pick"].update({"recommended": ["e3", "c3", "a1", "b1"]}),
            "summary-too-long": lambda c: c.update({"context_summary": "长" * 501}),
            "too-many-signals": lambda c: c["profile"].update({"signals": [f"s{i}" for i in range(13)]}),
            "option-missing-desc": lambda c: c["groups"][0]["options"][0].pop("desc"),
        }
        for name, mutate in cases.items():
            with self.subTest(case=name):
                with self.assertRaises(BridgeError) as rejected:
                    self.open_brief(broken(mutate))
                self.assertEqual(rejected.exception.status, 400)
                self.assertEqual(rejected.exception.code, "INVALID_ARGUMENT")
                self.assertEqual(self.core.get_status(session_id)["brief_options"], options)
        with self.assertRaises(BridgeError) as rejected:
            self.open_brief("not-an-object")
        self.assertEqual(rejected.exception.code, "INVALID_ARGUMENT")
        self.assertEqual(self.core.get_status(session_id)["brief_options"], options)

    def test_legacy_sessions_table_migrates(self):
        import sqlite3
        with tempfile.TemporaryDirectory(prefix="bridge-brief-migrate-") as tmp:
            internal = Path(tmp) / ".pptx-html"
            internal.mkdir()
            db = sqlite3.connect(internal / "bridge.sqlite3")
            db.execute("CREATE TABLE meta(key TEXT PRIMARY KEY,value TEXT NOT NULL)")
            db.execute("INSERT INTO meta VALUES('schema_version','3')")
            db.execute("CREATE TABLE sessions(id TEXT PRIMARY KEY,target_path TEXT NOT NULL UNIQUE,deck_path TEXT,phase TEXT NOT NULL,"
                       "created_at TEXT NOT NULL,updated_at TEXT NOT NULL,revision TEXT,export_revision TEXT,"
                       "export_source_revision TEXT,agent_state TEXT NOT NULL DEFAULT 'offline',owner_consumer_id TEXT,"
                       "git_ready INTEGER NOT NULL DEFAULT 0,git_ref TEXT)")
            db.commit(); db.close()
            core = BridgeCore(tmp)
            try:
                self.assertIn("brief_options_json", {r[1] for r in core.db.execute("PRAGMA table_info(sessions)")})
            finally:
                core.close()


class SecurityAndMigrationCase(unittest.TestCase):
    def test_hardlink_and_symlink_swap_are_denied(self):
        with tempfile.TemporaryDirectory(prefix="bridge-path-") as tmp,tempfile.TemporaryDirectory(prefix="bridge-out-") as outside:
            root=Path(tmp);(root/"safe").mkdir();(root/"safe/file.txt").write_text("inside");external=Path(outside)/"file.txt";external.write_text("outside")
            core=BridgeCore(root)
            try:
                os.link(root/"safe/file.txt",root/"hard.txt")
                with self.assertRaises(BridgeError):core.secure.read("hard.txt")
                (root/"safe").rename(root/"real-safe");os.symlink(outside,root/"safe")
                with self.assertRaises((BridgeError,OSError)):core.secure.read("safe/file.txt")
                self.assertEqual(external.read_text(),"outside")
            finally:core.close()

    def test_schema_v2_migrates_and_future_schema_is_rejected(self):
        import sqlite3
        with tempfile.TemporaryDirectory(prefix="bridge-migrate-") as tmp:
            internal=Path(tmp)/".pptx-html";internal.mkdir();db=sqlite3.connect(internal/"bridge.sqlite3")
            db.execute("CREATE TABLE meta(key TEXT PRIMARY KEY,value TEXT NOT NULL)");db.execute("INSERT INTO meta VALUES('schema_version','2')")
            db.execute("CREATE TABLE attempts(session_id TEXT,intent_id TEXT,attempt INTEGER,base_revision TEXT,work_path TEXT,consumer_id TEXT,status TEXT,result_json TEXT,created_at TEXT,PRIMARY KEY(intent_id,attempt))");db.commit();db.close()
            core=BridgeCore(tmp)
            try:self.assertIn("export_baseline_json",{r[1] for r in core.db.execute("PRAGMA table_info(attempts)")})
            finally:core.close()
        with tempfile.TemporaryDirectory(prefix="bridge-future-") as tmp:
            internal=Path(tmp)/".pptx-html";internal.mkdir();db=sqlite3.connect(internal/"bridge.sqlite3");db.execute("CREATE TABLE meta(key TEXT PRIMARY KEY,value TEXT NOT NULL)");db.execute("INSERT INTO meta VALUES('schema_version','999')");db.commit();db.close()
            with self.assertRaises(BridgeError):BridgeCore(tmp)

    def test_svg_inline_raster_is_self_contained_but_external_and_active_content_are_rejected(self):
        with tempfile.TemporaryDirectory(prefix="bridge-svg-") as tmp:
            root=Path(tmp);(root/"assets").mkdir();(root/"index.html").write_text("<html></html>")
            svg=root/"assets/x.svg"
            png="iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
            svg.write_text('<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"><defs><path id="p" d="M0 0"/></defs><image xlink:href="data:image/png;base64,'+png+'"/><image href="data:image/jpeg;base64,/9j/2Q=="/><use href="#p"/></svg>')
            core=BridgeCore(root)
            try:
                core.register_session(deck_path=str(root/"index.html"))
                rejected = [
                    '<script>alert(1)</script>',
                    '<image href="https://example.com/a.png"/>',
                    '<image href="file:///tmp/a.png"/>',
                    '<image href="local.png"/>',
                    '<image href="data:image/svg+xml;base64,PHN2Zy8+"/>',
                    '<image href="data:image/png;base64,not-base64"/>',
                    '<image href="data:image/png;base64,/9j/2Q=="/>',
                    '<rect style="fill:url(data:image/png;base64,'+png+')"/>',
                ]
                for payload in rejected:
                    svg.write_text('<svg xmlns="http://www.w3.org/2000/svg">'+payload+'</svg>')
                    with self.subTest(payload=payload), self.assertRaises(BridgeError) as invalid:
                        core._validate_svg(svg)
                    self.assertEqual(invalid.exception.code, "INVALID_ARTIFACT")
                svg.unlink();(root/"assets/run.exe").write_bytes(b"bad")
                with self.assertRaises(BridgeError) as unknown:
                    core.scan_bundle(root/"index.html")
                self.assertEqual(unknown.exception.code, "INVALID_ARTIFACT")
            finally:core.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
