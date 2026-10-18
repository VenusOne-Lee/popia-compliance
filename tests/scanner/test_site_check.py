"""site_check against a local server. No external network."""
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import site_check  # noqa: E402

PAGE = b"""<!doctype html><html><head>
<script async src="https://www.googletagmanager.com/gtag/js?id=G-TEST"></script>
<script>gtag('config','G-TEST'); fbq('init','1');</script></head>
<body><form><input type="email" name="email"><input type="checkbox" name="marketing_opt_in" checked></form>
<a href="/terms">Terms</a></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Set-Cookie", "_ga=GA1.1.1; Path=/")
            self.send_header("Set-Cookie", "session_id=abc; Path=/")
            self.send_header("X-Powered-By", "Express 4.17.1")
            self.end_headers()
            self.wfile.write(PAGE)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *a):
        pass


class SiteCheckTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = HTTPServer(("127.0.0.1", 0), Handler)
        cls.t = threading.Thread(target=cls.srv.serve_forever, daemon=True)
        cls.t.start()
        cls.res = site_check.check(f"http://127.0.0.1:{cls.srv.server_port}/", timeout=5)

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def test_findings(self):
        got = {f["rule_id"] for f in self.res["findings"]}
        for rid in ("WEB-001", "WEB-004", "WEB-009", "WEB-010", "WEB-011", "WEB-013", "WEB-015", "WEB-016", "WEB-019"):
            self.assertIn(rid, got, rid)
        self.assertIn("Meta Pixel", self.res["trackers"])

    def test_markdown(self):
        md = site_check.fmt_md(self.res)
        self.assertIn("# POPIA site check", md)
        self.assertIn("not legal advice", md)


if __name__ == "__main__":
    unittest.main()
