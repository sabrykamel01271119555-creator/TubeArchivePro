# =============================================================================
# TubeArchive Pro  |  Version 2.2.8  |  File: app/ui/icons.py
# Version history of this file:
#   2.2.8 - make_emoji_icon (category icon as a picture for drop-down lists)
#   2.2.7 - set_sync_button (green lit sync button / plain button)
#   2.2.3 - make_state_icon (down / queue / pause)
#   2.0.1 - New make_details_icon, make_channel_logo
#   1.0.12 - New make_globe_icon
#   1.0.11 - New make_sync_icon (two arrows in a circle)
#   1.0.10 - Side-menu icons: "downloads" (tray arrow), "playlist"
#   1.0.9 - New: make_trash_icon, make_star_icon, side-menu icon "downloads"
#   1.0.8 - New icons: download arrow, play, folder, success check, info-row icons; rounded_pixmap() for thumbnails
#   1.0.6 - No functional change (version header added)
#   1.0.0 - 1.0.5 - first version and earlier fixes (see CHANGELOG.md)
# =============================================================================
"""All icons are drawn in code (no image files needed)."""
import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QBrush, QColor, QIcon, QLinearGradient, QPainter,
                           QPainterPath, QPen, QPixmap, QPolygonF)


def _grad(x1, y1, x2, y2, c1, c2):
    g = QLinearGradient(x1, y1, x2, y2)
    g.setColorAt(0, QColor(c1))
    g.setColorAt(1, QColor(c2))
    return g


def make_app_icon(size: int = 256) -> QPixmap:
    """Stacked blue binders + play triangle + red download badge."""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.scale(size / 256, size / 256)
    p.setPen(Qt.NoPen)

    def card(x, y, w, h, c1, c2):
        p.setBrush(_grad(x, y, x + w, y + h, c1, c2))
        p.drawRoundedRect(QRectF(x, y, w, h), 20, 20)

    card(34, 28, 118, 176, "#1a45c8", "#2c6df0")      # back binder
    card(66, 48, 122, 176, "#2255de", "#4690ff")      # middle binder
    card(98, 74, 132, 152, "#3c82ff", "#6db8ff")      # front cover
    p.setBrush(QColor("#eaf3ff"))                      # white pages edge
    p.drawRoundedRect(QRectF(104, 66, 120, 9), 4, 4)
    for y in (84, 126):                                # binder holes
        p.setBrush(QColor("#0d2d86"))
        p.drawEllipse(QPointF(52, y), 9, 9)
        p.setBrush(QColor("#9fd0ff"))
        p.drawEllipse(QPointF(52, y), 5, 5)
    p.setBrush(QColor("white"))                        # play triangle
    p.drawPolygon(QPolygonF([QPointF(132, 120), QPointF(132, 176), QPointF(180, 148)]))
    # red badge
    p.setBrush(_grad(160, 150, 232, 230, "#ff6a6a", "#d11a2a"))
    p.setPen(QPen(QColor(255, 255, 255, 70), 3))
    p.drawEllipse(QPointF(198, 192), 40, 40)
    p.setPen(QPen(QColor("white"), 9, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.drawLine(QPointF(198, 172), QPointF(198, 204))
    p.setPen(Qt.NoPen)
    p.setBrush(QColor("white"))
    p.drawPolygon(QPolygonF([QPointF(179, 196), QPointF(217, 196), QPointF(198, 216)]))
    p.end()
    return pm


def make_app_qicon() -> QIcon:
    ic = QIcon()
    for s in (16, 32, 48, 64, 128, 256):
        ic.addPixmap(make_app_icon(s))
    return ic


def make_thumb(c1: str, c2: str, w: int = 100, h: int = 62) -> QPixmap:
    """Placeholder thumbnail (gradient + play button)."""
    pm = QPixmap(w, h)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    path = QPainterPath()
    path.addRoundedRect(QRectF(0, 0, w, h), 8, 8)
    p.setClipPath(path)
    p.fillRect(0, 0, w, h, _grad(0, 0, w, h, c1, c2))
    p.setPen(QPen(QColor(255, 255, 255, 230), 2))
    p.setBrush(QColor(20, 60, 140, 170))
    p.drawEllipse(QPointF(w / 2, h / 2), 15, 15)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor("white"))
    p.drawPolygon(QPolygonF([QPointF(w / 2 - 4, h / 2 - 7), QPointF(w / 2 - 4, h / 2 + 7),
                             QPointF(w / 2 + 8, h / 2)]))
    p.end()
    return pm


def draw_nav_icon(p: QPainter, kind: str, r: QRectF, color: QColor):
    """Simple line icons for the side menu."""
    p.save()
    p.setPen(QPen(color, 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.setBrush(Qt.NoBrush)
    x, y, w, h = r.x(), r.y(), r.width(), r.height()
    cx, cy = r.center().x(), r.center().y()
    if kind == "dashboard":      # house
        p.drawPolyline(QPolygonF([QPointF(x + 1, y + h * .48), QPointF(cx, y + 2),
                                  QPointF(x + w - 1, y + h * .48)]))
        p.drawPolyline(QPolygonF([QPointF(x + 4, y + h * .42), QPointF(x + 4, y + h - 2),
                                  QPointF(x + w - 4, y + h - 2), QPointF(x + w - 4, y + h * .42)]))
        p.drawRect(QRectF(cx - 3, y + h * .6, 6, h * .4 - 2))
    elif kind == "new":          # circle + plus
        p.drawEllipse(r.adjusted(2, 2, -2, -2))
        p.drawLine(QPointF(cx, cy - 5), QPointF(cx, cy + 5))
        p.drawLine(QPointF(cx - 5, cy), QPointF(cx + 5, cy))
    elif kind in ("downloader", "downloads"):   # arrow into tray
        p.drawLine(QPointF(cx, y + 2), QPointF(cx, y + h * .62))
        p.drawPolyline(QPolygonF([QPointF(cx - 6, y + h * .45), QPointF(cx, y + h * .65),
                                  QPointF(cx + 6, y + h * .45)]))
        p.drawPolyline(QPolygonF([QPointF(x + 2, y + h * .6), QPointF(x + 2, y + h - 2),
                                  QPointF(x + w - 2, y + h - 2), QPointF(x + w - 2, y + h * .6)]))
    elif kind in ("queue", "archive"):   # folder
        path = QPainterPath()
        path.moveTo(x + 1, y + 5)
        path.lineTo(x + 1, y + h - 3)
        path.lineTo(x + w - 1, y + h - 3)
        path.lineTo(x + w - 1, y + 8)
        path.lineTo(cx + 2, y + 8)
        path.lineTo(cx - 1, y + 4)
        path.lineTo(x + 1, y + 4)
        p.drawPath(path)
    elif kind == "library":      # folder with plus
        p.drawRoundedRect(r.adjusted(1, 4, -1, -2), 3, 3)
        p.drawLine(QPointF(x + 2, y + 4), QPointF(cx - 2, y + 4))
        p.drawLine(QPointF(cx, cy + 2), QPointF(cx, cy + 9))
        p.drawLine(QPointF(cx - 3.5, cy + 5.5), QPointF(cx + 3.5, cy + 5.5))
    elif kind == "playlist":     # list with sync arrow
        for i in range(3):
            yy = y + 5 + i * (h - 10) / 2.2
            p.drawLine(QPointF(x + 8, yy), QPointF(x + w - 2, yy))
            p.drawPoint(QPointF(x + 3, yy))
    elif kind == "monitor":      # chart
        p.drawPolyline(QPolygonF([QPointF(x + 1, y + 1), QPointF(x + 1, y + h - 2),
                                  QPointF(x + w - 1, y + h - 2)]))
        p.drawPolyline(QPolygonF([QPointF(x + 5, y + h - 7), QPointF(x + 10, y + h * .45),
                                  QPointF(x + 15, y + h * .62), QPointF(x + w - 2, y + 4)]))
    elif kind == "settings":     # gear
        p.drawEllipse(QPointF(cx, cy), 4, 4)
        p.drawEllipse(QPointF(cx, cy), 8, 8)
        for i in range(8):
            a = math.radians(i * 45)
            p.drawLine(QPointF(cx + 8 * math.cos(a), cy + 8 * math.sin(a)),
                       QPointF(cx + 11 * math.cos(a), cy + 11 * math.sin(a)))
    p.restore()


def make_warning_icon(size: int = 48) -> QPixmap:
    """Red warning triangle with a white exclamation mark."""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.scale(size / 48, size / 48)
    tri = QPolygonF([QPointF(24, 5), QPointF(44, 40), QPointF(4, 40)])
    p.setBrush(_grad(0, 5, 0, 40, "#ff7a7a", "#e0262f"))
    p.setPen(QPen(QColor("#ff9a9a"), 5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.drawPolygon(tri)
    p.setPen(QPen(QColor("white"), 4, Qt.SolidLine, Qt.RoundCap))
    p.drawLine(QPointF(24, 17), QPointF(24, 28))
    p.drawPoint(QPointF(24, 34))
    p.end()
    return pm


def make_exit_icon(size: int = 24) -> QPixmap:
    """Door bracket with an arrow leaving it."""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.scale(size / 24, size / 24)
    p.setPen(QPen(QColor("white"), 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.drawPolyline(QPolygonF([QPointF(12, 4), QPointF(4, 4), QPointF(4, 20), QPointF(12, 20)]))
    p.drawLine(QPointF(10, 12), QPointF(21, 12))
    p.drawPolyline(QPolygonF([QPointF(16, 7), QPointF(21, 12), QPointF(16, 17)]))
    p.end()
    return pm


def make_arrow_icon(size: int = 32) -> QPixmap:
    """White download arrow (round red button)."""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.scale(size / 32, size / 32)
    p.setPen(QPen(QColor("white"), 5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.drawLine(QPointF(16, 5), QPointF(16, 22))
    p.drawPolyline(QPolygonF([QPointF(7, 14), QPointF(16, 23), QPointF(25, 14)]))
    p.end()
    return pm


def make_state_icon(kind: str, size: int = 34, color: str = "#ffffff") -> QPixmap:
    """Icons of the counters (2.2.3): 'down' = downloading now, 'queue' = waiting list, 'pause' = paused."""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.scale(size / 32, size / 32)
    pen = QPen(QColor(color), 3.4, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    p.setPen(pen)
    if kind == "down":
        p.drawLine(QPointF(16, 4), QPointF(16, 21))
        p.drawPolyline(QPolygonF([QPointF(8, 14), QPointF(16, 22), QPointF(24, 14)]))
        p.drawLine(QPointF(6, 28), QPointF(26, 28))
    elif kind == "queue":
        for y in (8, 16, 24):
            p.drawLine(QPointF(11, y), QPointF(27, y))
            p.setBrush(QColor(color))
            p.drawEllipse(QPointF(5.5, y), 1.4, 1.4)
            p.setBrush(Qt.NoBrush)
    else:
        p.setBrush(QColor(color))
        p.drawRoundedRect(QRectF(7, 5, 6, 22), 2, 2)
        p.drawRoundedRect(QRectF(19, 5, 6, 22), 2, 2)
    p.end()
    return pm


def make_play_icon(size: int = 22) -> QPixmap:
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.scale(size / 22, size / 22)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor("white"))
    p.drawPolygon(QPolygonF([QPointF(4, 2), QPointF(4, 20), QPointF(19, 11)]))
    p.end()
    return pm


def make_folder_icon(size: int = 24) -> QPixmap:
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.scale(size / 24, size / 24)
    p.setPen(QPen(QColor("white"), 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    path = QPainterPath()
    path.moveTo(2, 6)
    path.lineTo(2, 20)
    path.lineTo(22, 20)
    path.lineTo(22, 8)
    path.lineTo(11, 8)
    path.lineTo(9, 5)
    path.lineTo(2, 5)
    p.drawPath(path)
    p.end()
    return pm


def make_check_icon(size: int = 150) -> QPixmap:
    """Glowing check mark inside broken rings (success dialog)."""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.scale(size / 150, size / 150)
    c = QPointF(75, 75)
    for r, w, a, parts in ((68, 4, 190, 3), (58, 3, 150, 4)):
        p.setPen(QPen(QColor(39, 211, 255, a), w, Qt.SolidLine, Qt.RoundCap))
        rect = QRectF(c.x() - r, c.y() - r, 2 * r, 2 * r)
        for k in range(parts):
            p.drawArc(rect, int((20 + k * 360 / parts) * 16), int(360 / parts * 0.6 * 16))
    for w, a in ((16, 45), (9, 255)):
        p.setPen(QPen(QColor(60, 210, 255, a), w, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.drawPolyline(QPolygonF([QPointF(46, 78), QPointF(67, 99), QPointF(108, 52)]))
    p.end()
    return pm


def make_info_icon(kind: str, size: int = 34, text: str = "") -> QPixmap:
    """Small icons for the rows of the success dialog: file / badge / size / folder."""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.scale(size / 34, size / 34)
    col = QColor("#dff4ff")
    p.setPen(QPen(col, 2.2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.setBrush(Qt.NoBrush)
    if kind == "file":
        p.drawPolyline(QPolygonF([QPointF(9, 4), QPointF(9, 30), QPointF(25, 30), QPointF(25, 12),
                                  QPointF(17, 4), QPointF(9, 4)]))
        p.drawPolyline(QPolygonF([QPointF(17, 4), QPointF(17, 12), QPointF(25, 12)]))
    elif kind == "badge":
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#bfe6ff"))
        p.drawRoundedRect(QRectF(2, 6, 30, 22), 5, 5)
        p.setPen(QColor("#0b3a7a"))
        f = p.font()
        f.setPixelSize(15 if len(text or 'HD') <= 2 else 11)
        f.setBold(True)
        p.setFont(f)
        p.drawText(QRectF(2, 6, 30, 22), Qt.AlignCenter, text or "HD")
    elif kind == "size":
        p.drawRoundedRect(QRectF(4, 8, 26, 18), 4, 4)
        p.drawLine(QPointF(4, 18), QPointF(30, 18))
        p.drawPolyline(QPolygonF([QPointF(11, 18), QPointF(11, 22), QPointF(23, 22), QPointF(23, 18)]))
    else:   # folder
        path = QPainterPath()
        path.moveTo(3, 9)
        path.lineTo(3, 28)
        path.lineTo(31, 28)
        path.lineTo(31, 12)
        path.lineTo(17, 12)
        path.lineTo(14, 8)
        path.lineTo(3, 8)
        p.drawPath(path)
    p.end()
    return pm


def rounded_pixmap(src: QPixmap, w: int, h: int, radius: int = 10) -> QPixmap:
    """Fill w x h with the picture (centre crop) and round the corners."""
    out = QPixmap(w, h)
    out.fill(Qt.transparent)
    p = QPainter(out)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.SmoothPixmapTransform)
    clip = QPainterPath()
    clip.addRoundedRect(QRectF(0, 0, w, h), radius, radius)
    p.setClipPath(clip)
    scaled = src.scaled(w, h, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
    p.drawPixmap((w - scaled.width()) // 2, (h - scaled.height()) // 2, scaled)
    p.end()
    return out


def make_trash_icon(size: int = 22) -> QPixmap:
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.scale(size / 22, size / 22)
    p.setPen(QPen(QColor("white"), 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.drawLine(QPointF(3, 5), QPointF(19, 5))
    p.drawLine(QPointF(8, 5), QPointF(8, 3))
    p.drawLine(QPointF(8, 3), QPointF(14, 3))
    p.drawLine(QPointF(14, 3), QPointF(14, 5))
    p.drawPolyline(QPolygonF([QPointF(5, 7), QPointF(6, 19), QPointF(16, 19), QPointF(17, 7)]))
    p.drawLine(QPointF(9, 9), QPointF(9, 16))
    p.drawLine(QPointF(13, 9), QPointF(13, 16))
    p.end()
    return pm


def make_star_icon(size: int = 22, filled: bool = False) -> QPixmap:
    """Star for 'add to favorites' (filled gold = already a favorite)."""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.scale(size / 22, size / 22)
    pts = []
    for i in range(10):
        r = 9.5 if i % 2 == 0 else 4.1
        a = math.radians(-90 + i * 36)
        pts.append(QPointF(11 + r * math.cos(a), 11.5 + r * math.sin(a)))
    p.setPen(QPen(QColor("#ffd24d") if filled else QColor("white"), 1.8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.setBrush(QColor("#ffc400") if filled else Qt.NoBrush)
    p.drawPolygon(QPolygonF(pts))
    p.end()
    return pm


def make_sync_icon(size: int = 22, color: str = "white") -> QPixmap:
    """Two arrows chasing each other in a circle ('Sync now')."""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.scale(size / 22, size / 22)
    pen = QPen(QColor(color), 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    r = QRectF(3.5, 3.5, 15, 15)
    p.drawArc(r, 20 * 16, 140 * 16)          # upper arc
    p.drawArc(r, 200 * 16, 140 * 16)         # lower arc
    p.drawPolyline(QPolygonF([QPointF(17.5, 3.2), QPointF(17.2, 7.6), QPointF(12.8, 7.2)]))
    p.drawPolyline(QPolygonF([QPointF(4.5, 18.8), QPointF(4.8, 14.4), QPointF(9.2, 14.8)]))
    p.end()
    return pm


def make_emoji_icon(emoji: str, size: int = 22) -> QIcon:
    """The icon (one emoji) of a favorite category as a real picture, so every list shows it beside the name."""
    from PySide6.QtGui import QFont
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.TextAntialiasing)
    f = QFont("Segoe UI Emoji")
    f.setPixelSize(max(8, int(size * 0.78)))
    p.setFont(f)
    p.setPen(QColor("white"))
    p.drawText(QRectF(0, 0, size, size), Qt.AlignCenter, emoji)
    p.end()
    return QIcon(pm)


def set_sync_button(b, on: bool):
    """Sync button of a playlist (Archive / Library / Playlist Sync): synchronised = full green button with a lit sign;
    not synchronised = normal border, no background, quiet sign. (2.2.7)"""
    from PySide6.QtCore import QSize
    from PySide6.QtGui import QColor
    from PySide6.QtWidgets import QGraphicsDropShadowEffect
    b.setObjectName("iconBtnOn" if on else "iconBtnOff")
    b.style().unpolish(b)
    b.style().polish(b)
    icon = make_sync_icon(20, "#ffffff" if on else "#b9cfee")
    b.setIcon(icon)
    b.setIconSize(QSize(icon.width(), icon.height()))
    if on:
        fx = QGraphicsDropShadowEffect(b)
        fx.setBlurRadius(16)
        fx.setOffset(0, 0)
        fx.setColor(QColor("#7dffb5"))
        b.setGraphicsEffect(fx)
    else:
        b.setGraphicsEffect(None)


def make_globe_icon(size: int = 26, color: str = "white") -> QPixmap:
    """Language button: a globe (circle + meridians + parallels)."""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(QPen(QColor(color), max(1.4, size / 13)))
    p.setBrush(Qt.NoBrush)
    m = size * 0.1
    r = QRectF(m, m, size - 2 * m, size - 2 * m)
    p.drawEllipse(r)
    p.drawEllipse(QRectF(size * 0.33, m, size * 0.34, size - 2 * m))      # meridian
    p.drawLine(QPointF(size / 2, m), QPointF(size / 2, size - m))
    p.drawLine(QPointF(m, size / 2), QPointF(size - m, size / 2))
    p.drawArc(QRectF(m, size * 0.25, size - 2 * m, size * 0.5), 0, 180 * 16)     # parallels
    p.drawArc(QRectF(m, size * 0.25, size - 2 * m, size * 0.5), 0, -180 * 16)
    p.end()
    return pm


def make_details_icon(size: int = 22) -> QPixmap:
    """Round 'i' icon of the Details button."""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.scale(size / 22, size / 22)
    p.setPen(QPen(QColor("white"), 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.setBrush(Qt.NoBrush)
    p.drawEllipse(QPointF(11, 11), 8.5, 8.5)
    p.drawLine(QPointF(11, 10), QPointF(11, 15.5))
    p.setPen(QPen(QColor("white"), 2.6, Qt.SolidLine, Qt.RoundCap))
    p.drawPoint(QPointF(11, 6.6))
    p.end()
    return pm


def make_channel_logo(size: int = 56, image_path: str | None = None) -> QPixmap:
    """Round logo of the owner's YouTube channel (Let's Have Fun).
    If assets/owner/channel_logo.(png|jpg) exists it is used (cropped to a circle); otherwise a drawn logo."""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.SmoothPixmapTransform)
    circle = QPainterPath()
    circle.addEllipse(QRectF(2, 2, size - 4, size - 4))
    src = QPixmap(image_path) if image_path else QPixmap()
    if not src.isNull():
        p.setClipPath(circle)
        scaled = src.scaled(size - 4, size - 4, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        p.drawPixmap(2 + (size - 4 - scaled.width()) // 2, 2 + (size - 4 - scaled.height()) // 2, scaled)
        p.setClipping(False)
    else:
        g = QLinearGradient(0, 0, size, size)
        g.setColorAt(0, QColor("#ffcf4a"))
        g.setColorAt(1, QColor("#ff7a1a"))
        p.setBrush(g)
        p.setPen(Qt.NoPen)
        p.drawPath(circle)
        k = size / 56.0
        p.setBrush(QColor(255, 255, 255, 235))                       # smiling face with a play-button mouth
        p.setPen(Qt.NoPen)
        p.drawEllipse(QPointF(19 * k, 22 * k), 4.2 * k, 5 * k)
        p.drawEllipse(QPointF(37 * k, 22 * k), 4.2 * k, 5 * k)
        p.setBrush(QColor("#c4302b"))
        p.drawRoundedRect(QRectF(16 * k, 32 * k, 24 * k, 15 * k), 5 * k, 5 * k)
        p.setBrush(QColor("white"))
        p.drawPolygon(QPolygonF([QPointF(25 * k, 35 * k), QPointF(25 * k, 44 * k), QPointF(33 * k, 39.5 * k)]))
    p.setBrush(Qt.NoBrush)
    p.setPen(QPen(QColor(255, 255, 255, 230), max(1.5, size / 28)))
    p.drawEllipse(QRectF(1.5, 1.5, size - 3, size - 3))
    p.end()
    return pm
