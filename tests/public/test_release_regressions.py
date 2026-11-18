"""Public regression tests using synthetic data, without a server or paid APIs.

Run from the repository root:
    python -m unittest discover -s tests/public -v
"""
from __future__ import annotations

import base64
import contextlib
import hashlib
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import AsyncMock, Mock, patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "skills/SlideForge/scripts/providers"))

import bridge_core
from bridge_dispatch import build_request
import edit
import openai_image


class BundleReadTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="slideforge-test-", dir=ROOT)
        self.addCleanup(temporary.cleanup)
        self.workdir = Path(temporary.name).resolve()
        old_umask = os.umask(0o077)
        self.addCleanup(os.umask, old_umask)
        self.core = bridge_core.BridgeCore(self.workdir)
        self.addCleanup(self.core.close)
        self.files = {
            "assets/photo.png": b"\x89PNG\r\n\x1a\nsynthetic image",
            "fonts/demo.ttf": b"synthetic font",
            "export/deck.pdf": b"%PDF-1.4\nsynthetic export",
            "export/manifest.json": b"{}",
        }
        self.sid = self.create_deck("decks/demo")

    def create_deck(self, directory):
        bundle = self.workdir / directory
        bundle.mkdir(parents=True, exist_ok=True)
        deck = bundle / "index.html"
        deck.write_text("<!doctype html><title>Synthetic deck</title>", encoding="utf-8")
        for relative, data in self.files.items():
            target = bundle / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        return self.core.register_session(deck_path=str(deck))["id"]

    def assert_payload(self, result, relative):
        data = self.files[relative]
        self.assertEqual(result["path"], relative)
        self.assertEqual(base64.b64decode(result["data_base64"]), data)
        self.assertEqual(result["sha256"], hashlib.sha256(data).hexdigest())
        self.assertEqual(result["bytes"], len(data))

    def test_nested_assets_and_fonts_use_bundle_relative_paths(self):
        for relative in ("assets/photo.png", "fonts/demo.ttf"):
            with self.subTest(path=relative):
                self.assert_payload(self.core.read_artifact(self.sid, relative, kind="asset"), relative)

    def test_root_bundle_reads_remain_supported(self):
        sid = self.create_deck("")
        self.assert_payload(self.core.read_artifact(sid, "assets/photo.png", kind="asset"), "assets/photo.png")
        self.assert_payload(self.core.read_export_file(sid, "deck.pdf"), "export/deck.pdf")

    def test_nested_exports_keep_the_existing_route_contract(self):
        for relative in ("export/deck.pdf", "export/manifest.json"):
            with self.subTest(path=relative):
                method, route, body = build_request(
                    "read_bundle_file", {"session_id": self.sid, "path": relative}, consumer_id="test")
                self.assertEqual((method, route), ("POST", "/api/bridge/export-read"))
                self.assert_payload(self.core.read_export_file(self.sid, body["file"]), relative)

    def test_direct_export_reads_are_bundle_relative(self):
        self.assert_payload(self.core.read_artifact(self.sid, "export/deck.pdf", kind="export"), "export/deck.pdf")

    def test_nested_asset_dispatch_preserves_the_relative_path(self):
        method, route, body = build_request(
            "read_bundle_file", {"session_id": self.sid, "path": "assets/photo.png"}, consumer_id="test")
        self.assertEqual((method, route), ("POST", "/api/bridge/asset-read"))
        self.assert_payload(self.core.read_artifact(self.sid, body["path"], kind="asset"), "assets/photo.png")

    def test_traversal_internal_and_cross_bundle_paths_are_denied(self):
        for relative in ("../assets/photo.png", "assets/../../other/photo.png",
                         "/assets/photo.png", "assets\\photo.png", "assets/.git/config",
                         "assets/.pptx-html/config.json", "decks/other/assets/photo.png"):
            with self.subTest(path=relative), self.assertRaises(bridge_core.BridgeError) as caught:
                self.core.read_artifact(self.sid, relative, kind="asset")
            self.assertIn(caught.exception.code, ("PATH_DENIED", "INVALID_ARGUMENT"))

    def test_export_traversal_is_denied(self):
        with self.assertRaises(bridge_core.BridgeError) as caught:
            self.core.read_export_file(self.sid, "../assets/photo.png")
        self.assertEqual(caught.exception.code, "PATH_DENIED")

    def test_unregistered_file_is_denied_even_when_it_exists(self):
        (self.workdir / "decks/demo/assets/extra.png").write_bytes(b"unregistered")
        with self.assertRaises(bridge_core.BridgeError) as caught:
            self.core.read_artifact(self.sid, "assets/extra.png", kind="asset")
        self.assertEqual(caught.exception.code, "NOT_FOUND")

    def test_wrong_file_class_is_denied(self):
        with self.core.db:
            self.core.db.execute("UPDATE bundle_files SET class='export' WHERE session_id=? AND path=?",
                                 (self.sid, "assets/photo.png"))
        with self.assertRaises(bridge_core.BridgeError) as caught:
            self.core.read_artifact(self.sid, "assets/photo.png", kind="asset")
        self.assertEqual(caught.exception.code, "NOT_FOUND")

    def test_read_limit_is_preserved(self):
        with patch.object(bridge_core, "ARTIFACT_READ_MAX", 1):
            with self.assertRaises(bridge_core.BridgeError) as caught:
                self.core.read_artifact(self.sid, "assets/photo.png", kind="asset")
        self.assertEqual(caught.exception.code, "PAYLOAD_TOO_LARGE")

    def test_local_convert_uses_the_shipped_exporter(self):
        deck = str(self.workdir / "decks/demo/index.html")
        self.core.await_intent = Mock(return_value={"work_path": deck, "attempt": 1})
        self.core.push_update = Mock()
        self.core._run_local_convert_process = Mock(return_value=subprocess.CompletedProcess([], 1, "", "test stop"))
        self.core._local_convert_worker(self.sid, "test", "intent")
        argv = self.core._run_local_convert_process.call_args.args[0]
        self.assertEqual(Path(argv[1]), ROOT / "skills/SlideForge/scripts/export-pptx.py")
        self.assertTrue(Path(argv[1]).is_file())
        self.assertEqual(argv[2:], [deck, "--force", "--track", "both"])
        self.core.push_update.assert_called_once()
        self.assertEqual(self.core._convert_state["status"], "failed")

    def test_local_illustration_uses_the_shipped_adapter(self):
        deck = self.workdir / "decks/demo/index.html"
        slot = "hero-1280x720"
        deck.write_text('<img data-editable-image data-image-state="placeholder" '
                        'data-image-slot="hero-1280x720" data-image-intent="Synthetic art" '
                        'src="assets/photo.png">', encoding="utf-8")
        self.core.await_intent = Mock(return_value={"work_path": str(deck), "attempt": 1,
                                                  "payload": {"slots": [slot]}})
        self.core.push_update = Mock()
        self.core.imagegen_provider = "unused-provider.py"
        self.core._run_local_process = Mock(return_value=subprocess.CompletedProcess([], 1, "", "test stop"))
        self.core._local_imagegen_worker(self.sid, "test", "intent")
        argv = self.core._run_local_process.call_args.args[0]
        self.assertEqual(Path(argv[1]), ROOT / "skills/SlideForge/scripts/imagegen-adapter.py")
        self.assertTrue(Path(argv[1]).is_file())
        self.assertEqual(self.core._imagegen_state["status"], "failed")


class ArbitrationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        from bridge_mcp import BridgeMCP, ToolError
        self.ToolError = ToolError
        # Bypass construction so tests never start a daemon or register a live consumer.
        self.bridge = BridgeMCP.__new__(BridgeMCP)
        self.bridge.view_wait_sec = 8
        self.bridge._request = AsyncMock()

    async def test_attached_view_does_not_hide_pending_or_processing_work(self):
        for work in ({"pending_count": 1}, {"processing": {"id": "intent"}}):
            with self.subTest(work=work):
                self.bridge._request.reset_mock()
                self.bridge._request.return_value = {"view_attached": True, **work}
                self.assertIsNone(await self.bridge._arbitrate_view("session", 1))
                self.bridge._request.assert_awaited_once()

    async def test_idle_attached_view_still_returns_without_blocking(self):
        self.bridge._request.return_value = {"view_attached": True, "pending_count": 0, "processing": None}
        result = await self.bridge._arbitrate_view("session", 86400)
        self.assertEqual(result["kind"], "mcp_app")
        self.bridge._request.assert_awaited_once()

    async def test_work_before_any_ui_signal_skips_the_window(self):
        self.bridge._request.return_value = {"pending_count": 1, "ui_signal_ever": False}
        with patch("bridge_mcp.asyncio.sleep", new_callable=AsyncMock) as sleep:
            self.assertIsNone(await self.bridge._arbitrate_view("session", 86400))
            sleep.assert_not_awaited()

    async def test_work_arriving_with_view_attachment_wins_during_window(self):
        self.bridge._request.side_effect = [{"ui_signal_ever": False},
                                            {"view_attached": True, "pending_count": 1}]
        with patch("bridge_mcp.asyncio.sleep", new_callable=AsyncMock):
            self.assertIsNone(await self.bridge._arbitrate_view("session", 10))
        self.assertEqual(self.bridge._request.await_count, 2)

    async def test_browser_and_previous_ui_signals_skip_the_window(self):
        for status in ({"page_online": True}, {"ui_signal_ever": True}):
            with self.subTest(status=status):
                self.bridge._request.return_value = status
                self.assertIsNone(await self.bridge._arbitrate_view("session", 10))

    async def test_one_second_wait_does_not_enter_arbitration_window(self):
        self.bridge._request.return_value = {}
        self.assertIsNone(await self.bridge._arbitrate_view("session", 1))
        self.bridge._request.assert_awaited_once()

    async def test_initial_status_error_is_not_hidden(self):
        self.bridge._request.side_effect = self.ToolError("session unavailable")
        with self.assertRaises(self.ToolError):
            await self.bridge._arbitrate_view("session", 1)


class ImageSelfCheckTests(unittest.TestCase):
    def run_check(self, arguments=(), **overrides):
        cfg = {"api_key": "synthetic-test-key", "env_file": None,
               "base_url": openai_image.DEFAULT_BASE_URL, "model": openai_image.DEFAULT_MODEL,
               "model_advanced": "", "input_fidelity": "", **overrides}
        output = io.StringIO()
        args = openai_image.build_parser().parse_args(["--self-check", *arguments])
        with patch.object(openai_image, "config", return_value=cfg), \
                patch.object(openai_image.urllib.request, "urlopen") as network, \
                contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            result = openai_image.run(args)
            network.assert_not_called()
        self.assertNotIn(cfg["api_key"] or "synthetic-test-key", output.getvalue())
        return result, output.getvalue()

    def test_default_check_uses_the_page_size_without_network(self):
        result, output = self.run_check()
        self.assertEqual(result, 0)
        self.assertIn("2560x1440", output)

    def test_missing_key_returns_failure_without_a_size_error(self):
        result, output = self.run_check(api_key="")
        self.assertEqual(result, 1)
        self.assertIn("OPENAI_API_KEY", output)

    def test_explicit_size_is_preserved(self):
        result, output = self.run_check(["--size", "1024x1024"])
        self.assertEqual(result, 0)
        self.assertIn("1024x1024", output)

    def test_explicit_ratio_is_preserved(self):
        result, output = self.run_check(["--aspect-ratio", "16:9", "--resolution", "2K"])
        self.assertEqual(result, 0)
        self.assertIn("2048x1152", output)

    def test_invalid_explicit_size_still_fails(self):
        with self.assertRaises(openai_image.ProviderError):
            self.run_check(["--size", "17x17"])

    def test_incompatible_page_model_is_reported(self):
        with self.assertRaises(openai_image.ProviderError):
            self.run_check(model="gpt-image-1")

    def test_explicit_legacy_size_can_be_checked(self):
        result, _ = self.run_check(["--size", "1024x1024"], model="gpt-image-1")
        self.assertEqual(result, 0)

    def test_generation_still_requires_an_explicit_size(self):
        args = openai_image.build_parser().parse_args([])
        with self.assertRaises(openai_image.ProviderError):
            openai_image.resolve_size(args, openai_image.DEFAULT_MODEL)


class RuntimeDoctorTests(unittest.TestCase):
    def run_doctor(self, *, missing_module=None, mcp_version="1.28.0", missing_file=None,
                   missing_command=None, driver_error=False):
        runtime = Mock()
        runtime.chromium.executable_path = str(ROOT / "synthetic-chromium")
        module = Mock()
        module.sync_playwright.return_value = contextlib.nullcontext(runtime)
        if driver_error:
            module.sync_playwright.side_effect = RuntimeError("synthetic driver failure")

        def import_module(name):
            if name == missing_module:
                raise ModuleNotFoundError("synthetic missing module")
            return module

        def which(command):
            return command if command in ("git", "node") and command != missing_command else None

        output = io.StringIO()
        with patch.object(edit.importlib, "import_module", side_effect=import_module), \
                patch.object(edit.importlib.metadata, "version", side_effect=lambda name: mcp_version if name == "mcp" else "1.0"), \
                patch.object(edit.shutil, "which", side_effect=which), \
                patch.object(edit.Path, "is_file", lambda path: path.name != missing_file), \
                contextlib.redirect_stdout(output):
            result = edit.doctor()
        runtime.chromium.launch.assert_not_called()
        return result, output.getvalue()

    def test_available_runtime_passes_with_optional_tool_warnings(self):
        result, output = self.run_doctor()
        self.assertEqual(result, 0)
        self.assertIn("[OK] Chromium", output)
        for command in ("pdftocairo", "fc-match", "soffice"):
            self.assertIn("[WARN] " + command, output)

    def test_missing_dependency_returns_failure(self):
        for module in ("mcp.server.fastmcp", "playwright.sync_api", "pptx", "PIL.Image",
                       "fontTools.ttLib", "lxml.etree", "pypdfium2", "brotli"):
            with self.subTest(module=module):
                result, output = self.run_doctor(missing_module=module)
                self.assertEqual(result, 1)
                self.assertIn("install requirements.txt", output)

    def test_unsupported_mcp_version_returns_failure(self):
        for version in ("1.27.0", "2.0.0", "unrecognized"):
            with self.subTest(version=version):
                result, output = self.run_doctor(mcp_version=version)
                self.assertEqual(result, 1)
                self.assertIn("requires >=1.28,<2", output)

    def test_missing_chromium_gives_install_guidance(self):
        result, output = self.run_doctor(missing_file="synthetic-chromium")
        self.assertEqual(result, 1)
        self.assertIn("playwright install chromium", output)

    def test_driver_failure_is_reported(self):
        result, output = self.run_doctor(driver_error=True)
        self.assertEqual(result, 1)
        self.assertIn("Playwright driver unavailable", output)

    def test_missing_shipped_file_is_reported(self):
        result, output = self.run_doctor(missing_file="export-pptx.py")
        self.assertEqual(result, 1)
        self.assertIn("missing from checkout", output)

    def test_missing_required_command_returns_failure(self):
        for command in ("git", "node"):
            with self.subTest(command=command):
                result, output = self.run_doctor(missing_command=command)
                self.assertEqual(result, 1)
                self.assertIn("[FAIL] " + command, output)

    def test_cli_propagates_diagnostic_exit_code_without_starting_services(self):
        for result in (0, 1):
            with self.subTest(result=result), \
                    patch.object(sys, "argv", ["edit.py", "--doctor"]), \
                    patch.object(edit, "doctor", return_value=result) as doctor, \
                    patch.object(edit, "resolve_imagegen_provider") as provider, \
                    patch.object(bridge_core, "BridgeCore") as core, \
                    patch.object(edit.webbrowser, "open") as browser:
                with self.assertRaises(SystemExit) as caught:
                    edit.main()
                self.assertEqual(caught.exception.code, result)
                doctor.assert_called_once_with()
                provider.assert_not_called()
                core.assert_not_called()
                browser.assert_not_called()

    def test_cli_rejects_operational_flags_without_running_diagnostics(self):
        for flags in (["--mcp"], ["--daemon"], ["--stop"], ["--convert"], ["--imagegen"],
                      ["--deck", "index.html"], ["--new"]):
            with self.subTest(flags=flags), \
                    patch.object(sys, "argv", ["edit.py", "--doctor", *flags]), \
                    patch.object(edit, "doctor") as doctor, \
                    contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as caught:
                    edit.main()
                self.assertEqual(caught.exception.code, 2)
                doctor.assert_not_called()


if __name__ == "__main__":
    unittest.main()
