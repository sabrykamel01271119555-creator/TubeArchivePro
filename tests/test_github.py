"""GitHub as the online folder (2.2.0): folder listing, releases -> version + downloads counter, download_count of one file.
A local web server plays api.github.com (the real one cannot be reached from the test machine)."""
import functools
import http.server
import json
import tempfile
import threading
import unittest
from datetime import datetime
from pathlib import Path

from app import ads

GIF = b"GIF89a" + b"\x00" * 40


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def release(tag, assets, pre=False, draft=False):
    return {"tag_name": tag, "prerelease": pre, "draft": draft, "html_url": f"https://github.com/me/app/releases/tag/{tag}",
            "assets": [{"name": n, "download_count": c, "browser_download_url": f"https://github.com/me/app/releases/download/{tag}/{n}"}
                       for n, c in assets]}


class GitHub(unittest.TestCase):
    def setUp(self):
        self.web, self.dst = tempfile.TemporaryDirectory(), tempfile.TemporaryDirectory()
        self.w, self.d = Path(self.web.name), Path(self.dst.name)
        srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=self.web.name))
        self.srv = srv
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        self.root = f"http://127.0.0.1:{srv.server_address[1]}"
        self.old_api, ads.GITHUB_API = ads.GITHUB_API, self.root
        (self.w / "raw").mkdir()
        (self.w / "raw" / "TubeArchivePro-2026-10_1.gif").write_bytes(GIF)
        (self.w / "raw" / "tubearchivepro-2026-10.txt").write_text("1\n")
        (self.w / "raw" / "downloads_counter.txt").write_text("old versions: 1,250\n")
        files = [{"name": n, "type": "file", "size": (self.w / "raw" / n).stat().st_size,
                  "download_url": f"{self.root}/raw/{n}"} for n in sorted(p.name for p in (self.w / "raw").iterdir())]
        files.append({"name": "sub", "type": "dir", "size": 0, "download_url": None})
        d = self.w / "repos" / "me" / "app"
        (d / "contents").mkdir(parents=True)
        (d / "contents" / "online").write_text(json.dumps(files))
        (d / "releases").write_text(json.dumps([
            release("v2.1.0", [("TubeArchivePro_Setup_2.1.0.exe", 40), ("TubeArchivePro_2.1.0.zip", 77), ("TubeArchivePro_Setup_2.1.0.exe.sha256", 9)]),
            release("v2.2.0-beta", [("TubeArchivePro_Setup_2.2.0.exe", 5)], pre=True),
            release("v2.0.0", [("TubeArchivePro_Setup_2.0.0.exe", 100)]),
            release("v9.9.9", [("x.zip", 1000)], draft=True)]))
        self.base = "https://github.com/me/app/tree/main/online"

    def tearDown(self):
        ads.GITHUB_API = self.old_api
        self.srv.shutdown(); self.srv.server_close(); self.web.cleanup(); self.dst.cleanup()

    def test_parse(self):
        self.assertEqual(ads.parse_github("https://github.com/me/app"), {"owner": "me", "repo": "app", "ref": "", "path": ""})
        self.assertEqual(ads.parse_github(self.base)["path"], "online")
        self.assertTrue(ads.is_github(self.base) and not ads.is_github("https://drive.google.com/x"))

    def test_stats_and_file_count(self):
        rel = ads.github_releases(self.base)
        self.assertEqual(len(rel), 3)                                   # the draft is ignored
        st = ads.github_stats(rel, (2, 0, 0))
        self.assertEqual((st["version"], st["total"]), ("2.1.0", 145))  # only the .exe setups are counted (zip / checksum not), beta never offered
        self.assertEqual(ads.github_stats(rel, (2, 1, 0))["version"], "")
        self.assertEqual(ads.asset_downloads(rel, "TubeArchivePro_Setup_2.1.0.exe"), 40)
        self.assertEqual(ads.file_download_count(self.base, "tubearchivepro_setup_2.0.0.EXE"), 100)

    def test_sync_ads_from_github(self):
        r = ads.sync_ads(self.base, "tubearchivepro", self.d, datetime(2026, 10, 18), current_version=(2, 0, 0),
                         cache_dir=self.d / "cache")
        self.assertEqual(r["downloaded"], 1)
        self.assertEqual(r["version"], "2.1.0")
        self.assertIn("TubeArchivePro_Setup_2.1.0.exe", r["version_url"])
        self.assertEqual(r["counter"]["total"], 145 + 1250)             # releases + 'earlier' total of downloads_counter.txt
        self.assertEqual([Path(p).name for p in r["files"]], ["TubeArchivePro-2026-10_1.gif"])

    def _publish_gif(self, data: bytes, sha: str):
        """Replace the online ad (same name) and its fingerprint in the fake contents listing."""
        (self.w / "raw" / "TubeArchivePro-2026-10_1.gif").write_bytes(data)
        p = self.w / "repos" / "me" / "app" / "contents" / "online"
        files = json.loads(p.read_text())
        for f in files:
            if f["name"] == "TubeArchivePro-2026-10_1.gif":
                f["sha"], f["size"] = sha, len(data)
        p.write_text(json.dumps(files))

    def test_changed_ad_is_downloaded_unchanged_is_not(self):
        """Every start: an ad whose online fingerprint (sha) differs from the stored one is downloaded again - even with the
        same size; an unchanged one is not downloaded."""
        run = lambda: ads.sync_ads(self.base, "tubearchivepro", self.d, datetime(2026, 10, 18), current_version=(2, 0, 0),
                                   cache_dir=self.d / "cache")
        self._publish_gif(GIF, "sha-1")
        self.assertEqual(run()["downloaded"], 1)
        self.assertEqual(run()["downloaded"], 0)                         # same sha: nothing to do
        new = b"GIF89a" + b"\x01" * 40                                    # same size, other picture
        self._publish_gif(new, "sha-2")
        self.assertEqual(run()["downloaded"], 1)
        self.assertEqual((self.d / "TubeArchivePro-2026-10_1.gif").read_bytes(), new)
        self.assertEqual(run()["downloaded"], 0)

    def test_ad_list_and_folder_exe(self):
        """2.2.6: 'number source url' lines of the month's txt; the update = a TubeArchivePro x.y.z.exe file of the folder."""
        (self.w / "raw" / "TubeArchivePro-2026-10.txt").write_text(
            f"# ads of october\n2  {self.root}/raw/b.png  https://two.example/\n1, {self.root}/raw/a.gif, https://one.example/\n")
        (self.w / "raw" / "a.gif").write_bytes(GIF)
        (self.w / "raw" / "b.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 30)
        (self.w / "raw" / "TubeArchivePro 2.5.0.exe").write_bytes(b"MZ")
        files = [{"name": n.name, "type": "file", "size": n.stat().st_size, "download_url": f"{self.root}/raw/{n.name}"}
                 for n in sorted((self.w / "raw").iterdir())]
        (self.w / "repos" / "me" / "app" / "contents" / "online").write_text(json.dumps(files))
        run = lambda: ads.sync_ads(self.base, "tubearchivepro", self.d, datetime(2026, 10, 18), current_version=(2, 2, 6),
                                   cache_dir=self.d / "cache")
        r = run()
        self.assertEqual((r["version"], r["downloaded"]), ("2.5.0", 2))
        self.assertTrue(r["version_url"].endswith("TubeArchivePro%202.5.0.exe") or r["version_url"].endswith("TubeArchivePro 2.5.0.exe"))
        self.assertEqual([Path(p).name for p in r["files"]], ["tubearchivepro-2026-10_01.gif", "tubearchivepro-2026-10_02.gif"])
        self.assertEqual(sorted(r["links"].values()), ["https://one.example/", "https://two.example/"])
        self.assertEqual(run()["downloaded"], 0)                                      # unchanged sources: nothing new
        self.assertEqual(run()["version"], "2.5.0")
        self.assertEqual(ads.parse_version("TubeArchivePro_Setup_2.6.1.exe"), (2, 6, 1))
        self.assertEqual(ads.direct_url("https://github.com/o/r/blob/main/a/b.gif"), "https://raw.githubusercontent.com/o/r/main/a/b.gif")
        self.assertEqual(ads.parse_ad_list("1 https://x/y.txt"), [])                  # old format: one address, not an image

    def test_total_users_file_gives_users_per_version(self):
        """2.2.8: total_users.txt + the .exe download counts = the counter with a list per version (splash screen)."""
        (self.w / "raw" / "total_users.txt").write_text("1.0.0 = 25\n2.0.0 = 5\n2.1.0 = 1\n")
        files = [{"name": n.name, "type": "file", "size": n.stat().st_size, "download_url": f"{self.root}/raw/{n.name}"}
                 for n in sorted((self.w / "raw").iterdir())]
        (self.w / "repos" / "me" / "app" / "contents" / "online").write_text(json.dumps(files))
        r = ads.sync_ads(self.base, "tubearchivepro", self.d, datetime(2026, 10, 18), current_version=(2, 0, 0),
                         cache_dir=self.d / "cache")
        c = r["counter"]
        # releases: v2.1.0 exe 40 (the file's 1 is ignored), v2.0.0 exe 100 (the file's 5 is ignored), 1.0.0 only in the file (25)
        self.assertEqual(c["versions"], [("1.0.0", 25), ("2.0.0", 100), ("2.1.0", 40), ("2.2.0", 5)])   # (the beta counts too)
        self.assertEqual(c["total"], 170)
        self.assertEqual(ads.load_counter(self.d / "cache")["versions"][0], ("1.0.0", 25))

    def test_rate_limit_message(self):
        ads.GITHUB_API = self.root + "/nothing"
        with self.assertRaises(OSError):
            ads.github_releases(self.base)


if __name__ == "__main__":
    unittest.main()
