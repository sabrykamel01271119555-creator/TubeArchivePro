# =============================================================================
# TubeArchive Pro  |  Version 1.0.13  |  File: app/ui/pages.py
# Version history of this file:
#   1.0.13 - Demo rows only when demo_rows is true
#   1.0.12 - SettingsPage moved to settings_page.py
#   1.0.10 - Old design-only LibraryPage removed (real one: library_page.py); demo queue rows in Downloads
#   1.0.8 - Removed the design-only NewDownloadPage (replaced by app/ui/new_download_page.py)
#   1.0.6 - No functional change (version header added)
#   1.0.0 - 1.0.5 - first version and earlier fixes (see CHANGELOG.md)
# =============================================================================
"""Work-area pages. INTERFACE ONLY: no button has a function yet."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox,
                               QFormLayout, QFrame, QGridLayout, QHBoxLayout,
                               QHeaderView, QLabel, QLineEdit, QPlainTextEdit,
                               QPushButton, QScrollArea, QSpinBox,
                               QTableWidget, QTableWidgetItem, QVBoxLayout,
                               QWidget)

from ..context import AppContext
from ..msg import M
from .icons import make_thumb
from .theme import glow
from .widgets import ArrowComboBox, DownloadItem


def _title(text: str) -> QLabel:
    lb = QLabel(text)
    lb.setObjectName("pageTitle")
    return lb


# ----------------------------------------------------------------------
class PlaceholderPage(QWidget):
    """Used for sections whose design is not drawn yet."""

    def __init__(self, ctx: AppContext, title_id: str):
        super().__init__()
        tr = ctx.lang.tr
        v = QVBoxLayout(self)
        v.setContentsMargins(24, 18, 24, 18)
        v.addWidget(_title(tr(title_id)))
        soon = QLabel(tr(M.COMING_SOON))
        soon.setObjectName("comingSoon")
        soon.setAlignment(Qt.AlignCenter)
        v.addWidget(soon, 1)


# ----------------------------------------------------------------------
class DownloaderPage(QWidget):
    """Download list + action buttons + system log (see mainwindow-downloader.jpg)."""

    # DEMO rows: (title, format, quality, total MB, pct, speed, colour1, colour2)
    DEMO = [
        ("Sample Documentary: The History of Flight", "MP4", "1080p", 2500, 72, 45, "#7a3fb0", "#c0392b"),
        ("Synthwave Mix - Full Soundtrack", "MP3", "", 780, 45, 28, "#e6d40a", "#222a44"),
        ("4K Nature Relaxing Video 10 Hours", "MKV", "4K", 1000, 12, 82, "#2f8a3c", "#7fd1c8"),
        ("Space Documentary [Science Channel]", "MP4", "1080p", 400, 95, 10, "#0a1233", "#c56a1c"),
        ("AI & Machine Learning Course - Lecture 03", "WEBM", "1080p", 650, 28, 34, "#12306b", "#3a7bd5"),
    ]

    # DEMO rows waiting in the queue: (title, format, quality, total MB, colour1, colour2)
    DEMO_QUEUE = [
        ("Top 50 Songs of the Decade (Playlist)", "MP3", "", 420, "#8e24aa", "#ff7043"),
        ("Ancient Civilizations - Full Documentary", "MP4", "720p", 1800, "#4e342e", "#ffb300"),
    ]

    def __init__(self, ctx: AppContext):
        super().__init__()
        tr = ctx.lang.tr
        v = QVBoxLayout(self)
        v.setContentsMargins(14, 14, 14, 12)
        v.setSpacing(8)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        holder = QWidget()
        self.list = QVBoxLayout(holder)
        self.list.setContentsMargins(4, 4, 8, 4)
        self.list.setSpacing(10)
        self.items: list[tuple[DownloadItem, float, float]] = []
        unit = tr(M.UNIT_MBS)
        demo_rows = self.DEMO if ctx.settings.get("demo_rows", False) else []
        for title, fmt, q, total, pct, speed, c1, c2 in demo_rows:
            it = DownloadItem(title, fmt, q, total, make_thumb(c1, c2, 100, 62), tr(M.ACTIVE_DOWNLOAD))
            it.set_progress(pct, speed, unit)
            self.list.addWidget(it)
            self.items.append((it, pct, speed))
        for title, fmt, q, total, c1, c2 in (self.DEMO_QUEUE if demo_rows else []):
            it = DownloadItem(title, fmt, q, total, make_thumb(c1, c2, 100, 62), tr(M.QUEUED))
            it.set_progress(0, 0, unit)                      # waiting: not moved by demo_tick
            self.list.addWidget(it)
        self.list.addStretch(1)
        scroll.setWidget(holder)
        v.addWidget(scroll, 1)

        btns = QHBoxLayout()
        btns.setSpacing(14)
        for name, msg, col in (("btnGreen", M.BTN_RESUME, "#1fd16a"), ("btnOrange", M.BTN_PAUSE, "#ffa800"),
                               ("btnRed", M.BTN_CANCEL, "#ff2f72"), ("btnBlue", M.BTN_OPEN_FOLDER, "#2b8cff")):
            b = QPushButton(tr(msg))
            b.setObjectName(name)
            b.setCursor(Qt.PointingHandCursor)
            glow(b, col, 18)
            btns.addWidget(b)
        v.addLayout(btns)

        v.addWidget(QLabel(tr(M.SYSTEM_LOG)))
        self.log = QPlainTextEdit()
        self.log.setObjectName("log")
        self.log.setReadOnly(True)
        self.log.setFixedHeight(84)
        self.log.setPlainText("\n".join((tr(M.LOG_1), tr(M.LOG_2, speed=185), tr(M.LOG_3, count=5))))
        v.addWidget(self.log)

    def demo_tick(self, unit: str):
        """DEMO only: moves the progress bars so the interface looks alive."""
        import random
        for i, (it, pct, speed) in enumerate(self.items):
            pct = min(99.0, pct + random.uniform(0, 0.6))
            speed = max(5.0, speed + random.uniform(-4, 4))
            self.items[i] = (it, pct, speed)
            it.set_progress(pct, speed, unit)
