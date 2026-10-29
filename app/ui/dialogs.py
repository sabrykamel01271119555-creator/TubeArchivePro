# =============================================================================
# TubeArchive Pro  |  Version 2.3.0  |  File: app/ui/dialogs.py
# Version history of this file:
#   2.3.0 - SyncDoneDialog (nothing new), UpdatesDialog, UpdateProgressDialog, BusyDialog(info=), ChoiceDialog(size=), 'yearly'
#   2.2.8 - rating window: a second box for the new features the user wants
#   2.2.8 - Add to Favorites list shows the category icons
#   2.2.7 - warning sound when a warning / error window opens
#   2.2.7 - SyncDialog: all videos of the playlist, buttons Sync / Download selected / Skip New / Later
#   2.2.3 - ExitWarningDialog: line about paused downloads
#   2.1.0 - No X button in message windows (exit, success, sync): every window has its own Cancel / OK / Close button;
#           exit window got a Cancel button (stay in the application)
#   2.0.12 - Exit window: the X followed the corner of the card (removed in 2.1.0)
#   2.0.11 - ChoiceDialog buttons: dimmed (4th item) and stay-open (5th item, on_keep)
#   2.0.10 - ChoiceDialog can show a picture (pixmap)
#   2.0.4 - Buttons (exit window, sync window, choice windows) use mnemonic_safe: 'Skip & Exit', 'Submit & Exit' show their &
#   2.0.3 - Details: the links inside the description are clickable
#   2.0.2 - Details: the folder and the web address are links (open the folder / the browser)
#   2.0.2 - GlassDialog fits the size of the main window (size + texts); Details links; ChoiceDialog used for space / delete questions
#   2.0.2 - Details: folder and web address are clickable links
#   1.0.14 - PlaylistSetupDialog(create_folder=...) default from Settings; CategoryDialog (name + icon)
#   1.0.13 - UpdateDialog
#   1.0.12 - MessageDialog info=True (blue notice); BusyDialog.cancelled
#   1.0.11 - New PlaylistSetupDialog, SyncDialog (new / previously downloaded videos), BusyDialog
#   1.0.10 - Category list of FavoriteDialog shows an arrow
#   1.0.9 - SuccessDialog: "Add to Favorite" button; new ChoiceDialog (delete) and FavoriteDialog (category)
#   1.0.8 - New MessageDialog (errors) and SuccessDialog ('File Successfully Downloaded!')
#   1.0.6 - No functional change (version header added)
#   1.0.0 - 1.0.5 - first version and earlier fixes (see CHANGELOG.md)
# =============================================================================
"""Exit dialogs (design guides: exit warning + 'Before You Go' rating)."""
import html
import math
import os
from datetime import datetime

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, QUrl, Signal
from PySide6.QtGui import (QColor, QDesktopServices, QFontMetrics, QLinearGradient, QPainter, QPen, QPixmap,
                           QPolygonF)
from PySide6.QtWidgets import (QCheckBox, QDialog, QFrame, QGridLayout, QHBoxLayout, QLabel,
                               QLineEdit, QProgressBar, QPushButton, QScrollArea, QTextBrowser, QTextEdit, QVBoxLayout, QWidget)

from ..downloader import fmt_size, fmt_time
from ..i18n import LanguageManager
from ..infodoc import description_html
from .. import sounds
from ..msg import M
from ..sync import add_schedule
from .icons import (make_emoji_icon, make_app_icon, make_arrow_icon, make_check_icon, make_exit_icon, make_folder_icon,
                    make_info_icon, make_play_icon, make_star_icon, make_sync_icon,
                    make_thumb, make_warning_icon, rounded_pixmap)
from .theme import glow
from .widgets import ArrowComboBox, ElidedLabel, mnemonic_safe


class GlassDialog(QDialog):
    """Frameless glowing glass dialog, centred over its parent window."""

    def __init__(self, parent, size, border: QColor, top: QColor, bottom: QColor):
        super().__init__(parent)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setModal(True)
        self.setFixedSize(*size)
        self._base_size = tuple(size)
        self._border, self._top, self._bottom = border, top, bottom

    def _fit_to_window(self):
        """2.0.2: the window follows the size of the main window (smaller window -> smaller dialog and texts, never
        bigger than the window; larger window -> a little larger)."""
        parent = self.parentWidget()
        if not parent:
            return
        from .theme import font_qss
        bw, bh = self._base_size
        s = max(0.7, min(1.3, min(parent.width() / 1180.0, parent.height() / 740.0)))
        s = min(s, (parent.width() * 0.96) / bw, (parent.height() * 0.96) / bh)
        s = round(max(0.55, s) * 20) / 20.0
        self.setFixedSize(int(bw * s), int(bh * s))
        if abs(s - 1.0) > 0.01:
            self.setStyleSheet(font_qss(s))

    def showEvent(self, e):
        self._fit_to_window()
        parent = self.parentWidget()
        if parent:
            self.move(parent.frameGeometry().center() - self.rect().center())
        super().showEvent(e)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        card = QRectF(self.rect()).adjusted(16, 16, -16, -16)
        p.setBrush(Qt.NoBrush)
        for i in range(12, 0, -1):          # outer glow
            c = QColor(self._border)
            c.setAlpha(6 + (12 - i) * 3)
            p.setPen(QPen(c, i * 2))
            p.drawRoundedRect(card, 24, 24)
        g = QLinearGradient(card.topLeft(), card.bottomRight())
        g.setColorAt(0, self._top)
        g.setColorAt(1, self._bottom)
        p.setBrush(g)
        p.setPen(QPen(self._border, 2))
        p.drawRoundedRect(card, 24, 24)
        sheen = QLinearGradient(card.topLeft(), card.center())
        sheen.setColorAt(0, QColor(255, 255, 255, 40))
        sheen.setColorAt(1, QColor(255, 255, 255, 0))
        p.setPen(Qt.NoPen)
        p.setBrush(sheen)
        p.drawRoundedRect(card.adjusted(2, 2, -2, -card.height() * .55), 22, 22)


def _center_row(*widgets) -> QHBoxLayout:
    row = QHBoxLayout()
    row.addStretch(1)
    for w in widgets:
        row.addWidget(w)
    row.addStretch(1)
    return row


# ----------------------------------------------------------------------
class ExitWarningDialog(GlassDialog):
    """Shown when downloads are still running. exec() == Accepted -> abort and exit."""

    def __init__(self, lang: LanguageManager, count: int, avg_pct: int, parent=None, paused: int = 0):
        super().__init__(parent, (680, 480), QColor(255, 80, 100),
                         QColor(78, 66, 126, 242), QColor(26, 38, 100, 248))
        sounds.play("warning")
        tr = lang.tr
        v = QVBoxLayout(self)
        v.setContentsMargins(46, 40, 46, 38)
        v.setSpacing(14)

        icon = QLabel()
        icon.setPixmap(make_warning_icon(46))
        title = QLabel(tr(M.EXIT_TITLE))
        title.setObjectName("dlgTitle")
        v.addLayout(_center_row(icon, title))

        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet("background: rgba(255,255,255,0.35);")
        v.addWidget(line)
        v.addSpacing(6)

        warn = QLabel(tr(M.EXIT_WARN))
        warn.setObjectName("dlgWarn")
        warn.setAlignment(Qt.AlignCenter)
        warn.setWordWrap(True)
        v.addWidget(warn)
        text = QLabel(tr(M.EXIT_TEXT))
        text.setObjectName("dlgText")
        text.setAlignment(Qt.AlignCenter)
        text.setWordWrap(True)
        v.addWidget(text)
        pill = QLabel(tr(M.EXIT_ONE if count == 1 else M.EXIT_MANY, count=count, pct=avg_pct))
        pill.setObjectName("dlgPill")
        v.addLayout(_center_row(pill))
        if paused:                                              # videos that were paused will not be finished either
            pz = QLabel(tr(M.EXIT_PAUSED, paused=paused))
            pz.setObjectName("dlWarn")
            pz.setAlignment(Qt.AlignCenter)
            pz.setWordWrap(True)
            v.addWidget(pz)
        v.addStretch(1)

        row = QHBoxLayout()
        row.setSpacing(18)
        back = QPushButton(tr(M.BTN_BACK))
        back.setObjectName("btnBlue")
        back.setDefault(True)
        back.setMinimumHeight(54)
        back.setCursor(Qt.PointingHandCursor)
        back.clicked.connect(self.reject)
        glow(back, "#2b8cff", 20)
        abort = QPushButton("  " + tr(M.BTN_ABORT))
        abort.setObjectName("btnRed")
        abort.setIcon(make_exit_icon(24))
        abort.setMinimumHeight(54)
        abort.setCursor(Qt.PointingHandCursor)
        abort.clicked.connect(self.accept)
        glow(abort, "#ff2f72", 20)
        row.addWidget(back, 1)
        row.addWidget(abort, 1)
        v.addLayout(row)


# ----------------------------------------------------------------------
class StarRating(QWidget):
    changed = Signal(int)
    hovered = Signal(int)      # 0 when the mouse leaves
    CELL = 74

    def __init__(self):
        super().__init__()
        self.value = 0
        self.hover = 0
        self.setMouseTracking(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(self.CELL * 5, self.CELL)

    def _index_at(self, x: float) -> int:
        return max(1, min(5, int(x // self.CELL) + 1))

    def mouseMoveEvent(self, e):
        self.hover = self._index_at(e.position().x())
        self.hovered.emit(self.hover)
        self.update()

    def leaveEvent(self, e):
        self.hover = 0
        self.hovered.emit(0)
        self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.value = self._index_at(e.position().x())
            self.changed.emit(self.value)
            self.update()

    @staticmethod
    def _star(cx, cy, r) -> QPolygonF:
        pts = []
        for i in range(10):
            ang = math.radians(-90 + i * 36)
            rad = r if i % 2 == 0 else r * 0.46
            pts.append(QPointF(cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
        return QPolygonF(pts)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        shown = self.hover or self.value
        for i in range(5):
            cx, cy = i * self.CELL + self.CELL / 2, self.CELL / 2 + 1
            poly = self._star(cx, cy, 31)
            if i < shown:
                p.setPen(QPen(QColor(255, 200, 60, 70), 9, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
                p.setBrush(Qt.NoBrush)
                p.drawPolygon(poly)
                g = QLinearGradient(cx, cy - 31, cx, cy + 31)
                g.setColorAt(0, QColor("#ffe88a"))
                g.setColorAt(1, QColor("#f0a000"))
                p.setBrush(g)
                p.setPen(QPen(QColor("#ffd24a"), 2.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            else:
                p.setBrush(QColor(255, 255, 255, 14))
                p.setPen(QPen(QColor(255, 255, 255, 120), 2.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.drawPolygon(poly)


class RatingDialog(GlassDialog):
    """'Before You Go!' dialog. After exec(): .action is 'submit', 'skip' or 'cancel'."""

    def __init__(self, lang: LanguageManager, parent=None, previous: dict | None = None):
        super().__init__(parent, (720, 740), QColor(70, 190, 255),
                         QColor(44, 108, 178, 240), QColor(14, 44, 118, 248))
        self.lang = lang
        self.action = "cancel"
        self.rating = 0
        tr = lang.tr
        v = QVBoxLayout(self)
        v.setContentsMargins(56, 40, 56, 40)
        v.setSpacing(10)

        logo = QLabel()
        logo.setPixmap(make_app_icon(78))
        name = QLabel(tr(M.APP_NAME))
        name.setObjectName("dlgBrand")
        v.addLayout(_center_row(logo, name))
        v.addSpacing(6)

        title = QLabel(tr(M.RATE_TITLE))
        title.setObjectName("dlgTitle")
        title.setAlignment(Qt.AlignCenter)
        v.addWidget(title)
        sub = QLabel(tr(M.RATE_SUB))
        sub.setObjectName("rateSub")
        sub.setAlignment(Qt.AlignCenter)
        sub.setWordWrap(True)
        v.addWidget(sub)

        self.stars = StarRating()
        v.addLayout(_center_row(self.stars))
        self.rate_label = QLabel(tr(M.RATE_HINT))
        self.rate_label.setObjectName("rateLabel")
        self.rate_label.setAlignment(Qt.AlignCenter)
        v.addWidget(self.rate_label)
        self.stars.changed.connect(self._on_rating)
        self.stars.hovered.connect(self._on_hover)

        self.comment = QTextEdit()
        self.comment.setObjectName("feedback")
        self.comment.setPlaceholderText(tr(M.RATE_PLACEHOLDER))
        self.comment.setFixedHeight(84)
        self.comment.setAcceptRichText(False)
        v.addWidget(self.comment)
        self.features = QTextEdit()                          # 2.2.8: which new features the user would like
        self.features.setObjectName("feedback")
        self.features.setPlaceholderText(tr(M.RATE_FEATURES_PH))
        self.features.setFixedHeight(84)
        self.features.setAcceptRichText(False)
        v.addWidget(self.features)

        detailed = QPushButton(tr(M.BTN_DETAILED))      # no function yet
        detailed.setObjectName("outline")
        detailed.setMinimumHeight(46)
        detailed.setCursor(Qt.PointingHandCursor)
        glow(detailed, "#27d3ff", 16)
        v.addWidget(detailed)
        v.addSpacing(4)

        row = QHBoxLayout()
        row.setSpacing(16)
        skip = QPushButton(mnemonic_safe(tr(M.BTN_SKIP)))
        skip.setObjectName("btnRed")
        submit = QPushButton(mnemonic_safe(tr(M.BTN_SUBMIT)))
        submit.setObjectName("btnGreen")
        back = QPushButton(tr(M.BTN_CANCEL1))             # Cancel: stay in the application (replaces the old X button)
        back.setObjectName("btnBlue")
        for b, col, fn in ((back, "#27a8ff", self.reject), (skip, "#ff2f72", self._skip), (submit, "#1fd16a", self._submit)):
            b.setMinimumHeight(52)
            b.setMinimumWidth(150)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(fn)
            glow(b, col, 18)
        row.addStretch(1)
        row.addWidget(back)
        row.addWidget(skip)
        row.addWidget(submit)
        row.addStretch(1)
        v.addLayout(row)

        if previous:                                      # the rating given before is shown again (and can be changed)
            self.stars.value = int(previous.get("rating", 0))
            self.comment.setPlainText(previous.get("comment", ""))
            self.features.setPlainText(previous.get("features", ""))
            self._on_rating(self.stars.value)

    def _text_for(self, n: int) -> str:
        ids = {1: M.RATE_1, 2: M.RATE_2, 3: M.RATE_3, 4: M.RATE_4, 5: M.RATE_5}
        return self.lang.tr(ids[n]) if n else self.lang.tr(M.RATE_HINT)

    def _on_rating(self, n: int):
        self.rating = n
        self.rate_label.setText(self._text_for(n))

    def _on_hover(self, n: int):
        self.rate_label.setText(self._text_for(n or self.rating))

    def _skip(self):
        self.action = "skip"
        self.accept()

    def _submit(self):
        self.action = "submit"
        self.accept()

    @property
    def feedback_text(self) -> str:
        return self.comment.toPlainText()

    @property
    def features_text(self) -> str:
        return self.features.toPlainText()


# ----------------------------------------------------------------------
class MessageDialog(GlassDialog):
    """One-button message window used for download errors (red glass)."""

    def __init__(self, lang: LanguageManager, title: str, text: str, parent=None, info: bool = False):
        # info=True: blue notice (notifications); default: red error window
        if not info:
            sounds.play("warning")
        super().__init__(parent, (660, 380), QColor(70, 200, 255) if info else QColor(255, 80, 100),
                         QColor(40, 110, 170, 240) if info else QColor(78, 66, 126, 242), QColor(26, 38, 100, 248))
        v = QVBoxLayout(self)
        v.setContentsMargins(46, 38, 46, 36)
        v.setSpacing(14)
        icon = QLabel()
        icon.setPixmap(make_sync_icon(44, "#27d3ff") if info else make_warning_icon(44))
        head = QLabel(title)
        head.setObjectName("dlgTitle")
        v.addLayout(_center_row(icon, head))
        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet("background: rgba(255,255,255,0.35);")
        v.addWidget(line)
        body = QLabel(text)
        body.setObjectName("dlgText")
        body.setAlignment(Qt.AlignCenter)
        body.setWordWrap(True)
        v.addWidget(body, 1)
        ok = QPushButton(lang.tr(M.BTN_OK))
        ok.setObjectName("btnBlue")
        ok.setMinimumHeight(50)
        ok.setMinimumWidth(200)
        ok.setDefault(True)
        ok.setCursor(Qt.PointingHandCursor)
        ok.clicked.connect(self.accept)
        glow(ok, "#2b8cff", 18)
        v.addLayout(_center_row(ok))


class SuccessDialog(GlassDialog):
    """'File Successfully Downloaded!' window.
    rows = [(icon kind, label, value, optional badge text)].  After exec():
    .action is 'play', 'folder' or 'ok';  .dont_show tells if the check box is ticked."""

    def __init__(self, lang: LanguageManager, title: str, rows: list, is_audio: bool,
                 dont_show: bool = False, parent=None, fav_cb=None):
        super().__init__(parent, (780, 770 if fav_cb else 690), QColor(70, 200, 255),
                         QColor(40, 110, 170, 240), QColor(12, 44, 112, 248))
        self.action = "ok"
        self.fav_cb = fav_cb              # called when 'Add to Favorite' is pressed; returns True when added
        self._tr = lang.tr
        tr = lang.tr
        v = QVBoxLayout(self)
        v.setContentsMargins(48, 30, 48, 36)
        v.setSpacing(10)

        top = QHBoxLayout()
        small = QLabel()
        small.setPixmap(make_app_icon(30))
        cap = QLabel(tr(M.APP_NAME))
        cap.setStyleSheet("font-size: 19px; color: #eaf4ff;")
        top.addWidget(small)
        top.addWidget(cap)
        top.addStretch(1)
        v.addLayout(top)

        check = QLabel()
        check.setPixmap(make_check_icon(130))
        v.addLayout(_center_row(check))
        head = QLabel(title)
        head.setObjectName("dlgTitle")
        head.setAlignment(Qt.AlignCenter)
        head.setWordWrap(True)
        v.addWidget(head)
        v.addSpacing(6)

        box = QFrame()
        box.setObjectName("infoBox")
        bl = QVBoxLayout(box)
        bl.setContentsMargins(26, 16, 26, 16)
        bl.setSpacing(12)
        for kind, key, value, badge in rows:
            r = QHBoxLayout()
            r.setSpacing(12)
            ic = QLabel()
            ic.setPixmap(make_info_icon(kind, 34, badge))
            ic.setFixedWidth(38)
            k = QLabel(key)
            k.setObjectName("infoKey")
            val = ElidedLabel(value)
            val.setObjectName("infoVal")
            r.addWidget(ic)
            r.addWidget(k)
            r.addWidget(val, 1)
            bl.addLayout(r)
        v.addWidget(box)

        self.chk = QCheckBox(tr(M.OK_DONT_SHOW))
        self.chk.setObjectName("dontShow")
        self.chk.setChecked(dont_show)
        v.addLayout(_center_row(self.chk))
        v.addStretch(1)

        row = QHBoxLayout()
        row.setSpacing(16)
        play = QPushButton("  " + tr(M.BTN_PLAY_AUDIO if is_audio else M.BTN_PLAY_VIDEO))
        play.setObjectName("playBtn")
        play.setIcon(make_play_icon(22))
        opn = QPushButton("  " + tr(M.BTN_FOLDER1))
        opn.setObjectName("openBtn")
        opn.setIcon(make_folder_icon(24))
        ok = QPushButton(tr(M.BTN_OK))
        ok.setObjectName("okBtn")
        ok.setDefault(True)
        for b, col, act in ((play, "#35e2ff", "play"), (opn, "#d8b98a", "folder"), (ok, "#ff4f78", "ok")):
            b.setMinimumHeight(54)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _=False, a=act: self._choose(a))
            glow(b, col, 18)
            row.addWidget(b, 1)
        v.addLayout(row)
        self.fav = None
        if fav_cb:
            self.fav = QPushButton("  " + tr(M.BTN_FAV))
            self.fav.setObjectName("favBtn")
            self.fav.setIcon(make_star_icon(24))
            self.fav.setMinimumHeight(54)
            self.fav.setCursor(Qt.PointingHandCursor)
            self.fav.clicked.connect(self._add_fav)
            glow(self.fav, "#ffc400", 18)
            v.addWidget(self.fav)

    def _add_fav(self):
        if self.fav_cb and self.fav_cb():
            self.fav.setText("  " + self._tr(M.FAV_ADDED))
            self.fav.setIcon(make_star_icon(24, True))
            self.fav.setEnabled(False)

    def _choose(self, action: str):
        self.action = action
        self.accept()

    @property
    def dont_show(self) -> bool:
        return self.chk.isChecked()


# ----------------------------------------------------------------------
class ChoiceDialog(GlassDialog):
    """Message with several buttons. buttons = [(choice id, text, style object name)].
    After exec(): .choice is the id of the pressed button, or None (window closed)."""

    def __init__(self, lang: LanguageManager, title: str, text: str, buttons: list, parent=None, pixmap=None,
                 size: tuple | None = None):
        """size = (width, height) for a long text or many buttons (2.3.0)."""
        super().__init__(parent, size or (760, 560 if pixmap is not None else 400), QColor(255, 170, 70),
                         QColor(84, 70, 120, 242), QColor(26, 38, 100, 248))
        sounds.play("warning")
        self.choice = None
        v = QVBoxLayout(self)
        v.setContentsMargins(46, 36, 46, 34)
        v.setSpacing(14)
        icon = QLabel()
        icon.setPixmap(make_warning_icon(44))
        head = QLabel(title)
        head.setObjectName("dlgTitle")
        v.addLayout(_center_row(icon, head))
        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet("background: rgba(255,255,255,0.35);")
        v.addWidget(line)
        if pixmap is not None and not pixmap.isNull():              # picture of the video (2.0.10)
            pic = QLabel()
            pic.setAlignment(Qt.AlignCenter)
            pic.setPixmap(rounded_pixmap(pixmap, 256, 144, 12))
            v.addWidget(pic)
        body = QLabel(text)
        body.setObjectName("dlgText")
        body.setAlignment(Qt.AlignCenter)
        body.setWordWrap(True)
        v.addWidget(body, 1)
        row = QHBoxLayout()
        row.setSpacing(14)
        self.on_keep = None                  # called with the id of a button that does not close the window
        for spec in buttons:
            cid, label, obj = spec[:3]
            enabled = spec[3] if len(spec) > 3 else True          # 4th item: False = dimmed
            keep = spec[4] if len(spec) > 4 else False            # 5th item: True = acts but the window stays open
            b = QPushButton(mnemonic_safe(label))
            b.setObjectName(obj)
            b.setMinimumHeight(50)
            b.setEnabled(enabled)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _=False, c=cid, k=keep: self._keep(c) if k else self._pick(c))
            row.addWidget(b, 1)
        v.addLayout(row)

    def _keep(self, cid):
        if self.on_keep:
            self.on_keep(cid)

    def _pick(self, cid):
        self.choice = cid
        self.accept()


class UpdateDialog(GlassDialog):
    """'A new version is available - update?'  After exec(): .choice is 'yes' or 'no' (closing = no);
    .dont_show tells if 'Don't show this message again' is ticked."""

    def __init__(self, lang: LanguageManager, new_version: str, current_version: str, parent=None):
        super().__init__(parent, (760, 470), QColor(70, 200, 255),
                         QColor(40, 110, 170, 240), QColor(12, 44, 112, 248))
        self.choice, self.dont_show = "no", False
        tr = lang.tr
        v = QVBoxLayout(self)
        v.setContentsMargins(46, 34, 46, 32)
        v.setSpacing(14)
        icon = QLabel()
        icon.setPixmap(make_arrow_icon(44))
        head = QLabel(tr(M.UP_TITLE))
        head.setObjectName("dlgTitle")
        v.addLayout(_center_row(icon, head))
        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet("background: rgba(255,255,255,0.35);")
        v.addWidget(line)
        body = QLabel(tr(M.UP_TEXT, new=new_version, cur=current_version))
        body.setObjectName("dlgText")
        body.setAlignment(Qt.AlignCenter)
        body.setWordWrap(True)
        v.addWidget(body, 1)
        self.chk = QCheckBox(tr(M.UP_DONT))
        self.chk.setObjectName("dontShow")
        v.addLayout(_center_row(self.chk))
        row = QHBoxLayout()
        row.setSpacing(14)
        for cid, msg, obj in (("yes", M.UP_YES, "btnGreen"), ("no", M.UP_NO, "btnBlue")):
            b = QPushButton(tr(msg))
            b.setObjectName(obj)
            b.setMinimumHeight(50)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _=False, c=cid: self._pick(c))
            row.addWidget(b, 1)
        v.addLayout(row)

    def _pick(self, cid):
        self.choice = cid
        self.dont_show = self.chk.isChecked()
        self.accept()

    def reject(self):                       # the X / Esc: same as 'No' (the tick is still remembered)
        self.dont_show = self.chk.isChecked()
        super().reject()


class UpdatesDialog(GlassDialog):
    """2.3.0 'Updates': the application (version, up to date or a newer one) and the tools (yt-dlp, ffmpeg).
    app_line = text of the application row; app_new = True when a newer program version exists (a tick box, ticked);
    tools = list of lines ('yt-dlp: 2026.01.01 -> 2026.10.20'), [] = up to date, None = the check did not work.
    After exec() == Accepted: .update_app, .update_tools (the 'Update tools' box starts UNticked)."""

    def __init__(self, lang: LanguageManager, app_line: str, app_new: bool, tools, parent=None):
        n = len(tools or [])
        super().__init__(parent, (760, 400 + 30 * n), QColor(70, 200, 255),
                         QColor(40, 110, 170, 240), QColor(12, 44, 112, 248))
        tr = lang.tr
        self.update_app = self.update_tools = False
        v = QVBoxLayout(self)
        v.setContentsMargins(46, 34, 46, 32)
        v.setSpacing(14)
        icon = QLabel()
        icon.setPixmap(make_arrow_icon(44))
        head = QLabel(tr(M.UPD_TITLE))
        head.setObjectName("dlgTitle")
        v.addLayout(_center_row(icon, head))
        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet("background: rgba(255,255,255,0.35);")
        v.addWidget(line)
        self.c_app = self.c_tools = None
        if app_new:
            self.c_app = QCheckBox(app_line)
            self.c_app.setObjectName("dontShow")
            self.c_app.setChecked(True)
            self.c_app.toggled.connect(self._refresh)
            v.addWidget(self.c_app)
        else:
            lab = QLabel(app_line)                                    # dimmed: nothing to choose
            lab.setObjectName("infoKey")
            v.addWidget(lab)
        if tools:
            self.c_tools = QCheckBox(tr(M.UPD_TOOLS))
            self.c_tools.setObjectName("dontShow")
            self.c_tools.setChecked(False)
            self.c_tools.toggled.connect(self._refresh)
            v.addWidget(self.c_tools)
            for t_line in tools:
                lab = QLabel("      " + t_line)
                lab.setObjectName("infoVal")
                v.addWidget(lab)
        else:
            lab = QLabel(tr(M.UPD_TOOLS_CURRENT if tools is not None else M.UPD_TOOLS_FAILED))
            lab.setObjectName("infoKey")
            v.addWidget(lab)
        v.addStretch(1)
        row = QHBoxLayout()
        row.setSpacing(14)
        self.b_update = QPushButton(tr(M.UPD_BTN_UPDATE))
        self.b_update.setObjectName("btnGreen")
        close = QPushButton(tr(M.UPD_BTN_CLOSE))
        close.setObjectName("btnBlue")
        for b in (self.b_update, close):
            b.setMinimumHeight(50)
            b.setCursor(Qt.PointingHandCursor)
            row.addWidget(b, 1)
        self.b_update.clicked.connect(self._ok)
        close.clicked.connect(self.reject)
        v.addLayout(row)
        self._refresh()

    def _refresh(self, *_a):
        self.b_update.setEnabled(bool((self.c_app and self.c_app.isChecked()) or (self.c_tools and self.c_tools.isChecked())))

    def _ok(self):
        self.update_app = bool(self.c_app and self.c_app.isChecked())
        self.update_tools = bool(self.c_tools and self.c_tools.isChecked())
        self.accept()


class UpdateProgressDialog(GlassDialog):
    """2.3.0 progress of a tool update: one percentage and 'x MB of y MB' (no file names). Cancel sets .cancelled."""

    def __init__(self, lang: LanguageManager, parent=None):
        super().__init__(parent, (700, 330), QColor(70, 200, 255),
                         QColor(40, 110, 170, 240), QColor(12, 44, 112, 248))
        self._tr = tr = lang.tr
        self.cancelled = False
        v = QVBoxLayout(self)
        v.setContentsMargins(46, 36, 46, 32)
        v.setSpacing(14)
        head = QLabel(tr(M.UPD_PROGRESS_TITLE))
        head.setObjectName("dlgTitle")
        head.setAlignment(Qt.AlignCenter)
        v.addWidget(head)
        self.bar = QProgressBar()
        self.bar.setObjectName("dlBarTotal")
        self.bar.setRange(0, 1000)
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(14)
        v.addWidget(self.bar)
        self.pct = QLabel("0 %")
        self.pct.setObjectName("dlgText")
        self.pct.setAlignment(Qt.AlignCenter)
        v.addWidget(self.pct)
        self.size = QLabel("")
        self.size.setObjectName("infoKey")
        self.size.setAlignment(Qt.AlignCenter)
        v.addWidget(self.size)
        v.addStretch(1)
        cancel = QPushButton(tr(M.UPD_BTN_CANCEL))
        cancel.setObjectName("btnRed")
        cancel.setMinimumHeight(48)
        cancel.setMinimumWidth(200)
        cancel.setCursor(Qt.PointingHandCursor)
        cancel.clicked.connect(self._cancel)
        v.addLayout(_center_row(cancel))

    def set_progress(self, done: int, total: int):
        frac = min(1.0, done / total) if total > 0 else 0.0
        self.bar.setValue(int(frac * 1000))
        self.pct.setText(f"{int(frac * 100)} %")
        self.size.setText(self._tr(M.UPD_PROGRESS_SIZE, done=fmt_size(done), total=fmt_size(total)) if total > 0
                          else self._tr(M.UPD_PROGRESS_UNKNOWN, done=fmt_size(done)))

    def _cancel(self):
        self.cancelled = True
        self.reject()

    def finish(self):
        self.accept()


class FavoriteDialog(GlassDialog):
    """'Add to Favorites': pick a category from the list or type a new one.
    After exec() == Accepted: .category holds the chosen / typed name."""

    def __init__(self, lang: LanguageManager, categories: list, default: str, parent=None, icons: dict | None = None):
        super().__init__(parent, (700, 400), QColor(255, 200, 70),
                         QColor(84, 74, 120, 242), QColor(26, 38, 100, 248))
        tr = lang.tr
        self.category = ""
        v = QVBoxLayout(self)
        v.setContentsMargins(46, 36, 46, 34)
        v.setSpacing(14)
        icon = QLabel()
        icon.setPixmap(make_star_icon(44, True))
        head = QLabel(tr(M.FAV_TITLE))
        head.setObjectName("dlgTitle")
        v.addLayout(_center_row(icon, head))
        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet("background: rgba(255,255,255,0.35);")
        v.addWidget(line)
        body = QLabel(tr(M.FAV_TEXT))
        body.setObjectName("dlgText")
        body.setAlignment(Qt.AlignCenter)
        body.setWordWrap(True)
        v.addWidget(body)
        self.combo = ArrowComboBox()
        self.combo.setEditable(True)               # typing a new name creates a new category
        self.combo.setMinimumHeight(48)
        for c in (categories or [default]):                  # 2.3.0: the icon of each category is shown beside its name
            ic = (icons or {}).get(c, "")
            if ic:
                self.combo.addItem(make_emoji_icon(ic, 24), c)
            else:
                self.combo.addItem(c)
        self.combo.setIconSize(QSize(24, 24))
        self.combo.setCurrentText(categories[0] if categories else default)
        v.addWidget(self.combo)
        v.addStretch(1)
        row = QHBoxLayout()
        row.setSpacing(14)
        add = QPushButton(tr(M.FAV_ADD))
        add.setObjectName("favBtn")
        add.setIcon(make_star_icon(22))
        add.setDefault(True)
        cancel = QPushButton(tr(M.BTN_CANCEL1))
        cancel.setObjectName("btnRed")
        for b in (add, cancel):
            b.setMinimumHeight(50)
            b.setCursor(Qt.PointingHandCursor)
            row.addWidget(b, 1)
        add.clicked.connect(self._ok)
        cancel.clicked.connect(self.reject)
        v.addLayout(row)

    def _ok(self):
        name = " ".join(self.combo.currentText().split())
        if name:
            self.category = name
            self.accept()


# ----------------------------------------------------------------------
# icons offered for a category: standard emoji (drawn by the system font, nothing to download)
CATEGORY_ICONS = ["⭐", "🎬", "🎵", "🎮", "📚", "🎓", "🔬", "🍳", "✈️", "🏋️", "😂", "🎨",
                  "📰", "🛠️", "💼", "🏠", "🚗", "⚽", "🐾", "💡", "🎤", "📷", "🧠", "❤️"]


class CategoryDialog(GlassDialog):
    """New / edit a favorites category: its name + one icon from a small list.
    After exec() == Accepted: .name and .icon.  `taken` = names (lower case) that may not be used again."""

    def __init__(self, lang: LanguageManager, title: str, name: str = "", icon: str = "",
                 taken=(), parent=None):
        super().__init__(parent, (760, 560), QColor(255, 200, 70),
                         QColor(84, 74, 120, 242), QColor(26, 38, 100, 248))
        tr = self._tr = lang.tr
        self.name, self.icon, self._taken = "", icon or CATEGORY_ICONS[0], {t.lower() for t in taken}
        v = QVBoxLayout(self)
        v.setContentsMargins(46, 32, 46, 32)
        v.setSpacing(12)
        icon_lb = QLabel()
        icon_lb.setPixmap(make_star_icon(40, True))
        head = QLabel(title)
        head.setObjectName("dlgTitle")
        v.addLayout(_center_row(icon_lb, head))
        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet("background: rgba(255,255,255,0.35);")
        v.addWidget(line)
        v.addWidget(self._label(tr(M.CAT_NAME)))
        self.edit = QLineEdit(name)
        self.edit.setMinimumHeight(44)
        self.edit.setMaxLength(40)
        v.addWidget(self.edit)
        v.addWidget(self._label(tr(M.CAT_ICON)))
        grid = QGridLayout()
        grid.setSpacing(8)
        self._buttons = []
        for i, ic in enumerate(CATEGORY_ICONS):
            b = QPushButton(ic)
            b.setObjectName("iconPick")
            b.setCheckable(True)
            b.setChecked(ic == self.icon)
            b.setFixedSize(52, 46)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _=False, x=ic: self._pick(x))
            grid.addWidget(b, i // 8, i % 8)
            self._buttons.append((ic, b))
        v.addLayout(grid)
        self.err = QLabel("")
        self.err.setObjectName("dlgText")
        self.err.setAlignment(Qt.AlignCenter)
        v.addWidget(self.err)
        v.addStretch(1)
        row = QHBoxLayout()
        row.setSpacing(14)
        ok = QPushButton(tr(M.CAT_SAVE))
        ok.setObjectName("btnGreen")
        ok.setDefault(True)
        cancel = QPushButton(tr(M.BTN_CANCEL1))
        cancel.setObjectName("btnRed")
        for b in (ok, cancel):
            b.setMinimumHeight(50)
            b.setCursor(Qt.PointingHandCursor)
            row.addWidget(b, 1)
        ok.clicked.connect(self._ok)
        cancel.clicked.connect(self.reject)
        v.addLayout(row)
        self.edit.returnPressed.connect(self._ok)

    @staticmethod
    def _label(text: str) -> QLabel:
        lb = QLabel(text)
        lb.setObjectName("cardTitle")
        return lb

    def _pick(self, icon: str):
        self.icon = icon
        for ic, b in self._buttons:
            b.setChecked(ic == icon)

    def _ok(self):
        name = " ".join(self.edit.text().split())
        if not name:
            return
        if name.lower() in self._taken:
            self.err.setText(self._tr(M.CAT_EXISTS))
            return
        self.name = name
        self.accept()


# ----------------------------------------------------------------------
class BusyDialog(GlassDialog):
    """'Checking the playlist...' with a Cancel button. The caller closes it with finish()."""

    def __init__(self, lang: LanguageManager, text: str, parent=None, info: list | None = None):
        """info (2.3.0): lines shown under the text (playlist, files already there, last sync, quality, folder ...)."""
        super().__init__(parent, (700, 300 + (30 * len(info) + 24 if info else 0)), QColor(70, 200, 255),
                         QColor(40, 110, 170, 240), QColor(12, 44, 112, 248))
        self.cancelled = False
        v = QVBoxLayout(self)
        v.setContentsMargins(46, 40, 46, 36)
        v.setSpacing(16)
        ic = QLabel()
        ic.setPixmap(make_sync_icon(56, "#27d3ff"))
        v.addLayout(_center_row(ic))
        body = QLabel(text)
        body.setObjectName("dlgText")
        body.setAlignment(Qt.AlignCenter)
        body.setWordWrap(True)
        v.addWidget(body, 1 if not info else 0)
        if info:
            box = QFrame()
            box.setObjectName("infoBox")
            bl = QVBoxLayout(box)
            bl.setContentsMargins(18, 10, 18, 10)
            bl.setSpacing(4)
            for line in info:
                lab = ElidedLabel(line)
                lab.setObjectName("infoVal")
                bl.addWidget(lab)
            v.addWidget(box, 1)
        cancel = QPushButton(lang.tr(M.BTN_CANCEL1))
        cancel.setObjectName("btnRed")
        cancel.setMinimumHeight(48)
        cancel.setMinimumWidth(200)
        cancel.setCursor(Qt.PointingHandCursor)
        cancel.clicked.connect(self._cancel)
        v.addLayout(_center_row(cancel))

    def _cancel(self):
        self.cancelled = True
        self.reject()

    def finish(self):
        self.accept()


# ----------------------------------------------------------------------
class SyncDoneDialog(GlassDialog):
    """2.3.0: 'Playlist synced - nothing new': last / next sync, schedule drop-down, automatic sync on / off.
    After exec(): .schedule ('daily' ...), .enabled (bool); .changed is True when the user pressed OK."""

    def __init__(self, lang: LanguageManager, title: str, last: str, schedule: str, enabled: bool,
                 can_keep: bool = True, parent=None):
        super().__init__(parent, (700, 520 if can_keep else 330), QColor(70, 200, 255),
                         QColor(40, 110, 170, 240), QColor(12, 44, 112, 248))
        tr = self._tr = lang.tr
        self.schedule, self.enabled, self.changed = schedule, enabled, False
        v = QVBoxLayout(self)
        v.setContentsMargins(46, 34, 46, 34)
        v.setSpacing(12)
        ic = QLabel()
        ic.setPixmap(make_check_icon(56))
        v.addLayout(_center_row(ic))
        head = QLabel(tr(M.SD_TITLE))
        head.setObjectName("dlgTitle")
        head.setAlignment(Qt.AlignCenter)
        v.addWidget(head)
        body = QLabel(tr(M.SD_TEXT, title=title))
        body.setObjectName("dlgText")
        body.setAlignment(Qt.AlignCenter)
        body.setWordWrap(True)
        v.addWidget(body)
        last_lbl = QLabel(tr(M.SD_LAST, date=last or tr(M.BZ_NEVER)))
        last_lbl.setObjectName("infoKey")
        last_lbl.setAlignment(Qt.AlignCenter)
        v.addWidget(last_lbl)
        self.combo = self.check = self.next_lbl = None
        if can_keep:
            self.check = QCheckBox(tr(M.SD_ENABLE))
            self.check.setObjectName("dontShow")
            self.check.setChecked(enabled)
            self.check.toggled.connect(self._update)
            v.addWidget(self.check)
            lab = QLabel(tr(M.PS_SCHEDULE))
            lab.setObjectName("infoKey")
            self.combo = ArrowComboBox()
            for key, msg in (("daily", M.PS_DAILY), ("weekly", M.PS_WEEKLY), ("monthly", M.PS_MONTHLY),
                             ("yearly", M.PS_YEARLY)):
                self.combo.addItem(tr(msg), key)
            idx = self.combo.findData(schedule)
            self.combo.setCurrentIndex(idx if idx >= 0 else 0)
            self.combo.setMinimumHeight(46)
            self.combo.currentIndexChanged.connect(self._update)
            self.next_lbl = QLabel("")
            self.next_lbl.setObjectName("syncInfo")
            self.next_lbl.setAlignment(Qt.AlignCenter)
            v.addWidget(lab)
            v.addWidget(self.combo)
            v.addWidget(self.next_lbl)
        v.addStretch(1)
        ok = QPushButton(tr(M.BTN_OK))
        ok.setObjectName("btnGreen")
        ok.setMinimumHeight(52)
        ok.setMinimumWidth(220)
        ok.setCursor(Qt.PointingHandCursor)
        ok.setDefault(True)
        glow(ok, "#1fd16a", 18)
        ok.clicked.connect(self._ok)
        v.addLayout(_center_row(ok))
        self._update()

    def _update(self, *_a):
        if self.combo is None:
            return
        on = self.check.isChecked()
        self.combo.setEnabled(on)
        if on:
            nxt = add_schedule(datetime.now(), self.combo.currentData() or "daily")
            self.next_lbl.setText(self._tr(M.SD_NEXT, date=nxt.strftime("%Y-%m-%d %H:%M")))
        else:
            self.next_lbl.setText(self._tr(M.SD_OFF))

    def _ok(self):
        if self.combo is not None:
            self.schedule = self.combo.currentData() or "daily"
            self.enabled = self.check.isChecked()
        self.changed = True
        self.accept()


# ----------------------------------------------------------------------
class PlaylistSetupDialog(GlassDialog):
    """Asked before a NEW playlist is downloaded: own folder? add to sync (daily / weekly / monthly)?
    After exec() == Accepted: .create_folder, .sync (bool), .schedule ('daily' | 'weekly' | 'monthly')."""

    def __init__(self, lang: LanguageManager, title: str, thumb: bytes | None, count: int, parent=None,
                 create_folder: bool = True):
        super().__init__(parent, (780, 600), QColor(70, 200, 255),
                         QColor(40, 110, 170, 240), QColor(12, 44, 112, 248))
        tr = self._tr = lang.tr
        self.create_folder, self.sync, self.schedule, self.ok = True, False, "daily", False
        v = QVBoxLayout(self)
        v.setContentsMargins(48, 32, 48, 34)
        v.setSpacing(14)
        head = QLabel(tr(M.PS_TITLE))
        head.setObjectName("dlgTitle")
        head.setAlignment(Qt.AlignCenter)
        v.addWidget(head)

        pill = QFrame()
        pill.setObjectName("infoBox")
        pl = QHBoxLayout(pill)
        pl.setContentsMargins(12, 10, 16, 10)
        pl.setSpacing(14)
        pic = QLabel()
        pm = QPixmap()
        pic.setPixmap(rounded_pixmap(pm, 128, 72, 8) if thumb and pm.loadFromData(thumb)
                      else make_thumb("#0a1a4a", "#1c4fa8", 128, 72))
        name = ElidedLabel(title)
        name.setObjectName("infoVal")
        cnt = QLabel(tr(M.ND_PLAYLIST, count=count))
        cnt.setObjectName("infoKey")
        col = QVBoxLayout()
        col.addWidget(name)
        col.addWidget(cnt)
        pl.addWidget(pic)
        pl.addLayout(col, 1)
        v.addWidget(pill)

        self.c_folder = QCheckBox(tr(M.PS_FOLDER))
        self.c_folder.setObjectName("dontShow")
        self.c_folder.setChecked(create_folder)
        v.addWidget(self.c_folder)
        self.c_sync = QCheckBox(tr(M.PS_SYNC))
        self.c_sync.setObjectName("dontShow")
        self.c_sync.toggled.connect(self._sync_toggled)
        v.addWidget(self.c_sync)

        self.sched_box = QWidget()                              # appears only when 'sync' is ticked
        sl = QVBoxLayout(self.sched_box)
        sl.setContentsMargins(34, 0, 0, 0)
        sl.setSpacing(6)
        lab = QLabel(tr(M.PS_SCHEDULE))
        lab.setObjectName("infoKey")
        self.combo = ArrowComboBox()
        for key, msg in (("daily", M.PS_DAILY), ("weekly", M.PS_WEEKLY), ("monthly", M.PS_MONTHLY), ("yearly", M.PS_YEARLY)):
            self.combo.addItem(tr(msg), key)
        self.combo.setMinimumHeight(46)
        self.combo.currentIndexChanged.connect(self._update_next)
        self.next_lbl = QLabel("")
        self.next_lbl.setObjectName("syncInfo")
        sl.addWidget(lab)
        sl.addWidget(self.combo)
        sl.addWidget(self.next_lbl)
        self.sched_box.setVisible(False)
        v.addWidget(self.sched_box)
        v.addStretch(1)

        row = QHBoxLayout()
        row.setSpacing(16)
        go = QPushButton("  " + tr(M.BTN_START))
        go.setObjectName("btnGreen")
        go.setIcon(make_play_icon(22))
        go.setDefault(True)
        cancel = QPushButton(tr(M.BTN_CANCEL1))
        cancel.setObjectName("btnRed")
        for b, col_ in ((go, "#1fd16a"), (cancel, "#ff2f72")):
            b.setMinimumHeight(54)
            b.setCursor(Qt.PointingHandCursor)
            glow(b, col_, 18)
            row.addWidget(b, 1)
        go.clicked.connect(self._ok)
        cancel.clicked.connect(self.reject)
        v.addLayout(row)
        self._update_next()

    def _sync_toggled(self, on: bool):
        self.sched_box.setVisible(on)

    def _update_next(self):
        nxt = add_schedule(datetime.now(), self.combo.currentData() or "daily")
        self.next_lbl.setText(self._tr(M.PS_NEXT, date=nxt.strftime("%Y-%m-%d")))

    def _ok(self):
        self.create_folder = self.c_folder.isChecked()
        self.sync = self.c_sync.isChecked()
        self.schedule = self.combo.currentData() or "daily"
        self.ok = True
        self.accept()


# ----------------------------------------------------------------------
class SyncPanel(QWidget):
    """2.3.2: the content of the sync window (header, list of new / previous videos, summary, the four buttons) as a widget,
    so it can sit in the 'Sync all' window as well as in the single sync window.
    chosen(action): 'sync' | 'download' | 'skip' | 'later'.  After the signal: .selected, .redownload."""
    chosen = Signal(str)

    def __init__(self, lang: LanguageManager, new: list, old: list, thumbs: dict, on_play=None, on_reveal=None, available=None):
        super().__init__()
        tr = self._tr = lang.tr
        self.selected, self.redownload = [], False
        self.checks: dict[str, QCheckBox] = {}
        self._new_ids = {n["id"] for n in new}
        avail = None if available is None else set(available)      # ids that are still in the online playlist
        self._need_ids = [n["id"] for n in new] + [o["id"] for o in old if o.get("kind") in ("skipped", "missing")
                                                   and (avail is None or o["id"] in avail)]
        self._thumbs, self._on_play, self._on_reveal = thumbs, on_play, on_reveal
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(10)

        head = QFrame()
        head.setObjectName("syncHead")
        hl = QHBoxLayout(head)
        hl.setContentsMargins(16, 8, 16, 8)
        warn = QLabel()
        warn.setPixmap(make_warning_icon(40))
        txt = tr(M.SY_NEW_FOUND, n=len(new)) if new else tr(M.SY_UPTODATE)
        ht = QLabel(f'<span style="color:#27d3ff">{tr(M.SY_HEADER)}</span> '
                    f'<span style="color:#ffb02e">{txt}</span>')
        ht.setObjectName("syncHeadText")
        hl.addStretch(1)
        hl.addWidget(warn)
        hl.addWidget(ht)
        hl.addStretch(1)
        v.addWidget(head)

        frame = QFrame()
        frame.setObjectName("syncList")
        fl = QVBoxLayout(frame)
        fl.setContentsMargins(6, 6, 6, 6)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        body = QWidget()
        body.setStyleSheet("background: transparent;")
        bl = QVBoxLayout(body)
        bl.setContentsMargins(8, 4, 8, 4)
        bl.setSpacing(8)
        if new:
            bl.addWidget(self._section(tr(M.SY_NEW)))
            for n in new:
                bl.addWidget(self._row(n, True))
        for kind, sec in (("skipped", M.SY_SEC_SKIPPED), ("missing", M.SY_SEC_MISSING), ("have", M.SY_PREV)):
            rows = [o for o in old if o.get("kind", "have") == kind]
            if rows:
                bl.addWidget(self._section(tr(sec)))
                for o in rows:
                    bl.addWidget(self._row(o, False))
        bl.addStretch(1)
        scroll.setWidget(body)
        fl.addWidget(scroll)
        v.addWidget(frame, 1)

        have = sum(1 for o in old if o.get("kind", "have") in ("have", "missing", "skipped"))
        summ = QLabel(tr(M.SY_SUMMARY, total=len(new) + have,
                         new=len(new), skipped=sum(1 for o in old if o.get("kind") == "skipped"),
                         missing=sum(1 for o in old if o.get("kind") == "missing")))
        summ.setObjectName("syncInfo")
        summ.setAlignment(Qt.AlignCenter)
        v.addWidget(summ)
        row = QHBoxLayout()
        row.setSpacing(16)
        self.b_sync = QPushButton()
        self.b_sync.setObjectName("btnGreen")
        self.b_sync.setIcon(make_sync_icon(22))
        self.b_go = QPushButton()
        self.b_go.setObjectName("btnBlue")
        self.b_go.setIcon(make_arrow_icon(22))
        b_skip = QPushButton(tr(M.SY_SKIP))
        b_skip.setObjectName("btnOrange")
        b_later = QPushButton(tr(M.SY_LATER))
        b_later.setObjectName("btnRed")
        for b, c in ((self.b_sync, "#1fd16a"), (self.b_go, "#2b8cff"), (b_skip, "#ffa800"), (b_later, "#ff2f72")):
            b.setMinimumHeight(54)
            b.setCursor(Qt.PointingHandCursor)
            glow(b, c, 18)
            row.addWidget(b, 1)
        b_skip.setEnabled(bool(new))
        self.b_sync.setText("  " + mnemonic_safe(tr(M.SY_SYNC, n=len(self._need_ids))))
        self.b_sync.setEnabled(bool(self._need_ids))
        self.b_sync.clicked.connect(lambda: self._pick("sync"))
        self.b_go.clicked.connect(lambda: self._pick("download"))
        b_skip.clicked.connect(lambda: self._pick("skip"))
        b_later.clicked.connect(lambda: self.chosen.emit("later"))
        v.addLayout(row)
        self._count()

    def _section(self, text: str) -> QLabel:
        lb = QLabel(text)
        lb.setObjectName("syncSection")
        return lb

    def _thumb(self, vid: str, is_new: bool) -> QWidget:
        holder = QWidget()
        g = QGridLayout(holder)
        g.setContentsMargins(0, 0, 0, 0)
        pic = QLabel()
        pm = QPixmap()
        data = self._thumbs.get(vid)
        pic.setPixmap(rounded_pixmap(pm, 150, 84, 8) if data and pm.loadFromData(data)
                      else make_thumb("#0a1a4a", "#1c4fa8", 150, 84))
        pic.setFixedSize(150, 84)
        g.addWidget(pic, 0, 0)
        if is_new:
            badge = QLabel(self._tr(M.SY_BADGE_NEW))
            badge.setObjectName("newBadge")
            g.addWidget(badge, 0, 0, Qt.AlignTop | Qt.AlignLeft)
        return holder

    def _row(self, item: dict, is_new: bool) -> QFrame:
        tr = self._tr
        fr = QFrame()
        fr.setObjectName("syncRow")
        h = QHBoxLayout(fr)
        h.setContentsMargins(10, 8, 12, 8)
        h.setSpacing(12)
        chk = QCheckBox()
        chk.setObjectName("rowCheck")
        chk.setChecked(is_new)
        chk.toggled.connect(self._count)
        self.checks[item["id"]] = chk
        h.addWidget(chk)
        h.addWidget(self._thumb(item["id"], is_new))
        col = QVBoxLayout()
        col.setSpacing(4)
        name = ElidedLabel(item.get("title", ""))
        name.setObjectName("syncTitle")
        col.addWidget(name)
        if is_new:
            d = item.get("duration")
            info = QLabel(tr(M.SY_DUR, d=fmt_time(d)) if d else "")
            info.setObjectName("syncInfo")
            col.addWidget(info)
            h.addLayout(col, 1)
        else:
            kind = item.get("kind", "have")
            badge = QLabel(tr({"skipped": M.SY_BADGE_SKIPPED, "missing": M.SY_BADGE_MISSING}.get(kind, M.SY_PREV_BADGE)))
            badge.setObjectName("prevBadge")
            col.addWidget(badge, 0, Qt.AlignLeft)
            h.addLayout(col, 1)
            det = QVBoxLayout()
            det.setSpacing(2)
            for t in (() if kind == "skipped" else
                      (tr(M.SY_DOWNLOADED, date=(item.get("date") or "")[:10]), f"{tr(M.OK_SIZE)} {fmt_size(item.get('size'))}")):
                lb = QLabel(t)
                lb.setObjectName("syncInfo")
                det.addWidget(lb)
            h.addLayout(det)
            path = item.get("path", "")
            for obj, icon, tip, fn in (
                    ("yelBtn", make_folder_icon(18), M.TIP_FOLDER, lambda _=False, p=path: self._on_reveal and self._on_reveal(p)),
                    ("bluBtn", make_play_icon(16), M.TIP_PLAY, lambda _=False, p=path: self._on_play and self._on_play(p)),
                    ("grnBtn", make_sync_icon(18), M.TIP_REDOWNLOAD, lambda _=False, c=chk: c.setChecked(not c.isChecked()))):
                b = QPushButton()
                b.setObjectName(obj)
                b.setIcon(icon)
                b.setIconSize(QSize(icon.width(), icon.height()))
                b.setToolTip(tr(tip))
                b.setCursor(Qt.PointingHandCursor)
                b.setFixedSize(34, 32)
                b.clicked.connect(fn)
                h.addWidget(b)
        return fr

    def _count(self, *_):
        n = sum(1 for c in self.checks.values() if c.isChecked())
        self.b_go.setText("  " + mnemonic_safe(self._tr(M.SY_SELECTED, n=n)))
        self.b_go.setEnabled(n > 0)

    def _pick(self, action: str):
        self.selected = list(self._need_ids) if action == "sync" else [i for i, c in self.checks.items() if c.isChecked()]
        self.redownload = any(i not in self._new_ids for i in self.selected)
        self.chosen.emit(action)



# ----------------------------------------------------------------------
class SyncDialog(GlassDialog):
    """'Playlist Sync Manager' window: new videos (ticked) + previously downloaded videos (not ticked).
    new = [{id, title, duration}]   old = [{id, title, date, size, file, path}]   thumbs = {id: bytes}
    2.2.7: every video of the playlist is listed - new, skipped before, downloaded but missing from the folder, and the
    ones that are in the folder (an item of `old` may carry kind = 'skipped' | 'missing' | 'have').
    Buttons: Sync (everything that is not in the folder), Download selected (the ticked ones), Skip New, Later.
    After exec(): .action = 'sync' | 'download' | 'skip' | None (later),  .selected = ids to download,
    .redownload = True when at least one of them is not a new video."""

    def __init__(self, lang: LanguageManager, title: str, new: list, old: list, thumbs: dict,
                 on_play=None, on_reveal=None, parent=None, available=None):
        super().__init__(parent, (900, 660), QColor(70, 200, 255),
                         QColor(40, 110, 170, 240), QColor(12, 44, 112, 248))
        tr = lang.tr
        self.action, self.selected, self.redownload = None, [], False
        v = QVBoxLayout(self)
        v.setContentsMargins(36, 24, 36, 30)
        v.setSpacing(10)

        top = QHBoxLayout()
        small = QLabel()
        small.setPixmap(make_app_icon(28))
        cap = ElidedLabel(f"{tr(M.APP_NAME)}  -  {title}")
        cap.setStyleSheet("font-size: 18px; color: #eaf4ff;")
        top.addWidget(small)
        top.addWidget(cap, 1)
        v.addLayout(top)
        self.panel = SyncPanel(lang, new, old, thumbs, on_play, on_reveal, available)
        self.checks, self.b_sync, self.b_go = self.panel.checks, self.panel.b_sync, self.panel.b_go
        self.panel.chosen.connect(self._done)
        v.addWidget(self.panel, 1)

    def _done(self, action: str):
        if action == "later":
            self.reject()
            return
        self.action = action
        self.selected, self.redownload = self.panel.selected, self.panel.redownload
        self.accept()


# ----------------------------------------------------------------------
class SyncAllDialog(GlassDialog):
    """2.3.2: ONE window for 'Sync all'. Top: progress bar (playlist i of n). Middle: the picture of the playlist (left) and
    its information (right). Bottom: the work area with what the single sync window used to show - the list of new videos
    (SyncPanel) or the 'nothing new' message. The controller drives it: set_progress / show_checking / set_content / show_message / finish."""

    def __init__(self, lang: LanguageManager, total: int, parent=None):
        super().__init__(parent, (1000, 760), QColor(70, 200, 255), QColor(40, 110, 170, 240), QColor(12, 44, 112, 248))
        self._tr = tr = lang.tr
        self.cancelled = False
        self._finished = False
        self._total = max(1, total)
        v = QVBoxLayout(self)
        v.setContentsMargins(34, 22, 34, 26)
        v.setSpacing(10)
        top = QHBoxLayout()
        small = QLabel()
        small.setPixmap(make_app_icon(28))
        cap = ElidedLabel(f"{tr(M.APP_NAME)}  -  {tr(M.SYP_ALL)}")
        cap.setStyleSheet("font-size: 18px; color: #eaf4ff;")
        top.addWidget(small)
        top.addWidget(cap, 1)
        v.addLayout(top)

        self.progress_text = QLabel("")
        self.progress_text.setObjectName("syncInfo")
        self.progress_text.setAlignment(Qt.AlignCenter)
        v.addWidget(self.progress_text)
        self.bar = QProgressBar()
        self.bar.setRange(0, self._total * 10)
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(16)
        self.bar.setStyleSheet("QProgressBar { background: rgba(5,40,110,170); border: 1px solid rgba(120,200,255,120); border-radius: 8px; }"
                               "QProgressBar::chunk { border-radius: 7px; background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
                               "stop:0 #ff4d6d, stop:0.35 #ffa800, stop:0.65 #e8e830, stop:1 #1fd16a); }")
        v.addWidget(self.bar)

        mid = QHBoxLayout()
        mid.setSpacing(18)
        self.pic = QLabel()
        self.pic.setFixedSize(240, 135)
        self.pic.setAlignment(Qt.AlignCenter)
        mid.addWidget(self.pic)
        box = QFrame()
        box.setObjectName("infoBox")
        self._info_lay = QVBoxLayout(box)
        self._info_lay.setContentsMargins(18, 10, 18, 10)
        self._info_lay.setSpacing(4)
        mid.addWidget(box, 1)
        v.addLayout(mid)

        self.area = QFrame()
        self.area.setObjectName("syncList")
        self._area_lay = QVBoxLayout(self.area)
        self._area_lay.setContentsMargins(10, 10, 10, 10)
        v.addWidget(self.area, 1)
        self._content = None

        self.b_stop = QPushButton(tr(M.BTN_CANCEL1))
        self.b_stop.setObjectName("btnRed")
        self.b_stop.setMinimumHeight(46)
        self.b_stop.setMinimumWidth(200)
        self.b_stop.setCursor(Qt.PointingHandCursor)
        self.b_stop.clicked.connect(self._stop)
        v.addLayout(_center_row(self.b_stop))

    def set_progress(self, i: int, n: int, done_part: int = 0):
        """i-th playlist of n is being handled (done_part 0 = checking, 10 = finished)."""
        self._total = max(1, n)
        self.bar.setRange(0, self._total * 10)
        self.bar.setValue(max(0, (i - 1) * 10 + done_part))
        self.progress_text.setText(self._tr(M.BZ_PROGRESS, i=i, n=n))

    def show_checking(self, pixmap, lines: list):
        pm = QPixmap()
        self.pic.setPixmap(rounded_pixmap(pixmap, 240, 135, 10) if pixmap is not None and not pixmap.isNull()
                           else make_thumb("#0a1a4a", "#1c4fa8", 240, 135))
        while self._info_lay.count():
            w = self._info_lay.takeAt(0).widget()
            if w:
                w.deleteLater()
        for line in lines:
            lab = ElidedLabel(line)
            lab.setObjectName("infoVal")
            self._info_lay.addWidget(lab)
        self.show_message("", self._tr(M.SY_CHECKING))

    def set_content(self, widget: QWidget):
        if self._content is not None:
            self._area_lay.removeWidget(self._content)
            self._content.deleteLater()
        self._content = widget
        self._area_lay.addWidget(widget, 1)

    def show_message(self, title: str, text: str, lines: list | None = None):
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        l = QVBoxLayout(w)
        l.setSpacing(10)
        l.addStretch(1)
        if title:
            head = QLabel(title)
            head.setObjectName("dlgTitle")
            head.setAlignment(Qt.AlignCenter)
            l.addWidget(head)
        body = QLabel(text)
        body.setObjectName("dlgText")
        body.setAlignment(Qt.AlignCenter)
        body.setWordWrap(True)
        l.addWidget(body)
        for line in lines or []:
            lab = QLabel(line)
            lab.setObjectName("infoKey")
            lab.setAlignment(Qt.AlignCenter)
            l.addWidget(lab)
        l.addStretch(1)
        self.set_content(w)

    def finish(self, text: str):
        """All playlists done: the summary stays in the work area, the button becomes OK."""
        self._finished = True
        self.bar.setValue(self.bar.maximum())
        self.show_message(self._tr(M.SYP_ALL), text)
        self.b_stop.setText(self._tr(M.BTN_OK))
        self.b_stop.setObjectName("btnGreen")
        self.b_stop.setStyle(self.b_stop.style())

    def _stop(self):
        self.cancelled = not self._finished
        self.accept()


# ----------------------------------------------------------------------
class DetailsDialog(GlassDialog):
    """'Details' of a video (Archive / Library): picture, facts and the description that was saved with it.
    For a playlist the description box lists its videos."""

    def __init__(self, lang: LanguageManager, rec: dict, pixmap=None, category: str = "", parent=None):
        super().__init__(parent, (820, 620), QColor(120, 200, 255), QColor(46, 100, 200, 238), QColor(12, 30, 92, 246))
        tr = lang.tr
        v = QVBoxLayout(self)
        v.setContentsMargins(38, 32, 38, 28)
        v.setSpacing(12)
        top = QHBoxLayout()
        top.setSpacing(16)
        pic = QLabel()
        pic.setFixedSize(224, 126)
        if pixmap is not None and not pixmap.isNull():
            pic.setPixmap(rounded_pixmap(pixmap, 224, 126, 10))
        else:
            pic.setPixmap(make_thumb("#0a1a4a", "#1c4fa8", 224, 126))
        top.addWidget(pic)
        col = QVBoxLayout()
        col.setSpacing(4)
        title = QLabel(rec.get("title") or rec.get("file_name", ""))
        title.setObjectName("dlgText")
        title.setWordWrap(True)
        col.addWidget(title)
        facts = [(tr(M.DET_DATE), rec.get("date", "")),
                 (tr(M.DET_FORMAT), "  ".join(x for x in (rec.get("format", ""), rec.get("quality", "")) if x)),
                 (tr(M.DET_SIZE), fmt_size(rec.get("size", 0)) +
                  (f"  ·  {tr(M.DL_FILES, count=rec.get('count', 1))}" if rec.get("is_playlist") else ""))]
        if rec.get("duration") and not rec.get("is_playlist"):
            facts.append((tr(M.DET_DURATION), fmt_time(rec["duration"])))
        if category:
            facts.append((tr(M.DET_CATEGORY), category))
        for k, val in facts:
            lb = QLabel(f"<span style='color:#bcd4f2'>{k}:</span>  {val}")
            lb.setObjectName("syncInfo")
            lb.setTextFormat(Qt.RichText)
            col.addWidget(lb)
        col.addStretch(1)
        top.addLayout(col, 1)
        v.addLayout(top)
        # the folder and the web address are links: the folder opens in the file manager, the address in the browser
        fm = QFontMetrics(self.font())
        for key, val, kind in ((tr(M.DET_FOLDER), rec.get("save_dir", ""), "folder"), (tr(M.DET_LINK), rec.get("url", ""), "web")):
            if not val:
                continue
            href = QUrl.fromLocalFile(os.path.expanduser(val)).toString() if kind == "folder" else val
            shown = html.escape(fm.elidedText(val, Qt.ElideMiddle, 700))
            lb = QLabel(f"<span style='color:#bcd4f2'>{key}:</span>  "
                        f"<a href='{html.escape(href, quote=True)}' style='color:#7fd0ff'>{shown}</a>")
            lb.setObjectName("syncInfo")
            lb.setTextFormat(Qt.RichText)
            lb.setCursor(Qt.PointingHandCursor)
            lb.setToolTip(val)
            lb.linkActivated.connect(lambda link: QDesktopServices.openUrl(QUrl(link)))
            v.addWidget(lb)
        head = QLabel(tr(M.DET_VIDEOS if rec.get("is_playlist") else M.DET_DESC))
        head.setObjectName("syncSection")
        v.addWidget(head)
        box = QTextBrowser()                                  # links of the description can be clicked
        box.setObjectName("feedback")
        box.setOpenExternalLinks(True)
        if rec.get("is_playlist"):
            vids = [x.get("title", "") for x in (rec.get("videos") or {}).values() if x.get("state") == "downloaded"]
            text = "\n".join(f"{i}.  {name}" for i, name in enumerate(vids, 1))
        else:
            text = rec.get("description") or ""
        box.setHtml(description_html(text) if text else html.escape(tr(M.DET_NO_DESC)))
        v.addWidget(box, 1)
        close = QPushButton(tr(M.DLQ_CLOSE))
        close.setObjectName("btnBlue")
        close.setMinimumHeight(46)
        close.setCursor(Qt.PointingHandCursor)
        close.clicked.connect(self.accept)
        glow(close, "#2b8cff", 18)
        v.addWidget(close)
