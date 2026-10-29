"""2.3.0: tool updates (yt-dlp / ffmpeg) against a local server."""
import hashlib
import http.server
import io
import json
import sys
import tempfile
import threading
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app import toolupdate as tu                                    # noqa: E402

YT = b"MZ fake yt-dlp " * 1000
ZIP = io.BytesIO()
with zipfile.ZipFile(ZIP, "w") as z:
    for n in ("ffmpeg.exe", "ffprobe.exe", "ffplay.exe"):
        z.writestr("ffmpeg-master/bin/" + n, b"bin " + n.encode())
    z.writestr("ffmpeg-master/doc/readme.txt", b"x")
ZIPB = ZIP.getvalue()


class H(http.server.BaseHTTPRequestHandler):
    base = ""
    bad_sum = False

    def log_message(self, *a):
        pass

    def do_GET(self):
        p = self.path
        if p == "/yt":
            body = json.dumps({"tag_name": "2026.10.20", "assets": [
                {"name": "yt-dlp.exe", "size": len(YT), "browser_download_url": H.base + "/yt.exe"},
                {"name": "SHA2-256SUMS", "browser_download_url": H.base + "/sums"}]}).encode()
        elif p == "/ff":
            body = json.dumps({"published_at": "2026-10-01T00:00:00Z", "assets": [
                {"name": tu.FFMPEG_ASSET, "size": len(ZIPB), "updated_at": "2026-10-20T10:00:00Z",
                 "browser_download_url": H.base + "/ff.zip"}]}).encode()
        elif p == "/yt.exe":
            body = YT
        elif p == "/ff.zip":
            body = ZIPB
        elif p == "/sums":
            h = "0" * 64 if H.bad_sum else hashlib.sha256(YT).hexdigest()
            body = f"{h} *yt-dlp.exe\n".encode()
        else:
            self.send_error(404)
            return
        self.send_response(200); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)


class ToolUpdate(unittest.TestCase):
    def setUp(self):
        self.srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        H.base = f"http://127.0.0.1:{self.srv.server_address[1]}"
        H.bad_sum = False
        self.dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        self.srv.shutdown(); self.srv.server_close()

    def test_check_and_install(self):
        items = tu.check_tools(None, None, self.dir, H.base + "/yt", H.base + "/ff")
        self.assertEqual([i["key"] for i in items], ["yt-dlp", "ffmpeg"])           # nothing installed: both offered
        self.assertEqual(items[0]["new"], "2026.10.20")
        seen = []
        tu.update_tools(items, lambda d, t: seen.append((d, t)), folder=self.dir)
        self.assertEqual((self.dir / "yt-dlp.exe").read_bytes(), YT)
        self.assertEqual(sorted(p.name for p in self.dir.iterdir()),
                         ["ffmpeg.exe", "ffplay.exe", "ffprobe.exe", "tools.json", "yt-dlp.exe"])
        self.assertEqual(seen[0][0], 0)
        self.assertEqual(seen[-1][0], seen[-1][1])                                    # one running total, ends at 100 %
        self.assertTrue(all(d <= t for d, t in seen))
        # ffmpeg is recorded -> not offered again; yt-dlp with the same version -> up to date
        ff = self.dir / "ffmpeg.exe"
        self.assertIsNone(tu.check_ffmpeg(str(ff), self.dir, H.base + "/ff"))
        orig = tu.ytdlp_version
        tu.ytdlp_version = lambda exe: "2026.10.20"
        try:
            self.assertEqual(tu.check_tools(str(ff), str(ff), self.dir, H.base + "/yt", H.base + "/ff"), [])
        finally:
            tu.ytdlp_version = orig

    def test_hand_made_ffmpeg_is_accepted(self):
        self.assertIsNone(tu.check_ffmpeg("C:/tools/ffmpeg.exe", self.dir, H.base + "/ff"))

    def test_checksum_mismatch_keeps_old_file(self):
        (self.dir / "yt-dlp.exe").write_bytes(b"old")
        H.bad_sum = True
        items = tu.check_tools(None, "x", self.dir, H.base + "/yt", H.base + "/ff")[:1]
        with self.assertRaises(tu.UpdateError):
            tu.update_tools(items, folder=self.dir)
        self.assertEqual((self.dir / "yt-dlp.exe").read_bytes(), b"old")

    def test_cancel(self):
        items = tu.check_tools(None, "x", self.dir, H.base + "/yt", H.base + "/ff")[:1]
        with self.assertRaises(tu.Cancelled):
            tu.update_tools(items, cancelled=lambda: True, folder=self.dir)
        self.assertFalse((self.dir / "yt-dlp.exe").exists())

    def test_release_unreadable(self):
        with self.assertRaises(tu.UpdateError):
            tu.check_tools(None, None, self.dir, H.base + "/nothing", H.base + "/ff")


if __name__ == "__main__":
    unittest.main()
