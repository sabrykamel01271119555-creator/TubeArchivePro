# =============================================================================
# TubeArchive Pro  |  Version 2.2.7  |  File: app/ui/widgets.py
# Version history of this file:
#   2.2.7 - ChannelBanner (clickable channel banner of the side menu); ad pictures always fill the ad frame
#   2.2.6 - NavButton: every menu item is a glass plate (idle / hover / active) like the design picture
#   2.0.5 - WinButton.sync_hover(): title-bar buttons forget a stale hover after the window is resized
#   2.0.4 - mnemonic_safe(): '&' in button texts is shown (Apply & Save, Skip & Exit, Submit & Exit, Download & Sync)
#   2.0.3 - MorphStack: soft fade-in of the real page (no picture of the page, no white flash); gauge titles under the gauges
#   2.0.2 - MiniGauge: measuring scale (ticks, needle, numbers at both ends); SpeedGauge shows 0 and the maximum;
#           colours of NavButton / ToggleSwitch back to 1.0.14
#   2.0.1 - AdBanner(fit=True): the partner ad is shrunk / stretched to show the whole picture in the frame;
#           ToggleSwitch(green=True); gauges: bright glass colours
#   1.0.14 - ToggleSwitch
#   1.0.12 - New MiniGauge; AdBanner.set_paths (ads list can change while running); language kind of WinButton
#   1.0.10 - New ArrowComboBox (visible drop-down arrow), MorphStack (blur + grow-from-centre page change)
#   1.0.8 - New ElidedLabel (long titles end with '...')
#   1.0.7 - AdBanner: new align_left option (crops the right side so the banner text stays visible)
#   1.0.6 - SpeedGauge / RingGauge / Sparkline are drawn relative to their size (no more overlapping)
#   1.0.6 - NavButton gets set_scale() and shrinks long text to fit
#   1.0.0 - 1.0.5 - first version and earlier fixes (see CHANGELOG.md)
# =============================================================================
"""Reusable custom-painted widgets."""
import math
import random
from collections import deque

from PySide6.QtCore import (QEasingCurve, QPointF, QRect, QRectF, QSize, Qt, QTimer,
                            QUrl, QVariantAnimation, Signal)
from PySide6.QtGui import (QColor, QDesktopServices, QFont, QFontMetrics, QLinearGradient, QMovie, QPainter,
                           QPainterPath, QPen, QPixmap)
from PySide6.QtWidgets import (QAbstractButton, QComboBox, QFrame, QGraphicsOpacityEffect, QHBoxLayout, QLabel,
                               QProgressBar, QSizePolicy, QStackedWidget, QStyle, QVBoxLayout,
                               QWidget)

from .icons import draw_nav_icon, make_app_icon, make_globe_icon


def mnemonic_safe(text: str) -> str:
    """Qt buttons treat a single '&' as a keyboard-shortcut mark and hide it ('Apply & Save' -> 'Apply  Save').
    Every button text that may contain '&' goes through here: '&' -> '&&'."""
    return (text or "").replace("&", "&&")


def _font(px: int, bold=False) -> QFont:
    f = QFont("Segoe UI")
    f.setPixelSize(px)
    f.setBold(bold)
    return f


# ----------------------------------------------------------------------
class FontScaler:
    """Mixin for the pages of the work area: the texts follow the size of the page (width AND height), so
    nothing is cut or tiny when the window is resized. Put it before QWidget:  class MyPage(FontScaler, QWidget)."""
    FS_BASE = (660.0, 520.0)           # size of the work area at the design size of the window (1180 x 740)
    _fs_scale = 0.0

    def apply_font_scale(self):
        from .theme import area_scale, font_qss
        s = area_scale(self.width(), self.height(), *self.FS_BASE)
        if s != self._fs_scale:
            self._fs_scale = s
            self.setStyleSheet(font_qss(s))
            self.on_font_scale(s)

    def on_font_scale(self, s: float):
        """Pages override this to scale fixed sizes (pictures, buttons, margins)."""

    def resizeEvent(self, e):
        self.apply_font_scale()
        super().resizeEvent(e)


class WinButton(QWidget):
    """Minimise / maximise / close button drawn by hand."""
    clicked = Signal()

    def __init__(self, kind: str):
        super().__init__()
        self.kind = kind
        self.hover = False
        self.setFixedSize(46, 34)
        self.setCursor(Qt.PointingHandCursor)

    def enterEvent(self, e):
        self.hover = True
        self.update()

    def leaveEvent(self, e):
        self.hover = False
        self.update()

    def sync_hover(self):
        """After the window was resized the mouse may be elsewhere without a leave event: look at the real position."""
        from PySide6.QtGui import QCursor
        now = self.isVisible() and self.rect().contains(self.mapFromGlobal(QCursor.pos()))
        if now != self.hover:
            self.hover = now
            self.update()

    def mousePressEvent(self, e):
        # Accept the press so it does not reach the title bar (which would start
        # moving the window and swallow the click).
        e.accept()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton and self.rect().contains(e.position().toPoint()):
            self.clicked.emit()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        if self.hover:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(232, 17, 35, 210) if self.kind == "close" else QColor(255, 255, 255, 40))
            p.drawRoundedRect(self.rect().adjusted(4, 2, -4, -2), 6, 6)
        p.setPen(QPen(QColor("#c4dcf8"), 1.6))
        c = QPointF(self.width() / 2, self.height() / 2)
        if self.kind == "lang":
            p.drawPixmap(int(c.x() - 11), int(c.y() - 11), make_globe_icon(22, "#e6f1ff"))
        elif self.kind == "min":
            p.drawLine(QPointF(c.x() - 6, c.y()), QPointF(c.x() + 6, c.y()))
        elif self.kind == "max":
            p.drawRect(QRectF(c.x() - 6, c.y() - 6, 12, 12))
        else:
            p.drawLine(QPointF(c.x() - 6, c.y() - 6), QPointF(c.x() + 6, c.y() + 6))
            p.drawLine(QPointF(c.x() - 6, c.y() + 6), QPointF(c.x() + 6, c.y() - 6))


# ----------------------------------------------------------------------
class NavButton(QWidget):
    clicked = Signal()

    def __init__(self, kind: str, text: str):
        super().__init__()
        self.kind, self.text, self.active, self.hover = kind, text, False, False
        self.s = 1.0                      # scale factor (changes with the window size)
        self.setFixedHeight(54)
        self.setCursor(Qt.PointingHandCursor)

    def set_scale(self, s: float):
        self.s = s
        self.setFixedHeight(int(54 * s))
        self.update()

    def set_active(self, on: bool):
        self.active = on
        self.update()

    def set_text(self, t: str):
        self.text = t
        self.update()

    def enterEvent(self, e):
        self.hover = True
        self.update()

    def leaveEvent(self, e):
        self.hover = False
        self.update()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton and self.rect().contains(e.position().toPoint()):
            self.clicked.emit()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        d, s, h = self.layoutDirection(), self.s, self.height()
        # every item is a glass plate (like the design picture): quiet when idle, brighter on hover, glowing when active
        body = QRectF(QStyle.visualRect(d, self.rect(), self.rect().adjusted(10, 3, -4, -3)))
        g = QLinearGradient(body.topLeft(), body.bottomRight())
        if self.active:
            g.setColorAt(0, QColor(80, 150, 235, 170))
            g.setColorAt(1, QColor(35, 95, 190, 140))
            border = QPen(QColor(120, 215, 255, 230), 1.6)
        elif self.hover:
            g.setColorAt(0, QColor(60, 120, 205, 120))
            g.setColorAt(1, QColor(30, 80, 170, 90))
            border = QPen(QColor(110, 200, 255, 140), 1.3)
        else:
            g.setColorAt(0, QColor(35, 75, 150, 80))
            g.setColorAt(1, QColor(15, 45, 110, 60))
            border = QPen(QColor(110, 170, 255, 55), 1.0)
        p.setBrush(g)
        p.setPen(border)
        p.drawRoundedRect(body, 14, 14)
        if self.active:   # bright accent bar on the leading edge, flush with the side panel
            m = int(8 * s)
            bar = QStyle.visualRect(d, self.rect(), QRect(0, m, 5, h - 2 * m))
            p.setPen(Qt.NoPen)
            p.setBrush(QColor("#27d3ff"))
            p.drawRoundedRect(QRectF(bar), 2.5, 2.5)
        color = QColor("#ffffff") if self.active else QColor("#c4dcf8")
        isz = int(28 * s)
        icon_r = QStyle.visualRect(d, self.rect(), QRect(int(20 * s), (h - isz) // 2, isz, isz))
        draw_nav_icon(p, self.kind, QRectF(icon_r), color)
        tx = int(60 * s)
        txt_r = QStyle.visualRect(d, self.rect(), QRect(tx, 0, max(10, self.width() - tx - 10), h))
        px = int(20 * s)                       # shrink the text until it fits the button
        f = _font(px)
        while px > 11 and QFontMetrics(f).horizontalAdvance(self.text) > txt_r.width():
            px -= 1
            f = _font(px)
        p.setFont(f)
        p.setPen(color)
        align = Qt.AlignVCenter | (Qt.AlignRight if d == Qt.RightToLeft else Qt.AlignLeft)
        p.drawText(txt_r, int(align), self.text)


# ----------------------------------------------------------------------
GAUGE_TITLE_PX = 12                      # one font size for the titles of all gauges (the main window scales it)


def draw_gauge_title(p: QPainter, area: QRectF, text: str, px: int) -> float:
    """Draws the title of a gauge at the BOTTOM of `area`, close to the gauge; returns the height it uses."""
    px = max(8, int(px))
    th = px * 1.7
    p.setPen(QColor("#f0f7ff"))
    p.setFont(_font(px, True))
    p.drawText(QRectF(area.left(), area.bottom() - th, area.width(), th), Qt.AlignHCenter | Qt.AlignTop, text)
    return th


class SpeedGauge(QWidget):
    """Semi-circular speedometer (Network ingest). Everything is drawn relative to the
    widget size, so it keeps its proportions when the window is resized."""

    def __init__(self, maximum=200.0, unit="", title: str = ""):
        super().__init__()
        self.maximum, self.value, self.unit = maximum, 0.0, unit
        self.title, self.title_px = title, GAUGE_TITLE_PX
        self.setMinimumSize(80, 80)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_value(self, v: float):
        self.value = v
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        th = draw_gauge_title(p, QRectF(self.rect()), self.title, self.title_px) if self.title else 0.0
        side = min(self.width(), self.height() - th)
        c = QPointF(self.width() / 2, (self.height() - th) / 2)
        r = side / 2 - max(5.0, side * 0.06)
        k = max(r / 95.0, 0.3)                     # scale vs. the reference design
        rect = QRectF(c.x() - r, c.y() - r, 2 * r, 2 * r)
        frac = max(0.0, min(1.0, self.value / self.maximum))
        p.setPen(QPen(QColor(20, 70, 140, 170), 10 * k, Qt.SolidLine, Qt.RoundCap))
        p.drawArc(rect, 225 * 16, -270 * 16)
        for w, a in ((18, 40), (10, 255)):
            p.setPen(QPen(QColor(39, 211, 255, a), w * k, Qt.SolidLine, Qt.RoundCap))
            p.drawArc(rect, 225 * 16, int(-270 * 16 * frac))
        for i in range(31):     # ticks
            a = math.radians(225 - 270 * i / 30)
            long = i % 5 == 0
            r1, r2 = r - 20 * k, r - (30 if long else 25) * k
            col = QColor("#ff7a4d") if i / 30 > 0.82 else QColor(190, 225, 255, 190)
            p.setPen(QPen(col, (2 if long else 1) * max(k, 0.6)))
            p.drawLine(QPointF(c.x() + r1 * math.cos(a), c.y() - r1 * math.sin(a)),
                       QPointF(c.x() + r2 * math.cos(a), c.y() - r2 * math.sin(a)))
        a = math.radians(225 - 270 * frac)
        p.setPen(QPen(QColor("#27d3ff"), max(2.0, 3 * k), Qt.SolidLine, Qt.RoundCap))
        p.drawLine(QPointF(c.x() + 38 * k * math.cos(a), c.y() - 38 * k * math.sin(a)),
                   QPointF(c.x() + (r - 28 * k) * math.cos(a), c.y() - (r - 28 * k) * math.sin(a)))
        p.setPen(QColor("white"))
        p.setFont(_font(max(9, int(38 * k)), True))
        p.drawText(QRectF(c.x() - 70 * k, c.y() - 8 * k, 140 * k, 46 * k), Qt.AlignCenter, f"{self.value:.1f}")
        p.setPen(QColor("#6fb6ff"))
        p.setFont(_font(max(8, int(18 * k))))
        p.drawText(QRectF(c.x() - 70 * k, c.y() + 34 * k, 140 * k, 26 * k), Qt.AlignCenter, self.unit)
        p.setPen(QColor("#cfe6ff"))
        p.setFont(_font(max(7, int(14 * k))))
        mx = f"{self.maximum:g}"
        p.drawText(QRectF(c.x() - r * 0.95, c.y() + r * 0.70, r * 0.9, 20 * k), Qt.AlignLeft | Qt.AlignVCenter, "0")
        p.drawText(QRectF(c.x() + r * 0.05, c.y() + r * 0.70, r * 0.9, 20 * k), Qt.AlignRight | Qt.AlignVCenter, mx)


class RingGauge(QWidget):
    """Circular gauge with animated side bars (Disk write / thread load). Size-relative."""

    def __init__(self, label=""):
        super().__init__()
        self.value, self.label = 0.0, label
        self.bars = [random.random() for _ in range(10)]
        self.setMinimumSize(80, 80)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_value(self, v: float):
        self.value = v
        self.bars = [max(.15, min(1.0, b + random.uniform(-.3, .3))) for b in self.bars]
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        c = QPointF(self.width() / 2, self.height() / 2)
        r = min(self.height() / 2, self.width() * .34) - max(5.0, min(self.width(), self.height()) * 0.04)
        k = max(r / 85.0, 0.3)
        rect = QRectF(c.x() - r, c.y() - r, 2 * r, 2 * r)
        p.setPen(QPen(QColor(20, 70, 140, 170), 12 * k))
        p.drawEllipse(rect)
        for w, a in ((20, 40), (12, 255)):
            p.setPen(QPen(QColor(39, 211, 255, a), w * k, Qt.SolidLine, Qt.RoundCap))
            p.drawArc(rect, 90 * 16, int(-360 * 16 * self.value / 100))
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(4, 20, 70, 210))
        p.drawEllipse(c, r - 12 * k, r - 12 * k)
        p.setPen(QColor("white"))
        p.setFont(_font(max(9, int(34 * k)), True))
        p.drawText(QRectF(c.x() - 60 * k, c.y() - 34 * k, 120 * k, 46 * k), Qt.AlignCenter, f"{self.value:.0f}%")
        p.setFont(_font(max(8, int(16 * k))))
        p.drawText(QRectF(c.x() - 70 * k, c.y() + 10 * k, 140 * k, 26 * k), Qt.AlignCenter, self.label)
        p.setBrush(QColor(39, 211, 255, 200))      # side bars
        for side in (-1, 1):
            for i in range(5):
                bh = 14 * k + 52 * k * self.bars[i + (5 if side > 0 else 0)]
                x = c.x() + side * (r + 12 * k + i * 6 * k)
                p.drawRoundedRect(QRectF(x - 1.5 * k, c.y() - bh / 2, 3 * k, bh), 1.5 * k, 1.5 * k)


class Sparkline(QWidget):
    def __init__(self, points=40):
        super().__init__()
        self.data = deque([0.0] * points, maxlen=points)
        self.setMinimumHeight(60)

    def push(self, v: float):
        self.data.append(v)
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        box = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        p.setPen(QPen(QColor(90, 170, 255, 90), 1))
        p.setBrush(QColor(4, 22, 70, 150))
        p.drawRoundedRect(box, 10, 10)
        inner = box.adjusted(8, 12, -8, -8)
        mx = max(max(self.data), 1.0)
        n = len(self.data)
        pts = [QPointF(inner.left() + inner.width() * i / (n - 1),
                       inner.bottom() - inner.height() * (v / mx) * 0.95)
               for i, v in enumerate(self.data)]
        path = QPainterPath(pts[0])
        for a, b in zip(pts, pts[1:]):
            mid = QPointF((a.x() + b.x()) / 2, (a.y() + b.y()) / 2)
            path.quadTo(a, mid)
        path.lineTo(pts[-1])
        area = QPainterPath(path)
        area.lineTo(inner.right(), inner.bottom())
        area.lineTo(inner.left(), inner.bottom())
        g = QLinearGradient(0, inner.top(), 0, inner.bottom())
        g.setColorAt(0, QColor(39, 211, 255, 90))
        g.setColorAt(1, QColor(39, 211, 255, 0))
        p.setPen(Qt.NoPen)
        p.setBrush(g)
        p.drawPath(area)
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(39, 211, 255, 70), 6, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.drawPath(path)
        p.setPen(QPen(QColor("#5ff3ff"), 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.drawPath(path)


# ----------------------------------------------------------------------
class DownloadItem(QFrame):
    """One row in the downloader list."""

    def __init__(self, title, fmt, quality, total_mb, thumb: QPixmap, active_text):
        super().__init__()
        self.setObjectName("dlItem")
        self.total_mb, self.active_text = total_mb, active_text
        row = QHBoxLayout(self)
        row.setContentsMargins(10, 8, 14, 8)
        row.setSpacing(12)
        pic = QLabel()
        pic.setPixmap(thumb)
        pic.setFixedSize(thumb.size())
        row.addWidget(pic)
        col = QVBoxLayout()
        col.setSpacing(5)
        top = QHBoxLayout()
        top.setSpacing(8)
        self.title = QLabel(title)
        self.title.setObjectName("dlTitle")
        self.title.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.stat = QLabel()
        self.stat.setObjectName("dlStat")
        b1, b2 = QLabel(fmt), QLabel(quality)
        b1.setObjectName("badgeFmt")
        b2.setObjectName("badgeQ")
        top.addWidget(self.title, 1)
        top.addWidget(self.stat)
        top.addWidget(b1)
        if quality:
            top.addWidget(b2)
        self.bar = QProgressBar()
        self.bar.setObjectName("dlBar")
        self.bar.setRange(0, 1000)
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(8)
        self.sub = QLabel()
        self.sub.setObjectName("dlSub")
        col.addLayout(top)
        col.addWidget(self.bar)
        col.addWidget(self.sub)
        row.addLayout(col, 1)

    @staticmethod
    def _size(mb: float) -> str:
        return f"{mb / 1000:.1f} GB" if mb >= 1000 else f"{mb:.0f} MB"

    def set_progress(self, pct: float, speed: float, unit: str):
        self.bar.setValue(int(pct * 10))
        self.stat.setText(f"{pct:.0f}% | {speed:.0f} {unit}")
        done = self.total_mb * pct / 100
        self.sub.setText(f"{self._size(done)} / {self._size(self.total_mb)} | {self.active_text}")


# ----------------------------------------------------------------------
class AdBanner(QFrame):
    """Banner frame used for the owner banner (header) and the partner ads (footer).

    * gif_paths given  -> plays the animated GIFs and rotates between them
    * nothing given    -> paints a placeholder (brand text or 'Advertisement space')
    """

    def __init__(self, placeholder: str, gif_paths=None, rotate_seconds=8,
                 brand: str = "", tagline: str = "", align_left: bool = False, fit: bool = False):
        super().__init__()
        self.fit = fit                    # True: the whole picture is shown (shrunk / stretched to the frame), never cropped
        self.placeholder, self.brand, self.tagline = placeholder, brand, tagline
        self.align_left = align_left      # True: if the picture must be cropped, crop the right side
        self.paths = list(gif_paths or [])
        self.links: dict = {}             # gif path -> web address opened when the ad is clicked
        self.index = -1
        self.movie: QMovie | None = None
        self.still: QPixmap | None = None
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.timer = QTimer(self, interval=max(2, rotate_seconds) * 1000)
        self.timer.timeout.connect(self._next)
        if self.paths:
            self._next()
            if len(self.paths) > 1:
                self.timer.start()

    def current_link(self) -> str:
        return self.links.get(self.paths[self.index], "") if 0 <= self.index < len(self.paths) else ""

    def mouseReleaseEvent(self, e):
        link = self.current_link()
        if link and e.button() == Qt.LeftButton:
            QDesktopServices.openUrl(QUrl(link))
        super().mouseReleaseEvent(e)

    def set_paths(self, paths, links=None):
        """New list of ads (after a refresh from the web): the show goes on in turns while the program runs."""
        paths = list(paths or [])
        self.links = dict(links or {})
        if paths == self.paths:
            self._cursor()
            return
        current = self.paths[self.index] if 0 <= self.index < len(self.paths) else None
        self.paths = paths
        self.timer.stop()
        if not paths:
            self.index = -1
            if self.movie:
                self.movie.stop()
                self.movie.deleteLater()
                self.movie = None
            self.still = None
            self.update()
            return
        self.index = (paths.index(current) - 1) if current in paths else -1
        self._next()
        if len(paths) > 1:
            self.timer.start()

    def _next(self):
        if not self.paths:
            return
        self.index = (self.index + 1) % len(self.paths)
        path = self.paths[self.index]
        if self.movie:
            self.movie.stop()
            self.movie.deleteLater()
            self.movie = None
        self.still = None
        if path.lower().endswith(".gif"):
            self.movie = QMovie(path)
            self.movie.setCacheMode(QMovie.CacheAll)
            self.movie.frameChanged.connect(self.update)
            self.movie.start()
        else:
            self.still = QPixmap(path)
        self._cursor()
        self.update()

    def _cursor(self):
        self.setCursor(Qt.PointingHandCursor if self.current_link() else Qt.ArrowCursor)
        self.setToolTip(self.current_link())

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        box = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        clip = QPainterPath()
        clip.addRoundedRect(box, 12, 12)
        p.setClipPath(clip)
        frame = self.movie.currentPixmap() if self.movie else self.still
        if frame and not frame.isNull() and self.fit:
            g = QLinearGradient(box.topLeft(), box.topRight())          # frame colour around a picture that is not as wide
            g.setColorAt(0, QColor(8, 30, 90))
            g.setColorAt(1, QColor(24, 60, 130))
            p.fillRect(box, g)
            bs = box.size().toSize()
            ratio = (frame.width() / frame.height()) / max(0.01, bs.width() / max(1, bs.height()))
            # 2.2.7: the picture always fills the whole ad frame (stretched or shrunk to its shape)
            scaled = frame.scaled(bs, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
            p.drawPixmap(int(box.x() + (box.width() - scaled.width()) / 2),
                         int(box.y() + (box.height() - scaled.height()) / 2), scaled)
        elif frame and not frame.isNull():
            scaled = frame.scaled(self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            x = 0 if self.align_left else (self.width() - scaled.width()) // 2
            p.drawPixmap(x, (self.height() - scaled.height()) // 2, scaled)
        else:
            g = QLinearGradient(box.topLeft(), box.topRight())
            g.setColorAt(0, QColor(3, 12, 40))
            g.setColorAt(1, QColor(20, 40, 80))
            p.fillRect(box, g)
            if self.brand:     # owner banner placeholder
                self._paint_brand(p, box)
            else:
                p.setPen(QColor(140, 180, 230, 150))
                p.setFont(_font(16))
                p.drawText(box, Qt.AlignCenter, self.placeholder)
        p.setClipping(False)
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(60, 180, 255, 190), 1.6))
        p.drawRoundedRect(box, 12, 12)

    def _paint_brand(self, p: QPainter, box: QRectF):
        # decorative golden rings on the trailing side
        cx = box.right() - box.height() * 0.9
        cy = box.center().y()
        for i, rad in enumerate((box.height() * .95, box.height() * .75, box.height() * .5, box.height() * .22)):
            p.setPen(QPen(QColor(205, 170, 120, 200 - i * 30), 3 if i == 0 else 1.5))
            p.setBrush(QColor(40, 50, 70, 120) if i == 0 else Qt.NoBrush)
            p.drawEllipse(QPointF(cx, cy), rad, rad)
        d = Qt.RightToLeft if self.layoutDirection() == Qt.RightToLeft else Qt.LeftToRight
        text_r = QRectF(box.left() + 24, box.top() + 10, box.width() * 0.55, box.height() - 20)
        p.setPen(QColor("#4fe6ff"))
        p.setFont(_font(int(box.height() * .30), True))
        p.drawText(text_r, int(Qt.AlignLeft | Qt.AlignTop), self.brand)
        p.setPen(QColor("#9fdcf0"))
        p.setFont(_font(int(box.height() * .14)))
        p.drawText(text_r.adjusted(4, box.height() * .36, 0, 0), int(Qt.AlignLeft | Qt.AlignTop), self.tagline)


# ----------------------------------------------------------------------
class ChannelBanner(QWidget):
    """The owner's channel banner (side menu, bottom): the picture fills the width, a click opens the channel address."""

    def __init__(self, path, url: str, tip: str = ""):
        super().__init__()
        self.url = url
        self.pm = QPixmap(str(path))
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(f"{tip}\n{url}" if tip else url)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFixedHeight(40)

    def resizeEvent(self, e):
        if not self.pm.isNull() and self.width() > 0:
            h = max(24, int(self.width() * self.pm.height() / self.pm.width()))
            if h != self.height():
                self.setFixedHeight(h)
        super().resizeEvent(e)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        box = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        clip = QPainterPath()
        clip.addRoundedRect(box, 8, 8)
        p.setClipPath(clip)
        if self.pm.isNull():
            p.fillRect(box, QColor(150, 40, 40))
            p.setPen(QColor("#ffffff"))
            p.drawText(box, Qt.AlignCenter, "Let'sHaveFun")
        else:
            p.drawPixmap(box.toRect(), self.pm)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton and self.rect().contains(e.position().toPoint()):
            QDesktopServices.openUrl(QUrl(self.url))
        super().mouseReleaseEvent(e)


class MiniGauge(QWidget):
    """Small round measuring meter (270 degree arc with a scale of ticks and a needle).
    Title above, value + unit inside, and the numbers of the ends of the scale (`min_text` ... `max_text`)
    below the arc. Everything is drawn relative to the widget size. `fraction` 0..1 fills the arc."""

    def __init__(self, title: str = "", color: str = "#27d3ff"):
        super().__init__()
        self.title, self.color = title, QColor(color)
        self.fraction, self.text, self.unit = 0.0, "0", ""
        self.min_text, self.max_text = "0", ""
        self.title_px = GAUGE_TITLE_PX
        self.setMinimumSize(60, 70)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_state(self, fraction: float, text: str, unit: str = "", max_text: str = "", min_text: str = "0"):
        self.fraction, self.text, self.unit = max(0.0, min(1.0, fraction)), text, unit
        self.max_text, self.min_text = max_text, min_text
        self.update()

    def set_title(self, title: str):
        self.title = title
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        th = draw_gauge_title(p, QRectF(0, 0, w, h), self.title, self.title_px)      # under the gauge, same font everywhere
        side = min(w, h - th)
        r = side / 2 - max(4.0, side * 0.09)
        c = QPointF(w / 2, (h - th) / 2 - side * 0.03)
        k = max(r / 55.0, 0.3)
        rect = QRectF(c.x() - r, c.y() - r, 2 * r, 2 * r)
        p.setPen(QPen(QColor(20, 70, 140, 170), 7 * k, Qt.SolidLine, Qt.RoundCap))
        p.drawArc(rect, 225 * 16, -270 * 16)
        if self.fraction > 0:
            for wd, a in ((11, 45), (6, 255)):
                col = QColor(self.color)
                col.setAlpha(a)
                p.setPen(QPen(col, wd * k, Qt.SolidLine, Qt.RoundCap))
                p.drawArc(rect, 225 * 16, int(-270 * 16 * self.fraction))
        for i in range(21):                                           # the small measuring scale
            ang = math.radians(225 - 270 * i / 20)
            long = i % 5 == 0
            r1, r2 = r - 9 * k, r - (16 if long else 13) * k
            col = QColor(200, 228, 255, 200)
            p.setPen(QPen(col, (1.6 if long else 1.0) * max(k, 0.6)))
            p.drawLine(QPointF(c.x() + r1 * math.cos(ang), c.y() - r1 * math.sin(ang)),
                       QPointF(c.x() + r2 * math.cos(ang), c.y() - r2 * math.sin(ang)))
        ang = math.radians(225 - 270 * self.fraction)                 # needle
        p.setPen(QPen(QColor("#ffffff"), max(1.5, 2.2 * k), Qt.SolidLine, Qt.RoundCap))
        p.drawLine(QPointF(c.x() + 6 * k * math.cos(ang), c.y() - 6 * k * math.sin(ang)),
                   QPointF(c.x() + (r - 19 * k) * math.cos(ang), c.y() - (r - 19 * k) * math.sin(ang)))
        p.setBrush(QColor("#ffffff"))
        p.setPen(Qt.NoPen)
        p.drawEllipse(c, 3 * k, 3 * k)
        p.setPen(QColor("white"))
        p.setFont(_font(max(8, int(19 * k)), True))
        p.drawText(QRectF(c.x() - r, c.y() + 6 * k, 2 * r, 22 * k), Qt.AlignCenter, self.text)
        p.setPen(QColor("#6fb6ff"))
        p.setFont(_font(max(7, int(10 * k))))
        p.drawText(QRectF(c.x() - r, c.y() + 25 * k, 2 * r, 15 * k), Qt.AlignCenter, self.unit)
        # numbers at both ends of the scale
        p.setPen(QColor("#cfe6ff"))
        p.setFont(_font(max(7, int(10 * k))))
        by = c.y() + r * 0.70
        bw = max(30.0, r * 0.95)
        p.drawText(QRectF(c.x() - r * 0.95, by, bw, 15 * k), Qt.AlignLeft | Qt.AlignVCenter, self.min_text)
        p.drawText(QRectF(c.x() + r * 0.95 - bw, by, bw, 15 * k), Qt.AlignRight | Qt.AlignVCenter, self.max_text)


class ToggleSwitch(QAbstractButton):
    """On / off switch (pill with a round knob), like the Settings design."""

    def __init__(self, checked: bool = False, green: bool = False):
        super().__init__()
        self.green = green                  # Playlist Sync: a green switch when ON
        self.setCheckable(True)
        self.setChecked(checked)
        self.setFixedSize(54, 28)
        self.setCursor(Qt.PointingHandCursor)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        on = self.isChecked()
        g = QLinearGradient(r.topLeft(), r.topRight())
        c0, c1 = ("#1fc45f", "#6df0a0") if self.green else ("#1aa7ff", "#35e0ff")
        g.setColorAt(0, QColor(c0) if on else QColor(60, 80, 130))
        g.setColorAt(1, QColor(c1) if on else QColor(60, 80, 130))
        p.setPen(QPen(QColor(190, 255, 215, 220) if (on and self.green) else QColor(140, 220, 255, 200) if on
                      else QColor(120, 150, 210, 160), 1.2))
        p.setBrush(g)
        p.drawRoundedRect(r, r.height() / 2, r.height() / 2)
        d = r.height() - 6
        x = r.right() - d - 3 if on else r.left() + 3
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("white"))
        p.drawEllipse(QRectF(x, r.top() + 3, d, d))


class ElidedLabel(QLabel):
    """Label that shortens long text with '...' instead of widening the layout."""

    def __init__(self, text: str = ""):
        super().__init__()
        self._full = ""
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.set_full_text(text)

    def set_full_text(self, text: str):
        self._full = text
        self.setToolTip(text)
        self._elide()

    def _elide(self):
        shown = self.fontMetrics().elidedText(self._full, Qt.ElideRight, max(20, self.width()))
        super().setText(shown)

    def resizeEvent(self, e):
        self._elide()
        super().resizeEvent(e)


# ----------------------------------------------------------------------
class ArrowComboBox(QComboBox):
    """Combo box that draws a clear drop-down arrow, so the user sees it can be clicked."""

    def paintEvent(self, e):
        super().paintEvent(e)
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        h, w = self.height(), 30
        area = QStyle.visualRect(self.layoutDirection(), self.rect(), QRect(self.width() - w - 2, 3, w, h - 6))
        hot = self.underMouse() or self.hasFocus()
        col = QColor("#ffffff") if hot else QColor("#27d3ff")
        p.setPen(QPen(QColor(120, 190, 255, 90), 1))                 # thin divider before the arrow
        p.drawLine(area.left(), area.top() + 3, area.left(), area.bottom() - 3)
        c = area.center()
        a = max(4, int(h * 0.12))
        p.setPen(QPen(col, 2.4, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.drawPolyline([QPointF(c.x() - a * 1.4, c.y() - a * 0.6), QPointF(c.x(), c.y() + a * 0.8),
                        QPointF(c.x() + a * 1.4, c.y() - a * 0.6)])
        p.end()


# ----------------------------------------------------------------------
class MorphStack(QStackedWidget):
    """QStackedWidget whose page change is a soft fade-in of the real new page on the panel's own colour
    (no picture of the page is taken, so nothing white can flash; 2.0.3)."""
    DURATION = 240

    def __init__(self):
        super().__init__()
        self._anim = self._fx_widget = None

    def setCurrentIndex(self, i: int):
        was = self.currentIndex()
        self._finish()
        super().setCurrentIndex(i)
        if i == was or not self.isVisible():
            return
        page = self.currentWidget()
        if page is None:
            return
        fx = QGraphicsOpacityEffect(page)
        fx.setOpacity(0.0)
        page.setGraphicsEffect(fx)
        self._fx_widget = page
        a = self._anim = QVariantAnimation(self)
        a.setDuration(self.DURATION)
        a.setStartValue(0.0)
        a.setEndValue(1.0)
        a.setEasingCurve(QEasingCurve.OutQuad)
        a.valueChanged.connect(self._tick)
        a.finished.connect(self._finish)
        a.start()

    def _tick(self, v):
        w = self._fx_widget
        fx = w.graphicsEffect() if w is not None else None
        if fx is not None:
            fx.setOpacity(float(v))

    def _finish(self):
        a, self._anim = self._anim, None
        if a is not None:
            a.stop()
            a.deleteLater()
        w, self._fx_widget = self._fx_widget, None
        if w is not None:
            w.setGraphicsEffect(None)
