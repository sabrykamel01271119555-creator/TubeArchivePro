"""Page flow test with the fake yt-dlp and a stand-in for Qt:  python -m unittest discover -s tests -v
2.0.1: Start puts the video / playlist in the download queue (app/dlqueue.py); progress lives on the Downloads page."""
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import qt_stub
qt_stub.install()

from app.context import AppContext                       # noqa: E402
from app.ui import new_download_page as ndp              # noqa: E402

PL_FILES = [f"0{i} - Video v{i}.mp4" for i in range(1, 6)]       # 5 videos -> 01 ... 05 (one zero more than the digits)
FAKE = [sys.executable, str(Path(__file__).resolve().parent / "fake_ytdlp.py")]


def wait(cond, timeout=20):
    end = time.time() + timeout
    while not cond() and time.time() < end:
        time.sleep(0.05)
    return cond()


class PageFlow(unittest.TestCase):
    def setUp(self):
        self.out = tempfile.mkdtemp()
        data = Path(tempfile.mkdtemp())                       # history / favorites never touch the real data folder
        import app.history, app.favorites, app.sync
        app.history.HISTORY_FILE, app.history.THUMBS_DIR = data / "history.json", data / "thumbs"
        app.favorites.FAVORITES_FILE = data / "favorites.json"
        app.sync.SYNC_FILE = data / "sync.json"
        ctx = AppContext()
        ctx.failed.path = data / "failed.json"
        ctx.lang.discover()
        ctx.lang.load("en")
        ctx.settings.defaults = {"download_dir": self.out, "last_format": "MP4", "last_quality": 0,
                                 "show_success_dialog": True}
        ctx.settings.current = dict(ctx.settings.defaults)
        ctx.settings.save = lambda: None
        ctx.settings.download_dir = lambda: Path(self.out)
        ctx.resources.ytdlp, ctx.resources.ffmpeg_dir, ctx.resources.ffmpeg_ok = FAKE, None, True
        self.ctx = ctx
        os.environ["FAKE_STEPS"] = "5"
        self.dialogs = []
        self._orig = (ndp.SuccessDialog, ndp.MessageDialog, ndp.PlaylistSetupDialog)
        self.setup = {"ok": True, "create_folder": True, "sync": False, "schedule": "daily", "shown": 0}
        ndp.SuccessDialog = lambda *a, **k: self._dlg("success", a, k)
        ndp.add_to_favorites = lambda ctx, rec, parent, blur=False: (ctx.favorites.add(rec["id"], "Music"), True)[1]
        ndp.MessageDialog = lambda *a, **k: self._dlg("error", a, k)

        def setup_dialog(*a, **k):
            self.setup["shown"] += 1
            d = self._dlg("setup", a, k)
            d.ok, d.create_folder, d.sync, d.schedule = (self.setup[x] for x in ("ok", "create_folder", "sync", "schedule"))
            return d
        ndp.PlaylistSetupDialog = setup_dialog
        self.page = ndp.NewDownloadPage(ctx)

    def tearDown(self):
        ndp.SuccessDialog, ndp.MessageDialog, ndp.PlaylistSetupDialog = self._orig
        self.page.mgr.queue.cancel_all(wait=True)

    def _dlg(self, kind, a, k):
        d = type("D", (), {"exec": lambda s: 0, "action": "ok", "dont_show": False})()
        d.kind, d.args, d.kwargs = kind, a, k
        self.dialogs.append(d)
        return d

    def load_link(self, url="https://x.com/video"):
        self.page.url.setText(url)
        self.page._fetch()
        self.assertTrue(wait(lambda: self.page.state == "ready"), self.page.log.toPlainText())

    def log(self):
        return self.page.log.toPlainText()

    # -------------------------------------------------------------
    def test_dropdowns(self):
        p = self.page
        labels = p.fmt.labels()
        self.assertEqual(labels, ["MP4 · Video", "MKV · Video", "WEBM · Video", "AVI · Video",
                                  "MP3 · Audio", "WAV · Audio"])
        sep = [t for t, _v in p.fmt.items].index("---")
        self.assertEqual(sep, 4)                                  # separator, then the audio formats
        self.assertEqual(p.quality.labels()[0], "Best Quality")
        self.assertEqual(p.quality.labels()[1:], ["144p", "240p", "360p", "480p", "720p", "1080p", "2K", "4K", "8K"])

    def test_fetch_and_filter_and_estimate(self):
        p = self.page
        self.load_link()
        wait(lambda: "Video found: Summer Vlog" in self.log())        # the log line is written just after the state changes (a thread race on Windows)
        self.assertIn("Video found: Summer Vlog", self.log())
        p.quality.setCurrentIndex(p.quality.findData(1080))
        self.assertIn("Estimated size: 78 MB", p.meta.text())
        self.assertIn("Duration: 01:40", p.meta.text())
        p.fmt.setCurrentIndex(p.fmt.findData("MP3"))              # audio -> kbps list
        names = lambda: [x.split("  ·  ")[0] for x in p.quality.labels()]                   # noqa: E731  (the size follows the name)
        self.assertEqual(names(), ["320 kbps", "256 kbps", "192 kbps", "128 kbps", "96 kbps", "64 kbps"])
        self.assertIn("4 MB", p.quality.labels()[0])                                          # 2.3.1: size beside the quality
        self.assertIn("Estimated size: 4 MB", p.meta.text())
        p.fmt.setCurrentIndex(p.fmt.findData("WAV"))
        self.assertEqual(names(), ["48 kHz", "44.1 kHz", "22.05 kHz"])
        p.fmt.setCurrentIndex(p.fmt.findData("MKV"))
        self.assertEqual(names()[-1], "4K")

    def test_bad_url_and_unavailable(self):
        self.page.url.setText("hello")
        self.page._start()
        self.assertEqual(self.dialogs[-1].kind, "error")
        self.assertIn("valid video or playlist link", self.log())
        self.page.url.setText("https://x.com/bad")
        self.page._fetch()
        self.assertTrue(wait(lambda: "unavailable or has been removed" in self.log()), self.log())
        self.assertEqual(self.page.state, "idle")

    def test_download_success(self):
        p = self.page
        self.load_link()
        p.folder.setText(self.out)
        p._start()
        self.assertEqual(p.state, "idle")                         # the page is free for the next link at once
        self.assertIsNone(p.info)
        self.assertIn("Added to the download queue: Summer Vlog", self.log())
        self.assertTrue(wait(lambda: any(d.kind == "success" for d in self.dialogs)), self.log())
        self.assertIn("Download completed: Summer Vlog.mp4", self.log())
        self.assertEqual([x.name for x in Path(self.out).iterdir()], ["Summer Vlog.mp4"])
        title, rows = self.dialogs[-1].args[1], self.dialogs[-1].args[2]
        self.assertEqual(title, "File Successfully Downloaded!")
        self.assertEqual([r[1] for r in rows], ["File Name:", "Quality:", "Size:", "Location:"])
        self.assertEqual(rows[0][2], "Summer Vlog.mp4")
        self.assertEqual(rows[1][2], "4K")                          # Best -> highest available (2160)
        self.assertEqual(rows[2][2], "3 KB")

    def test_same_link_twice_is_refused_while_queued(self):
        os.environ["FAKE_STEPS"] = "30"
        p = self.page
        self.load_link()
        p._start()
        self.load_link()
        p._start()
        self.assertIn("already in the download queue", self.log())
        self.assertEqual(len(p.mgr.queue.tasks), 1)

    def test_history_record_and_favorite_button(self):
        p = self.page
        self.load_link()
        p.folder.setText(self.out)
        p._start()
        self.assertTrue(wait(lambda: any(d.kind == "success" for d in self.dialogs)), self.log())
        rec = self.ctx.history.records[0]
        self.assertEqual((rec["title"], rec["file_name"], rec["extension"], rec["format"]),
                         ("Summer Vlog", "Summer Vlog.mp4", "mp4", "MP4"))
        self.assertEqual((rec["save_dir"], rec["quality"], rec["url"]), (self.out, "4K", "https://x.com/video"))
        self.assertTrue(rec["size"] > 0 and rec["id"])
        kw = [d for d in self.dialogs if d.kind == "success"][-1].kwargs
        self.assertTrue(callable(kw["fav_cb"]))                   # the success window has the Add to Favorite button
        self.assertTrue(kw["fav_cb"]())
        self.assertEqual(self.ctx.favorites.category_of(rec["id"]), "Music")
        self.assertIn("Added to favorites (Music)", self.log())

    def test_start_needs_a_ready_video_and_empty_frame(self):
        p = self.page
        self.assertFalse(p.b_start.isEnabled())                   # nothing read yet
        self.assertIsNone(p.info)
        self.load_link()
        self.assertTrue(p.b_start.isEnabled())

    def test_prefill_from_history(self):
        p = self.page
        rec = {"url": "https://x.com/watch?v=1", "save_dir": self.out, "format": "MKV", "quality_value": 1080}
        p.prefill(rec)
        self.assertEqual((p.url.text(), p.folder.text(), p.cur_format()), (rec["url"], self.out, "MKV"))
        p._fetch()
        self.assertTrue(wait(lambda: p.state == "ready"), self.log())
        self.assertEqual(p.cur_quality(), 1080)                   # the old quality is selected again, user may change it
        self.assertTrue(p.fmt.isEnabled() and p.quality.isEnabled())

    def test_only_available_resolutions(self):
        p = self.page
        self.assertEqual(len(p.quality.labels()), 10)             # before reading the link: the standard list
        self.load_link()
        self.assertEqual([x.split("  ·  ")[0] for x in p.quality.labels()], ["Best Quality", "360p", "1080p", "4K"])   # what this video really has
        self.assertEqual(p.sizes[("MP4", 1080)], p.estimate_for("MP4", 1080))           # sizes are kept in memory
        self.assertIn(("MP3", 320), p.sizes)

    def test_not_enough_space_warns_and_does_not_start(self):
        p = self.page
        self.load_link()
        p.quality.setCurrentIndex(p.quality.findData(1080))
        big = p.space_needed_for(p.est_size)
        self.assertGreaterEqual(big, 2 * p.est_size)              # the file twice: parts + merged file
        orig = ndp.free_bytes, ndp.ChoiceDialog
        try:
            ndp.free_bytes = lambda path: big - 1
            asked = []

            def choice(*a, **k):
                d = self._dlg("space", a, k)
                d.choice = "cancel"
                asked.append([b[0] for b in a[3]])
                return d
            ndp.ChoiceDialog = choice
            p._update_meta()
            self.assertIn("Not enough free space", p.warn.text())
            p._start()
            self.assertEqual(asked, [["lower", "folder", "cancel"]])      # lower quality is suggested (360p fits? no: 360p needs less)
            self.assertEqual(self.page.mgr.queue.counts(), (0, 0))        # nothing was started
            ndp.free_bytes = lambda path: big
            self.assertTrue(p._space_ok())
        finally:
            ndp.free_bytes, ndp.ChoiceDialog = orig

    def test_library_filters_and_sorting(self):
        from app.demo import seed_demo
        from app.ui import library_page as lp_mod
        self.ctx.settings.current["demo_mode"] = True
        self.assertTrue(seed_demo(self.ctx))
        recs = self.ctx.history.records
        lp = object.__new__(lp_mod.LibraryPage)
        lp.ctx, lp.mode, lp._kind = self.ctx, "archive", None          # Archive = everything that was downloaded
        lp.sort = type("S", (), {"currentData": lambda s: "date"})()
        newest = lp._sorted(recs)
        self.assertEqual(newest[0]["title"], "Cyberpunk Cinematic Journey")            # most recent first
        self.assertEqual([r["date"] for r in newest], sorted((r["date"] for r in recs), reverse=True))
        lp._kind = "audio"
        self.assertTrue(all(r["is_audio"] for r in recs if lp._matches(r, "", "all")))
        lp._kind = "playlist"
        self.assertEqual(len([r for r in recs if lp._matches(r, "", "all")]), 4)
        lp._kind = None
        self.assertEqual(len([r for r in recs if lp._matches(r, "", "all")]), len(recs))    # nothing is hidden in the Archive
        lp.mode = "library"                                                           # Library = favorites only
        arch = [r for r in recs if lp._matches(r, "", "fav")]
        self.assertTrue(arch and all(self.ctx.favorites.is_favorite(r["id"]) for r in arch))
        self.assertEqual({self.ctx.favorites.category_of(r["id"]) for r in arch}, {"Cinema", "Music", "Science"})
        self.assertEqual([r["title"] for r in recs if lp._matches(r, "lo-fi", "fav")], ["Relaxing Lo-Fi Mix", "Relaxing Lo-Fi Beats"])

    def test_real_data_mode_removes_samples_only(self):
        from app.demo import purge_demo, seed_demo
        self.ctx.settings.current["demo_mode"] = True
        seed_demo(self.ctx)
        self.ctx.history.records.append({"id": "real1", "title": "Mine", "is_playlist": False, "date": "2026-10-18 10:00"})
        self.assertTrue(purge_demo(self.ctx))
        self.assertEqual([r["id"] for r in self.ctx.history.records], ["real1"])
        self.assertEqual((self.ctx.favorites.items, self.ctx.sync.entries), ({}, []))
        self.assertFalse(purge_demo(self.ctx))

    def test_seed_only_once(self):
        from app.demo import seed_demo
        self.ctx.settings.current["demo_mode"] = True
        self.assertTrue(seed_demo(self.ctx))
        self.assertEqual(self.ctx.settings.get("demo_seed_version"), 2)
        self.assertEqual(len(self.ctx.sync.entries), 4)                      # the four demo playlists are synchronized
        self.assertFalse(seed_demo(self.ctx))
        self.assertEqual(len(self.ctx.history.records), 14)

    # ---------------------------------------------------------------- playlists
    PL = "https://x.com/playlist?list=PLX"

    def download_playlist(self, **setup):
        self.setup.update(setup)
        p = self.page
        self.load_link(self.PL)
        self.assertEqual(p.info["count"], 5)
        p.folder.setText(self.out)
        p._start()
        self.assertTrue(wait(lambda: len(self.ctx.history.records) >= 1), self.log())
        return self.ctx.history.records[0]

    def test_new_playlist_asks_options_folder_and_sync(self):
        rec = self.download_playlist(create_folder=True, sync=True, schedule="weekly")
        self.assertEqual(self.setup["shown"], 1)                                   # options window for a NEW playlist
        self.assertEqual([x.name for x in Path(self.out).iterdir()], ["My List"])  # folder created in the save directory
        self.assertEqual(rec["save_dir"], str(Path(self.out) / "My List"))
        self.assertEqual((rec["playlist_id"], rec["count"], sorted(rec["videos"])), ("PLX", 5, ["v1", "v2", "v3", "v4", "v5"]))
        e = self.ctx.sync.find("PLX")                                              # ticked 'add to sync' -> weekly schedule
        self.assertEqual((e["schedule"], e["rec_id"], e["enabled"]), ("weekly", rec["id"], True))
        from datetime import datetime
        d = lambda k: datetime.strptime(e[k], "%Y-%m-%d %H:%M")                  # noqa: E731
        self.assertEqual((d("next_sync") - d("last_sync")).days, 7)
        self.assertIn("Playlist added to sync (Weekly)", self.log())

    def test_new_playlist_without_folder_and_without_sync(self):
        rec = self.download_playlist(create_folder=False, sync=False)
        names = sorted(x.name for x in Path(self.out).iterdir())
        self.assertEqual(names, PL_FILES)                          # straight in the save directory, numbered 01 ... 05
        self.assertEqual(rec["save_dir"], self.out)
        self.assertIsNone(self.ctx.sync.find("PLX"))

    def test_cancel_in_options_window_downloads_nothing(self):
        self.setup["ok"] = False
        self.load_link(self.PL)
        self.page.folder.setText(self.out)
        self.page._start()
        self.assertEqual(self.page.state, "ready")
        self.assertEqual(list(Path(self.out).iterdir()), [])
        self.assertEqual(self.ctx.history.records, [])
        self.assertEqual(self.page.mgr.queue.groups, [])

    # --- 2.3.0: a video link that carries a playlist -----------------------------------------------------
    def test_playlist_url_of_video_link(self):
        f = ndp.NewDownloadPage._playlist_url_of
        self.assertEqual(f("https://www.youtube.com/watch?v=abc&list=PLX&index=2"), "https://www.youtube.com/playlist?list=PLX")
        self.assertEqual(f("https://www.youtube.com/watch?v=abc"), "")
        self.assertEqual(f("https://www.youtube.com/watch?v=abc&list=RDabc"), "")        # a mix is not a playlist
        self.assertEqual(f("https://www.youtube.com/playlist?list=PLX"), "")             # already a playlist link
        self.assertEqual(f("https://x.com/watch?v=abc&list=PLX"), "")

    def _choice(self, answer):
        asked = []

        def choice(*a, **k):
            d = self._dlg("choice", a, k)
            d.choice = answer
            asked.append((a[2], [b[0] for b in a[3]]))
            return d
        orig = ndp.ChoiceDialog
        ndp.ChoiceDialog = choice
        self.addCleanup(setattr, ndp, "ChoiceDialog", orig)
        return asked

    def test_video_of_a_downloaded_playlist_says_if_the_file_was_downloaded(self):
        rec = self.download_playlist()
        asked = self._choice("cancel")
        link = "https://www.youtube.com/watch?v=v2&list=PLX"
        self.assertFalse(self.page._playlist_gate(link))
        text, buttons = asked[-1]
        self.assertEqual(buttons, ["sync", "file", "cancel"])
        self.assertIn("downloaded before", text)
        self.assertIn("WAS downloaded before", text)                                     # v2 is in the history
        self.assertIn("My List", text)
        self.assertFalse(self.page._playlist_gate("https://www.youtube.com/watch?v=zzz&list=PLX"))
        self.assertIn("NOT downloaded before", asked[-1][0])                             # a video that is not there
        self._choice("sync")
        got = []
        self.page.sync_requested.connect(got.append)
        self.assertFalse(self.page._playlist_gate(link))
        self.assertEqual(got, [rec])
        self._choice("file")
        self.assertTrue(self.page._playlist_gate("https://www.youtube.com/watch?v=zzz&list=PLX"))
        self.assertTrue(self.page._playlist_gate("https://www.youtube.com/watch?v=zzz&list=PLX"))   # asked once only

    def test_video_of_a_new_playlist_offers_four_choices(self):
        import app.ui.dialogs as dl

        class Busy:
            def __init__(s, *a, **k):
                s.cancelled = False

            def exec(s):
                wait(lambda: self.page._pl_info is not None)

            def finish(s):
                pass
        orig = dl.BusyDialog
        dl.BusyDialog = Busy
        self.addCleanup(setattr, dl, "BusyDialog", orig)
        asked = self._choice("check")
        link = "https://www.youtube.com/watch?v=v2&list=PLX"
        self.page.url.setText(link)
        self.page._fetch()
        text, buttons = asked[-1]
        self.assertEqual(buttons, ["all", "check", "file", "cancel"])
        self.assertIn("not downloaded before", text)
        self.assertIn("Videos: 5", text)
        self.assertEqual(self.page.url.text(), "https://www.youtube.com/playlist?list=PLX")   # 'Check playlist'
        self.assertTrue(wait(lambda: self.page.state == "ready"), self.log())
        self.assertTrue(self.page.info["is_playlist"])
        self.assertEqual(self.ctx.history.records, [])                                       # only checked, not downloaded

    def test_playlist_downloaded_before_goes_to_sync(self):
        rec = self.download_playlist()
        asked = []
        self.page.sync_requested.connect(asked.append)
        self.setup["shown"] = 0
        self.page._start()                                                         # same playlist again
        self.assertEqual(asked, [rec])                                             # -> sync window, not the options window
        self.assertEqual(self.setup["shown"], 0)

    def test_sync_downloads_only_chosen_new_videos(self):
        rec = self.download_playlist(create_folder=True, sync=True)
        gone = rec["videos"].pop("v3")                                             # pretend v3 is new on YouTube
        Path(gone["file"]).unlink()
        e = self.ctx.sync.find("PLX")
        e["next_sync"] = "2000-01-01 00:00"
        entries = [{"id": "v3", "index": 3, "title": "Three"}]
        self.page.history_changed.connect(lambda: None)
        self.assertTrue(self.page.start_sync(rec, entries))
        self.assertTrue(wait(lambda: "Sync completed" in self.log()), self.log())
        self.assertEqual(sorted(x.name for x in (Path(self.out) / "My List").iterdir()), PL_FILES)
        self.assertEqual(sorted(rec["videos"]), ["v1", "v2", "v3", "v4", "v5"])
        self.assertEqual(rec["count"], 5)
        self.assertFalse(self.ctx.sync.is_due(e))                                  # next sync moved forward
        self.assertEqual(len(self.ctx.history.records), 1)                         # no second history record

    def test_background_sync_adds_new_and_warns_about_missing_files(self):
        """2.2.7 'Sync now' of the due window: no dialog while it runs, only the new videos are queued, and one warning lists
        the downloaded videos whose files are gone from the folder."""
        from app.ui import sync_flow as sf
        rec = self.download_playlist(create_folder=True, sync=True)
        gone = rec["videos"].pop("v5")
        Path(gone["file"]).unlink()
        lost = rec["videos"]["v2"]
        Path(lost["file"]).unlink()
        shown = []

        class Msg:
            def __init__(s, lang, title, text, *a, **k): shown.append(text)

        orig = (sf.MessageDialog, sf.exec_blurred)
        sf.MessageDialog, sf.exec_blurred = Msg, lambda *a, **k: 0
        try:
            ctl = sf.SyncController(self.ctx, self.page)
            ctl.run_background([rec])
            self.assertTrue(wait(lambda: "Sync completed: 1 new" in self.log()), self.log())
            self.assertEqual(rec["videos"]["v5"]["state"], "downloaded")
            self.assertEqual(len(shown), 1)
            self.assertIn(lost["title"], shown[0])
            self.assertIsNone(ctl._bg)
        finally:
            sf.MessageDialog, sf.exec_blurred = orig

    def test_sync_all_single_window(self):
        """2.3.2: Sync all = one window; playlists are checked one after the other, the work area shows the new videos
        (chosen ones start when the window closes) or the 'nothing new' message."""
        from app.ui import sync_flow as sf
        rec = self.download_playlist(create_folder=True, sync=True)
        gone = rec["videos"].pop("v5")
        Path(gone["file"]).unlink()
        events = []

        class Dlg:
            cancelled = False
            def __init__(s, lang, total, parent=None): events.append(("total", total)); Dlg.last = s
            def set_progress(s, i, n, part=0): events.append(("progress", i, n, part))
            def show_checking(s, pm, lines): events.append(("checking", len(lines)))
            def set_content(s, w): events.append(("content", len(w.new))); w.chosen.emit("download")
            def show_message(s, title, text, lines=None): events.append(("message", title))
            def finish(s, text): events.append(("finish", text))
            def exec(s): wait(lambda: any(e[0] == "finish" for e in events))

        class Panel:
            def __init__(s, lang, new, old, thumbs, **k):
                from tests.qt_stub import Signal
                s.new, s.selected, s.redownload = new, [n["id"] for n in new], False
                s.chosen = type("B", (), {"handlers": [], "connect": lambda b, f: b.handlers.append(f),
                                          "emit": lambda b, *a: [h(*a) for h in b.handlers]})()

        orig = (sf.SyncAllDialog, sf.SyncPanel, sf.exec_blurred)
        sf.SyncAllDialog, sf.SyncPanel, sf.exec_blurred = Dlg, Panel, lambda w, d: d.exec()
        try:
            ctl = sf.SyncController(self.ctx, self.page)
            started = []
            ctl.started.connect(lambda: started.append(1))
            ctl.run_all()
            self.assertEqual(events[0], ("total", 1))
            self.assertIn(("content", 1), events)                       # the new video is listed in the work area
            self.assertEqual(events[-1][0], "finish")
            self.assertEqual(started, [1])
            self.assertTrue(wait(lambda: "Sync completed: 1 new" in self.log()), self.log())
        finally:
            sf.SyncAllDialog, sf.SyncPanel, sf.exec_blurred = orig

    def test_sync_flow_download_and_skip(self):
        from app.ui import sync_flow as sf
        rec = self.download_playlist(create_folder=True, sync=True)
        gone = rec["videos"].pop("v5")
        Path(gone["file"]).unlink()
        seen = {}

        class Busy:
            cancelled = False
            def __init__(s, *a, **k): s.ctl = None
            def finish(s): pass
            def exec(s):
                wait(lambda: ctl._result is not None)

        class Win:
            action, selected, redownload = "download", [], False
            def __init__(s, lang, title, new, old, thumbs, **k):
                seen.update(new=[n["id"] for n in new], old=sorted(o["id"] for o in old))
                Win.selected = [n["id"] for n in new]
            def exec(s): return 0

        orig = (sf.BusyDialog, sf.SyncDialog)
        sf.BusyDialog, sf.SyncDialog = Busy, Win
        try:
            ctl = sf.SyncController(self.ctx, self.page)
            started = []
            ctl.started.connect(lambda: started.append(1))
            ctl.run(rec)
            self.assertEqual(seen, {"new": ["v5"], "old": ["v1", "v2", "v3", "v4"]})   # 1 new, 4 already downloaded
            self.assertIn("5 videos in the playlist, 4 already downloaded, 1 new", self.log())
            self.assertEqual(started, [1])
            self.assertTrue(wait(lambda: "Sync completed: 1 new" in self.log()), self.log())
            self.assertEqual(rec["videos"]["v5"]["state"], "downloaded")
            # skip: a new video is remembered as skipped and not offered again
            rec["videos"].pop("v4")
            Win.action = "skip"
            ctl.run(rec)
            self.assertEqual(seen["new"], ["v4"])
            self.assertEqual(rec["videos"]["v4"]["state"], "skipped")
            ctl.run(rec)
            self.assertEqual(seen["new"], [])                                           # nothing new any more
            self.assertEqual(sorted(seen["old"]), ["v1", "v2", "v3", "v4", "v5"])        # 2.2.7: the skipped video (v4) is listed too
        finally:
            sf.BusyDialog, sf.SyncDialog = orig

    def test_sync_flow_error_and_busy(self):
        from app.ui import sync_flow as sf
        rec = self.download_playlist()
        rec["url"] = "https://x.com/bad/playlist?list=PLX"                           # the fake answers 'unavailable'
        class Busy:
            cancelled = False
            def __init__(s, *a, **k): pass
            def finish(s): pass
            def exec(s): wait(lambda: ctl._result is not None)
        orig = sf.BusyDialog
        sf.BusyDialog = Busy
        try:
            ctl = sf.SyncController(self.ctx, self.page)
            self.dialogs.clear()
            ctl.run(rec)
            self.assertEqual(self.dialogs[-1].kind, "error")
            self.assertIn("unavailable or has been removed", self.log())
        finally:
            sf.BusyDialog = orig

    def test_defaults_from_settings(self):
        st, p = self.ctx.settings, self.page
        st.set("default_format", "MP3")
        st.set("audio_format", "MP3")
        st.set("audio_quality", 192)
        st.set("download_dir", str(Path(self.out) / "other"))
        st.download_dir = lambda: Path(st.get("download_dir"))      # (setUp replaced it by a fixed folder)
        p.apply_defaults()
        self.assertEqual((p.cur_format(), p.cur_quality()), ("MP3", 192))
        self.assertEqual(p.folder.text(), str(Path(self.out) / "other"))
        self.load_link()
        p.folder.setText(self.out)                    # a folder typed for one download does not change the default
        p._start()
        self.assertTrue(wait(lambda: "Download completed" in self.log()), self.log())
        self.assertEqual(st.get("download_dir"), str(Path(self.out) / "other"))
        self.assertEqual(st.get("default_format"), "MP3")

    def test_old_settings_file_with_text_quality(self):
        self.ctx.settings.set("default_quality", "1080p")      # older versions saved text here
        self.ctx.settings.set("default_format", "MP4")
        self.page.apply_defaults()
        self.assertEqual(self.page.cur_quality(), 1080)         # "1080p" is understood

    def test_audio_default_playlist_folder_and_favorite_prompt_from_settings(self):
        st, p = self.ctx.settings, self.page
        st.set("audio_format", "MP3"); st.set("audio_quality", 192)
        p.apply_defaults()
        p.fmt.setCurrentIndex(p.fmt.findData("MP3"))
        self.assertEqual(p.cur_quality(), 192)                                    # bitrate chosen in Settings
        st.set("playlist_subfolders", False)
        self.download_playlist(create_folder=False)
        self.assertEqual(self.dialogs[0].kwargs.get("create_folder"), False)      # the options window starts unticked
        self.dialogs.clear()
        st.set("fav_notify", False)                                               # "don't notify me to add to a category"
        p._set_state("ready")
        self.load_link()
        p.folder.setText(self.out)
        p._start()
        self.assertTrue(wait(lambda: any(d.kind == "success" for d in self.dialogs)), self.log())
        self.assertIsNone([d for d in self.dialogs if d.kind == "success"][-1].kwargs.get("fav_cb"))

    def test_playlist_sync_notification_can_be_switched_off(self):
        rec = self.download_playlist(create_folder=True, sync=True)
        rec["videos"].pop("v3")
        for on in (True, False):
            self.dialogs.clear()
            self.ctx.settings.set("notify_sync_done", on)
            n0 = self.log().count("Sync completed")
            self.assertTrue(self.page.start_sync(rec, [{"id": "v3", "index": 3, "title": "Three"}], True))
            self.assertTrue(wait(lambda: self.log().count("Sync completed") > n0), self.log())
            time.sleep(0.3)
            kinds = [d.kind for d in self.dialogs]
            self.assertEqual("error" in kinds, on)        # the stub records MessageDialog as 'error'
            if on:
                self.assertIn("1 new video", self.dialogs[-1].args[2])

    def test_success_dialog_can_be_disabled(self):
        self.ctx.settings.set("show_success_dialog", False)
        self.load_link()
        self.page._start()
        self.assertTrue(wait(lambda: "Download completed" in self.log()))
        time.sleep(0.2)
        self.assertFalse(any(d.kind == "success" for d in self.dialogs))

    def test_pause_resume_cancel(self):
        os.environ["FAKE_STEPS"] = "60"
        p = self.page
        self.load_link()
        p._start()
        q = p.mgr.queue
        t = q.tasks[0]
        self.assertTrue(wait(lambda: t.percent > 0), self.log())
        self.assertTrue(q.pause_task(t))
        self.assertEqual(t.state, "paused")
        pct = t.percent
        time.sleep(0.8)
        self.assertEqual(t.percent, pct)
        self.assertTrue(t.job.alive())
        self.assertTrue(q.resume_task(t))
        self.assertEqual(t.state, "downloading")
        q.cancel_task(t)
        self.assertTrue(wait(lambda: t.state == "cancelled"))
        self.assertIn("Download cancelled", self.log())
        self.assertEqual(list(Path(self.out).iterdir()), [])
        self.assertEqual(p.active_percent(), [])

    def test_engine_error_is_translated(self):
        asked = self._choice("cancel")
        self.page.url.setText("https://x.com/fail")
        self.page._start()
        self.assertTrue(wait(lambda: bool(asked)), self.log())
        self.assertIn("Too many requests", self.log())
        self.assertEqual(self.page.state, "idle")
        text, buttons = asked[0]
        self.assertIn("One video cannot be downloaded now", text)                    # 2.3.2: the window of failed videos
        self.assertIn("Too many requests", text)
        self.assertEqual(buttons, ["retry", "later", "cancel"])
        self.assertEqual(self.ctx.failed.entries, [])                                 # Cancel: forgotten

    def test_failed_video_later_is_kept_and_reminded_then_retry(self):
        asked = self._choice("later")
        self.page.url.setText("https://x.com/fail")
        self.page._start()
        self.assertTrue(wait(lambda: bool(asked)), self.log())
        self.assertEqual(len(self.ctx.failed.entries), 1)                             # Later: kept
        e = self.ctx.failed.entries[0]
        self.assertEqual((e["url"], e["code"]), ("https://x.com/fail", "rate"))
        self.assertIn("kept for later", self.log())
        from app.failed import FailedManager
        again = FailedManager(self.ctx.failed.path)
        again.load()
        self.assertEqual([x["url"] for x in again.entries], ["https://x.com/fail"])   # saved on disk
        asked2 = self._choice("retry")                                                 # the reminder at the next start
        self.page.remind_failed()
        self.assertIn("waiting for a new try", asked2[0][0])
        self.assertEqual(self.ctx.failed.entries, [])                                  # Retry now: removed from the list
        self.assertTrue(wait(lambda: sum(1 for t in self.page.mgr.queue.tasks if t.url == "https://x.com/fail") >= 2), self.log())
        self.assertIn("Trying again: 1 video(s)", self.log())

    def test_missing_tools(self):
        self.ctx.resources.ffmpeg_ok = False
        self.page.url.setText("https://x.com/watch?v=1")
        self.page._start()
        self.assertIn("ffmpeg.exe was not found", self.log())
        self.ctx.resources.ytdlp = None
        self.page._start()
        self.assertIn("yt-dlp.exe) was not found", self.log())

    def test_exit_check_and_abort(self):
        os.environ["FAKE_STEPS"] = "60"
        p = self.page
        self.load_link()
        p._start()
        t = p.mgr.queue.tasks[0]
        self.assertTrue(wait(lambda: t.percent > 0), self.log())
        self.assertEqual(len(p.active_percent()), 1)
        p.cancel_for_exit()
        self.assertEqual(p.active_percent(), [])
        self.assertEqual(list(Path(self.out).iterdir()), [])

    def test_arabic_messages(self):
        self.ctx.lang.load("ar")
        self.assertIn("{", self.ctx.lang.tr("MSG_130") + "{")      # loads without errors
        for k in ("ERR_RATE", "LG_CANCEL", "OK_TITLE", "ND_EST"):
            from app.msg import M
            self.assertNotEqual(self.ctx.lang.tr(getattr(M, k)), getattr(M, k))


if __name__ == "__main__":
    unittest.main()
