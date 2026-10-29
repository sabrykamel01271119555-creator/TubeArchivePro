# =============================================================================
# TubeArchive Pro  |  Version 2.3.1  |  File: app/ui/new_download_page.py
# Version history of this file:
#   2.3.2 - a video that cannot be downloaded: window 'N videos cannot be downloaded now' - Retry now / Later (kept, reminded at the next
#           start) / Cancel (forgotten); several failures are gathered into one window
#   2.3.1 - the size is shown beside every quality of the list
#   2.3.0 - tools_check_requested: after an error that an old yt-dlp can cause the main window checks for tool updates
#   2.3.0 - a video link that carries a playlist (list=) asks what to do (_playlist_gate): download / check the playlist,
#           the file only, or - when the playlist is in the history - sync it and say if the file was downloaded before
#   2.2.7 - sound when a download / playlist / sync is completed
#   2.2.5 - a playlist cancelled in the Downloads list is not saved in the history
#   2.2.3 - Counters: downloading / queue / paused with icons
#   2.2.2 - Big counters (downloading now / queue) in place of the file frame while downloads run; title 'Downloading'
#   2.0.11 - Already-downloaded window also when the file is gone: Play dimmed, Open folder
#   2.0.10 - Already-downloaded window shows the thumbnail; a record whose file is gone is treated as new (MSG_410)
#   2.0.9 - Check: errors are shown, never silent
#   2.0.7 - A redownloaded video replaces its old history entry (favorite kept); Check / Start ask 'Redownload / Play / Cancel' when the video is already in the history (_duplicate_ok)
#   2.0.2 - Four buttons again (Start, Pause, Cancel, Open folder: act on the queue); a 'Check' button reads the link
#           (no automatic reading); only the really available resolutions; sizes kept in memory; free-space check
#           (needs ~2x the size) with the suggestion to lower the quality or choose another folder; playlist total size
#   2.0.1 - Start adds the video / playlist to the download queue (app/dlqueue.py) and the page is free for the
#           next link; progress, pause and cancel live on the Downloads page; playlists = one task per video;
#           the description of each video is saved in the history
#   1.0.14 - Settings drive yt-dlp options, audio bitrate default, playlist-folder default, favorite prompt switch
#   1.0.12 - Default format / quality / folder come from Settings (apply_defaults); downloaded signal; playlist-updated notification
#   1.0.11 - Playlists: options window for a NEW playlist (own folder, add to sync + schedule); a playlist that
#            is already in the history opens the sync window instead; start_sync() downloads the chosen new videos.
#   1.0.10 - Drop-down lists show an arrow (ArrowComboBox)
#   1.0.9 - Red round button removed (link is read automatically / Enter); Format drop-down now before
#           Quality; whole page scales with its size; the video frame stays empty until a link is read;
#           Start only when a video is ready; finished downloads are saved in the history (with thumbnail);
#           'Add to Favorite' in the success window; prefill() for 'Download again' of the Downloads tab.
#   1.0.8 - Created: "New Download" tab (URL, save folder, quality / file type drop-downs,
#           ready-to-download card, Start / Pause / Cancel / Open Folder, system log,
#           success and error windows). Replaces the design-only NewDownloadPage of pages.py.
# =============================================================================
"""'New Download' tab (design guide: mainwindow-downloader.jpg + file-downloaded dialog).

The page reads a link, shows the video and puts it in the download queue. The real work is done by
app/download_manager.py (signals) -> app/dlqueue.py (queue) -> app/downloader.py (yt-dlp command line, no Qt).
"""
import html
import os
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QPixmap
from PySide6.QtWidgets import (QFileDialog, QFrame, QHBoxLayout, QLabel,
                               QLineEdit, QPlainTextEdit, QPushButton,
                               QVBoxLayout, QWidget)

from ..context import AppContext
from ..download_manager import DownloadManager, InfoFetcher
from ..history import video_key
from ..failed import entry_of
from ..downloader import (AUDIO_FORMATS, playlist_id, VIDEO_FORMATS, available_heights, drive_name, estimate_playlist_size,
                          estimate_size, fmt_size, fmt_time, free_bytes, is_audio, is_playlist_url, looks_like_url,
                          max_height, parse_quality, quality_label, quality_options, size_table, space_needed)
from .. import sounds
from ..msg import M
from ..sync import now_text
from .actions import add_to_favorites, badge_text, exec_blurred, reveal_file
from .dialogs import ChoiceDialog, MessageDialog, PlaylistSetupDialog, SuccessDialog
from .icons import make_play_icon, make_state_icon, make_thumb, rounded_pixmap
from .theme import glow
from .widgets import ArrowComboBox, ElidedLabel

MB = 1024 * 1024
THUMB_W, THUMB_H = 232, 130          # design size, multiplied by the page scale
DESIGN_W, DESIGN_H = 680, 560        # page size at which the scale is 1.0

# error code (from downloader.py) -> message id
ERROR_MSG = {
    "no_ytdlp": M.ERR_NO_YTDLP, "no_ffmpeg": M.ERR_NO_FFMPEG, "bad_url": M.ERR_BAD_URL,
    "unsupported": M.ERR_UNSUPPORTED, "unavailable": M.ERR_UNAVAILABLE, "private": M.ERR_PRIVATE,
    "age": M.ERR_AGE, "signin": M.ERR_SIGNIN, "geo": M.ERR_GEO, "network": M.ERR_NETWORK,
    "rate": M.ERR_RATE, "disk": M.ERR_DISK, "format": M.ERR_FORMAT, "unknown": M.ERR_UNKNOWN,
    "folder": M.ERR_FOLDER, "pause": M.ERR_PAUSE,
}
LOG_COLOR = {"info": "#38ff6a", "warn": "#ffc94d", "error": "#ff6b7d"}


_badge = badge_text          # kept for the tests


class NewDownloadPage(QWidget):
    history_changed = Signal()          # a finished download was added to the history
    sync_requested = Signal(object)     # playlist already in the history -> main window opens the sync window
    show_downloads = Signal()           # "Downloads" button -> main window shows the Downloads page
    tools_check_requested = Signal()    # 2.3.0: a download / check failed for a reason an old yt-dlp can cause

    def __init__(self, ctx: AppContext):
        super().__init__()
        self.ctx = ctx
        self.t = ctx.lang.tr
        self.state = "idle"             # idle | fetching | ready
        self.info = None
        self.est_size = None
        self.sizes: dict = {}           # {(format, quality): estimated bytes} of the video that was read (kept in memory)
        self._thumb_src = None          # QPixmap of the video (None = no picture)
        self._pending_q = None          # quality to select once the link is read (Download again)
        self._scale = 0.0
        self._silent = False
        self._fail_buf, self._fail_gen = [], 0     # 2.3.2: failed single videos, shown together after a short pause
        self._pl_ok_url = ""              # video link whose playlist question was answered 'file only' (not asked again)
        self._auto_start = False          # 'Download playlist' chosen: Start runs as soon as the playlist is read
        self._pl_fetcher = InfoFetcher(ctx.resources.ytdlp)
        self._pl_tag, self._pl_info, self._pl_busy = 0, None, None
        self._pl_fetcher.ready.connect(self._pl_ready)
        self._pl_fetcher.failed.connect(self._pl_failed)
        self._redo_url = ""               # link the user chose to 'Redownload' (the file is replaced, no second question)
        if getattr(ctx, "downloads", None) is None:       # one manager (and queue) for the whole program run
            ctx.downloads = DownloadManager(ctx.resources.ytdlp, ctx.resources.ffmpeg_dir, ctx.settings.get)
        self.mgr = ctx.downloads
        self.mgr.sync_tools(ctx.resources.ytdlp, ctx.resources.ffmpeg_dir)
        self._build()
        self._wire()
        self._rescale(1.0)
        self._fill_formats()
        self._rebuild_quality()
        self._set_state("idle")
        self._log("info", M.LG_READY)
        if not ctx.resources.ytdlp:
            self._log("error", ERROR_MSG["no_ytdlp"])

    # ------------------------------------------------------------------
    # building the interface
    # ------------------------------------------------------------------
    def _build(self):
        t = self.t
        root = QVBoxLayout(self)
        root.setContentsMargins(22, 16, 22, 14)
        root.setSpacing(10)

        lbl = QLabel(t(M.ND_URL))
        lbl.setObjectName("fieldLabel")
        root.addWidget(lbl)
        row = QHBoxLayout()
        row.setSpacing(14)
        self.url = QLineEdit()
        self.url.setObjectName("urlEdit")
        self.url.setPlaceholderText(t(M.ND_URL_PH))
        self.url.setMinimumHeight(48)
        row.addWidget(self.url, 1)
        self.b_check = QPushButton(t(M.ND_ANALYZE))              # reads the link on demand (pasted link -> press this)
        self.b_check.setObjectName("primary")
        self.b_check.setCursor(Qt.PointingHandCursor)
        self.b_check.setToolTip(t(M.ND_ANALYZE_TIP))
        self.b_check.setEnabled(False)
        row.addWidget(self.b_check)
        root.addLayout(row)

        cards = QHBoxLayout()
        cards.setSpacing(12)
        # save directory
        c1 = self._card(t(M.ND_SAVE_DIR))
        r1 = QHBoxLayout()
        self.folder = QLineEdit(str(self.ctx.settings.download_dir()))
        self.browse = QPushButton(t(M.BTN_BROWSE))
        self.browse.setObjectName("primary")
        self.browse.setCursor(Qt.PointingHandCursor)
        r1.addWidget(self.folder, 1)
        r1.addWidget(self.browse)
        c1.layout().addLayout(r1)
        # container format (first) ...
        c2 = self._card(t(M.ND_FORMAT))
        self.fmt = ArrowComboBox()
        c2.layout().addWidget(self.fmt)
        # ... then the quality, which depends on it
        c3 = self._card(t(M.ND_QUALITY))
        self.q_title = c3.layout().itemAt(0).widget()
        self.quality = ArrowComboBox()
        c3.layout().addWidget(self.quality)
        cards.addWidget(c1, 5)
        cards.addWidget(c2, 3)
        cards.addWidget(c3, 3)
        root.addLayout(cards)

        self.state_lbl = QLabel(t(M.ND_READY))
        self.state_lbl.setObjectName("fieldLabel")
        root.addWidget(self.state_lbl)

        self.card = QFrame()                  # empty frame until a link has been read
        self.card.setObjectName("dlItem")
        cl = QVBoxLayout(self.card)
        cl.setContentsMargins(0, 0, 0, 0)
        self.card_inner = QWidget()
        self.card_inner.setStyleSheet("background: transparent;")
        h = self.h_card = QHBoxLayout(self.card_inner)
        h.setContentsMargins(12, 12, 16, 12)
        h.setSpacing(16)
        self.thumb = QLabel()
        self.thumb.setObjectName("thumb")
        self.thumb.setFixedSize(THUMB_W, THUMB_H)
        h.addWidget(self.thumb)
        col = QVBoxLayout()
        col.setSpacing(6)
        self.title = ElidedLabel("")
        self.title.setObjectName("ndTitle")
        self.meta = QLabel("")
        self.meta.setObjectName("ndSub")
        self.warn = QLabel("")                                   # not enough free space ...
        self.warn.setObjectName("ndWarn")
        self.warn.setWordWrap(True)
        self.warn.setVisible(False)
        col.addStretch(1)
        col.addWidget(self.title)
        col.addWidget(self.meta)
        col.addWidget(self.warn)
        col.addStretch(1)
        h.addLayout(col, 1)
        cl.addWidget(self.card_inner)
        self.counters = QWidget()              # big numbers shown in place of the file frame while downloads are running (2.2.2)
        self.counters.setStyleSheet("background: transparent;")
        ch = QHBoxLayout(self.counters)
        ch.setContentsMargins(12, 6, 12, 6)
        self.big_run, self.big_wait, self.big_pause = QLabel("0"), QLabel("0"), QLabel("0")
        self.cap_run, self.cap_wait = QLabel(t(M.ND_CNT_RUNNING)), QLabel(t(M.ND_CNT_QUEUE))
        self.cap_pause = QLabel(t(M.ND_CNT_PAUSED))
        self.cnt_icons = []
        for kind, name, big, cap in (("down", "bigRun", self.big_run, self.cap_run),
                                     ("queue", "bigWait", self.big_wait, self.cap_wait),
                                     ("pause", "bigPause", self.big_pause, self.cap_pause)):
            ic = QLabel()
            ic.setAlignment(Qt.AlignCenter)
            self.cnt_icons.append((ic, kind))
            big.setObjectName(name)
            big.setAlignment(Qt.AlignCenter)
            cap.setObjectName("bigCap")
            cap.setAlignment(Qt.AlignCenter)
            colv = QVBoxLayout()
            colv.setSpacing(0)
            colv.addStretch(1)
            colv.addWidget(ic)
            colv.addWidget(big)
            colv.addWidget(cap)
            colv.addStretch(1)
            ch.addLayout(colv, 1)
        self.counters.setVisible(False)
        cl.addWidget(self.counters)
        root.addWidget(self.card)

        btns = QHBoxLayout()
        btns.setSpacing(14)
        self.b_start = QPushButton("  " + t(M.BTN_START))
        self.b_start.setIcon(make_play_icon(22))
        self.b_pause = QPushButton(t(M.BTN_PAUSE1))
        self.b_cancel = QPushButton(t(M.BTN_CANCEL1))
        self.b_folder = QPushButton(t(M.BTN_FOLDER1))
        for b, name, colr in ((self.b_start, "btnGreen", "#1fd16a"), (self.b_pause, "btnOrange", "#ffa800"),
                              (self.b_cancel, "btnRed", "#ff2f72"), (self.b_folder, "btnBlue", "#2b8cff")):
            b.setObjectName(name)
            b.setMinimumHeight(48)
            b.setCursor(Qt.PointingHandCursor)
            glow(b, colr, 18)
            btns.addWidget(b)
        root.addLayout(btns)

        lg = QLabel(t(M.SYSTEM_LOG))
        lg.setObjectName("sysLog")
        root.addWidget(lg)
        self.log = QPlainTextEdit()
        self.log.setObjectName("log")
        self.log.setReadOnly(True)
        self.log.setMinimumHeight(40)
        root.addWidget(self.log, 1)
        self.root_l = root

    def _card(self, title: str) -> QFrame:
        f = QFrame()
        f.setObjectName("optCard")
        v = QVBoxLayout(f)
        v.setContentsMargins(16, 12, 16, 14)
        v.setSpacing(8)
        lb = QLabel(title)
        lb.setObjectName("cardTitle")
        v.addWidget(lb)
        return f

    def _wire(self):
        self.url.returnPressed.connect(self._fetch)
        self.url.textChanged.connect(self._url_changed)
        self.browse.clicked.connect(self._browse)
        self.folder.editingFinished.connect(self._save_folder)
        self.fmt.currentIndexChanged.connect(self._format_changed)
        self.quality.currentIndexChanged.connect(self._quality_changed)
        self.b_start.clicked.connect(self._start)
        self.b_check.clicked.connect(self._fetch)
        self.b_pause.clicked.connect(self._pause_clicked)
        self.b_cancel.clicked.connect(self._cancel_clicked)
        self.b_folder.clicked.connect(lambda: self._open_folder())
        m = self.mgr
        m.info_ready.connect(self._info_ready)
        m.info_failed.connect(self._info_failed)
        m.task_changed.connect(lambda _t: self._sync_buttons())
        m.group_changed.connect(lambda _g: self._sync_buttons())
        m.task_done.connect(self._task_done)
        m.task_failed.connect(self._task_failed)
        m.task_cancelled.connect(self._task_cancelled)
        m.group_done.connect(self._group_done)

    # ------------------------------------------------------------------
    # drop-downs
    # ------------------------------------------------------------------
    def _fill_formats(self):
        t = self.t
        self.fmt.blockSignals(True)
        self.fmt.clear()
        for f in VIDEO_FORMATS:
            self.fmt.addItem(f"{f} · {t(M.ND_VIDEO_TAG)}", f)
        self.fmt.insertSeparator(self.fmt.count())                 # audio formats at the bottom
        for f in AUDIO_FORMATS:
            self.fmt.addItem(f"{f} · {t(M.ND_AUDIO_TAG)}", f)
        i = self.fmt.findData(self.ctx.settings.get("default_format", "MP4"))
        self.fmt.setCurrentIndex(max(0, i))
        self.fmt.blockSignals(False)

    def cur_format(self) -> str:
        return self.fmt.currentData() or "MP4"

    def cur_quality(self) -> int:
        return int(self.quality.currentData() or 0)

    def _rebuild_quality(self):
        """Quality list depends on the file type: heights for video, kbps / kHz for audio."""
        t, fmt = self.t, self.cur_format()
        prev = self._pending_q if self._pending_q is not None else self.quality.currentData()
        st = self.ctx.settings
        if is_audio(fmt):                                           # the bitrate chosen in Settings (for its format)
            default = parse_quality(st.get("audio_quality", 320)) if fmt == st.get("audio_format", "MP3") else None
        else:
            default = parse_quality(st.get("default_quality", 0))
        mh = 0 if (self.info and self.info.get("is_playlist")) else max_height(self.info)
        opts = quality_options(fmt, mh)
        hs = [] if (not self.info or self.info.get("is_playlist")) else available_heights(self.info)
        if hs and not is_audio(fmt):                                # only the resolutions that this video really has
            opts = [0] + hs
        self.quality.blockSignals(True)
        self.quality.clear()
        for q in opts:
            label = quality_label(fmt, q) or t(M.ND_BEST)
            size = (self.sizes or {}).get((fmt.upper(), q))
            self.quality.addItem(f"{label}  ·  {fmt_size(size)}" if size else label, q)     # 2.3.1: the size beside each quality
        i = self.quality.findData(prev) if prev is not None else -1
        if i < 0 and default is not None:
            i = self.quality.findData(default)                      # not available any more -> the default of Settings
        self.quality.setCurrentIndex(i if i >= 0 else 0)
        self.quality.blockSignals(False)
        self.q_title.setText(t(M.ND_QUALITY_AUDIO if is_audio(fmt) else M.ND_QUALITY))
        self._update_meta()

    def _format_changed(self):
        self._rebuild_quality()

    def _quality_changed(self):
        self._update_meta()

    # ------------------------------------------------------------------
    # link information
    # ------------------------------------------------------------------
    def _url_changed(self):
        if self._silent:
            return
        self._redo_url = "" if self._redo_url != self.url.text().strip() else self._redo_url
        self.mgr.invalidate()
        self.info = None
        self.est_size = None
        self.sizes = {}
        self._thumb_src = None
        self.title.set_full_text("")
        self._rebuild_quality()
        self._set_state("idle")
        self.b_check.setEnabled(looks_like_url(self.url.text()))      # the link is read when the user presses it

    def _fetch(self, *_):
        try:
            self._fetch_now()
        except Exception as exc:                               # noqa: BLE001  (never a silent button)
            import traceback
            from ..downloader import log_fetch
            log_fetch("Check button error:\n" + traceback.format_exc())
            self._set_state("idle")
            self._error("unknown", str(exc))

    def _fetch_now(self):
        url = self.url.text().strip()
        if not looks_like_url(url):
            self._error("bad_url")
            return
        if not self.ctx.resources.ytdlp:
            self._error("no_ytdlp")
            return
        if not self._playlist_gate(url):
            return
        url = self.url.text().strip()                             # 'Download / Check playlist' replaced the link
        if not self._duplicate_ok(url):
            return
        self._set_state("fetching")
        self._log("info", M.LG_FETCH)
        self.mgr.fetch(url)

    # --- 2.3.0: a video link that also carries a playlist (watch?v=...&list=...) -----------------------------------
    @staticmethod
    def _playlist_url_of(url: str) -> str:
        """The playlist page of a YouTube video link that carries list=...; '' for every other link."""
        low = url.lower()
        if is_playlist_url(url) or not ("youtube.com" in low or "youtu.be" in low):
            return ""
        pid = playlist_id(url)
        if not pid or pid.upper().startswith("RD"):
            return ""                                             # mixes ('RD...') are endless: treat as a single video
        return "https://www.youtube.com/playlist?list=" + pid

    def _pl_ready(self, tag, info, _thumbs):
        if tag == self._pl_tag:
            self._pl_info = info
            if self._pl_busy:
                self._pl_busy.finish()

    def _pl_failed(self, tag, _code, _detail):
        if tag == self._pl_tag:
            self._pl_info = {}
            if self._pl_busy:
                self._pl_busy.finish()

    def _playlist_gate(self, url: str) -> bool:
        """True = go on with the link as a single video; False = stopped (cancel) or another flow took over.
        Playlist not in the history: Download playlist / Check playlist / Download file only / Cancel.
        Playlist in the history: says if THIS file was downloaded before, shows the list, offers Sync playlist."""
        pl_url = self._playlist_url_of(url)
        if not pl_url or self._pl_ok_url == url or self._redo_url == url:
            return True
        ctx, t = self.ctx, self.ctx.lang.tr
        rec = ctx.history.find_playlist(pl_url)
        if rec:
            vid = video_key(url).removeprefix("yt:")                  # the id yt-dlp gives to the video of a playlist
            vids = rec.get("videos") or {}
            hit = next((v for k, v in vids.items() if k == vid and v.get("state", "downloaded") == "downloaded"), None)
            single = ctx.history.find_video(url)
            when = (hit or {}).get("date") or (single or {}).get("date", "")
            if hit or single:
                f = hit.get("file", "") if hit else ""
                path = f if f and os.path.isabs(f) else os.path.join(os.path.expanduser(rec.get("save_dir", "")),
                                                                      f or (single or {}).get("file_name", ""))
                gone = not os.path.isfile(path)
                state = t(M.PLC_FILE_GONE if gone else M.PLC_FILE_YES, date=when)
            else:
                state = t(M.PLC_FILE_NO)
            have = sum(1 for v in vids.values() if v.get("state", "downloaded") == "downloaded")
            text = t(M.PLC_OLD_TEXT, title=rec.get("title", ""), count=have, last=rec.get("last_sync") or rec.get("date", ""),
                     folder=rec.get("save_dir", ""), state=state)
            tp = ctx.history.thumb_path(rec)
            buttons = [("sync", t(M.PLC_BTN_SYNC), "btnGreen"),
                       ("file", t(M.PLC_BTN_AGAIN if (hit or single) else M.PLC_BTN_FILE), "btnOrange"),
                       ("cancel", t(M.BTN_CANCEL1), "btnRed")]
            dlg = ChoiceDialog(ctx.lang, t(M.PLC_TITLE), text, buttons, self.window(),
                               pixmap=QPixmap(tp) if tp else None, size=(860, 600))
            exec_blurred(self, dlg)
            if dlg.choice == "sync":
                self.sync_requested.emit(rec)
                return False
            if dlg.choice == "file":
                self._pl_ok_url = url
                if hit or single:
                    self._redo_url = url                           # asked once: the file is replaced
                return True
            return False
        # not downloaded before: read the list (title, number of videos), then ask
        if not ctx.resources.ytdlp:
            return True
        self._pl_info, self._pl_tag = None, self._pl_tag + 1
        from .dialogs import BusyDialog
        self._pl_busy = busy = BusyDialog(ctx.lang, t(M.PLC_CHECKING), self.window())
        self._pl_fetcher.ytdlp = ctx.resources.ytdlp
        self._pl_fetcher.fetch(self._pl_tag, pl_url)
        exec_blurred(self, busy)
        self._pl_busy = None
        if busy.cancelled:
            self._pl_tag += 1
            return False
        info = self._pl_info or {}
        pm = QPixmap()
        pic = pm if info.get("thumb_bytes") and pm.loadFromData(info["thumb_bytes"]) else None
        text = t(M.PLC_NEW_TEXT, title=info.get("title") or "-", count=info.get("count") or len(info.get("entries", [])) or "?")
        buttons = [("all", t(M.PLC_BTN_DL), "btnGreen"), ("check", t(M.PLC_BTN_CHECK), "btnBlue"),
                   ("file", t(M.PLC_BTN_FILE), "btnOrange"), ("cancel", t(M.BTN_CANCEL1), "btnRed")]
        dlg = ChoiceDialog(ctx.lang, t(M.PLC_TITLE), text, buttons, self.window(), pixmap=pic, size=(980, 600))
        exec_blurred(self, dlg)
        if dlg.choice in ("all", "check"):
            self._auto_start = dlg.choice == "all"
            self.url.setText(pl_url)                              # the playlist link replaces the video link
            self.mgr.invalidate()
            self.info = None
            self._set_state("fetching")
            self._log("info", M.LG_FETCH)
            self.mgr.fetch(pl_url)
            return False
        if dlg.choice == "file":
            self._pl_ok_url = url
            return True
        return False

    def _duplicate_ok(self, url: str) -> bool:
        """Check / Start: a single video found in the history (and its file still there) asks what to do (2.0.5).
        True = go on (new video, or 'Redownload'); False = stop ('Play' opens the file, 'Cancel' does nothing)."""
        if is_playlist_url(url) or self._redo_url == url:
            return True
        rec = self.ctx.history.find_video(url)
        path = os.path.join(os.path.expanduser((rec or {}).get("save_dir", "")), (rec or {}).get("file_name", ""))
        if not rec:
            return True                                           # never downloaded: normal way
        gone = not os.path.isfile(path)                           # in the history, but removed from the folder / drive
        t = self.ctx.lang.tr
        tp = self.ctx.history.thumb_path(rec)
        pic = QPixmap(tp) if tp else None
        text = t(M.DUP_TEXT_GONE if gone else M.DUP_TEXT, date=rec.get("date", ""), title=rec.get("title", ""),
                 format=rec.get("format", ""), quality=rec.get("quality", ""), folder=rec.get("save_dir", ""))
        buttons = [("again", t(M.DUP_REDOWNLOAD), "btnOrange"),
                   ("play", t(M.TIP_PLAY), "btnGreen", not gone)]            # no file: Play is dimmed
        if gone:
            buttons.append(("folder", t(M.DUP_OPEN_FOLDER), "btnBlue", True, True))   # opens the folder, window stays
        buttons.append(("cancel", t(M.BTN_CANCEL1), "btnBlue"))
        dlg = ChoiceDialog(self.ctx.lang, t(M.DUP_TITLE), text, buttons, self.window(), pixmap=pic)
        dlg.on_keep = lambda _c: self._open_folder(rec.get("save_dir", ""))
        exec_blurred(self, dlg)
        if dlg.choice == "play":
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))
            return False
        if dlg.choice == "again":
            self._redo_url = url                                  # asked once: Start does not ask again, the file is replaced
            return True
        return False

    def _info_ready(self, token: int, info: dict):
        if token != self.mgr._token or self.state != "fetching":
            return
        self.info = info
        self.sizes = size_table(info)                              # estimated size of every format x quality, in memory
        self.title.set_full_text(info["title"])
        pm = QPixmap()
        self._thumb_src = pm if info.get("thumb_bytes") and pm.loadFromData(info["thumb_bytes"]) else None
        self._show_thumb()
        self._set_state("ready")
        self._rebuild_quality()
        self._pending_q = None
        auto, self._auto_start = self._auto_start, False
        if auto and info["is_playlist"]:                           # 'Download playlist' of the playlist question
            QTimer.singleShot(0, self._start)
        if info["is_playlist"]:
            self._log("info", M.LG_FOUND_PL, title=info["title"], count=info["count"])
        else:
            self._log("info", M.LG_FOUND, title=info["title"])
            hs = available_heights(info)
            if hs:
                self._log("info", M.LG_ANALYZED, list=", ".join(f"{h}p" for h in hs))

    def _info_failed(self, token: int, code: str, detail: str):
        if token != self.mgr._token or self.state != "fetching":
            return
        self._pending_q = None
        self._set_state("idle")
        self._error(code, detail)

    def _thumb_size(self):
        s = self._scale or 1.0
        h = max(40, int(THUMB_H * s))
        return int(h * THUMB_W / THUMB_H), h

    def _show_thumb(self):
        """Picture of the video (or a plain placeholder when the site gave none), at the current scale."""
        w, h = self._thumb_size()
        self.thumb.setFixedSize(w, h)
        if self._thumb_src is not None:
            self.thumb.setPixmap(rounded_pixmap(self._thumb_src, w, h, 10))
        else:
            self.thumb.setPixmap(make_thumb("#0a1a4a", "#1c4fa8", w, h))

    def _sync_card(self):
        """The frame shows the link that was read; when nothing is read and downloads are running or waiting it shows the
        big counters (downloading now / in the queue) and the title above it says 'Downloading' (2.2.2)."""
        n = self.mgr.queue.counts_by_state()
        running, waiting, paused = n["downloading"], n["waiting"], n["paused"]
        show = (running + waiting + paused) > 0 and self.info is None and self.state != "fetching"
        self.card_inner.setVisible(self.info is not None)
        self.counters.setVisible(show)
        self.big_run.setText(str(running))
        self.big_wait.setText(str(waiting))
        self.big_pause.setText(str(paused))
        self.state_lbl.setText(self.t(M.ND_DL_TITLE) if show else getattr(self, "_state_text", self.state_lbl.text()))

    # ------------------------------------------------------------------
    # size of the page: every element follows it
    # ------------------------------------------------------------------
    def resizeEvent(self, e):
        s = max(0.55, min(1.5, min(self.width() / DESIGN_W, self.height() / DESIGN_H)))
        if abs(s - self._scale) >= 0.02:
            self._rescale(s)
        super().resizeEvent(e)

    def _rescale(self, s: float):
        self._scale = s

        def r(x):
            return max(1, int(x * s))
        self.root_l.setContentsMargins(r(22), r(14), r(22), r(12))
        self.root_l.setSpacing(r(9))
        self.url.setMinimumHeight(r(46))
        for b in (self.b_start, self.b_pause, self.b_cancel, self.b_folder):
            b.setMinimumHeight(r(46))
        self.log.setMinimumHeight(r(40))
        self.h_card.setContentsMargins(r(12), r(10), r(16), r(10))
        self.h_card.setSpacing(r(16))
        w, h = self._thumb_size()
        self.card.setFixedHeight(h + r(22))
        cols = {"down": "#7dffb0", "queue": "#7fc8ff", "pause": "#ffc24d"}
        for ic, kind in self.cnt_icons:
            ic.setPixmap(make_state_icon(kind, max(20, r(30)), cols[kind]))
        self._show_thumb()
        self.setStyleSheet(f"""
            #fieldLabel {{ font-size: {r(19)}px; }}
            #cardTitle {{ font-size: {r(18)}px; }}
            #ndTitle {{ font-size: {r(19)}px; }}
            #ndSub {{ font-size: {r(15)}px; }}
            QLabel#bigRun, QLabel#bigWait, QLabel#bigPause {{ font-size: {r(46)}px; font-weight: bold; }}
            QLabel#bigRun {{ color: #7dffb0; }}
            QLabel#bigWait {{ color: #7fc8ff; }}
            QLabel#bigPause {{ color: #ffc24d; }}
            QLabel#bigCap {{ font-size: {r(17)}px; color: #cfe7ff; }}
            #ndWarn {{ font-size: {r(14)}px; color: #ffb3c0; font-weight: bold; }}
            QLabel#sysLog {{ font-size: {r(15)}px; }}
            QLineEdit#urlEdit {{ font-size: {r(17)}px; padding: {r(6)}px {r(14)}px; }}
            QLineEdit, QComboBox {{ font-size: {r(14)}px; padding: {r(5)}px {r(8)}px; min-height: {r(20)}px; }}
            QPushButton#primary {{ font-size: {r(14)}px; padding: {r(7)}px {r(18)}px; }}
            QPushButton#btnGreen, QPushButton#btnOrange, QPushButton#btnBlue, QPushButton#btnRed
                {{ font-size: {r(15)}px; padding: {r(7)}px 6px; }}
            QPlainTextEdit#log {{ font-size: {r(13)}px; }}
        """)

    def estimate_for(self, fmt: str, q: int):
        """Estimated bytes of this video / playlist for a format + quality: the table kept in memory, or the playlist sum."""
        if not self.info:
            return None
        if self.info.get("is_playlist"):
            return estimate_playlist_size(self.info.get("entries"), fmt, q)
        key = (fmt.upper(), q)
        if key in self.sizes:
            return self.sizes[key]
        return estimate_size(self.info, fmt, q)

    def space_needed_for(self, est) -> int:
        """Free bytes that a download of `est` bytes needs: twice the size (parts + final file); a playlist keeps its
        finished files, so it needs the total + the working space of the videos that run at the same time."""
        if not est:
            return 0
        if self.info and self.info.get("is_playlist"):
            n = max(1, int(self.info.get("count") or 1))
            try:
                par = max(1, int(self.ctx.settings.get("playlist_concurrent", 1)))
            except (TypeError, ValueError):
                par = 1
            return space_needed(est, 1.0, extra=par * (est / n))
        return space_needed(est)

    def _update_meta(self):
        """'Estimated size: 850 MB | Duration: 12:30' under the title + the free-space warning."""
        t = self.t
        self.warn.setVisible(False)
        if not self.info:
            self.meta.setText("")
            self.est_size = None
            return
        if self.info["is_playlist"]:
            self.est_size = self.estimate_for(self.cur_format(), self.cur_quality())
            parts = [t(M.ND_PLAYLIST, count=self.info["count"])]
            if self.est_size:
                parts.append(t(M.ND_EST, size=fmt_size(self.est_size)))
            self.meta.setText("  |  ".join(parts))
        else:
            self.est_size = self.estimate_for(self.cur_format(), self.cur_quality())
            parts = [t(M.ND_EST, size=fmt_size(self.est_size)) if self.est_size else t(M.ND_EST_UNKNOWN)]
            if self.info.get("duration"):
                parts.append(t(M.ND_DURATION, duration=fmt_time(self.info["duration"])))
            self.meta.setText("  |  ".join(parts))
        self._show_space_warning()

    def _folder_path(self) -> Path:
        return Path(os.path.expanduser(self.folder.text().strip() or str(self.ctx.settings.download_dir())))

    def _show_space_warning(self):
        need = self.space_needed_for(self.est_size)
        free = free_bytes(self._folder_path())
        if need and free is not None and free < need:
            self.warn.setText(self.t(M.SP_WARN_LINE, drive=drive_name(self._folder_path()), free=fmt_size(free),
                                     need=fmt_size(need)))
            self.warn.setVisible(True)
        else:
            self.warn.setVisible(False)

    def _space_ok(self) -> bool:
        """Before a download starts: is there room on the partition of the folder? When not, the user may lower the
        quality (the best one that fits is suggested), choose another folder, or cancel."""
        t = self.t
        for _round in range(6):
            est = self.estimate_for(self.cur_format(), self.cur_quality())
            need = self.space_needed_for(est)
            folder = self._folder_path()
            free = free_bytes(folder)
            if not need or free is None or free >= need:
                return True
            fmt = self.cur_format()
            cands = [self.quality.itemData(i) for i in range(self.quality.count())]
            ok = [q for q in cands if (e := self.estimate_for(fmt, q)) and self.space_needed_for(e) <= free]
            fit = max(ok, key=lambda q: (self.estimate_for(fmt, q) or 0)) if ok else None      # the best one that fits
            text = t(M.SP_TEXT, drive=drive_name(folder), free=fmt_size(free), need=fmt_size(need),
                     size=fmt_size(est))
            buttons = []
            if fit is not None and fit != self.cur_quality():
                buttons.append(("lower", t(M.SP_LOWER, q=quality_label(fmt, fit) or t(M.ND_BEST)), "btnOrange"))
            else:
                text += "\n\n" + t(M.SP_NONE_FITS)
            buttons += [("folder", t(M.SP_FOLDER), "btnBlue"), ("cancel", t(M.SP_CANCEL), "btnRed")]
            dlg = ChoiceDialog(self.ctx.lang, t(M.SP_TITLE), text, buttons, self.window())
            exec_blurred(self, dlg)
            if dlg.choice == "lower":
                self.quality.setCurrentIndex(max(0, self.quality.findData(fit)))
                continue
            if dlg.choice == "folder":
                self._browse()
                continue
            self._log("warn", M.LG_SPACE_LOW, drive=drive_name(folder))
            return False
        return False

    # ------------------------------------------------------------------
    # state of the page (buttons, labels)
    # ------------------------------------------------------------------
    def _set_state(self, state: str):
        t = self.t
        self.state = state
        texts = {"idle": M.ND_READY, "ready": M.ND_READY, "fetching": M.ND_FETCHING}
        self._state_text = t(texts[state])
        self.state_lbl.setText(self._state_text)
        self.b_start.setEnabled(state == "ready")          # nothing to start before a link is read
        self._sync_card()

    def active_percent(self) -> list:
        """Used by the exit check of the main window: progress of every unfinished link / playlist."""
        return self.mgr.queue.active_percents()

    # ------------------------------------------------------------------
    # buttons
    # ------------------------------------------------------------------
    def _browse(self):
        start = os.path.expanduser(self.folder.text().strip() or "~")
        path = QFileDialog.getExistingDirectory(self, self.t(M.ND_BROWSE_TITLE), start)
        if path:
            self.folder.setText(os.path.normpath(path))
            self._save_folder()

    def _save_folder(self):
        """The folder chosen here is for this download only; the default folder is set in Settings."""
        if self.info is not None:
            self._show_space_warning()

    # --- Pause / Cancel of the downloads (all running + waiting ones) ---------------------------
    def _sync_buttons(self):
        q = self.mgr.queue
        running, waiting = q.counts()
        working = any(t.state in ("downloading", "processing") for t in q.tasks)
        paused = any(t.state == "paused" for t in q.tasks)
        self.b_pause.setText(self.t(M.BTN_RESUME1 if paused and not working else M.BTN_PAUSE1))
        self.b_pause.setEnabled(working or paused)
        self.b_cancel.setEnabled(running + waiting > 0)
        self._sync_card()                                   # counters / title follow every change of the queue

    def _pause_clicked(self):
        q = self.mgr.queue
        working = [t for t in q.tasks if t.state in ("downloading", "processing")]
        if working:
            q.pause_all()
            self._log("info", M.LG_PAUSED_ALL)
        elif any(t.state == "paused" for t in q.tasks):
            q.resume_all()
            self._log("info", M.LG_RESUMED_ALL)
        else:
            self._log("warn", M.LG_NO_ACTIVE)
        self._sync_buttons()

    def _cancel_clicked(self):
        running, waiting = self.mgr.queue.counts()
        if running + waiting == 0:
            self._log("warn", M.LG_NO_ACTIVE)
            return
        t = self.t
        dlg = ChoiceDialog(self.ctx.lang, t(M.CF_CANCEL_TITLE), t(M.CF_CANCEL_TEXT),
                           [("yes", t(M.CF_CANCEL_YES), "btnRed"), ("no", t(M.CF_CANCEL_NO), "btnGreen")], self.window())
        exec_blurred(self, dlg)
        if dlg.choice == "yes":
            self.mgr.queue.cancel_all()
            self._log("warn", M.LG_CANCELLED_ALL)
        self._sync_buttons()

    def apply_defaults(self):
        """Settings were saved / restored: show the new default folder, format and quality."""
        self.folder.setText(str(self.ctx.settings.download_dir()))
        self._pending_q = None
        self._fill_formats()
        self.quality.clear()                                   # -> the default quality is used
        self._rebuild_quality()

    # ------------------------------------------------------------------
    # Start = put the video / playlist in the queue
    # ------------------------------------------------------------------
    def _check_tools(self) -> bool:
        if not self.ctx.resources.ytdlp:
            self._error("no_ytdlp")
            return False
        if not self.ctx.resources.ffmpeg_ok:
            self._error("no_ffmpeg")
            return False
        return True

    def _folder_ok(self, folder: Path) -> bool:
        try:
            folder.mkdir(parents=True, exist_ok=True)
            return True
        except OSError as exc:
            self._error("folder", str(exc))
            return False

    def _in_queue(self, url: str) -> bool:
        q = self.mgr.queue
        return any(g.url == url and g.state != "done" for g in q.groups) or \
            any(t.group is None and t.url == url and not t.finished for t in q.tasks)

    def _start(self):
        url = self.url.text().strip()
        if not looks_like_url(url):
            self._error("bad_url")
            return
        if not self._check_tools():
            return
        folder = Path(os.path.expanduser(self.folder.text().strip()))
        if not self._folder_ok(folder):
            return
        if self._in_queue(url):
            self._log("warn", M.LG_IN_QUEUE)
            return
        if not self._playlist_gate(url):
            return
        url = self.url.text().strip()
        if not self._duplicate_ok(url):
            return
        if self.info is not None and not self._space_ok():
            return
        folder = Path(os.path.expanduser(self.folder.text().strip()))      # the user may have chosen another folder
        if not self._folder_ok(folder):
            return
        if is_playlist_url(url):
            rec = self.ctx.history.find_playlist(url)
            if rec:                                  # downloaded before: compare with the playlist as it is now
                self.sync_requested.emit(rec)
                return
            info = self.info or {}
            dlg = PlaylistSetupDialog(self.ctx.lang, info.get("title") or url, info.get("thumb_bytes"),
                                      info.get("count", 0), self.window(),
                                      create_folder=bool(self.ctx.settings.get("playlist_subfolders", True)))
            exec_blurred(self, dlg)
            if not dlg.ok:
                return
            self._enqueue_playlist(url, folder, info, self.cur_format(), self.cur_quality(), dlg.create_folder,
                                   {"kind": "normal", "sync": dlg.sync, "schedule": dlg.schedule})
        else:
            self._enqueue_video(url, folder)
        self._reset_after_enqueue()

    def _enqueue_video(self, url: str, folder: Path):
        info = self.info or {}
        fmt, q = self.cur_format(), self.cur_quality()
        meta = {"kind": "normal", "url": url, "info": info, "fmt": fmt, "quality_value": q}
        self.mgr.queue.add_video(url, folder, fmt, q, title=info.get("title") or url, info=info,
                                 est_total=self.est_size, thumb_bytes=info.get("thumb_bytes"), meta=meta,
                                 force=(self._redo_url == url))
        self._log("info", M.LG_QUEUED, title=info.get("title") or url)

    def _enqueue_playlist(self, url, folder, info, fmt, q, create_folder, meta, entries=None, force=False, count=None):
        entries = entries if entries is not None else list(info.get("entries", []))
        meta = dict(meta, url=url, info=info, fmt=fmt, quality_value=q, entries=entries)
        title = info.get("title") or url
        self.mgr.queue.add_playlist(title, entries, folder, fmt, q, subfolder=create_folder,
                                    count=count or info.get("count") or len(entries), force=force,
                                    thumb_bytes=info.get("thumb_bytes"), url=url, meta=meta)
        self._log("info", M.LG_QUEUED_PL, title=title, count=len(entries))

    def _reset_after_enqueue(self):
        """The page is free for the next link (progress is on the Downloads page)."""
        self.mgr.invalidate()
        self._silent = True
        self.url.clear()
        self._silent = False
        self._redo_url = ""
        self.info = None
        self.est_size = None
        self._thumb_src = None
        self.title.set_full_text("")
        self._pending_q = None
        self._rebuild_quality()
        self._set_state("idle")
        self._sync_card()

    def start_sync(self, rec: dict, entries: list, force: bool = False) -> bool:
        """Download the chosen new videos of an already downloaded playlist into its folder.
        entries = [{id, index, title, url}] (index = position in the playlist)."""
        if not self._check_tools():
            return False
        folder = Path(os.path.expanduser(rec.get("save_dir", "")))
        if not self._folder_ok(folder):
            return False
        if self._in_queue(rec["url"]):
            self._log("warn", M.LG_IN_QUEUE)
            return False
        info = {"title": rec.get("title", ""), "is_playlist": True, "count": len(entries), "entries": entries,
                "thumb_bytes": None}
        path = self.ctx.history.thumb_path(rec)
        if path:
            try:
                info["thumb_bytes"] = Path(path).read_bytes()
            except OSError:
                pass
        total = max(max([e.get("index") or 0 for e in entries] + [0]), int(rec.get("count", 0)) + len(entries))
        self._log("info", M.LG_SYNC_START, n=len(entries), title=rec.get("title", ""))
        self._enqueue_playlist(rec["url"], folder, info, rec.get("format", "MP4"), int(rec.get("quality_value", 0)),
                               False, {"kind": "sync", "rec": rec}, entries=entries, force=force, count=total)
        return True

    def cancel_for_exit(self):
        """Called by the main window when the user chooses 'Abort Downloads'."""
        self.mgr.queue.cancel_all(wait=True)

    def _open_folder(self, path=None):
        folder = Path(os.path.expanduser(path or self.folder.text().strip()))
        if not folder.exists():
            self._log("warn", M.ERR_NO_FOLDER)
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

    @staticmethod
    def _reveal(path: str):
        reveal_file(path)

    def prefill(self, rec: dict):
        """'Download again' of the Library / Archive: same link, folder, format and quality; the user may change them."""
        self.folder.setText(rec.get("save_dir") or self.folder.text())
        self._save_folder()
        i = self.fmt.findData(rec.get("format") or str(rec.get("extension", "mp4")).upper())
        if i >= 0:
            self.fmt.setCurrentIndex(i)
        self._pending_q = int(rec.get("quality_value", 0))
        self._rebuild_quality()
        self._log("info", M.LG_PREFILLED)
        if self.url.text().strip() == rec.get("url", ""):
            self._url_changed()                      # same text -> no textChanged signal, read it again
        else:
            self.url.setText(rec.get("url", ""))
        if looks_like_url(self.url.text()) and self.ctx.resources.ytdlp:
            self._fetch()                            # 'Download again' reads the link at once

    # ------------------------------------------------------------------
    # events coming from the queue
    # ------------------------------------------------------------------
    def _task_done(self, task):
        r = task.result or {}
        if task.group is not None:                   # a video of a playlist: the playlist reports when all are done
            return
        t = self.t
        size = fmt_size(r.get("size"))
        self._log("info", M.LG_DONE, name=r.get("name", ""), size=size)
        sounds.play("done")
        rec = self._save_history(task)
        if self.ctx.settings.get("show_success_dialog", True):
            self._show_success(r, size, r.get("quality") or t(M.ND_BEST), rec, task.meta.get("fmt", "MP4"))

    def _task_failed(self, task):
        code, detail = task.error or ("unknown", "")
        text = self.t(ERROR_MSG.get(code, M.ERR_UNKNOWN), detail=detail)
        if task.group is not None:                           # a playlist video: the window comes when the playlist is done
            self._log("error", M.LG_TASK_FAIL, title=task.title, error=text)
            self._maybe_check_tools(code)
            return
        self._log("error", ERROR_MSG.get(code, M.ERR_UNKNOWN), detail=detail)
        self._maybe_check_tools(code)
        self._fail_buf.append(entry_of(task))
        self._fail_gen += 1
        QTimer.singleShot(900, lambda g=self._fail_gen: self._flush_failures(g))

    # --- 2.3.2: videos that cannot be downloaded: Retry now / Later / Cancel ------------------------------------
    def _flush_failures(self, gen: int):
        if gen != self._fail_gen or not self._fail_buf:
            return
        items, self._fail_buf = self._fail_buf, []
        self.offer_retry(items)

    def _failure_text(self, items: list, one_msg, many_msg) -> str:
        t = self.t
        names = [f"•  {i['title']}" for i in items[:8]] + ([t(M.FL_MORE, n=len(items) - 8)] if len(items) > 8 else [])
        if len(items) == 1:
            i = items[0]
            reason = self.t(ERROR_MSG.get(i.get("code"), M.ERR_UNKNOWN), detail=i.get("detail", ""))
            return t(one_msg, list="\n".join(names), reason=reason)
        return t(many_msg, n=len(items), list="\n".join(names))

    def offer_retry(self, items: list, reminder: bool = False):
        """Window for videos that could not be downloaded. Retry now = download again; Later (or closing the window) = kept and
        reminded at the next start; Cancel = forgotten."""
        if not items:
            return
        t = self.t
        text = self._failure_text(items, M.FL_REMIND_ONE if reminder else M.FL_ONE, M.FL_REMIND_MANY if reminder else M.FL_MANY) \
            if not reminder else self._failure_text(items, M.FL_REMIND_ONE, M.FL_REMIND_MANY)
        dlg = ChoiceDialog(self.ctx.lang, t(M.FL_TITLE), text,
                           [("retry", t(M.FL_RETRY), "btnGreen"), ("later", t(M.FL_LATER), "btnOrange"),
                            ("cancel", t(M.BTN_CANCEL1), "btnRed")], self.window(), size=(820, 520))
        exec_blurred(self, dlg)
        if dlg.choice == "retry":
            self.ctx.failed.remove(items)
            self._log("info", M.LG_FL_RETRY, n=len(items))
            for i in items:
                self.mgr.queue.add_retry(i["url"], i["folder"], i["fmt"], i["quality"], title=i["title"],
                                         template=i.get("template"), index=i.get("index"), vid=i.get("vid", ""))
        elif dlg.choice == "cancel":
            self.ctx.failed.remove(items)
        else:                                                    # Later / window closed
            self.ctx.failed.add(items)
            if not reminder:
                self._log("info", M.LG_FL_SAVED, n=len(items))

    def remind_failed(self):
        """At start-up: the videos kept with 'Later' are offered again."""
        items = list(self.ctx.failed.entries)
        if items:
            self.offer_retry(items, reminder=True)

    def _task_cancelled(self, task):
        if task.group is None:
            self._log("warn", M.LG_CANCEL)

    def _group_done(self, g):
        self._group_done_inner(g)
        failed = [entry_of(t) for t in g.tasks if t.state == "failed"]
        if failed and not g.discard:                          # 2.3.2: the videos of the playlist that could not be downloaded
            self.offer_retry(failed)

    def _group_done_inner(self, g):
        r = g.result or {}
        if g.discard and g.meta.get("kind") != "sync":      # cancelled in the Downloads list: nothing is kept in the history
            self._log("warn", M.LG_CANCEL)
            return
        if r.get("count", 0) == 0:
            self._log("warn", M.LG_PL_NOTHING, title=g.title)
            return
        if r.get("failed") or r.get("skipped"):
            self._log("warn", M.LG_PL_PARTIAL, count=r["count"], skipped=r["skipped"], failed=r["failed"])
        else:
            self._log("info", M.LG_PL_DONE, count=r["count"], folder=r["folder"])
        sounds.play("done")
        if g.meta.get("kind") == "sync":
            n = self._sync_finished(g)
            if self.ctx.settings.get("notify_sync_done", True):
                self._notify_sync(g.meta["rec"].get("title", ""), n)
            return
        rec = self._save_history_group(g)
        if self.ctx.settings.get("show_success_dialog", True):
            size = fmt_size(r["size"])
            self._show_success(r, size, r.get("quality") or self.t(M.ND_BEST), rec, g.fmt)

    def _save_history(self, task):
        """Put the finished download in history.json (+ its thumbnail + the description). Never breaks the success flow."""
        r, info = task.result or {}, task.meta.get("info") or {}
        try:
            rec = self.ctx.history.new_record(
                url=task.meta.get("url", task.url), title=info.get("title") or r["name"],
                file_name=r["name"], save_dir=r["folder"],
                fmt=task.meta.get("fmt", task.fmt), quality=r.get("quality") or "",
                quality_value=task.meta.get("quality_value", task.quality),
                size=r["size"], duration=info.get("duration"), is_audio=r["is_audio"],
                is_playlist=False, count=1, thumb_bytes=info.get("thumb_bytes"),
                extra={"description": r.get("description") or info.get("description") or ""})
        except Exception:                           # noqa: BLE001
            return None
        try:                                                       # one entry per FILE: the same file replaces its old entry
            for old in self.ctx.history.same_file(rec):
                cat = self.ctx.favorites.category_of(old["id"])
                if cat:                                                # a favorite stays a favorite
                    self.ctx.favorites.remove(old["id"])
                    self.ctx.favorites.add(rec["id"], cat)
                self.ctx.history.remove(old["id"])                     # only the entry, never the file
        except Exception:                           # noqa: BLE001
            pass
        self.history_changed.emit()
        return rec

    def _save_history_group(self, g):
        r, info = g.result, g.meta.get("info") or {}
        titles = {e["id"]: e["title"] for e in g.meta.get("entries", [])}
        extra = {"videos": self._videos_from(r, titles), "last_sync": now_text(), "subfolder": bool(getattr(g, "subfolder", False)),
                 "description": info.get("description") or ""}
        try:
            rec = self.ctx.history.new_record(
                url=g.meta.get("url", g.url), title=g.title, file_name="", save_dir=r["folder"],
                fmt=g.fmt, quality=r.get("quality") or "", quality_value=g.quality, size=r["size"],
                duration=None, is_audio=r["is_audio"], is_playlist=True, count=r["count"],
                thumb_bytes=g.thumb_bytes, extra=extra)
        except Exception:                           # noqa: BLE001
            return None
        if g.meta.get("sync") and rec.get("playlist_id"):
            entry = self.ctx.sync.add(rec["playlist_id"], rec["id"], rec["url"], rec["title"],
                                      g.meta.get("schedule", "daily"))
            self._log("info", M.LG_SYNC_ADDED, schedule=self._schedule_name(entry["schedule"]),
                      date=entry["next_sync"][:10])
        self.history_changed.emit()
        return rec

    @staticmethod
    def _videos_from(r: dict, titles: dict) -> dict:
        """{video id: {...}} of the videos that this download put on the disk (needed by 'Sync now')."""
        now = now_text()
        descs = r.get("descriptions") or {}
        out = {}
        for vid, path in r.get("items", []):
            if not vid:
                continue
            try:
                size = os.path.getsize(path)
            except OSError:
                size = 0
            out[vid] = {"title": titles.get(vid) or Path(path).stem, "file": path, "size": size,
                        "date": now, "state": "downloaded", "description": descs.get(vid, "")}
        return out

    def _schedule_name(self, key: str) -> str:
        return self.t({"daily": M.PS_DAILY, "weekly": M.PS_WEEKLY, "monthly": M.PS_MONTHLY, "yearly": M.PS_YEARLY}.get(key, M.PS_DAILY))

    def _sync_finished(self, g):
        """'Download & Sync' ended: remember the new videos, schedule the next sync."""
        rec, r = g.meta["rec"], g.result
        titles = {e["id"]: e["title"] for e in g.meta.get("entries", [])}
        videos = rec.setdefault("videos", {})
        new = self._videos_from(r, titles)
        videos.update(new)
        done = [v for v in videos.values() if v.get("state") == "downloaded"]
        rec["count"] = len(done)
        rec["size"] = sum(v.get("size", 0) for v in done) or rec.get("size", 0)
        rec["last_sync"] = now_text()
        self.ctx.history.save()
        if rec.get("playlist_id"):
            self.ctx.sync.synced_now(rec["playlist_id"])
        self._log("info", M.LG_SYNC_DONE, n=len(new), title=rec.get("title", ""))
        self.history_changed.emit()
        return len(new)

    def _notify_sync(self, title: str, n: int):
        """'Notify me when a playlist has been updated' (Settings > Notifications)."""
        t = self.t
        win = self.window()
        exec_blurred(self, MessageDialog(self.ctx.lang, t(M.NT_SYNC_TITLE), t(M.NT_SYNC_TEXT, title=title, n=n),
                                         win, info=True))

    def _fav_from_dialog(self, rec: dict, dlg) -> bool:
        if add_to_favorites(self.ctx, rec, dlg):
            self.history_changed.emit()
            self._log("info", M.LG_FAV_ADDED, category=self.ctx.favorites.category_of(rec["id"]))
            return True
        return False

    def _show_success(self, r: dict, size: str, quality: str, rec=None, fmt: str = "MP4"):
        t = self.t
        if r["is_playlist"]:
            rows = [("folder", t(M.OK_FILES), str(r["count"]), ""),
                    ("badge", t(M.OK_QUALITY), quality, _badge(quality, fmt)),
                    ("size", t(M.OK_SIZE), size, ""),
                    ("folder", t(M.OK_LOCATION), r["folder"], "")]
            title = t(M.OK_TITLE_PL)
        else:
            rows = [("file", t(M.OK_FILE), r["name"], ""),
                    ("badge", t(M.OK_QUALITY), quality, _badge(quality, fmt)),
                    ("size", t(M.OK_SIZE), size, ""),
                    ("folder", t(M.OK_LOCATION), r["folder"], "")]
            title = t(M.OK_TITLE)
        win = self.window()
        blur = getattr(win, "_blur_background", None)
        if blur:
            blur(True)
        try:
            dlg = SuccessDialog(self.ctx.lang, title, rows, r["is_audio"], parent=win,
                                fav_cb=(lambda: self._fav_from_dialog(rec, dlg))
                                if rec and self.ctx.settings.get("fav_notify", True) else None)
            dlg.exec()
        finally:
            if blur:
                blur(False)
        if dlg.dont_show:
            self.ctx.settings.set("show_success_dialog", False)
            self.ctx.settings.save()
        if dlg.action == "play" and r.get("path"):
            QDesktopServices.openUrl(QUrl.fromLocalFile(r["path"]))
        elif dlg.action == "folder" and r.get("path"):
            self._reveal(r["path"])

    # ------------------------------------------------------------------
    # messages
    # ------------------------------------------------------------------
    def _log(self, level: str, msg_id: str, **params):
        stamp = datetime.now().strftime("%H:%M:%S")
        text = html.escape(self.t(msg_id, **params))
        self.log.appendHtml(f'<span style="color:{LOG_COLOR.get(level, "#38ff6a")}">[{stamp}] {text}</span>')

    def _maybe_check_tools(self, code: str):
        if code in ("unknown", "unsupported", "format"):
            QTimer.singleShot(0, self.tools_check_requested.emit)

    def _error(self, code: str, detail: str = ""):
        """Error line in the system log + an error window."""
        msg_id = ERROR_MSG.get(code, M.ERR_UNKNOWN)
        text = self.t(msg_id, detail=detail)
        self._log("error", msg_id, detail=detail)
        win = self.window()
        blur = getattr(win, "_blur_background", None)
        if blur:
            blur(True)
        try:
            MessageDialog(self.ctx.lang, self.t(M.ERR_TITLE), text, win).exec()
        finally:
            if blur:
                blur(False)
        self._maybe_check_tools(code)
