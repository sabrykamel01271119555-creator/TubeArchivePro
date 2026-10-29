# =============================================================================
# TubeArchive Pro  |  Version 2.3.1  |  File: app/ui/splash.py
# Version history of this file:
#   2.3.2 - the counter and the bar run evenly in 10 s: every number 1, 2, 3 ... total appears (no easing, no rolling digit)
#   2.3.2 - faster (counting 2.6 - 3.5 s, hold 0.3 s); the users number is big, coral and rolls like an odometer; the version bar uses the
#           red -> green gauge colours with a marker and the percentage
#   2.3.1 - slower counting (6 - 10 s): the users frame pulses while it counts from 1 up to the total, and the number of the version
#           the bar is passing counts up too ('Version 1.0.2   22')
#   2.3.0 - slower: every version gets about a second (the counter and the bar move version by version); the number has its
#           label 'Users' below it; main.py keeps the splash screen until the animation has finished
#   2.2.8 - Left: users counter that counts up from 1; right: rating of the users (stars) and a bar that fills version by version
#           (the numbers are those of the last online check, see app/stats.py)
#   1.0.6 - No functional change (version header added)
#   1.0.0 - 1.0.5 - first version and earlier fixes (see CHANGELOG.md)
# =============================================================================
"""Splash screen (design guide: tubearchive_pro_loading_screen.jpg)."""
import math
import time

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import (QColor, QFont, QLinearGradient, QPainter, QPainterPath,
                           QPen, QPolygonF, QRadialGradient)
from PySide6.QtWidgets import QApplication, QWidget

from ..i18n import LanguageManager
from ..msg import M
from .icons import make_app_icon, make_app_qicon


class SplashScreen(QWidget):
    W, H = 1060, 480
    HOLD = 0.5                        # seconds the final numbers stay on the screen

    def __init__(self, lang: LanguageManager, stats: dict | None = None):
        super().__init__()
        self.lang = lang
        self.stats = stats or {}                  # {"total", "versions": [(version, users)], "rating": {"average", "count"}}
        self._t0 = time.monotonic()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.SplashScreen | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowIcon(make_app_qicon())
        self.resize(self.W, self.H)
        self._icon = make_app_icon(170)
        self.percent = 0
        self.shown_percent = 0.0
        self.status = ""
        self.tick = 0
        self.timer = QTimer(self, interval=16)
        self.timer.timeout.connect(self._animate)
        self.timer.start()
        scr = QApplication.primaryScreen().availableGeometry()
        self.move(scr.center().x() - self.W // 2, scr.center().y() - self.H // 2)

    # called by StartupLoader.progress
    def set_progress(self, percent: int, msg_id: str):
        self.percent = percent
        self.status = self.lang.tr(msg_id)

    def _animate(self):
        self.tick += 1
        self.shown_percent += (self.percent - self.shown_percent) * 0.12
        self.update()

    # ------------------------------------------------------------------
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        card = QRectF(self.rect()).adjusted(34, 34, -34, -34)

        # soft cyan glow around the glass card
        for i in range(14, 0, -1):
            p.setPen(QPen(QColor(39, 211, 255, 5 + (14 - i) * 2), i * 2))
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(card, 30, 30)

        # glass body
        g = QLinearGradient(card.topLeft(), card.bottomRight())
        g.setColorAt(0, QColor(70, 170, 235, 235))
        g.setColorAt(1, QColor(10, 80, 170, 240))
        p.setPen(QPen(QColor(150, 235, 255, 230), 2))
        p.setBrush(g)
        p.drawRoundedRect(card, 30, 30)
        sheen = QLinearGradient(card.topLeft(), card.center())
        sheen.setColorAt(0, QColor(255, 255, 255, 60))
        sheen.setColorAt(1, QColor(255, 255, 255, 0))
        p.setPen(Qt.NoPen)
        p.setBrush(sheen)
        p.drawRoundedRect(card.adjusted(3, 3, -3, -card.height() * .5), 28, 28)

        # rotating rings around the icon
        cx, cy = card.center().x(), card.top() + card.height() * 0.40
        halo = QRadialGradient(cx, cy, 130)
        halo.setColorAt(0, QColor(110, 230, 255, 120))
        halo.setColorAt(1, QColor(110, 230, 255, 0))
        p.setBrush(halo)
        p.drawEllipse(QRectF(cx - 130, cy - 130, 260, 260))
        p.setBrush(Qt.NoBrush)
        for radius, speed, width, alpha, parts in ((118, 1.4, 7, 230, 3),
                                                   (98, -2.1, 4, 190, 4),
                                                   (78, 3.0, 2, 150, 6)):
            p.setPen(QPen(QColor(39, 225, 255, alpha), width, Qt.SolidLine, Qt.RoundCap))
            rect = QRectF(cx - radius, cy - radius, radius * 2, radius * 2)
            base = (self.tick * speed) % 360
            for k in range(parts):
                p.drawArc(rect, int((base + k * 360 / parts) * 16), int(360 / parts * 0.55 * 16))
        p.setPen(QPen(QColor(150, 235, 255, 90), 1, Qt.DotLine))
        p.drawEllipse(QRectF(cx - 132, cy - 132, 264, 264))

        p.drawPixmap(int(cx - 62), int(cy - 62), 124, 124, self._icon)

        # name
        f = QFont("Segoe UI", 1)
        f.setPixelSize(36)
        f.setBold(True)
        p.setFont(f)
        name_rect = QRectF(card.left(), cy + 138, card.width(), 48)
        p.setPen(QColor(8, 30, 90, 255))
        p.drawText(name_rect, Qt.AlignCenter, self.lang.tr(M.APP_NAME))

        # "Loading..." (animated dots)
        f2 = QFont("Segoe UI", 1)
        f2.setPixelSize(20)
        p.setFont(f2)
        dots = "." * ((self.tick // 18) % 4)
        p.setPen(QColor(190, 250, 255))
        p.drawText(QRectF(card.left(), cy + 186, card.width(), 30), Qt.AlignCenter,
                   self.lang.tr(M.LOADING) + dots)

        # progress bar + status line
        bw = card.width() * 0.5
        bar = QRectF(card.center().x() - bw / 2, card.bottom() - 46, bw, 6)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(5, 40, 110, 150))
        p.drawRoundedRect(bar, 3, 3)
        fill = QRectF(bar.left(), bar.top(), bar.width() * self.shown_percent / 100, bar.height())
        pg = QLinearGradient(bar.topLeft(), bar.topRight())
        pg.setColorAt(0, QColor("#1d8bff"))
        pg.setColorAt(1, QColor("#5ff3ff"))
        p.setBrush(pg)
        p.drawRoundedRect(fill, 3, 3)
        f3 = QFont("Segoe UI", 1)
        f3.setPixelSize(13)
        p.setFont(f3)
        p.setPen(QColor(210, 240, 255, 230))
        p.drawText(QRectF(card.left(), card.bottom() - 36, card.width(), 24), Qt.AlignCenter, self.status)
        self._paint_users(p, card, cy)
        self._paint_rating_and_versions(p, card, cy)

    # ------------------------------------------------------------------
    def _versions(self) -> list:
        return [(v, int(n)) for v, n in self.stats.get("versions", []) if int(n) > 0]

    DURATION = 10.0                   # seconds the counter takes from 1 to the number of users

    def duration(self) -> float:
        """The counting takes 10 s however many users there are (every number 1, 2, 3 ... appears in turn)."""
        return self.DURATION if int(self.stats.get("total", 0) or 0) else 0.0

    def remaining_ms(self) -> int:
        """Milliseconds until the animation (and its hold time) is over - the splash screen stays until then."""
        left = self.duration() + self.HOLD - (time.monotonic() - self._t0)
        return max(0, int(left * 1000)) if self.duration() else 0

    def _value(self) -> float:
        """The number the counter / bar show now: 1 -> total, one version after the other (smooth inside a version)."""
        total = float(self.stats.get("total", 0) or 0)
        if total <= 0:
            return 0.0
        f = min(1.0, (time.monotonic() - self._t0) / self.duration())
        return float(1 + int(round((total - 1) * f)))        # whole numbers, evenly spaced in time: 1, 2, 3 ... total

    def _glass(self, p, r: QRectF):
        counting = (time.monotonic() - self._t0) < self.duration()
        pulse = 0.5 + 0.5 * math.sin(self.tick * 0.12) if counting else 0.0       # the frame breathes while the numbers grow
        p.setPen(QPen(QColor(150, 235, 255, int(110 + 120 * pulse)), 1.2 + 1.2 * pulse))
        p.setBrush(QColor(5, 35, 100 + int(30 * pulse), 120))
        p.drawRoundedRect(r, 18, 18)

    def _paint_users(self, p, card, cy):
        """Left side: the number of users, counting up."""
        total = int(self.stats.get("total", 0) or 0)
        if total <= 0:
            return
        r = QRectF(card.left() + 26, cy - 92, 250, 184)
        self._glass(p, r)
        f = QFont("Segoe UI", 1)
        f.setPixelSize(17)
        p.setFont(f)
        p.setPen(QColor(190, 240, 255))
        self._odometer(p, r, self._value())
        f = QFont("Segoe UI", 1)                                                  # the label under the number: "Users"
        f.setPixelSize(22)
        f.setBold(True)
        p.setFont(f)
        p.setPen(QColor(150, 235, 255))
        p.drawText(QRectF(r.left(), r.bottom() - 52, r.width(), 32), Qt.AlignCenter, self.lang.tr(M.SPL_USERS).lower()
                   if self.lang.code == "en" else self.lang.tr(M.SPL_USERS))

    def _odometer(self, p, r: QRectF, value: float):
        """The big number: coral, bold; the last digit rolls up to the next one while the number grows."""
        n = max(0, int(value))
        frac = value - n
        text = str(n)
        big = QFont("Segoe UI", 1)
        big.setPixelSize(78 if len(text) <= 3 else 62 if len(text) <= 5 else 48)
        big.setBold(True)
        p.setFont(big)
        fm = p.fontMetrics()
        h = fm.height()
        width = fm.horizontalAdvance(text)
        x = r.center().x() - width / 2
        top = r.top() + 40
        prefix, last, nxt = text[:-1], text[-1], str((n + 1) % 10)
        px = fm.horizontalAdvance(prefix)
        for dx, dy, col in ((2, 3, QColor(8, 30, 90, 120)), (0, 0, QColor("#ff3b6b"))):     # shadow, then the number
            p.setPen(col)
            if prefix:
                p.drawText(QRectF(x + dx, top + dy, px + 4, h), Qt.AlignLeft | Qt.AlignVCenter, prefix)
            p.save()
            p.setClipRect(QRectF(x + px + dx - 1, top + dy, fm.horizontalAdvance(last) + 6, h))
            roll = frac * h * 0.9
            p.drawText(QRectF(x + px + dx, top + dy - roll, fm.horizontalAdvance(last) + 4, h), Qt.AlignLeft | Qt.AlignVCenter, last)
            p.drawText(QRectF(x + px + dx, top + dy - roll + h * 0.9, fm.horizontalAdvance(last) + 4, h), Qt.AlignLeft | Qt.AlignVCenter, nxt)
            p.restore()

    @staticmethod
    def _star(cx, cy, r) -> QPolygonF:
        pts = []
        for i in range(10):
            ang = -math.pi / 2 + i * math.pi / 5
            rad = r if i % 2 == 0 else r * 0.45
            pts.append(QPointF(cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
        return QPolygonF(pts)

    def _paint_rating_and_versions(self, p, card, cy):
        """Right side: rating of the users (stars + average) and the bar that fills version after version."""
        versions = self._versions()
        rating = self.stats.get("rating")
        if not versions and not rating:
            return
        r = QRectF(card.right() - 276, cy - 92, 250, 184)
        self._glass(p, r)
        y = r.top() + 14
        if rating:
            f = QFont("Segoe UI", 1)
            f.setPixelSize(15)
            p.setFont(f)
            p.setPen(QColor(190, 240, 255))
            p.drawText(QRectF(r.left(), y, r.width(), 22), Qt.AlignCenter, self.lang.tr(M.SPL_RATING))
            y += 26
            avg = max(0.0, min(5.0, float(rating["average"])))
            k = min(1.0, (time.monotonic() - self._t0) / max(1.0, self.duration() * 0.8))
            lit = avg * (1 - (1 - k) ** 3)                                      # the stars fill up with the counter
            sx, size = r.left() + (r.width() - 5 * 32) / 2, 14
            for i in range(5):
                star = self._star(sx + i * 32 + 16, y + 16, size)
                p.setPen(QPen(QColor(255, 210, 90, 200), 1.4))
                p.setBrush(QColor(255, 255, 255, 40))
                p.drawPolygon(star)
                part = max(0.0, min(1.0, lit - i))
                if part > 0:
                    clip = QPainterPath()
                    clip.addRect(QRectF(sx + i * 32, y, 32 * part, 34))
                    path = QPainterPath()
                    path.addPolygon(star)
                    p.save()
                    p.setClipPath(clip)
                    p.setPen(Qt.NoPen)
                    p.setBrush(QColor("#ffc93c"))
                    p.drawPath(path)
                    p.restore()
            y += 38
            f2 = QFont("Segoe UI", 1)
            f2.setPixelSize(15)
            f2.setBold(True)
            p.setFont(f2)
            p.setPen(QColor("#ffffff"))
            p.drawText(QRectF(r.left(), y, r.width(), 22), Qt.AlignCenter,
                       f"{avg:.1f} / 5   -   " + self.lang.tr(M.SPL_RATED_BY, n=f"{int(rating['count']):,}"))
            y += 30
        if not versions:
            return
        total = sum(n for _v, n in versions)
        value = self._value()
        # the bar: one part per version, filled from the left while the counter runs
        bar = QRectF(r.left() + 16, r.bottom() - 52, r.width() - 32, 14)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(5, 40, 110, 170))
        p.drawRoundedRect(bar, 7, 7)
        clip = QPainterPath()
        clip.addRoundedRect(bar, 7, 7)
        p.save()
        p.setClipPath(clip)
        start, label, count_now = 0.0, versions[0][0], 0
        for idx, (ver, n) in enumerate(versions):
            seg_l = bar.left() + bar.width() * start / total
            seg_w = bar.width() * n / total
            done = max(0.0, min(1.0, (value - start) / n))
            if done > 0:
                g = QLinearGradient(seg_l, 0, seg_l + seg_w, 0)
                k = idx / max(1, len(versions) - 1)                       # red -> orange -> yellow -> green (like the gauge picture)
                hue = 5 + 115 * k
                g.setColorAt(0, QColor.fromHsv(int(hue), 235, 255))
                g.setColorAt(1, QColor.fromHsv(int(min(125, hue + 10)), 220, 245))
                p.setBrush(g)
                p.drawRect(QRectF(seg_l, bar.top(), seg_w * done, bar.height()))
            if idx:
                p.setPen(QPen(QColor(8, 30, 90, 200), 1.4))
                p.drawLine(QPointF(seg_l, bar.top()), QPointF(seg_l, bar.bottom()))
                p.setPen(Qt.NoPen)
            if value >= start + 1e-9:                                        # the version the bar is passing now
                label, count_now = ver, int(min(n, value - start))
            start += n
        p.restore()
        mx = bar.left() + bar.width() * min(1.0, value / total)           # the marker (triangle) under the bar
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(235, 245, 255, 230))
        p.drawPolygon(QPolygonF([QPointF(mx, bar.bottom() + 1), QPointF(mx - 6, bar.bottom() + 9), QPointF(mx + 6, bar.bottom() + 9)]))
        f3 = QFont("Segoe UI", 1)
        f3.setPixelSize(14)
        p.setFont(f3)
        p.setPen(QColor(210, 245, 255))
        p.drawText(QRectF(r.left(), r.bottom() - 28, r.width(), 22), Qt.AlignCenter,
                   self.lang.tr(M.SPL_VERSION, v=label) + f"     {count_now:,}")
