"""2.2.8: users per version (release .exe counts + total_users.txt), splash numbers, rating cache, feedback endpoint."""
import functools
import http.server
import json
import tempfile
import threading
import unittest
from pathlib import Path

from app import ads, stats
from app.feedback import FeedbackManager, post_json


def rel(tag, assets):
    return {"tag_name": tag, "assets": [{"name": n, "download_count": c} for n, c in assets]}


class Users(unittest.TestCase):
    def test_parse_and_build(self):
        totals = ads.parse_user_totals("1.0.0 = 25\n1.0.2 = 22\n# x\nv2.0.1: 65\n2.2.3 = 72\nbad line\n")
        self.assertEqual(totals, {(1, 0, 0): 25, (1, 0, 2): 22, (2, 0, 1): 65, (2, 2, 3): 72})
        rels = [rel("v2.2.3", [("TubeArchivePro_Setup_2.2.3.exe", 100), ("x.zip", 999)]),
                rel("v2.2.4", [("TubeArchivePro_Setup_2.2.4.exe", 7)]), rel("v1.0.2", [("notes.txt", 3)])]
        s = ads.build_user_stats(rels, totals)
        # 2.2.3 has an .exe file -> its download count (100) wins over the file (72); 1.0.2 has no .exe -> the file (22)
        self.assertEqual(s["versions"], [("1.0.0", 25), ("1.0.2", 22), ("2.0.1", 65), ("2.2.3", 100), ("2.2.4", 7)])
        self.assertEqual(s["total"], 25 + 22 + 65 + 100 + 7)

    def test_splash_numbers_and_rating_cache(self):
        with tempfile.TemporaryDirectory() as d:
            cache = Path(d)
            base = Path(d) / "b.json"
            base.write_text(json.dumps({"versions": [["2.0.0", 5], ["1.0.0", 10]]}))
            first = stats.users_data(cache, base)                       # nothing cached: the shipped baseline, old -> new
            self.assertEqual(first, {"total": 15, "versions": [("1.0.0", 10), ("2.0.0", 5)]})
            (cache / stats.USERS_FILE).write_text(json.dumps({"users": 4, "versions": {"2.0.0": 1, "2.3.0": 3}}))
            # old numbers + the register: 2.0.0 5+1, 2.3.0 3
            self.assertEqual(stats.users_data(cache, base),
                             {"total": 19, "versions": [("1.0.0", 10), ("2.0.0", 6), ("2.3.0", 3)]})
            (cache / stats.BASE_FILE).write_text(json.dumps({"versions": [["1.0.0", 30]]}))   # online base wins over the shipped one
            self.assertEqual(stats.users_data(cache, base)["total"], 30 + 1 + 3)
            self.assertIsNone(stats.load_rating(cache))


class Quiet(http.server.BaseHTTPRequestHandler):
    seen = []

    def log_message(self, *a):
        pass

    def do_GET(self):
        if "action=reviews" in self.path:
            body = json.dumps({"reviews": [{"rating": 5, "feedback": "great", "date": "2026-10-20 10:00:00", "country": "EG", "version": "2.3.1"},
                                           {"rating": 9, "feedback": "bad row"}]}).encode()
            self.send_response(200); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
            return
        body = json.dumps({"average": 4.55, "count": 12, "users": 4, "versions": {"2.3.0": 4}} if "action=stats" in self.path else {"status": "x"}).encode()
        self.send_response(200); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        Quiet.seen.append(json.loads(self.rfile.read(n).decode("utf-8")))
        body = b'{"status": "success"}'
        self.send_response(200); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)


class Endpoint(unittest.TestCase):
    def setUp(self):
        self.srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Quiet)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.srv.server_address[1]}/exec"

    def tearDown(self):
        self.srv.shutdown(); self.srv.server_close()

    def test_rating_stats_and_send(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(stats.fetch_rating(self.url, Path(d)), {"average": 4.55, "count": 12})
            self.assertEqual(stats.load_rating(Path(d)), {"average": 4.55, "count": 12})
            self.assertEqual(stats.users_data(Path(d), Path(d) / "none.json")["versions"], [("2.3.0", 4)])
            fb = FeedbackManager(Path(d) / "h.json", Path(d) / "my.json")
            self.assertTrue(fb.save_rating(5, "great", "2.2.8", "a player please"))
            self.assertTrue(fb.send_endpoint(self.url, "ar"))
            got = Quiet.seen[-1]
            self.assertEqual((got["rating"], got["feedback"], got["new_features"], got["language"], got["version"]),
                             (5, "great", "a player please", "ar", "2.2.8"))
            self.assertEqual(got["new_features"], "a player please")
            self.assertRegex(got["rating_date"], r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")
            self.assertRegex(got["installation_date"], r"^\d{4}-\d{2}-\d{2}")
            self.assertTrue(got["os"])
            self.assertEqual(got["install_id"], fb.install_id())
            self.assertTrue(fb.current()["sent"])
            self.assertFalse(fb.save_rating(5, "great", "2.2.8", "a player please"))   # unchanged and sent: nothing to send
            self.assertTrue(fb.save_rating(5, "great", "2.2.8", "something else"))      # features changed: send again
        self.assertFalse(post_json("http://127.0.0.1:9/none", {"a": 1}, timeout=1))

    def test_reviews_of_the_sheet(self):
        with tempfile.TemporaryDirectory() as d:
            rows = stats.fetch_reviews(self.url, Path(d))
            self.assertEqual([(r["rating"], r["feedback"], r["country"]) for r in rows], [(5, "great", "EG")])   # the bad row is dropped
            self.assertEqual(stats.load_reviews(Path(d)), rows)                                                   # cached for offline
            self.assertIsNone(stats.fetch_reviews("https://example.com/x", Path(d)))
            self.assertEqual(stats.load_reviews(Path(d) / "none"), [])

    def test_other_json_names_from_settings(self):
        with tempfile.TemporaryDirectory() as d:
            fb = FeedbackManager(Path(d) / "h.json", Path(d) / "my.json")
            fb.save_rating(4, "ok", "2.2.9", "")
            self.assertTrue(fb.send_endpoint(self.url, "en", {"rating": "stars", "new_features": "wishes"}))
            got = Quiet.seen[-1]
            self.assertEqual((got["stars"], got["wishes"]), (4, ""))
            from app.feedback import is_script_url
            self.assertTrue(is_script_url("https://script.google.com/macros/s/X/exec"))
            self.assertFalse(is_script_url("https://docs.google.com/forms/d/e/X/viewform"))


if __name__ == "__main__":
    unittest.main()
