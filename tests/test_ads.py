import functools, http.server, tempfile, threading, unittest
from datetime import datetime
from pathlib import Path
from app import ads

GIF = b"GIF89a" + b"\x00" * 40


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass

    def list_directory(self, path):                  # no directory index: the numbered names are probed
        self.send_error(404)


class Ads(unittest.TestCase):
    def setUp(self):
        self.web, self.dst = tempfile.TemporaryDirectory(), tempfile.TemporaryDirectory()
        self.w, self.d = Path(self.web.name), Path(self.dst.name)
        h = functools.partial(Quiet, directory=self.web.name)
        self.srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), h)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.srv.server_address[1]}/"
        self.now = datetime(2026, 10, 18)

    def tearDown(self):
        self.srv.shutdown(); self.srv.server_close(); self.web.cleanup(); self.dst.cleanup()

    def test_numbered_download_refresh_and_cleanup(self):
        for i in (1, 2, 3):
            (self.w / f"tubearchivepro-2026-10_{i}.gif").write_bytes(GIF)
        (self.w / "tubearchivepro-2026-10_5.gif").write_bytes(GIF)       # after a gap: not looked for
        (self.d / "tubearchivepro-2026-09_1.gif").write_bytes(GIF)       # old month -> removed
        (self.d / "mine.gif").write_bytes(GIF)                           # own file -> kept
        r = ads.sync_ads(self.url, "tubearchivepro", self.d, self.now)
        self.assertEqual(r["downloaded"], 3)
        self.assertEqual(sorted(Path(p).name for p in r["files"]),
                         ["mine.gif"] + [f"tubearchivepro-2026-10_{i}.gif" for i in (1, 2, 3)])
        r = ads.sync_ads(self.url, "tubearchivepro", self.d, self.now)   # second run: nothing changed
        self.assertEqual(r["downloaded"], 0)
        self.assertEqual(len(r["files"]), 4)
        (self.w / "tubearchivepro-2026-10_2.gif").write_bytes(GIF + b"x" * 20)   # changed on the server
        import os; os.utime(self.w / "tubearchivepro-2026-10_2.gif", (4_000_000_000, 4_000_000_000))
        self.assertEqual(ads.sync_ads(self.url, "tubearchivepro", self.d, self.now)["downloaded"], 1)

    def test_directory_index_names(self):
        (self.w / "tubearchivepro-2026-10_summer.gif").write_bytes(GIF)
        (self.w / "tubearchivepro-2026-10_zebra.gif").write_bytes(GIF)
        (self.w / "tubearchivepro-2026-10_extra.gif").write_bytes(GIF)       # on the server but NOT paid / allowed
        (self.w / "tubearchivepro-2026-10.txt").write_text("summer\nzebra https://z.example\n")
        (self.w / "downloads_counter.txt").write_text("v1.0.12 = 100\nv1.0.14 = 50\n")
        (self.w / "index.html").write_text('<a href="tubearchivepro-2026-10_summer.gif">a</a>'
                                           '<a href="tubearchivepro-2026-10_zebra.gif">b</a>'
                                           '<a href="tubearchivepro-2026-10_extra.gif">c</a>'
                                           '<a href="tubearchivepro-2026-10.txt">t</a>'
                                           '<a href="downloads_counter.txt">n</a>')
        (self.d / "tubearchivepro-2026-10_old.gif").write_bytes(GIF)           # downloaded before, not allowed any more
        cache = self.d / "cache"
        r = ads.sync_ads(self.url, "tubearchivepro", self.d, self.now, cache_dir=cache)
        self.assertEqual(r["downloaded"], 2)
        self.assertEqual(sorted(Path(p).name for p in r["files"]),
                         ["tubearchivepro-2026-10_summer.gif", "tubearchivepro-2026-10_zebra.gif"])
        self.assertFalse((self.d / "tubearchivepro-2026-10_old.gif").exists())
        self.assertEqual(r["counter"]["total"], 150)
        self.assertEqual(ads.load_counter(cache, self.d / "none")["total"], 150)     # kept for the next offline start
        (self.w / "tubearchivepro-2026-10.txt").write_text("summer\n")              # zebra is no longer paid
        r = ads.sync_ads(self.url, "tubearchivepro", self.d, self.now, cache_dir=cache)
        self.assertEqual([Path(p).name for p in r["files"]], ["tubearchivepro-2026-10_summer.gif"])
        self.assertEqual([Path(p).name for p in ads.local_ads(self.d, self.now)], ["tubearchivepro-2026-10_summer.gif"])
        self.assertEqual(ads.local_ads(self.d, datetime(2026, 11, 2)), [])            # next month: nothing allowed yet
        (self.w / "tubearchivepro-2026-10.txt").unlink()                              # no list at all -> every ad of the month is shown (2.0.2)
        (self.w / "index.html").write_text('<a href="tubearchivepro-2026-10_summer.gif">a</a>')
        r = ads.sync_ads(self.url, "tubearchivepro", self.d, self.now, cache_dir=cache)
        self.assertEqual([Path(p).name for p in r["files"]], ["tubearchivepro-2026-10_summer.gif"])

    def test_read_text_file_and_cache(self):
        (self.w / "reviews.txt").write_text("Great app\nSabry")
        (self.w / "index.html").write_text('<a href="reviews.txt">r</a>')
        cache = self.d / "cache"
        r = ads.fetch_remote_text(self.url, "reviews.txt", "reviews.txt", cache)
        self.assertEqual((r["text"], r["cached"]), ("Great app\nSabry", False))
        r = ads.fetch_remote_text("http://127.0.0.1:1/", "reviews.txt", "reviews.txt", cache)     # offline: old copy
        self.assertEqual((r["text"], r["cached"]), ("Great app\nSabry", True))
        self.assertEqual(ads.fetch_remote_text("http://127.0.0.1:1/", "x.txt", "x.txt", cache)["text"], "")

    def test_counter_parsing(self):
        self.assertEqual(ads.parse_counter("old versions: 1,250\nv1.0.14 = 30\n# note")["total"], 1280)
        self.assertEqual(ads.parse_counter("total = 999\nv1 = 5")["total"], 999)
        self.assertEqual(ads.parse_counter("")["total"], 0)
        self.assertIsNone(ads.load_counter(self.d / "nocache", self.d / "nobase"))
        (self.d / "base.txt").write_text("old = 400")
        self.assertEqual(ads.load_counter(self.d / "nocache", self.d / "base.txt")["total"], 400)

    def test_offline_keeps_old_files_and_bad_gif_ignored(self):
        (self.d / "tubearchivepro-2026-09_1.gif").write_bytes(GIF)
        (self.w / "tubearchivepro-2026-10_1.gif").write_bytes(b"not a gif")
        r = ads.sync_ads(self.url, "tubearchivepro", self.d, self.now)
        self.assertEqual(r["downloaded"], 0)
        self.assertEqual(len(r["files"]), 1)                              # nothing valid found -> old ad stays
        self.assertEqual(ads.sync_ads("", "x", self.d)["downloaded"], 0)
        self.assertEqual(ads.sync_ads("http://127.0.0.1:1/", "tubearchivepro", self.d, self.now)["downloaded"], 0)


class Share(Ads):
    """Folder page + file pages like 4shared: names without extension, the picture address is inside the file page."""

    def test_folder_page_version_and_pages(self):
        base = self.url
        (self.w / "p1.html").write_text(f'<img src="{base}img1/x/TubeArchivePro-2026-10_1">')
        (self.w / "img1").mkdir(); (self.w / "img1" / "x").mkdir()
        (self.w / "folder.html").write_text(
            f'<a href="{base}photo/A/TubeArchivePro-2026-10_1.html">TubeArchivePro-2026-10_1.gif</a> 9,542 KB'
            f'<a href="{base}file/B/tubearchivepro_v1_0_13.html">tubearchivepro_v1.0.13.exe</a>'
            f'<a href="{base}file/C/tubearchivepro_v1_0_9.html">tubearchivepro_v1.0.9.exe</a>'
            f'<a href="{base}photo/D/TubeArchivePro-2026-09_1.html">TubeArchivePro-2026-09_1.gif</a>')
        from app import ads as A
        e = A.list_remote((self.w / "folder.html").read_text(), self.url)
        self.assertEqual(A.parse_version("tubearchivepro_v1.0.13.exe"), (1, 0, 13))
        self.assertEqual(A.parse_version("tubearchivepro_v1_0_13"), (1, 0, 13))
        self.assertIsNone(A.parse_version("TubeArchivePro-2026-10_1.gif"))
        v, ent = A.newest_version(e, (1, 0, 12))
        self.assertEqual((v, ent["name"].split(".html")[0]), ((1, 0, 13), "tubearchivepro_v1_0_13"))
        self.assertEqual(A.newest_version(e, (1, 0, 13)), (None, None))              # not higher: no message
        self.assertEqual([x["file"] for x in A.pick(e, "tubearchivepro-2026-10")], ["TubeArchivePro-2026-10_1.gif"])
        self.assertEqual(A.pick(e, "tubearchivepro-2026-10")[0]["size"], 9542 * 1024)

    def test_sync_with_version_and_cleanup(self):
        (self.w / "TubeArchivePro-2026-10_1.gif").write_bytes(GIF)
        (self.w / "TubeArchivePro-2026-10_2.gif").write_bytes(GIF)
        (self.w / "tubearchivepro_v1.0.13.exe").write_bytes(b"MZ")
        (self.w / "tubearchivepro-2026-10.txt").write_text("1\n2\n")
        (self.w / "index.html").write_text('<a href="TubeArchivePro-2026-10_1.gif">a</a><a href="TubeArchivePro-2026-10_2.gif">b</a>'
                                           '<a href="tubearchivepro_v1.0.13.exe">c</a><a href="TubeArchivePro-2026-09_7.gif">old</a>'
                                           '<a href="tubearchivepro-2026-10.txt">t</a>')
        (self.d / "TubeArchivePro-2026-09_7.gif").write_bytes(GIF)
        r = ads.sync_ads(self.url, "tubearchivepro", self.d, self.now, current_version=(1, 0, 12))
        self.assertEqual((r["downloaded"], r["version"]), (2, "1.0.13"))
        self.assertEqual(sorted(Path(p).name for p in r["files"]), ["TubeArchivePro-2026-10_1.gif", "TubeArchivePro-2026-10_2.gif"])
        self.assertEqual(ads.sync_ads(self.url, "tubearchivepro", self.d, self.now, current_version=(1, 0, 13))["version"], "")


Share.test_numbered_download_refresh_and_cleanup = None
Share.test_directory_index_names = None
Share.test_offline_keeps_old_files_and_bad_gif_ignored = None
Share.test_read_text_file_and_cache = None
Share.test_counter_parsing = None


class Drive(unittest.TestCase):
    PAGE = "".join(f'<div class="flip-entry" id="entry-{i}"><a href="https://drive.google.com/file/d/{i}/view?usp=drive_web">'
                   f'<div class="flip-entry-title">{n}</div></a></div>' for i, n in (
        ("AAA1", "TubeArchivePro-2026-10_1.gif"), ("AAA2", "TubeArchivePro-2026-10_2.gif"),
        ("AAA3", "TubeArchivePro-2026-10_1.txt"), ("AAA4", "TubeArchivePro-2026-10_links.txt"),
        ("AAA5", "TubeArchivePro-2026-09_1.gif"), ("AAA6", "tubearchivepro_v1.0.14.exe"), ("AAA7", "tubearchivepro_v1.0.12.exe"),
        ("AAA8", "TubeArchivePro-2026-10.txt"), ("AAA9", "TubeArchivePro-2026-10_3.gif"), ("AABA", "downloads_counter.txt")))
    FILES = {"AAA1": GIF, "AAA2": GIF + b"2", "AAA3": b"\xef\xbb\xbfhttps://one.example/a?x=1\n",
             "AAA4": b"TubeArchivePro-2026-10_2.gif = https://two.example\n", "AAA5": GIF,
             "AAA8": b"TubeArchivePro-2026-10_1.gif\nTubeArchivePro-2026-10_2.gif\n", "AAA9": GIF + b"3",
             "AABA": b"v1.0.12 = 100\nv1.0.14 = 20\n"}

    def setUp(self):
        self.dst = tempfile.TemporaryDirectory()
        self.d = Path(self.dst.name)
        self._page, self._open = ads._page, ads._open
        ads._page = lambda url: self.PAGE
        outer = self

        class R:
            def __init__(s, data): s.data = data
            def __enter__(s): return s
            def __exit__(s, *a): return False
            def read(s, n=-1): return s.data[:n] if n >= 0 else s.data
        def fake_open(url, headers=None, timeout=15):
            import re
            fid = re.search(r"id=([\w-]+)", url).group(1)
            return R(outer.FILES[fid])
        ads._open = fake_open

    def tearDown(self):
        ads._page, ads._open = self._page, self._open
        self.dst.cleanup()

    def test_drive_folder_ads_links_and_version(self):
        url = "https://drive.google.com/drive/folders/1vbPXUkyWrVTcZql-uzIeYCVzD03_KzfK?usp=sharing"
        self.assertEqual(ads.drive_folder_id(url), "1vbPXUkyWrVTcZql-uzIeYCVzD03_KzfK")
        (self.d / "tubearchivepro-2026-09_1.gif").write_bytes(GIF)                     # old month: removed
        cache = self.d / "cache"
        r = ads.sync_ads(url, "tubearchivepro", self.d, datetime(2026, 10, 18), current_version=(1, 0, 13), cache_dir=cache)
        self.assertEqual((r["downloaded"], r["version"]), (2, "1.0.14"))      # _3.gif is on Drive but not in the allowed list
        self.assertEqual(r["counter"]["total"], 120)
        self.assertTrue(r["version_url"].endswith("/file/d/AAA6/view"))
        self.assertEqual(sorted(Path(p).name for p in r["files"]), ["TubeArchivePro-2026-10_1.gif", "TubeArchivePro-2026-10_2.gif"])
        links = {Path(p).name: u for p, u in r["links"].items()}
        self.assertEqual(links, {"TubeArchivePro-2026-10_1.gif": "https://one.example/a?x=1",
                                 "TubeArchivePro-2026-10_2.gif": "https://two.example"})
        r = ads.sync_ads(url, "tubearchivepro", self.d, datetime(2026, 10, 18), current_version=(1, 0, 14), cache_dir=cache)
        self.assertEqual((r["downloaded"], r["version"]), (0, ""))                      # same files, no newer version
        self.assertEqual(len(r["links"]), 2)

    def test_link_parsing_variants(self):
        g = ["t-2026-10_1.gif", "t-2026-10_2.gif", "t-2026-10_10.gif"]
        self.assertEqual(ads.parse_links({"t-2026-10.txt": "https://a.x\nhttps://b.x\nhttps://c.x"}, g),
                         {"t-2026-10_1.gif": "https://a.x", "t-2026-10_2.gif": "https://b.x", "t-2026-10_10.gif": "https://c.x"})
        self.assertEqual(ads.parse_links({"t-2026-10.txt": "10: https://c.x\n1 - https://a.x"}, g),
                         {"t-2026-10_10.gif": "https://c.x", "t-2026-10_1.gif": "https://a.x"})
        self.assertEqual(ads.parse_links({"t-2026-10_2.txt": "see https://b.x now"}, g), {"t-2026-10_2.gif": "https://b.x"})


if __name__ == "__main__":
    unittest.main()
