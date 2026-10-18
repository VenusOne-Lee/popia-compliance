"""Regression tests for the October 2026 security review. Synthetic values only."""
import contextlib
import io
import json
import os
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "mcp"))

import popia_fleet  # noqa: E402
import popia_scan  # noqa: E402
import server  # noqa: E402
import site_check  # noqa: E402

SECRET = "SYNTHETICTOKEN" + "q" * 30
EMAIL_ENC = "person%40example.test"


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        # value and path contain the flag words; the flags themselves are absent
        self.send_header("Set-Cookie", "session_id=secure-httponly; Path=/samesite=strict")
        self.send_header("Set-Cookie", "auth_token=x; Secure; HttpOnly; SameSite=Lax; Path=/")
        self.end_headers()
        self.wfile.write(
            f'<html><body><script src="http://cdn.example.test/a.js?token={SECRET}"></script>'
            f'<a href="/p?email={EMAIL_ENC}&token={SECRET}">x</a></body></html>'.encode())

    def log_message(self, *a):
        pass


class SiteCheckHardening(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = HTTPServer(("127.0.0.1", 0), _Handler)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.url = f"http://user:{SECRET}@127.0.0.1:{cls.srv.server_port}/profile?email={EMAIL_ENC}&token={SECRET}#frag"
        cls.res = site_check.check(cls.url, timeout=5, probe_paths=False)

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def test_no_sensitive_url_data_in_output(self):
        blob = json.dumps(self.res) + site_check.fmt_md(self.res)
        for needle in (SECRET, EMAIL_ENC, "person@example.test", "user:", "#frag"):
            self.assertNotIn(needle, blob, needle)
        got = {f["rule_id"] for f in self.res["findings"]}
        self.assertIn("WEB-012", got)  # mixed content still reported
        self.assertIn("WEB-021", got)  # PI in URL still reported

    def test_cookie_flags_not_spoofed_by_values(self):
        cookies = {c["name"]: c for c in self.res["cookies"]}
        self.assertFalse(cookies["session_id"]["secure"])
        self.assertFalse(cookies["session_id"]["httponly"])
        self.assertTrue(cookies["auth_token"]["secure"])
        self.assertTrue(cookies["auth_token"]["httponly"])
        self.assertEqual(cookies["auth_token"]["samesite"], "lax")
        weak = [f for f in self.res["findings"] if f["rule_id"] == "WEB-011"]
        self.assertEqual(len(weak), 1)
        self.assertIn("session_id", weak[0]["evidence"])

    def test_block_private_refuses_internal_targets(self):
        with self.assertRaises(site_check.BlockedTarget):
            site_check.check(f"http://127.0.0.1:{self.srv.server_port}/", timeout=5, block_private=True)
        for bad in ("http://169.254.169.254/latest/meta-data/", "http://10.0.0.1/", "http://[::1]/"):
            with self.assertRaises(site_check.BlockedTarget):
                site_check._check_target(bad, True)
        with self.assertRaises(site_check.BlockedTarget):
            site_check._check_target("ftp://example.test/", False)
        with self.assertRaises(site_check.BlockedTarget):
            site_check._check_target("file:///etc/passwd", False)

    def test_cli_error_does_not_echo_url(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            rc = site_check.main([f"https://does-not-exist.invalid/?token={SECRET}", "--no-probe", "--timeout", "2"])
        self.assertEqual(rc, 2)
        self.assertNotIn(SECRET, err.getvalue())


class McpHardening(unittest.TestCase):
    def setUp(self):
        self.s = server.Server()

    def test_tool_exception_details_not_leaked(self):
        orig = server.TOOLS["popia_lookup"]

        def boom(args):
            raise ValueError(f"failed for https://x.test/?token={SECRET} at /Users/someone/private")
        server.TOOLS["popia_lookup"] = boom
        err = io.StringIO()
        try:
            with contextlib.redirect_stderr(err):
                out = self.s.call_tool({"name": "popia_lookup", "arguments": {"query": "x"}})
        finally:
            server.TOOLS["popia_lookup"] = orig
        text = out["content"][0]["text"]
        self.assertTrue(out["isError"])
        for blob in (text, err.getvalue()):
            self.assertNotIn(SECRET, blob)
            self.assertNotIn("/Users/someone", blob)
        self.assertIn("ValueError", text)

    def test_scan_path_refuses_sensitive_locations(self):
        for bad in ("/", "~", "~/.ssh", "/etc"):
            with self.assertRaises(server.ToolError, msg=bad):
                server._safe_scan_path(bad)
        self.assertEqual(server._safe_scan_path(str(ROOT / "scripts")), (ROOT / "scripts").resolve())

    def test_out_dir_confined_and_never_overwrites(self):
        with tempfile.TemporaryDirectory() as d:
            cwd = os.getcwd()
            os.chdir(d)
            try:
                for bad in ("/tmp/elsewhere", "../escape", "."):
                    with self.assertRaises(server.ToolError, msg=bad):
                        server._safe_out_dir(bad)
                Path("full").mkdir()
                Path("full/keep.txt").write_text("keep")
                with self.assertRaises(server.ToolError):
                    server._safe_out_dir("full")
                self.assertTrue(str(server._safe_out_dir("new-pack")).endswith("new-pack"))
            finally:
                os.chdir(cwd)

    def test_site_check_tool_blocks_private_addresses(self):
        out = self.s.call_tool({"name": "popia_site_check", "arguments": {"url": "http://127.0.0.1:9/"}})
        self.assertTrue(out["isError"])
        self.assertIn("Refused", out["content"][0]["text"])


class FleetAndScannerHardening(unittest.TestCase):
    def test_clone_rejects_unsafe_urls(self):
        for bad in ("--upload-pack=touch /tmp/pwned", "file:///etc", "/local/repo", "ext::sh -c id",
                    "http://insecure.test/repo.git", "-c core.sshCommand=id"):
            with self.assertRaises(ValueError, msg=bad):
                popia_fleet.clone(bad, tempfile.mkdtemp())

    def test_git_error_redacts_tokens(self):
        msg = popia_fleet._redact_git_error(f"fatal: could not read https://{SECRET}@github.com/x/y.git")
        self.assertNotIn(SECRET, msg)

    def test_scanner_does_not_follow_symlinks(self):
        with tempfile.TemporaryDirectory() as outside, tempfile.TemporaryDirectory() as repo:
            secret_file = Path(outside, "creds.ts")
            secret_file.write_text('const k = "AKIA' + "Q" * 4 + "7" * 4 + 'ZXCVBNMA";\n')
            os.symlink(secret_file, Path(repo, "linked.ts"))
            res = popia_scan.scan(repo)
            self.assertEqual(res["files_scanned"], 0)
            self.assertNotIn("SEC-001", {f["rule_id"] for f in res["findings"]})


if __name__ == "__main__":
    unittest.main()
