# =============================================================================
# TubeArchive Pro  |  Version 2.3.0  |  File: app/ui/sync_flow.py
# Version history of this file:
#   2.3.2 - 'Sync all' is ONE window: progress bar, picture + info of the playlist, and the usual sync content in its work area
#   2.3.2 - the sync window shows the pictures of the list again (also Sync all)
#   2.3.2 - videos downloaded directly are absorbed into the playlist (not downloaded again by a sync)
#   2.3.2 - 'Sync all' shows a window for EVERY playlist (nothing new: the 'synced' window; new videos: the sync window) and reads
#           no thumbnails (bulk=True)
#   2.3.0 - 'Nothing new' window (next sync, schedule, on / off); the checking window shows the playlist details
#   2.2.7 - 'Let me check' window lists all videos (new / skipped / missing file / in folder); background sync
#           (run_background); the 'later' answer changes nothing
#   2.2.2 - run_all() 'Sync all' (quiet when nothing new); run() returns a result
#   1.0.11 - Created: 'Sync now' for a playlist that was downloaded before. Reads the playlist, compares it with
#            the videos in the history, shows the sync window (new / previously downloaded videos) and
#            starts the download of the chosen videos or skips the new ones.
# =============================================================================
"""Sync flow (one object for the whole application, used by the New Download page, Library, Archive and
the Playlist Sync page).

  run(record) -> 'Checking the playlist...' -> window 'Sync Update: N New Videos Found'
      Download & Sync (N)  -> NewDownloadPage.start_sync(...)  (progress shows in the New Download tab)
      Skip New             -> the new videos are marked 'skipped' (not offered again), next sync is scheduled
      Cancel               -> nothing changes
"""
import os

from PySide6.QtCore import QObject, QTimer, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QPixmap

from ..context import AppContext
from ..download_manager import InfoFetcher
from ..msg import M
from datetime import datetime

from ..sync import add_schedule, now_text
from .actions import exec_blurred, reveal_file
from .dialogs import BusyDialog, MessageDialog, SyncAllDialog, SyncDialog, SyncDoneDialog, SyncPanel

BUSY = ("downloading", "paused", "processing")


class SyncController(QObject):
    started = Signal()                  # a sync download was started -> show the New Download tab

    def __init__(self, ctx: AppContext, page):
        super().__init__()
        self.ctx, self.page = ctx, page
        self.t = ctx.lang.tr
        self._tag = 0
        self._result = None
        self._busy = None
        self._known = {}
        self._all = None                # 2.3.2: state of the 'Sync all' window (None = not open)
        self._bg = None                 # 2.2.7: state of the background sync (None = not running)
        self._fetcher = InfoFetcher(ctx.resources.ytdlp)
        self._fetcher.ready.connect(self._on_ready)
        self._fetcher.failed.connect(self._on_failed)

    # --- worker results (run in the interface thread) ---------------------
    def _on_ready(self, tag, info, thumbs):
        if self._bg is not None and tag == self._bg.get("tag"):
            self._bg_result(info)
            return
        if self._all is not None and tag == self._all.get("tag"):
            self._all_result(("ok", info, thumbs))
            return
        if tag == self._tag:
            self._result = ("ok", info, thumbs)
            if self._busy:
                self._busy.finish()

    def _on_failed(self, tag, code, detail):
        if self._bg is not None and tag == self._bg.get("tag"):
            self._bg_failed(detail or code)
            return
        if self._all is not None and tag == self._all.get("tag"):
            self._all_result(("error", code, detail))
            return
        if tag == self._tag:
            self._result = ("error", code, detail)
            if self._busy:
                self._busy.finish()

    def _thumb_ids(self, info: dict) -> list:
        """Pictures are read for the first new videos and a few old ones only (keeps the window quick)."""
        # 2.3.2: pictures in every sync window (also Sync all)
        entries = info.get("entries", [])
        new = [e["id"] for e in entries if e["id"] not in self._known][:12]
        return new + [e["id"] for e in entries if e["id"] in self._known][:6]

    # --- the flow -----------------------------------------------------------
    def run_all(self):
        """'Sync all' (Playlist Sync page): ONE window checks every playlist that is switched on, one after the other.
        Work area: the list of new videos (choose, then the next playlist follows) or the 'nothing new' message (moves on by itself)."""
        ctx, page, t = self.ctx, self.page, self.t
        win = page.window()
        recs = []
        for e in ctx.sync.entries:
            rec = ctx.history.find(e.get("rec_id", "")) if e.get("enabled", True) else None
            if rec:
                recs.append(rec)
        if not recs:
            exec_blurred(page, MessageDialog(ctx.lang, t(M.SYP_ALL), t(M.SYP_ALL_NONE), win, info=True))
            return
        if page.state in BUSY or self._bg is not None:
            page._log("warn", M.LG_BUSY)
            exec_blurred(page, MessageDialog(ctx.lang, t(M.ERR_TITLE), t(M.LG_BUSY), win))
            return
        if not ctx.resources.ytdlp:
            page._error("no_ytdlp")
            return
        dlg = SyncAllDialog(ctx.lang, len(recs), win)
        self._all = {"recs": recs, "i": 0, "dlg": dlg, "tag": None, "checked": 0, "with_new": 0, "start": []}
        self._fetcher.ytdlp = ctx.resources.ytdlp
        QTimer.singleShot(0, self._all_next)
        exec_blurred(page, dlg)
        st, self._all = self._all, None
        self._tag += 1                                           # a late answer is ignored
        started = False
        for rec, chosen, redo in st["start"]:                    # downloads start when the window is closed
            if page.start_sync(rec, chosen, redo):
                started = True
        if started:
            self.started.emit()
        if st["checked"]:
            page._log("info", M.SYP_ALL_DONE, n=st["checked"], new=st["with_new"])

    def _all_next(self):
        st = self._all
        if st is None:
            return
        dlg = st["dlg"]
        if dlg.cancelled:
            return
        if st["i"] >= len(st["recs"]):
            dlg.finish(self.t(M.SYP_ALL_DONE, n=st["checked"], new=st["with_new"]))
            return
        rec = st["recs"][st["i"]]
        n = len(st["recs"])
        dlg.set_progress(st["i"] + 1, n)
        path = self.ctx.history.thumb_path(rec)
        pm = QPixmap(path) if path else None
        dlg.show_checking(pm, self._busy_info(rec))
        self._known = rec.get("videos") or {}
        self._bulk = False
        self._tag += 1
        st["tag"] = self._tag
        self.page._log("info", M.LG_SYNC_CHECK, title=rec.get("title", ""))
        self._fetcher.fetch(st["tag"], rec["url"], self._thumb_ids)

    def _all_advance(self, delay: int = 0):
        st = self._all
        if st is None:
            return
        st["i"] += 1
        st["tag"] = None
        st["dlg"].set_progress(min(st["i"], len(st["recs"])), len(st["recs"]), 10)
        QTimer.singleShot(delay, self._all_next)

    def _all_result(self, result):
        st = self._all
        if st is None or st["dlg"].cancelled:
            return
        dlg, ctx, t = st["dlg"], self.ctx, self.t
        rec = st["recs"][st["i"]]
        if result[0] == "error":
            self.page._log("warn", M.LG_SYNC_CHECK, title=rec.get("title", ""))
            dlg.show_message(rec.get("title", ""), t(M.SA_FAILED))
            self._all_advance(1800)
            return
        info, thumbs = result[1], result[2]
        entries = info.get("entries", [])
        ctx.history.absorb_singles(rec, [e["id"] for e in entries])
        self._known = rec.get("videos") or {}
        new = [e for e in entries if e["id"] not in self._known]
        old = self._old_rows(rec)
        self.page._log("info", M.LG_SYNC_FOUND, title=rec.get("title", ""), total=len(entries), done=len(old), new=len(new))
        st["checked"] += 1
        if not new and not any(o["kind"] in ("skipped", "missing") for o in old):
            pid = rec.get("playlist_id", "")
            if pid:
                ctx.sync.synced_now(pid)
            entry = ctx.sync.find(pid) if pid else None
            lines = [t(M.SD_LAST, date=(entry or {}).get("last_sync") or rec.get("last_sync", "") or t(M.BZ_NEVER))]
            if entry and entry.get("enabled", True):
                nxt = add_schedule(datetime.now(), entry.get("schedule", "daily"))
                lines.append(t(M.SD_NEXT, date=nxt.strftime("%Y-%m-%d %H:%M")))
            dlg.show_message(t(M.SD_TITLE), t(M.SD_TEXT, title=rec.get("title", "")), lines)
            self._all_advance(1500)
            return
        panel = SyncPanel(ctx.lang, new, old, thumbs, on_play=self._play, on_reveal=reveal_file,
                          available=[e["id"] for e in entries])
        panel.chosen.connect(lambda action, p=panel, r=rec, nw=new, es=entries: self._all_chosen(action, p, r, nw, es))
        dlg.set_content(panel)
        if new:
            st["with_new"] += 1

    def _all_chosen(self, action: str, panel, rec: dict, new: list, entries: list):
        st = self._all
        if st is None:
            return
        if action in ("download", "sync"):
            chosen = [e for e in entries if e["id"] in panel.selected]
            if chosen:
                st["start"].append((rec, chosen, panel.redownload))
        elif action == "skip":
            self._skip(rec, new)
        self._all_advance(0)

    def _busy_info(self, rec: dict, progress=None) -> list:
        """Lines of the checking window: which playlist, files already there, last sync, quality, folder."""
        t = self.t
        entry = self.ctx.sync.find(rec.get("playlist_id", "")) if rec.get("playlist_id") else None
        last = (entry or {}).get("last_sync") or rec.get("last_sync") or t(M.BZ_NEVER)
        have = sum(1 for v in (rec.get("videos") or {}).values() if v.get("state", "downloaded") == "downloaded")
        lines = [t(M.BZ_PROGRESS, i=progress[0], n=progress[1])] if progress else []
        lines += [t(M.BZ_PLAYLIST, title=rec.get("title", "")), t(M.BZ_FILES, n=have), t(M.BZ_LAST, date=last),
                  t(M.BZ_QUALITY, q=rec.get("quality") or "-"), t(M.BZ_FOLDER, folder=rec.get("save_dir", "") or "-")]
        return lines

    def _nothing_new(self, rec: dict):
        """'Playlist synced, nothing new' window; the choices are saved in the sync list."""
        ctx = self.ctx
        pid = rec.get("playlist_id", "")
        if pid:
            ctx.sync.synced_now(pid)
        entry = ctx.sync.find(pid) if pid else None
        dlg = SyncDoneDialog(ctx.lang, rec.get("title", ""), (entry or {}).get("last_sync") or rec.get("last_sync", ""),
                             (entry or {}).get("schedule", "daily"), bool(entry and entry.get("enabled", True)),
                             can_keep=bool(pid and rec.get("url")), parent=self.page.window())
        exec_blurred(self.page, dlg)
        if not dlg.changed or not pid:
            return
        if entry:
            if entry.get("schedule") != dlg.schedule:
                ctx.sync.set_schedule(entry, dlg.schedule)
            entry["enabled"] = dlg.enabled
            ctx.sync.save()
        elif dlg.enabled:
            ctx.sync.add(pid, rec.get("id", ""), rec.get("url", ""), rec.get("title", ""), dlg.schedule)
        else:
            return
        self.page.history_changed.emit()

    def run(self, rec: dict, quiet: bool = False, progress=None, bulk: bool = False):
        """Check one playlist. Returns 'busy' / 'error' / 'cancelled' / 'none' (no new videos) / 'new'.
        quiet=True: no window when there is nothing new. bulk=True (Sync all): every playlist gets its window, no thumbnails."""
        ctx, page, t = self.ctx, self.page, self.t
        win = page.window()
        if page.state in BUSY or self._bg is not None:
            page._log("warn", M.LG_BUSY)
            exec_blurred(page, MessageDialog(ctx.lang, t(M.ERR_TITLE), t(M.LG_BUSY), win))
            return "busy"
        if not ctx.resources.ytdlp:
            page._error("no_ytdlp")
            return "error"
        self._known = rec.get("videos") or {}
        self._bulk = bulk
        self._result = None
        self._tag += 1
        tag = self._tag
        page._log("info", M.LG_SYNC_CHECK, title=rec.get("title", ""))
        self._fetcher.ytdlp = ctx.resources.ytdlp
        self._busy = busy = BusyDialog(ctx.lang, t(M.SY_CHECKING), win, info=self._busy_info(rec, progress))
        self._fetcher.fetch(tag, rec["url"], self._thumb_ids)
        exec_blurred(page, busy)
        self._busy = None
        if busy.cancelled or self._result is None:
            self._tag += 1                                   # a late answer is ignored
            return "cancelled"
        if self._result[0] == "error":
            page._error(self._result[1], self._result[2])
            return "error"
        _ok, info, thumbs = self._result
        entries = info.get("entries", [])
        ctx.history.absorb_singles(rec, [e["id"] for e in entries])
        self._known = rec.get("videos") or {}
        new = [e for e in entries if e["id"] not in self._known]
        old = self._old_rows(rec)
        page._log("info", M.LG_SYNC_FOUND, title=rec.get("title", ""), total=len(entries), done=len(old), new=len(new))
        if quiet and not new:                                 # Sync all: nothing new here -> no window
            if rec.get("playlist_id"):
                ctx.sync.synced_now(rec["playlist_id"])
            return "none"
        if not new and not any(o["kind"] in ("skipped", "missing") for o in old):    # 2.3.0: tell the user, offer the schedule
            self._nothing_new(rec)
            return "none"
        dlg = SyncDialog(ctx.lang, rec.get("title", ""), new, old, thumbs,
                         on_play=self._play, on_reveal=reveal_file, parent=win, available=[e["id"] for e in entries])
        exec_blurred(page, dlg)
        if dlg.action in ("download", "sync"):
            chosen = [e for e in entries if e["id"] in dlg.selected]
            if chosen and page.start_sync(rec, chosen, dlg.redownload):
                self.started.emit()
        elif dlg.action == "skip":
            self._skip(rec, new)
        return "new" if new else "none"

    def _old_rows(self, rec: dict) -> list:
        """Every video the history knows: kind = 'have' (file is in the folder), 'missing' (downloaded, but the file is not
        in the folder any more) or 'skipped' (skipped before)."""
        rows = []
        for vid, v in (rec.get("videos") or {}).items():
            state = v.get("state", "downloaded")
            if state not in ("downloaded", "skipped"):
                continue
            path = self._path(rec, v)
            kind = "skipped" if state == "skipped" else ("have" if os.path.isfile(path) else "missing")
            rows.append({"id": vid, "title": v.get("title", vid), "date": v.get("date", ""), "size": v.get("size", 0),
                         "file": v.get("file", ""), "path": path, "kind": kind})
        return rows

    # --- 'Sync now' of the due-playlists window: in the background, nothing is shown while it runs -------------
    def run_background(self, recs: list):
        """Check the playlists one after the other without any window: only the NEW videos are added to the downloads;
        a warning at the end lists the downloaded videos whose files are not in the folder."""
        ctx, page = self.ctx, self.page
        if self._bg is not None or not recs:
            return
        if not ctx.resources.ytdlp:
            page._error("no_ytdlp")
            return
        self._bg = {"queue": list(recs), "rec": None, "tag": None, "missing": []}
        page._log("info", M.LG_DUE_BG, n=len(recs))
        self._bg_next()

    def _bg_next(self):
        bg = self._bg
        if not bg["queue"]:
            self._bg_finish()
            return
        bg["rec"] = rec = bg["queue"].pop(0)
        self._tag += 1
        bg["tag"] = self._tag
        self._fetcher.ytdlp = self.ctx.resources.ytdlp
        self._fetcher.fetch(self._tag, rec["url"])

    def _bg_result(self, info: dict):
        bg, page, ctx = self._bg, self.page, self.ctx
        rec = bg["rec"]
        entries = info.get("entries", [])
        ctx.history.absorb_singles(rec, [e["id"] for e in entries])
        known = rec.get("videos") or {}
        new = [e for e in entries if e["id"] not in known]
        for row in self._old_rows(rec):
            if row["kind"] == "missing":
                bg["missing"].append(f"{rec.get('title', '')}:  {row['title']}")
        if new and page.start_sync(rec, new, False):
            page._log("info", M.LG_DUE_ADDED, title=rec.get("title", ""), n=len(new))
        else:
            if not new:
                page._log("info", M.LG_DUE_NONE, title=rec.get("title", ""))
                if rec.get("playlist_id"):
                    ctx.sync.synced_now(rec["playlist_id"])
        QTimer.singleShot(0, self._bg_next)

    def _bg_failed(self, detail: str):
        self.page._log("warn", M.LG_DUE_FAIL, title=self._bg["rec"].get("title", ""), detail=detail)
        QTimer.singleShot(0, self._bg_next)

    def _bg_finish(self):
        missing = self._bg["missing"]
        self._bg = None
        if missing:
            ctx, t = self.ctx, self.t
            shown = "\n".join(missing[:12]) + (f"\n... (+{len(missing) - 12})" if len(missing) > 12 else "")
            exec_blurred(self.page, MessageDialog(ctx.lang, t(M.DUE_MISSING_TITLE), t(M.DUE_MISSING_TEXT, list=shown),
                                                  self.page.window()))

    @staticmethod
    def _path(rec: dict, video: dict) -> str:
        f = video.get("file", "")
        return f if os.path.isabs(f) else os.path.join(os.path.expanduser(rec.get("save_dir", "")), f)

    @staticmethod
    def _play(path: str):
        if path and os.path.isfile(path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def _skip(self, rec: dict, new: list):
        """'Skip New': remember the new videos as skipped so they are not offered again."""
        videos = rec.setdefault("videos", {})
        now = now_text()
        for e in new:
            videos[e["id"]] = {"title": e["title"], "file": "", "size": 0, "date": now, "state": "skipped"}
        rec["last_sync"] = now
        self.ctx.history.save()
        if rec.get("playlist_id"):
            self.ctx.sync.synced_now(rec["playlist_id"])
        self.page._log("info", M.LG_SYNC_SKIP, n=len(new))
        self.page.history_changed.emit()
