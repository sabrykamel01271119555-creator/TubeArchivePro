# =============================================================================
# TubeArchive Pro  |  Version 2.2.7  |  File: app/ui/sync_page.py
# Version history of this file:
#   2.2.7 - sync button green / plain (set_sync_button)
#   2.2.2 - 'Sync all' button; sync_changed signal
#   2.0.3 - Smaller text (FS_BASE) and a wider date column: last sync / next sync are fully readable
#   2.0.2 - Texts follow the size of the work area (FontScaler)
#   2.0.1 - ON / OFF is a green toggle switch (the ON caption was hard to read)
#   1.0.12 - QPixmap import moved to the top of the file
#   1.0.11 - Created: 'Playlist Sync' tab = list of synchronized playlists (name, status, last / next sync,
#            format + quality, frequency, ON / OFF) with Sync now / Open folder / Stop syncing buttons
# =============================================================================
"""'Playlist Sync' tab (design guide: Playlist Sync Manager)."""
import os

from PySide6.QtCore import QSize, Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QPixmap
from PySide6.QtWidgets import (QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton,
                               QScrollArea, QVBoxLayout, QWidget)

from ..context import AppContext
from ..msg import M
from ..sync import SCHEDULES, SyncManager
from .actions import exec_blurred
from .dialogs import ChoiceDialog, MessageDialog
from .icons import set_sync_button, make_folder_icon, make_sync_icon, make_thumb, make_trash_icon, rounded_pixmap
from .widgets import ArrowComboBox, ElidedLabel, FontScaler, ToggleSwitch, mnemonic_safe

SCHEDULE_MSG = {"daily": M.PS_DAILY, "weekly": M.PS_WEEKLY, "monthly": M.PS_MONTHLY, "yearly": M.PS_YEARLY}
# column stretch factors: name + status | last / next sync | format + quality | frequency | ON-OFF | actions
COLS = (5, 4, 3, 3, 2, 3)


class SyncPage(FontScaler, QWidget):
    FS_BASE = (1000.0, 540.0)             # smaller text than other pages: every column (last / next sync ...) stays readable
    sync_requested = Signal(object)        # history record of the playlist -> sync window
    add_requested = Signal()               # "Add Playlist" -> New Download tab
    sync_all_requested = Signal()          # "Sync all": check every playlist now
    sync_changed = Signal()                # a playlist was switched on/off or removed -> the cards of the other pages reload

    def __init__(self, ctx: AppContext):
        super().__init__()
        self.ctx = ctx
        self.t = ctx.lang.tr
        self._dirty = True
        self._build()

    # ------------------------------------------------------------------
    def _build(self):
        t = self.t
        root = QVBoxLayout(self)
        root.setContentsMargins(22, 16, 22, 14)
        root.setSpacing(10)
        top = QHBoxLayout()
        self.title = QLabel("")
        self.title.setObjectName("pageTitle")
        add = QPushButton("+  " + t(M.SYP_ADD))
        add.setObjectName("btnGreen")
        add.setMinimumHeight(42)
        add.setCursor(Qt.PointingHandCursor)
        add.clicked.connect(self.add_requested.emit)
        sync_all = QPushButton(mnemonic_safe(t(M.SYP_ALL)))
        sync_all.setObjectName("btnBlue")
        sync_all.setMinimumHeight(42)
        sync_all.setCursor(Qt.PointingHandCursor)
        sync_all.clicked.connect(self.sync_all_requested.emit)
        top.addWidget(self.title, 1)
        top.addWidget(sync_all)
        top.addWidget(add)
        root.addLayout(top)

        head = QGridLayout()
        head.setContentsMargins(14, 0, 14, 0)
        for i, (msg, st) in enumerate(((M.SYP_COL_NAME, COLS[0]), (M.SYP_COL_NEXT, COLS[1]),
                                       (M.SYP_COL_FMT, COLS[2]), (M.SYP_COL_FREQ, COLS[3]),
                                       (M.SYP_ON, COLS[4]), (M.SYP_COL_ACT, COLS[5]))):
            lb = ElidedLabel(t(msg) if i != 1 else f"{t(M.SYP_COL_LAST)} / {t(M.SYP_COL_NEXT)}")
            lb.setObjectName("colHead")
            head.addWidget(lb, 0, i)
            head.setColumnStretch(i, st)
        root.addLayout(head)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        body = QWidget()
        body.setStyleSheet("background: transparent;")
        self.rows = QVBoxLayout(body)
        self.rows.setContentsMargins(0, 0, 6, 0)
        self.rows.setSpacing(8)
        self.scroll.setWidget(body)
        root.addWidget(self.scroll, 1)
        self.empty = QLabel(t(M.SYP_EMPTY))
        self.empty.setObjectName("emptyMsg")
        self.empty.setAlignment(Qt.AlignCenter)
        self.empty.setWordWrap(True)
        root.addWidget(self.empty, 1)

    # ------------------------------------------------------------------
    def mark_dirty(self):
        self._dirty = True
        if self.isVisible():
            self.refresh()

    def showEvent(self, e):
        if self._dirty:
            self.refresh()
        super().showEvent(e)

    def refresh(self):
        self._dirty = False
        entries = self.ctx.sync.entries
        self.title.setText(self.t(M.SYP_TITLE, n=len(entries)))
        while self.rows.count():
            it = self.rows.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        for e in entries:
            self.rows.addWidget(self._row(e))
        self.rows.addStretch(1)
        self.scroll.setVisible(bool(entries))
        self.empty.setVisible(not entries)

    # ------------------------------------------------------------------
    def _status(self, e: dict):
        t = self.t
        if not e.get("enabled", True):
            return t(M.SYP_PAUSED), "stOff"
        if SyncManager.is_due(e):
            return t(M.SYP_DUE), "stDue"
        if e.get("last_sync"):
            return t(M.SYP_SYNCED), "stOk"
        return t(M.SYP_IDLE), "stIdle"

    def _row(self, e: dict) -> QFrame:
        t = self.t
        rec = self.ctx.history.find(e.get("rec_id", ""))
        fr = QFrame()
        fr.setObjectName("syncRow")
        g = QGridLayout(fr)
        g.setContentsMargins(12, 8, 12, 8)
        g.setHorizontalSpacing(10)
        for i, st in enumerate(COLS):
            g.setColumnStretch(i, st)

        cell = QHBoxLayout()                                   # picture + name + status
        cell.setSpacing(10)
        pic = QLabel()
        src = None
        if rec:
            path = self.ctx.history.thumb_path(rec)
            src = QPixmap(path) if path else None
            if src is not None and src.isNull():
                src = None
        c1, c2 = (rec or {}).get("thumb_colors") or ("#0a1a4a", "#1c4fa8")
        pic.setPixmap(rounded_pixmap(src, 64, 36, 6) if src else make_thumb(c1, c2, 64, 36))
        pic.setFixedSize(64, 36)
        names = QVBoxLayout()
        names.setSpacing(2)
        name = ElidedLabel(e.get("title", ""))
        name.setObjectName("syncTitle")
        text, obj = self._status(e)
        st = QLabel(text)
        st.setObjectName(obj)
        names.addWidget(name)
        names.addWidget(st, 0, Qt.AlignLeft)
        cell.addWidget(pic)
        cell.addLayout(names, 1)
        g.addLayout(cell, 0, 0)

        dates = QVBoxLayout()
        dates.setSpacing(2)
        for label, key in ((M.SYP_COL_LAST, "last_sync"), (M.SYP_COL_NEXT, "next_sync")):
            lb = QLabel(f"{t(label)}: {(e.get(key) or t(M.SYP_NEVER))[:10]}")      # never cut with '...'
            lb.setObjectName("syncInfo")
            dates.addWidget(lb)
        g.addLayout(dates, 0, 1)

        fq = ElidedLabel(f"{rec.get('format', '')}  {rec.get('quality') or t(M.ND_BEST)}" if rec else "-")
        fq.setObjectName("syncInfo")
        g.addWidget(fq, 0, 2)

        combo = ArrowComboBox()
        for key in SCHEDULES:
            combo.addItem(t(SCHEDULE_MSG[key]), key)
        combo.setCurrentIndex(max(0, combo.findData(e.get("schedule", "daily"))))
        combo.currentIndexChanged.connect(lambda _=0, c=combo, en=e: self._set_schedule(en, c.currentData()))
        g.addWidget(combo, 0, 3)

        tg = ToggleSwitch(bool(e.get("enabled", True)), green=True)          # green switch (was an ON / OFF button)
        tg.setToolTip(t(M.SYP_ON if e.get("enabled", True) else M.SYP_OFF))
        tg.toggled.connect(lambda on, en=e: self._set_enabled(en, on))
        g.addWidget(tg, 0, 4, Qt.AlignLeft)

        acts = QHBoxLayout()
        acts.setSpacing(4)
        for icon, tip, fn in ((make_sync_icon(18), M.TIP_SYNC, lambda _=False, en=e, r=rec: self._sync(en, r)),
                              (make_folder_icon(18), M.TIP_FOLDER, lambda _=False, r=rec: self._folder(r)),
                              (make_trash_icon(18), M.TIP_SYNC_DEL, lambda _=False, en=e: self._stop(en))):
            b = QPushButton()
            b.setObjectName("iconBtn")
            b.setIcon(icon)
            b.setIconSize(QSize(icon.width(), icon.height()))
            b.setToolTip(t(tip))
            b.setFixedSize(30, 28)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(fn)
            if tip == M.TIP_SYNC:                              # 2.2.7: green and lit while the playlist is synchronised
                set_sync_button(b, bool(e.get("enabled", True)))
            acts.addWidget(b)
        acts.addStretch(1)
        g.addLayout(acts, 0, 5)
        return fr

    # --- actions ---------------------------------------------------------
    def _set_schedule(self, e: dict, key):
        if key:
            self.ctx.sync.set_schedule(e, key)             # next sync = last sync + 1 day / 7 days / 1 month
            self.refresh()

    def _set_enabled(self, e: dict, on: bool):
        e["enabled"] = bool(on)
        self.ctx.sync.save()
        self.refresh()
        self.sync_changed.emit()

    def _message(self, text: str):
        exec_blurred(self, MessageDialog(self.ctx.lang, self.t(M.ERR_TITLE), text, self.window()))

    def _sync(self, e: dict, rec):
        if not rec:
            self._message(self.t(M.SYP_NOREC))
            return
        self.sync_requested.emit(rec)

    def _folder(self, rec):
        d = os.path.expanduser((rec or {}).get("save_dir", ""))
        if os.path.isdir(d):
            QDesktopServices.openUrl(QUrl.fromLocalFile(d))
        else:
            self._message(self.t(M.ERR_NO_FOLDER))

    def _stop(self, e: dict):
        t = self.t
        dlg = ChoiceDialog(self.ctx.lang, t(M.SYP_STOP), f"{t(M.SYP_DEL_TEXT)}\n{e.get('title', '')}",
                           [("stop", t(M.SYP_STOP), "btnRed"), ("cancel", t(M.BTN_CANCEL1), "btnBlue")],
                           self.window())
        exec_blurred(self, dlg)
        if dlg.choice == "stop":
            self.ctx.sync.remove(e["playlist_id"])
            self.refresh()
            self.sync_changed.emit()
