"""MCP server unit tests (in-process) plus the stdio smoke test."""
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "mcp"))
sys.path.insert(0, str(ROOT / "scripts"))

import server  # noqa: E402
import sa_id  # noqa: E402


class TestServer(unittest.TestCase):
    def setUp(self):
        self.s = server.Server()

    def rpc(self, method, params=None, mid=1):
        m = {"jsonrpc": "2.0", "id": mid, "method": method}
        if params is not None:
            m["params"] = params
        return self.s.handle(m)

    def test_tools_json_matches_handlers(self):
        names = {t["name"] for t in json.loads((ROOT / "mcp" / "tools.json").read_text())["tools"]}
        self.assertEqual(names, set(server.TOOLS))

    def test_protocol_fallback(self):
        r = self.rpc("initialize", {"protocolVersion": "1999-01-01"})
        self.assertEqual(r["result"]["protocolVersion"], server.DEFAULT_PROTOCOL)

    def test_notification_has_no_reply(self):
        self.assertIsNone(self.s.handle({"jsonrpc": "2.0", "method": "notifications/initialized"}))

    def test_invalid_request(self):
        self.assertEqual(self.s.handle({"id": 3, "method": "ping"})["error"]["code"], -32600)

    def test_sa_id_never_echoed(self):
        fid = sa_id.fake(1, seed=3)[0]
        r = self.rpc("tools/call", {"name": "popia_validate_sa_id", "arguments": {"id_number": fid}})
        text = r["result"]["content"][0]["text"]
        self.assertNotIn(fid, text)
        self.assertNotIn("date_of_birth", text)

    def test_breach_triage_does_not_echo_pi(self):
        fid = sa_id.fake(1, seed=4)[0]
        r = self.rpc("tools/call", {"name": "popia_breach_triage",
                                    "arguments": {"description": f"spreadsheet with {fid} sent to wrong recipient"}})
        text = r["result"]["content"][0]["text"]
        self.assertNotIn(fid, text)
        self.assertIn("Misdirected email", text)

    def test_every_result_has_disclaimer(self):
        for name, args in (("popia_lookup", {"query": "retention"}), ("popia_checklist", {"area": "ai"}),
                           ("popia_scan", {"path": "/no/such/path"})):
            r = self.rpc("tools/call", {"name": name, "arguments": args})
            self.assertTrue(r["result"]["content"][0]["text"].endswith(server.DISCLAIMER))

    def test_missing_module_is_tool_error(self):
        r = self.rpc("tools/call", {"name": "popia_generate_pack", "arguments": {"answers": {}}})
        res = r["result"]
        try:
            import popia_pack  # noqa: F401
        except ImportError:
            self.assertTrue(res["isError"])
            self.assertIn("popia_pack", res["content"][0]["text"])

    def test_checklist_areas(self):
        for area in server.CHECKLIST_AREAS:
            r = self.rpc("tools/call", {"name": "popia_checklist", "arguments": {"area": area}})
            self.assertFalse(r["result"]["isError"], area)


class TestSmoke(unittest.TestCase):
    def test_smoke(self):
        p = subprocess.run([sys.executable, str(ROOT / "mcp" / "smoke_test.py")], capture_output=True, text=True,
                           timeout=120)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)


if __name__ == "__main__":
    unittest.main()
