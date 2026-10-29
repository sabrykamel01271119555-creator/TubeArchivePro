"""Exit rating: kept locally, shown again, sent to the Google form only when new or changed (2.0.2)."""
import http.server
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.parse import parse_qs

from app.feedback import FeedbackManager, form_response_url, post_form


class Handler(http.server.BaseHTTPRequestHandler):
    got = []

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        Handler.got.append((self.path, parse_qs(self.rfile.read(n).decode())))
        self.send_response(200)
        self.end_headers()

    def log_message(self, *a):
        pass


class FeedbackTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        d = Path(self.tmp.name)
        self.fb = FeedbackManager(d / "feedback.json", d / "my_rating.json")
        Handler.got = []
        self.srv = http.server.HTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.srv.server_port}/forms/d/e/X/viewform?usp=sf"
        self.fields = {"rating": "entry.1", "comment": "entry.2", "version": "entry.3"}

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()
        self.tmp.cleanup()

    def test_url(self):
        self.assertEqual(form_response_url("https://docs.google.com/forms/d/e/X/viewform?usp=sf"),
                         "https://docs.google.com/forms/d/e/X/formResponse")

    def test_flow(self):
        self.assertIsNone(self.fb.current())
        self.assertTrue(self.fb.save_rating(4, "good", "2.0.2"))
        self.assertEqual(self.fb.current()["rating"], 4)
        self.assertFalse(self.fb.current()["sent"])
        self.assertTrue(self.fb.send(self.url, self.fields))
        self.assertEqual(Handler.got[0][0], "/forms/d/e/X/formResponse")
        self.assertEqual(Handler.got[0][1]["entry.1"], ["4"])
        self.assertEqual(Handler.got[0][1]["entry.2"], ["good"])
        self.assertTrue(self.fb.current()["sent"])
        self.assertFalse(self.fb.save_rating(4, "good", "2.0.2"))          # unchanged: nothing to send
        self.assertTrue(self.fb.save_rating(5, "good", "2.0.2"))           # changed: send again
        self.assertFalse(self.fb.current()["sent"])
        self.assertTrue(self.fb.send(self.url, self.fields))
        self.assertEqual(len(Handler.got), 2)

    def test_no_form_or_offline_keeps_it_pending(self):
        self.fb.save_rating(3, "", "2.0.2")
        self.assertFalse(self.fb.send("", self.fields))
        self.assertFalse(post_form("http://127.0.0.1:9/x", self.fields, {"rating": 3}, timeout=1))
        self.assertFalse(self.fb.current()["sent"])
        self.assertTrue(self.fb.save_rating(3, "", "2.0.2"))               # still pending -> tried again next time


if __name__ == "__main__":
    unittest.main()
