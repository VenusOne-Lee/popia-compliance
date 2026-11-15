"""site_check against a local server. No external network."""
import sys
import os
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
        w15 = next(f for f in self.res["findings"] if f["rule_id"] == "WEB-015")
        self.assertEqual(w15["severity"], "high")  # the page has a form, trackers and cookies

    def test_markdown(self):
        md = site_check.fmt_md(self.res)
        self.assertIn("# POPIA site check", md)
        self.assertIn("not legal advice", md)


class Plain(BaseHTTPRequestHandler):
    """Pages with no privacy notice link, with and without a way to collect personal information."""

    def do_GET(self):
        routes = {
            "/": (b'<a href="/map">Map</a><input type="hidden" name="t"><button>Go</button>', []),
            "/search": (b'<form action="/search" method="get"><input name="q"><select name="from_stop"></select></form>', []),
            "/form": (b'<form method="POST" action="/s"><button>Go</button></form>', []),
            "/textarea": (b"<form><textarea></textarea></form>", []),
            "/field": (b'<form><input name="full_name"></form>', []),
            "/frame-own": (b'<iframe src="/embed"></iframe>', []),
            "/frame": (b'<iframe src="https://video.example.net/embed/1"></iframe>', []),
            "/cookie": (b"<p>hi</p>", ["pref=1; Path=/; Secure; HttpOnly"]),
        }
        route = routes.get(self.path)
        if route is None:
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        for c in route[1]:
            self.send_header("Set-Cookie", c)
        self.end_headers()
        self.wfile.write(route[0])

    def log_message(self, *a):
        pass


class SeverityContextTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = HTTPServer(("127.0.0.1", 0), Plain)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.srv.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def finding(self, path, rid):
        res = site_check.check(self.base + path, timeout=5, probe_paths=False)
        return next(f for f in res["findings"] if f["rule_id"] == rid)

    def test_privacy_notice_is_medium_when_nothing_collects(self):
        f = self.finding("/", "WEB-015")
        self.assertEqual(f["severity"], "medium")
        self.assertIn("No forms for personal details, cookies or trackers", f["evidence"])
        self.assertIn("IP addresses", f["fix"])
        self.assertEqual(self.finding("/frame-own", "WEB-015")["severity"], "medium")
        self.assertEqual(self.finding("/search", "WEB-015")["severity"], "medium")  # a search box alone

    def test_privacy_notice_is_high_when_the_page_collects(self):
        for path in ("/form", "/textarea", "/field", "/frame", "/cookie"):
            self.assertEqual(self.finding(path, "WEB-015")["severity"], "high", path)

    def test_paia_finding_notes_non_business_projects(self):
        f = self.finding("/", "WEB-016")
        self.assertEqual(f["severity"], "medium")
        self.assertIn("not a business may not need one", f["fix"])


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
            self.assertIn("popia-kit scan .", ctx.exception.hint)
            self.assertIn(site_check.BOT_INFO_URL, ctx.exception.hint)

    def test_user_agent_names_the_checker_and_links_its_page(self):
        # Site owners allowlist or block on this token, so it must not change.
        self.assertTrue(site_check.UA.startswith("popia-site-check/"))
        self.assertIn(site_check.BOT_INFO_URL, site_check.UA)
        page = os.path.join(os.path.dirname(__file__), "..", "..", "docs", "site-check-bot.md")
        with open(page, encoding="utf-8") as f:
            self.assertIn(site_check.UA, f.read())

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


class Crawl(BaseHTTPRequestHandler):
    """A home page linking to same-site pages, one with a script from a CDN. robots.txt varies per test."""

    robots = (404, b"")

    def do_GET(self):
        pages = {
            "/": b'<a href="/map">Map</a><a href="/stops">Stops</a><a href="/away">Away</a><a href="/slow">Slow</a>',
            "/map": b'<script src="https://cdn.example.net/leaflet.js"></script>'
                    b'<script src="https://connect.facebook.net/en_US/fbevents.js"></script>',
            "/stops": b"<p>stops</p>",
            "/slow": b"<p>slow</p>",
        }
        if self.path == "/robots.txt":
            st, body = Crawl.robots
            self.send_response(st)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == "/away":
            self.send_response(302)
            self.send_header("Location", "http://localhost:1/")  # off the site: never graded
            self.end_headers()
            return
        body = pages.get(self.path)
        self.send_response(200 if body is not None else 404)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(body or b"")

    def log_message(self, *a):
        pass


class LinkedPagesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = HTTPServer(("127.0.0.1", 0), Crawl)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.srv.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def run_check(self, robots, pages=3):
        Crawl.robots = robots
        return site_check.check(self.base + "/", timeout=5, probe_paths=False, extra_pages=pages)

    def test_robots_rules(self):
        allowed = site_check.parse_robots("User-agent: *\nDisallow: /private\nAllow: /private/open\nDisallow: /*.php$\n")
        self.assertEqual([allowed(p) for p in ("/", "/private", "/private/x", "/private/open/1", "/a.php", "/a.php/b")],
                         [True, False, False, True, False, True])
        mine = site_check.parse_robots("User-agent: *\nDisallow: /\n\nUser-agent: popia-site-check\nAllow: /\n")
        self.assertTrue(mine("/map"))
        self.assertFalse(site_check.parse_robots("User-agent: popia-site-check\nUser-agent: other\nDisallow: /\n")("/m"))
        self.assertTrue(site_check.parse_robots("User-agent: *\nDisallow: /a\nAllow: /a\n")("/a"))
        self.assertTrue(site_check.parse_robots("User-agent: *\nDisallow:\n")("/x"))

    def test_pick_links_matches_the_hosted_check(self):
        page = site_check._PageParser()
        page.feed('<a href="/map">Map</a><a href="/map#top">Map again</a><a href="https://other.example.net/x">O</a>'
                  '<a href="/search?q=a">S</a><a href="/files/a.pdf">P</a><a href="/logout">Out</a>'
                  '<a href="/privacy">Privacy</a><a href="/">Home</a><a href="mailto:a@example.test">M</a>'
                  '<a href="/stops">Stops</a><a href="/routes/">Routes</a><a href="/about">About</a>')
        got = site_check.pick_links(page, "https://example.co.za/", 10)
        self.assertEqual(got, ["https://example.co.za/map", "https://example.co.za/stops",
                               "https://example.co.za/routes/", "https://example.co.za/about"])

    def test_linked_pages_are_checked_where_robots_allows(self):
        res = self.run_check((404, b""))
        self.assertEqual(res["pages_checked"], ["/", "/map", "/stops"])  # /away left the site, /slow is the 4th
        w23 = next(f for f in res["findings"] if f["rule_id"] == "WEB-023")
        self.assertEqual(w23["evidence"], "cdn.example.net (/map)")
        w14 = next(f for f in res["findings"] if f["rule_id"] == "WEB-014")
        self.assertEqual(w14["evidence"], "Meta Pixel on /map")
        self.assertIn("**Pages checked:** /, /map, /stops", site_check.fmt_md(res))

    def test_robots_disallow_and_server_error(self):
        res = self.run_check((200, b"User-agent: *\nDisallow: /map\n"))
        self.assertNotIn("/map", res["pages_checked"])
        self.assertNotIn("WEB-023", {f["rule_id"] for f in res["findings"]})
        self.assertEqual(self.run_check((503, b""))["pages_checked"], ["/"])

    def test_zero_pages_turns_it_off(self):
        self.assertEqual(self.run_check((404, b""), pages=0)["pages_checked"], ["/"])
