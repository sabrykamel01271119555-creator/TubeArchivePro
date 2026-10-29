"""History + favorites (no Qt):  python -m unittest discover -s tests"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import app.favorites as fav_mod                       # noqa: E402
import app.history as hist_mod                        # noqa: E402
import app.sync as sync_mod                           # noqa: E402
from datetime import datetime                        # noqa: E402


class HistoryTests(unittest.TestCase):
    def setUp(self):
        d = Path(tempfile.mkdtemp())
        hist_mod.HISTORY_FILE, hist_mod.THUMBS_DIR = d / "h" / "history.json", d / "h" / "thumbs"
        fav_mod.FAVORITES_FILE = d / "f" / "favorites.json"
        sync_mod.SYNC_FILE = d / "s" / "sync.json"
        self.h = hist_mod.HistoryManager()
        self.h.load()
        self.f = fav_mod.FavoritesManager()

    def rec(self, title, date, thumb=None):
        r = self.h.new_record(url="https://x/" + title, title=title, file_name=title + ".mp4", save_dir="D:/v",
                              fmt="mp4", quality="1080p", quality_value=1080, size=1000, thumb_bytes=thumb)
        r["date"] = date
        return r

    def test_record_fields_and_thumb(self):
        r = self.rec("a", "2026-10-01 10:00", b"imgdata")
        self.assertEqual((r["extension"], r["format"], r["quality_value"]), ("mp4", "MP4", 1080))
        self.assertEqual(Path(self.h.thumb_path(r)).read_bytes(), b"imgdata")
        self.assertIsNone(self.h.thumb_path(self.rec("b", "2026-10-02 10:00")))

    def test_newest_first_and_persistence(self):
        self.rec("old", "2026-01-01 08:00"); self.rec("new", "2026-10-16 23:51"); self.rec("mid", "2026-05-05 12:00")
        self.assertEqual([r["title"] for r in self.h.sorted_records()], ["new", "mid", "old"])
        self.h.save()
        h2 = hist_mod.HistoryManager(); h2.load()
        self.assertEqual(len(h2.records), 3)

    def test_old_records_get_an_id_and_remove_deletes_thumb(self):
        hist_mod.HISTORY_FILE.write_text('[{"url":"u","title":"t","date":"2026-01-01 00:00"}]', encoding="utf-8")
        h = hist_mod.HistoryManager(); h.load()
        self.assertTrue(h.records[0]["id"])
        r = self.rec("x", "2026-02-02 00:00", b"zz")
        p = self.h.thumb_path(r)
        self.h.remove(r["id"])
        self.assertIsNone(self.h.find(r["id"]))
        self.assertFalse(Path(p).exists())

    def test_favorites(self):
        r = self.rec("a", "2026-10-01 10:00")
        self.assertEqual(self.f.add(r["id"], "Music"), "Music")
        self.assertEqual(self.f.add(r["id"], " music "), "Music")      # same category, other letters
        self.f.add("other", "Kids")
        self.assertEqual(self.f.used_categories(), ["Music", "Kids"])
        f2 = fav_mod.FavoritesManager(); f2.load()
        self.assertEqual(f2.category_of(r["id"]), "Music")
        self.f.remove(r["id"])
        self.assertFalse(self.f.is_favorite(r["id"]))
        self.assertEqual(self.f.used_categories(), ["Kids"])

    def test_sync_schedule(self):
        d = datetime(2026, 1, 31, 10, 0)
        self.assertEqual(sync_mod.add_schedule(d, "daily"), datetime(2026, 2, 1, 10, 0))        # + 1 day
        self.assertEqual(sync_mod.add_schedule(d, "weekly"), datetime(2026, 2, 7, 10, 0))       # + 7 days
        self.assertEqual(sync_mod.add_schedule(d, "monthly"), datetime(2026, 2, 28, 10, 0))     # + 1 month (short month)
        self.assertEqual(sync_mod.add_schedule(datetime(2026, 12, 15), "monthly"), datetime(2027, 1, 15))

    def test_sync_entries(self):
        s = sync_mod.SyncManager()
        e = s.add("PL1", "rec1", "https://x/playlist?list=PL1", "List", "weekly")
        self.assertEqual((e["schedule"], e["enabled"]), ("weekly", True))
        last, nxt = (datetime.strptime(e[k], sync_mod.FMT) for k in ("last_sync", "next_sync"))
        self.assertEqual((nxt - last).days, 7)
        s.set_schedule(e, "daily")
        self.assertEqual((datetime.strptime(e["next_sync"], sync_mod.FMT) - last).days, 1)
        self.assertFalse(s.is_due(e))
        e["next_sync"] = "2000-01-01 00:00"
        self.assertTrue(s.is_due(e))
        e["enabled"] = False
        self.assertFalse(s.is_due(e))                                 # switched OFF: never due
        s2 = sync_mod.SyncManager(); s2.load()
        self.assertEqual(len(s2.entries), 1)
        s.remove("PL1")
        self.assertEqual(s.entries, [])

    def test_find_playlist(self):
        r = self.h.new_record(url="https://www.youtube.com/playlist?list=PLABC", title="P", file_name="", save_dir="D:/p",
                              fmt="mp4", quality="720p", quality_value=720, size=1, is_playlist=True, count=3)
        self.assertEqual(r["playlist_id"], "PLABC")
        self.assertEqual(self.h.find_playlist("https://www.youtube.com/playlist?list=PLABC&x=1")["id"], r["id"])
        self.assertIsNone(self.h.find_playlist("https://www.youtube.com/playlist?list=OTHER"))
        self.assertIsNone(self.h.find_playlist("https://www.youtube.com/watch?v=abc&list=PLABC"))   # a video link


if __name__ == "__main__":
    unittest.main()


class CategoryTests(unittest.TestCase):
    def test_add_edit_delete_category_with_icons(self):
        import tempfile
        from pathlib import Path
        import app.favorites as fm
        keep = fm.FAVORITES_FILE
        with tempfile.TemporaryDirectory() as d:
            fm.FAVORITES_FILE = Path(d) / "favorites.json"
            try:
                f = fm.FavoritesManager()
                self.assertEqual(f.add_category("  Cinema ", "🎬"), "Cinema")
                self.assertIsNone(f.add_category("cinema", "🎵"))                 # same name in another letter case
                self.assertIsNone(f.add_category("   "))
                f.add_category("Music", "🎵")
                f.add("v1", "Cinema"); f.add("v2", "Cinema"); f.add("v3", "Music")
                self.assertEqual(f.label("Cinema"), "🎬 Cinema")
                self.assertFalse(f.edit_category("Cinema", "music"))                # name of another category
                self.assertTrue(f.edit_category("Cinema", "Movies", "🍿"))
                self.assertEqual((f.category_of("v1"), f.label("Movies"), f.icon_of("Cinema")), ("Movies", "🍿 Movies", ""))
                f.delete_category("Movies")
                self.assertEqual((f.categories, f.items, f.icons), (["Music"], {"v3": "Music"}, {"Music": "🎵"}))
                g = fm.FavoritesManager(); g.load()                                  # saved on disk
                self.assertEqual((g.categories, g.items, g.icons), (f.categories, f.items, f.icons))
            finally:
                fm.FAVORITES_FILE = keep


class DeleteFilesTests(unittest.TestCase):
    """2.0.2: Delete -> yes = the entry AND the physical file(s) go (a playlist: files + its own folder)."""

    def setUp(self):
        import tempfile
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_video_file(self):
        from app.history import delete_files
        f = self.root / "a.mp4"
        f.write_bytes(b"x")
        self.assertEqual(delete_files({"save_dir": str(self.root), "file_name": "a.mp4"}), (1, []))
        self.assertFalse(f.exists())
        self.assertEqual(delete_files({"save_dir": str(self.root), "file_name": "a.mp4"}), (0, []))   # already gone

    def test_playlist_with_own_folder(self):
        from app.history import delete_files
        folder = self.root / "My List"
        folder.mkdir()
        files = []
        for i in (1, 2):
            f = folder / f"0{i} - v.mp4"
            f.write_bytes(b"x")
            files.append(str(f))
        (folder / "cover.jpg").write_bytes(b"y")                  # leftover that is not tracked
        rec = {"is_playlist": True, "save_dir": str(folder), "subfolder": True,
               "videos": {str(i): {"file": f} for i, f in enumerate(files)}}
        self.assertEqual(delete_files(rec, protect=[self.root]), (2, []))
        self.assertFalse(folder.exists())                         # the whole playlist folder is gone
        self.assertTrue(self.root.exists())

    def test_playlist_without_own_folder_keeps_the_download_folder(self):
        from app.history import delete_files
        f = self.root / "01 - v.mp4"
        f.write_bytes(b"x")
        (self.root / "other.mp4").write_bytes(b"x")
        rec = {"is_playlist": True, "save_dir": str(self.root), "subfolder": True, "videos": {"1": {"file": str(f)}}}
        self.assertEqual(delete_files(rec, protect=[self.root]), (1, []))       # protected: only its own file goes
        self.assertTrue((self.root / "other.mp4").exists())
        rec["subfolder"] = False                                   # unknown / no own folder: removed only when empty
        folder = self.root / "mix"
        folder.mkdir()
        (folder / "keep.txt").write_text("k")
        rec2 = {"is_playlist": True, "save_dir": str(folder), "videos": {}}
        delete_files(rec2, protect=[self.root])
        self.assertTrue(folder.exists())                           # not empty -> kept


class FindVideo(unittest.TestCase):
    """2.0.6: the same video is recognised from every form of its link."""

    def test_keys(self):
        from app.history import video_key
        a = video_key("https://www.youtube.com/watch?v=abc123&list=PL1")
        self.assertEqual(a, "yt:abc123")
        self.assertEqual(video_key("https://youtu.be/abc123?t=5"), a)
        self.assertEqual(video_key("https://m.youtube.com/shorts/abc123"), a)
        self.assertNotEqual(video_key("https://youtu.be/zzz"), a)
        self.assertEqual(video_key("not a url"), "")

    def test_find_video(self):
        from app.history import HistoryManager
        h = HistoryManager.__new__(HistoryManager)
        h.records = [{"id": "1", "url": "https://youtu.be/abc123", "date": "2026-01-01 10:00"},
                     {"id": "2", "url": "https://www.youtube.com/playlist?list=PLx", "is_playlist": True, "date": "2026-01-02 10:00"}]
        self.assertEqual(h.find_video("https://www.youtube.com/watch?v=abc123")["id"], "1")
        self.assertIsNone(h.find_video("https://www.youtube.com/watch?v=other"))




class PlaylistEquivalence(unittest.TestCase):
    """2.3.2: a single link and the same video inside a playlist are the same video."""

    def _h(self, recs):
        from app.history import HistoryManager
        h = HistoryManager.__new__(HistoryManager)
        h.records = recs
        h.save = lambda: None
        return h

    def test_find_video_in_playlist(self):
        pl = {"id": "p", "url": "https://www.youtube.com/playlist?list=PLx", "is_playlist": True, "title": "L", "save_dir": "/x",
              "videos": {"abc123": {"title": "T", "file": "/x/01 - T.mp4", "date": "2026-01-01", "state": "downloaded"},
                         "skp": {"title": "S", "file": "", "state": "skipped"}}}
        h = self._h([pl])
        r = h.find_video("https://youtu.be/abc123")
        self.assertEqual((r["title"], r["file_name"], r["is_playlist"]), ("T", "01 - T.mp4", False))
        self.assertIsNone(h.find_video("https://youtu.be/skp"))

    def test_absorb_singles(self):
        import tempfile, os
        d = tempfile.mkdtemp()
        open(os.path.join(d, "a.mp4"), "w").close()
        h = self._h([{"id": "1", "url": "https://youtu.be/abc123", "title": "A", "save_dir": d, "file_name": "a.mp4", "date": "d"},
                     {"id": "2", "url": "https://youtu.be/nofile", "title": "B", "save_dir": d, "file_name": "gone.mp4"}])
        rec = {"videos": {}}
        self.assertEqual(h.absorb_singles(rec, ["abc123", "nofile", "other"]), 1)
        self.assertEqual(rec["videos"]["abc123"]["state"], "downloaded")
        self.assertTrue(os.path.isabs(rec["videos"]["abc123"]["file"]))
        self.assertNotIn("nofile", rec["videos"])


class OneEntryPerFile(unittest.TestCase):
    def test_same_file_and_dedupe(self):
        from app.history import HistoryManager
        h = HistoryManager.__new__(HistoryManager)
        h.save = lambda: None
        a = {"id": "a", "save_dir": "/x", "file_name": "v.mp4", "date": "2026-01-01 10:00"}
        b = {"id": "b", "save_dir": "/x", "file_name": "v.mp4", "date": "2026-02-01 10:00"}
        c = {"id": "c", "save_dir": "/x", "file_name": "v.mp3", "date": "2026-01-01 10:00"}
        h.records = [a, b, c]
        self.assertEqual([r["id"] for r in h.same_file(b)], ["a"])
        self.assertEqual(h.dedupe_files(), {"a": "b"})
        self.assertEqual([r["id"] for r in h.records], ["b", "c"])      # another quality / format = another file = kept


