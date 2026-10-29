# =============================================================================
# TubeArchive Pro  |  Version 2.2.5  |  File: app/ui/downloads_page.py
# Version history of this file:
#   2.2.5 - Cancel (file / playlist / all) asks first, then stops and removes it from the list
#   2.2.4 - status 'Paused - resumes when a place is free'
#   2.2.3 - Completed bars turn green (paused orange, failed red); 'Clear completed automatically' check box (auto_clear_completed)
#   2.0.2 - Texts follow the size of the work area (FontScaler)
#   2.0.1 - Created: the real Downloads page (replaces the demo page of pages.py). One row per video, one row per
#           playlist (file counter, current-file bar + playlist bar, thumbnail of the newest started file,
#           Details window with every video and "Skip this one"). Shows the number of waiting files.
# =============================================================================
"""'Downloads' tab: everything that is running or waiting in the download queue (app/dlqueue.py)."""
import os

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QColor, QDesktopServices, QPixmap
from PySide6.QtWidgets import (QCheckBox, QFrame, QHBoxLayout, QLabel, QProgressBar, QPushButton,
                               QScrollArea, QVBoxLayout, QWidget)

from ..context import AppContext
from ..downloader import fmt_size, fmt_time, index_text, quality_label
from ..msg import M
from .actions import exec_blurred
from .dialogs import ChoiceDialog, GlassDialog
from .icons import make_thumb, rounded_pixmap
from .theme import glow
from .widgets import ElidedLabel, FontScaler

MB = 1024 * 1024
ERROR_MSG = {"no_ytdlp": M.ERR_NO_YTDLP, "no_ffmpeg": M.ERR_NO_FFMPEG, "bad_url": M.ERR_BAD_URL,
             "unsupported": M.ERR_UNSUPPORTED, "unavailable": M.ERR_UNAVAILABLE, "private": M.ERR_PRIVATE,
             "age": M.ERR_AGE, "signin": M.ERR_SIGNIN, "geo": M.ERR_GEO, "network": M.ERR_NETWORK,
             "rate": M.ERR_RATE, "disk": M.ERR_DISK, "format": M.ERR_FORMAT, "unknown": M.ERR_UNKNOWN,
             "folder": M.ERR_FOLDER, "pause": M.ERR_PAUSE}
STATE_MSG = {"downloading": M.DLQ_DOWNLOADING, "processing": M.DLQ_PROCESSING, "paused": M.DLQ_PAUSED,
             "done": M.DLQ_DONE, "cancelled": M.DLQ_CANCELLED, "skipped": M.DLQ_SKIPPED}


def size_ratio(done, total) -> str:
    """'123 MB / 456 MB' - what came so far and what is expected (the expected size is refined while it downloads)."""
    if total:
        return f"{fmt_size(done)} / {fmt_size(total)}"
    return fmt_size(done) if done else "-"


def state_text(t, task, queue=None) -> str:
    if task.state == "queued":
        waiting = [x for x in queue.tasks if x.state == "queued"] if queue else []
        return t(M.DLQ_WAIT, pos=(waiting.index(task) + 1) if task in waiting else 1)
    if task.state == "paused" and getattr(task, "_resume_wanted", False):
        return t(M.DLQ_WAIT_RESUME)
    if task.state == "failed":
        code, detail = task.error or ("unknown", "")
        return t(M.DLQ_FAILED, error=t(ERROR_MSG.get(code, M.ERR_UNKNOWN), detail=detail))
    return t(STATE_MSG.get(task.state, M.DLQ_DOWNLOADING))


def task_pixmap(task, w: int, h: int, fallback=None):
    data = task.thumb_bytes or fallback
    if data:
        pm = QPixmap()
        if pm.loadFromData(data):
            return rounded_pixmap(pm, w, h, 8)
    return make_thumb("#0a1a4a", "#1c4fa8", w, h)


def _icon_button(text: str, tip: str, slot, obj="miniBtn") -> QPushButton:
    b = QPushButton(text)
    b.setObjectName(obj)
    b.setToolTip(tip)
    b.setCursor(Qt.PointingHandCursor)
    b.setFixedSize(34, 30)
    b.clicked.connect(slot)
    return b


def _bar(height=8) -> QProgressBar:
    bar = QProgressBar()
    bar.setObjectName("dlBar")
    bar.setRange(0, 1000)
    bar.setTextVisible(False)
    bar.setFixedHeight(height)
    return bar


def bar_state(bar: QProgressBar, st: str):
    """Colour of a progress bar by state: "" blue (working), "done" green, "paused" orange, "failed" red (2.2.3)."""
    if bar.property("st") != st:
        bar.setProperty("st", st)
        bar.style().unpolish(bar)
        bar.style().polish(bar)


# ----------------------------------------------------------------------
class TaskRow(QFrame):
    """One video."""

    def __init__(self, page: "DownloadsPage", task):
        super().__init__()
        self.page, self.task = page, task
        self.setObjectName("dlItem")
        row = QHBoxLayout(self)
        row.setContentsMargins(10, 8, 14, 8)
        row.setSpacing(12)
        self.pic = QLabel()
        self.pic.setFixedSize(100, 62)
        row.addWidget(self.pic)
        col = QVBoxLayout()
        col.setSpacing(5)
        top = QHBoxLayout()
        top.setSpacing(8)
        self.title = ElidedLabel(task.title)
        self.title.setObjectName("dlTitle")
        self.stat = QLabel()
        self.stat.setObjectName("dlStat")
        b1 = QLabel(task.fmt)
        b1.setObjectName("badgeFmt")
        top.addWidget(self.title, 1)
        top.addWidget(self.stat)
        top.addWidget(b1)
        q = quality_label(task.fmt, task.quality)
        if q:
            b2 = QLabel(q)
            b2.setObjectName("badgeQ")
            top.addWidget(b2)
        self.bar = _bar()
        self.sub = QLabel()
        self.sub.setObjectName("dlSub")
        col.addLayout(top)
        col.addWidget(self.bar)
        col.addWidget(self.sub)
        row.addLayout(col, 1)
        t = page.t
        self.b_pause = _icon_button("⏸", t(M.BTN_PAUSE), self._pause)
        self.b_cancel = _icon_button("✕", t(M.BTN_CANCEL), self._cancel, "miniBtn")
        row.addWidget(self.b_pause)
        row.addWidget(self.b_cancel)
        self._pic_has = False
        self.update_from(task)

    def _pause(self):
        q = self.page.mgr.queue
        q.resume_task(self.task) if self.task.state == "paused" else q.pause_task(self.task)

    def _cancel(self):
        if self.page.confirm_cancel(self.task.title):
            self.page.mgr.queue.discard_task(self.task)

    def update_from(self, task):
        t = self.page.t
        self.task = task
        if not self._pic_has or task.thumb_bytes:
            self.pic.setPixmap(task_pixmap(task, 100, 62))
            self._pic_has = bool(task.thumb_bytes)
        done = task.state == "done"
        self.bar.setValue(1000 if done else int(task.percent * 10))
        bar_state(self.bar, "done" if done else "paused" if task.state == "paused"
                  else "failed" if task.state in ("failed", "cancelled", "skipped") else "")
        speed = task.speed / MB
        self.stat.setText(f"{task.percent:.0f}% | {speed:.1f} {t(M.UNIT_MBS)}" if task.state == "downloading"
                          else "\u2714 100%" if done
                          else f"{task.percent:.0f}%" if task.state in ("processing", "paused") else "")
        bits = [size_ratio(task.downloaded, task.total)] if task.state != "queued" else []
        if task.state == "downloading" and task.eta is not None and task.speed:
            bits.append(t(M.ND_ETA, eta=fmt_time(task.eta)))
        bits.append(state_text(t, task, self.page.mgr.queue))
        self.sub.setText("  |  ".join(bits))
        self.b_pause.setText("▶" if task.state == "paused" else "⏸")
        self.b_pause.setToolTip(t(M.BTN_RESUME if task.state == "paused" else M.BTN_PAUSE))
        live = task.state in ("downloading", "processing", "paused")
        self.b_pause.setEnabled(live)
        self.b_cancel.setEnabled(not task.finished)


# ----------------------------------------------------------------------
class GroupRow(QFrame):
    """A playlist: counter, the current file + the whole playlist progress, thumbnail of the newest started file."""

    def __init__(self, page: "DownloadsPage", group):
        super().__init__()
        self.page, self.group = page, group
        self.setObjectName("dlItem")
        row = QHBoxLayout(self)
        row.setContentsMargins(10, 8, 14, 8)
        row.setSpacing(12)
        self.pic = QLabel()
        self.pic.setFixedSize(124, 76)
        row.addWidget(self.pic)
        col = QVBoxLayout()
        col.setSpacing(4)
        top = QHBoxLayout()
        top.setSpacing(8)
        self.title = ElidedLabel(group.title)
        self.title.setObjectName("dlTitle")
        self.counter = QLabel()
        self.counter.setObjectName("dlStat")
        b1 = QLabel(group.fmt)
        b1.setObjectName("badgeFmt")
        top.addWidget(self.title, 1)
        top.addWidget(self.counter)
        top.addWidget(b1)
        q = quality_label(group.fmt, group.quality)
        if q:
            b2 = QLabel(q)
            b2.setObjectName("badgeQ")
            top.addWidget(b2)
        col.addLayout(top)
        self.cur_line = ElidedLabel("")
        self.cur_line.setObjectName("dlSub")
        self.cur_bar = _bar(7)
        self.tot_line = QLabel()
        self.tot_line.setObjectName("dlSub")
        self.tot_bar = _bar(9)
        self.tot_bar.setObjectName("dlBarTotal")
        for w in (self.cur_line, self.cur_bar, self.tot_line, self.tot_bar):
            col.addWidget(w)
        row.addLayout(col, 1)
        t = page.t
        side = QVBoxLayout()
        side.setSpacing(4)
        self.b_details = QPushButton(t(M.DLQ_DETAILS))
        self.b_details.setObjectName("secondary")
        self.b_details.setCursor(Qt.PointingHandCursor)
        self.b_details.clicked.connect(lambda: page.show_details(self.group))
        btns = QHBoxLayout()
        self.b_pause = _icon_button("⏸", t(M.BTN_PAUSE), self._pause)
        self.b_cancel = _icon_button("✕", t(M.BTN_CANCEL), self._cancel)
        btns.addWidget(self.b_pause)
        btns.addWidget(self.b_cancel)
        side.addWidget(self.b_details)
        side.addLayout(btns)
        row.addLayout(side)
        self.update_from(group)

    def _pause(self):
        q = self.page.mgr.queue
        tasks = [x for x in self.group.tasks if x.active]
        if any(x.state == "paused" for x in tasks):
            for x in tasks:
                q.resume_task(x)
        else:
            for x in tasks:
                q.pause_task(x)

    def _cancel(self):
        if self.page.confirm_cancel(self.group.title):
            self.page.mgr.queue.discard_group(self.group)

    def update_from(self, g=None):
        t = self.page.t
        g = self.group = g or self.group
        c = g.counts()
        n = len(g.tasks)
        cur = g.current
        self.pic.setPixmap(task_pixmap(cur or g, 124, 76, g.thumb_bytes))      # the file that started last
        finished = g.state == "done"
        if finished:
            self.counter.setText(t(M.DLQ_PL_DONE_ROW, done=c["done"], n=n))
        elif cur is not None:
            self.counter.setText(t(M.DLQ_FILE_OF, i=index_text(cur.index or 1, g.count), n=g.count))
        else:
            self.counter.setText(t(M.DLQ_FILE_OF, i=index_text(1, g.count), n=g.count))
        if cur is not None and not finished:
            self.cur_line.set_full_text(f"{t(M.DLQ_CURRENT)}: {cur.title}   {cur.percent:.0f}%  |  "
                                        f"{size_ratio(cur.downloaded, cur.total)}  |  {cur.speed / MB:.1f} {t(M.UNIT_MBS)}")
            self.cur_bar.setValue(int(cur.percent * 10))
        else:
            self.cur_line.set_full_text(t(M.DLQ_DONE) if finished else "")
            self.cur_bar.setValue(1000 if finished else 0)
        self.tot_line.setText(f"{t(M.DLQ_TOTAL)}: {g.percent:.0f}%   |   " +
                              t(M.DLQ_PL_STATS, done=c["done"], active=c["active"], waiting=c["queued"]))
        self.tot_bar.setValue(int(g.percent * 10) if not finished else 1000)
        paused = c["paused"] > 0
        bar_state(self.cur_bar, "done" if finished else "paused" if paused else "")
        bar_state(self.tot_bar, "done" if finished else "paused" if paused else "")
        self.b_pause.setText("▶" if paused else "⏸")
        self.b_pause.setEnabled(c["active"] > 0 and not finished)
        self.b_cancel.setEnabled(not finished)


# ----------------------------------------------------------------------
class PlaylistDetailsDialog(GlassDialog):
    """Every video of the playlist with its own bar; 'Skip this one' for the videos that are not finished."""

    def __init__(self, ctx: AppContext, mgr, group, parent=None):
        super().__init__(parent, (900, 640), QColor(120, 200, 255), QColor(40, 90, 190, 238), QColor(12, 30, 92, 246))
        self.mgr, self.group = mgr, group
        self.t = t = ctx.lang.tr
        v = QVBoxLayout(self)
        v.setContentsMargins(36, 30, 36, 28)
        v.setSpacing(10)
        head = QLabel(f"{t(M.DLQ_DET_TITLE)}:  {group.title}")
        head.setObjectName("dlgText")
        head.setWordWrap(True)
        v.addWidget(head)
        self.summary = QLabel()
        self.summary.setObjectName("dlSub")
        v.addWidget(self.summary)
        self.one = QCheckBox(t(M.DLQ_ONE_BY_ONE))
        self.one.setChecked(group.sequential)
        self.one.toggled.connect(lambda on: mgr.queue.set_sequential(group, on))
        v.addWidget(self.one)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        holder = QWidget()
        holder.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(holder)
        lay.setContentsMargins(2, 2, 8, 2)
        lay.setSpacing(6)
        self.rows = {}
        for task in group.tasks:
            r = self._row(task)
            lay.addWidget(r["frame"])
            self.rows[task.id] = r
        lay.addStretch(1)
        scroll.setWidget(holder)
        v.addWidget(scroll, 1)
        close = QPushButton(t(M.DLQ_CLOSE))
        close.setObjectName("btnBlue")
        close.setMinimumHeight(44)
        close.setCursor(Qt.PointingHandCursor)
        close.clicked.connect(self.accept)
        glow(close, "#2b8cff", 18)
        v.addWidget(close)
        mgr.task_changed.connect(self._changed)
        mgr.thumb_ready.connect(self._changed)
        self.refresh()

    def _row(self, task) -> dict:
        t = self.t
        fr = QFrame()
        fr.setObjectName("syncRow")
        h = QHBoxLayout(fr)
        h.setContentsMargins(8, 6, 10, 6)
        h.setSpacing(10)
        pic = QLabel()
        pic.setFixedSize(80, 46)
        h.addWidget(pic)
        num = QLabel(index_text(task.index or 1, self.group.count))
        num.setObjectName("dlStat")
        num.setMinimumWidth(44)
        h.addWidget(num)
        col = QVBoxLayout()
        col.setSpacing(3)
        title = ElidedLabel(task.title)
        title.setObjectName("syncTitle")
        bar = _bar(8)
        info = QLabel()
        info.setObjectName("syncInfo")
        col.addWidget(title)
        col.addWidget(bar)
        col.addWidget(info)
        h.addLayout(col, 1)
        skip = QPushButton(t(M.DLQ_SKIP))
        skip.setObjectName("secondary")
        skip.setCursor(Qt.PointingHandCursor)
        skip.clicked.connect(lambda _=False, task=task: self.mgr.queue.skip(task))
        h.addWidget(skip)
        return {"frame": fr, "pic": pic, "bar": bar, "info": info, "skip": skip, "has_pic": False}

    def _changed(self, task):
        if task.group is self.group:
            self.refresh(task)

    def refresh(self, only=None):
        t = self.t
        for task in ([only] if only is not None else self.group.tasks):
            r = self.rows.get(task.id)
            if not r:
                continue
            if not r["has_pic"]:
                r["pic"].setPixmap(task_pixmap(task, 80, 46))
                r["has_pic"] = bool(task.thumb_bytes)
            r["bar"].setValue(int(task.percent * 10))
            bits = [state_text(t, task, self.mgr.queue)]
            if task.state not in ("queued", "skipped", "cancelled"):
                bits.insert(0, size_ratio(task.downloaded, task.total))
            if task.state == "downloading":
                bits.insert(1, f"{task.percent:.0f}%  {task.speed / MB:.1f} {t(M.UNIT_MBS)}")
            r["info"].setText("  |  ".join(bits))
            r["skip"].setEnabled(not task.finished)
        c = self.group.counts()
        self.summary.setText(f"{t(M.DLQ_FILE_OF, i=c['done'], n=len(self.group.tasks))}   |   " +
                             t(M.DLQ_PL_STATS, done=c["done"], active=c["active"], waiting=c["queued"]))


# ----------------------------------------------------------------------
class DownloadsPage(FontScaler, QWidget):
    def __init__(self, ctx: AppContext):
        super().__init__()
        self.ctx = ctx
        self.t = t = ctx.lang.tr
        if getattr(ctx, "downloads", None) is None:
            from ..download_manager import DownloadManager
            ctx.downloads = DownloadManager(ctx.resources.ytdlp, ctx.resources.ffmpeg_dir, ctx.settings.get)
        self.mgr = ctx.downloads
        self.rows: dict = {}
        v = QVBoxLayout(self)
        v.setContentsMargins(14, 14, 14, 12)
        v.setSpacing(8)
        head = QHBoxLayout()
        self.status = QLabel()
        self.status.setObjectName("fieldLabel")
        self.clear = QPushButton(t(M.DLQ_CLEAR))
        self.clear.setObjectName("secondary")
        self.clear.setCursor(Qt.PointingHandCursor)
        self.clear.clicked.connect(self._clear)
        self.auto = QCheckBox(t(M.DLQ_AUTO_CLEAR))             # clear the completed downloads by itself (saved in the settings)
        self.auto.setChecked(bool(ctx.settings.get("auto_clear_completed", False)))
        self.auto.toggled.connect(self._auto_toggled)
        ctx.settings.subscribe(self._on_setting)
        head.addWidget(self.status, 1)
        head.addWidget(self.auto)
        head.addWidget(self.clear)
        v.addLayout(head)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        holder = QWidget()
        holder.setStyleSheet("background: transparent;")
        self.list = QVBoxLayout(holder)
        self.list.setContentsMargins(4, 4, 8, 4)
        self.list.setSpacing(10)
        self.list.addStretch(1)
        self.scroll.setWidget(holder)
        v.addWidget(self.scroll, 1)
        self.empty = QLabel(t(M.DLQ_EMPTY))
        self.empty.setObjectName("emptyMsg")
        self.empty.setAlignment(Qt.AlignCenter)
        self.empty.setWordWrap(True)
        v.addWidget(self.empty, 1)

        btns = QHBoxLayout()
        btns.setSpacing(14)
        for name, msg, col, slot in (("btnGreen", M.BTN_RESUME, "#1fd16a", self._resume_all),
                                     ("btnOrange", M.BTN_PAUSE, "#ffa800", self._pause_all),
                                     ("btnRed", M.BTN_CANCEL, "#ff2f72", self._cancel_all),
                                     ("btnBlue", M.BTN_OPEN_FOLDER, "#2b8cff", self._open_folder)):
            b = QPushButton(t(msg))
            b.setObjectName(name)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(slot)
            glow(b, col, 18)
            btns.addWidget(b)
        v.addLayout(btns)

        self.mgr.task_changed.connect(self._task_changed)
        self.mgr.group_changed.connect(self._group_changed)
        self.mgr.group_done.connect(self._group_changed)
        self.mgr.thumb_ready.connect(self._task_changed)
        self.rebuild()

    # --- building the list --------------------------------------------------
    def rebuild(self):
        for r in self.rows.values():
            self.list.removeWidget(r)
            r.deleteLater()
        self.rows = {}
        for item in self.mgr.queue.top_items():
            self._add_row(item)
        self._sync()

    def _key(self, item):
        return ("g" if hasattr(item, "tasks") else "t", item.id)

    def _add_row(self, item):
        row = GroupRow(self, item) if hasattr(item, "tasks") else TaskRow(self, item)
        self.list.insertWidget(self.list.count() - 1, row)
        self.rows[self._key(item)] = row

    def _auto_toggled(self, on: bool):
        if bool(self.ctx.settings.get("auto_clear_completed", False)) != on:
            self.ctx.settings.set("auto_clear_completed", on)
            self.ctx.settings.save()
        if on:
            self._auto_clear()

    def _on_setting(self, key: str):
        """The Settings page changed the same option: show it here too."""
        if key in ("auto_clear_completed", "*"):
            on = bool(self.ctx.settings.get("auto_clear_completed", False))
            if self.auto.isChecked() != on:
                self.auto.blockSignals(True)
                self.auto.setChecked(on)
                self.auto.blockSignals(False)
            if on:
                self._auto_clear()

    def _auto_clear(self):
        """Option on: a finished download (or playlist) leaves the list at once."""
        if self.mgr.queue.clear_finished():
            self.rebuild()

    def _task_changed(self, task):
        if self._purge():                                  # a cancelled (discarded) video has stopped: it leaves the list
            return
        item = task.group or task
        row = self.rows.get(self._key(item))
        if row is None:
            self._add_row(item)
            row = self.rows[self._key(item)]
        row.update_from(item)
        self._sync()
        if task.state == "done" and self.ctx.settings.get("auto_clear_completed", False):
            QTimer.singleShot(1500, self._auto_clear)        # the green 'completed' bar is seen for a moment

    def _group_changed(self, g):
        if self._purge():
            return
        row = self.rows.get(self._key(g))
        if row is None:
            self._add_row(g)
        else:
            row.update_from(g)
        self._sync()
        if g.state == "done" and self.ctx.settings.get("auto_clear_completed", False):
            QTimer.singleShot(1500, self._auto_clear)

    def _sync(self):
        t = self.t
        running, waiting = self.mgr.queue.counts()
        self.status.setText(t(M.DLQ_STATUS, running=running, waiting=waiting))
        has = bool(self.rows)
        self.scroll.setVisible(has)
        self.empty.setVisible(not has)

    # --- actions ----------------------------------------------------------------
    def show_details(self, group):
        dlg = PlaylistDetailsDialog(self.ctx, self.mgr, group, self.window())
        exec_blurred(self, dlg)

    def _clear(self):
        self.mgr.queue.clear_finished()
        self.rebuild()

    def _resume_all(self):
        self.mgr.queue.resume_all()

    def _pause_all(self):
        self.mgr.queue.pause_all()

    def confirm_cancel(self, title=None) -> bool:
        """Warning window of every Cancel of this page; True = the user confirmed (the download is then removed)."""
        t = self.t
        running, waiting = self.mgr.queue.counts()
        text = t(M.DLQ_CANCEL_ONE, title=title) if title else t(M.DLQ_CANCEL_ALL, n=running + waiting)
        dlg = ChoiceDialog(self.ctx.lang, t(M.DLQ_CANCEL_TITLE), text,
                           [("yes", t(M.DLQ_CANCEL_YES), "btnRed"), ("no", t(M.CF_CANCEL_NO), "btnGreen")], self.window())
        exec_blurred(self, dlg)
        return dlg.choice == "yes"

    def _purge(self) -> bool:
        if self.mgr.queue.purge_discarded():
            self.rebuild()
            return True
        return False

    def _cancel_all(self):
        running, waiting = self.mgr.queue.counts()
        if running + waiting and self.confirm_cancel(None):
            self.mgr.queue.discard_all()

    def _open_folder(self):
        folder = os.path.expanduser(str(self.ctx.settings.download_dir()))
        if os.path.isdir(folder):
            QDesktopServices.openUrl(QUrl.fromLocalFile(folder))
