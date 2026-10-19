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


SHELL = b"""<!doctype html><html><head><script type="module" src="/assets/index.js"></script></head>
<body><div id="root"></div></body></html>"""


class Unreadable(BaseHTTPRequestHandler):
    """Routes that must not be graded, plus a JavaScript-built page."""

    def do_GET(self):
        routes = {
            "/vercel": (429, {"X-Vercel-Mitigated": "challenge", "Content-Type": "text/html"}, b"<html></html>"),
            "/cf": (200, {"Content-Type": "text/html"}, b"<html><head><title>Just a moment...</title></head></html>"),
            "/down": (500, {"Content-Type": "text/html"}, b"error"),
            "/spa": (200, {"Content-Type": "text/html"}, SHELL),
        }
        st, headers, body = routes.get(self.path.split("?")[0], (404, {}, b""))
        self.send_response(st)
        for k, v in headers.items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


class UnreadableSiteTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = HTTPServer(("127.0.0.1", 0), Unreadable)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.srv.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def test_bot_checks_and_errors_are_not_graded(self):
        for path, reason in (("/vercel", "blocked"), ("/cf", "blocked"), ("/down", "error")):
            with self.assertRaises(site_check.SiteUnreadable) as ctx:
                site_check.check(self.base + path, timeout=5, probe_paths=False)
            self.assertEqual(ctx.exception.reason, reason, path)
            self.assertIn("nothing was checked", str(ctx.exception))

    def test_javascript_page_reports_unknown_not_missing(self):
        res = site_check.check(self.base + "/spa", timeout=5, probe_paths=False)
        self.assertEqual(res["notices"], {"privacy": None, "paia": None, "cookie": None, "information_officer": None})
        got = [f["rule_id"] for f in res["findings"]]
        self.assertIn("WEB-022", got)
        self.assertNotIn("WEB-015", got)
        self.assertNotIn("WEB-016", got)
        self.assertIn("couldn't tell", site_check.fmt_md(res))

    def test_challenge_detection_ignores_normal_pages(self):
        self.assertFalse(site_check.is_challenge({}, '<title>Shop</title><script src="/cdn-cgi/challenge-platform/x.js">'))
        self.assertTrue(site_check.is_challenge({"cf-mitigated": "challenge"}, ""))
