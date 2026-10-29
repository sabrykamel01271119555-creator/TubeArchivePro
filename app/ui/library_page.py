# =============================================================================
# TubeArchive Pro  |  Version 2.2.8  |  File: app/ui/library_page.py
# Version history of this file:
#   2.3.2 - the videos of an opened playlist get their pictures (fetched in the background, kept in the thumbs folder)
#   2.3.2 - double-click on a playlist card opens it in the same work area: all its videos in order, same cards, 'Back' button
#   2.2.7 - filter by the clicked kind every time; sync button green / plain (set_sync_button)
#   2.2.2 - Playlist card: sync button lit when the playlist is synchronised; Sync now adds an unset playlist to Playlist Sync
#   2.0.3 - The category drop-down shows each category's own icon (not a star)
#   2.0.2 - Delete asks 'delete the physical file(s) too?' (videos and playlists: files + the playlist's own folder)
#   2.0.1 - ARCHIVE (mode "archive") = every download of the program, in three vaults (Videos / Audio / Playlists),
#           no favorites filter; LIBRARY (mode "library") = only what was put in a favorite category (drop-down of
#           categories); "Details" button on every card (description saved with the video)
#   1.0.14 - Category icon on the card tag
#   1.0.11 - Playlist cards: the first button is "Sync now" (two arrows in a circle) instead of Play
#   1.0.10 - Replaces downloads_page.py (1.0.9). 'Library' = history of finished downloads: "My Digital Vault"
#            folders (Videos / Music MP3 / Playlists) + "Recently Archived" cards (newest first).
#            Same class with mode="archive" = the 'Archive' menu item (favorites only, grouped by category filter).
#   1.0.9 - (downloads_page.py) first version of the history cards
# =============================================================================
"""'Library' and 'Archive' tabs (design guide: Library & Archive mockup)."""
import os

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, QUrl, Signal
from PySide6.QtGui import (QColor, QDesktopServices, QFont, QLinearGradient, QPainter,
                           QPainterPath, QPen, QPixmap, QPolygonF)
from PySide6.QtWidgets import (QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
                               QPushButton, QScrollArea, QVBoxLayout, QWidget)

from ..context import AppContext
from ..downloader import fmt_size, fmt_time, playlist_id
from ..history import delete_files
from ..msg import M
from .actions import add_to_favorites, card_tag, exec_blurred, reveal_file
from .dialogs import ChoiceDialog, DetailsDialog, MessageDialog
from .icons import (make_emoji_icon, set_sync_button, make_arrow_icon, make_folder_icon, make_play_icon, make_star_icon, make_sync_icon,
                    make_details_icon,
                    make_thumb, make_trash_icon, rounded_pixmap)
from .widgets import ArrowComboBox, ElidedLabel

MAX_CARDS = 300            # newest first; protects the interface from a huge history
FILTER_ALL, FILTER_FAV = "all", "fav"


def _full_path(rec: dict) -> str:
    return os.path.join(os.path.expanduser(rec.get("save_dir", "")), rec.get("file_name", ""))


def kind_of(rec: dict) -> str:
    return "playlist" if rec.get("is_playlist") else "audio" if rec.get("is_audio") else "video"


# ----------------------------------------------------------------------
class FolderTile(QWidget):
    """Glass folder of the vault (Videos / Music / Playlists). Click = show only that kind."""
    clicked = Signal(str)

    def __init__(self, kind: str, name: str):
        super().__init__()
        self.kind, self.name, self.count_text = kind, name, ""
        self.selected = self.hover = False
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(70)

    def set_count(self, text: str):
        self.count_text = text
        self.update()

    def set_selected(self, on: bool):
        self.selected = on
        self.update()

    def enterEvent(self, e):
        self.hover = True
        self.update()

    def leaveEvent(self, e):
        self.hover = False
        self.update()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.clicked.emit(self.kind)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        W, H = self.width(), self.height()
        if self.selected or self.hover:
            p.setBrush(QColor(60, 140, 230, 70 if self.selected else 35))
            p.setPen(QPen(QColor(39, 211, 255, 200 if self.selected else 90), 1.6))
            p.drawRoundedRect(QRectF(2, 2, W - 4, H - 4), 14, 14)
        text_h = max(34.0, H * 0.34)
        ah = H - text_h - 8                                   # height left for the folder picture
        fw = min(W * 0.62, ah * 1.25)
        fh = fw * 0.78
        fx, fy = (W - fw) / 2, 6 + (ah - fh) / 2
        # back plate + tab
        back = QPainterPath()
        back.addRoundedRect(QRectF(fx, fy + fh * 0.10, fw, fh * 0.9), fw * 0.07, fw * 0.07)
        tab = QPainterPath()
        tab.addRoundedRect(QRectF(fx, fy, fw * 0.42, fh * 0.2), fw * 0.05, fw * 0.05)
        g = QLinearGradient(fx, fy, fx, fy + fh)
        g.setColorAt(0, QColor(120, 190, 255, 230))
        g.setColorAt(1, QColor(40, 100, 200, 230))
        p.setBrush(g)
        p.setPen(QPen(QColor(170, 225, 255, 230), 1.4))
        p.drawPath(back.united(tab))
        # front panel
        front = QRectF(fx, fy + fh * 0.28, fw, fh * 0.72)
        g2 = QLinearGradient(front.topLeft(), front.bottomLeft())
        g2.setColorAt(0, QColor(150, 210, 255, 235))
        g2.setColorAt(1, QColor(50, 120, 220, 235))
        p.setBrush(g2)
        p.drawRoundedRect(front, fw * 0.07, fw * 0.07)
        self._symbol(p, front)
        # texts
        f = QFont("Segoe UI")
        f.setPixelSize(max(11, int(H * 0.15)))
        p.setFont(f)
        p.setPen(QColor("#ffffff"))
        p.drawText(QRectF(0, H - text_h, W, text_h * 0.55), int(Qt.AlignHCenter | Qt.AlignBottom), self.name)
        f.setPixelSize(max(10, int(H * 0.115)))
        p.setFont(f)
        p.setPen(QColor("#a9cdf5"))
        p.drawText(QRectF(0, H - text_h * 0.42, W, text_h * 0.42), int(Qt.AlignHCenter | Qt.AlignTop), self.count_text)
        p.end()

    def _symbol(self, p: QPainter, r: QRectF):
        c = r.center()
        s = min(r.width(), r.height()) * 0.36
        p.setPen(QPen(QColor(20, 60, 140), max(1.5, s * 0.12), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.setBrush(QColor(20, 60, 140))
        if self.kind == "video":
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(QRectF(c.x() - s, c.y() - s * 0.75, s * 2, s * 1.5), s * 0.2, s * 0.2)
            p.setBrush(QColor(20, 60, 140))
            p.drawPolygon(QPolygonF([QPointF(c.x() - s * 0.3, c.y() - s * 0.4), QPointF(c.x() - s * 0.3, c.y() + s * 0.4),
                                     QPointF(c.x() + s * 0.45, c.y())]))
        elif self.kind == "audio":
            p.drawEllipse(QPointF(c.x() - s * 0.35, c.y() + s * 0.5), s * 0.32, s * 0.26)
            p.drawLine(QPointF(c.x() - s * 0.08, c.y() + s * 0.45), QPointF(c.x() - s * 0.08, c.y() - s * 0.7))
            p.drawLine(QPointF(c.x() - s * 0.08, c.y() - s * 0.7), QPointF(c.x() + s * 0.5, c.y() - s * 0.5))
        else:
            for i in range(3):
                yy = c.y() - s * 0.55 + i * s * 0.55
                p.drawEllipse(QPointF(c.x() - s * 0.7, yy), s * 0.1, s * 0.1)
                p.drawLine(QPointF(c.x() - s * 0.4, yy), QPointF(c.x() + s * 0.8, yy))


# ----------------------------------------------------------------------
class VideoCard(QFrame):
    """One history record: thumbnail + badge, title, info, size and the five small buttons."""

    def __init__(self, page: "LibraryPage", rec: dict):
        super().__init__()
        self.page, self.rec = page, rec
        t = page.t
        self.setObjectName("vCard")
        self._src = page.thumb_source(rec)
        self._w = 0
        v = QVBoxLayout(self)
        v.setContentsMargins(10, 10, 10, 10)
        v.setSpacing(6)

        holder = QWidget()                                   # picture with the badges laid over it
        g = QGridLayout(holder)
        g.setContentsMargins(0, 0, 0, 0)
        self.thumb = QLabel()
        self.thumb.setAlignment(Qt.AlignCenter)
        g.addWidget(self.thumb, 0, 0)
        badge = QLabel(card_tag(rec.get("quality", ""), rec.get("format", rec.get("extension", "mp4"))))
        badge.setObjectName("vBadge")
        g.addWidget(badge, 0, 0, Qt.AlignTop | Qt.AlignRight)
        self.cat = QLabel()
        self.cat.setObjectName("vCat")
        g.addWidget(self.cat, 0, 0, Qt.AlignBottom | Qt.AlignLeft)
        v.addWidget(holder)

        self.title = ElidedLabel(rec.get("title") or rec.get("file_name", ""))
        self.title.setObjectName("vTitle")
        v.addWidget(self.title)
        bits = [(rec.get("extension") or "").upper(), rec.get("quality") or "", rec.get("date", "")]
        sub = ElidedLabel("  ·  ".join(b for b in bits if b))
        sub.setObjectName("vSub")
        v.addWidget(sub)
        size_bits = []
        if rec.get("is_playlist"):
            size_bits.append(t(M.DL_FILES, count=rec.get("count", 1)))
        size_bits.append(fmt_size(rec.get("size", 0)))
        if rec.get("duration") and not rec.get("is_playlist"):
            size_bits.append(fmt_time(rec["duration"]))
        size = ElidedLabel("  ·  ".join(size_bits))
        size.setObjectName("vSize")
        v.addWidget(size)

        row = QHBoxLayout()
        row.setSpacing(4)
        if rec.get("is_playlist"):                           # a playlist has no single file to play: sync it instead
            self.b_play = self._btn(make_sync_icon(18), t(M.TIP_SYNC), self._sync)
        else:
            self.b_play = self._btn(make_play_icon(16), t(M.TIP_PLAY), self._play)
        self.b_folder = self._btn(make_folder_icon(18), t(M.TIP_FOLDER), self._folder)
        self.b_again = self._btn(make_arrow_icon(18), t(M.TIP_REDOWNLOAD), self._again)
        self.b_info = self._btn(make_details_icon(18), t(M.TIP_DETAILS), self._details)
        self.b_fav = self._btn(make_star_icon(18), t(M.TIP_FAV_ADD), self._fav)
        self.b_del = self._btn(make_trash_icon(18), t(M.TIP_DELETE), self._delete)
        for b in (self.b_play, self.b_folder, self.b_again, self.b_info):
            row.addWidget(b)
        row.addStretch(1)
        row.addWidget(self.b_fav)
        row.addWidget(self.b_del)
        v.addLayout(row)
        self.refresh_fav()
        self.refresh_sync()
        if rec.get("_child"):                                # a video inside an opened playlist: play / folder / details only
            for b in (self.b_again, self.b_fav, self.b_del):
                b.setVisible(False)
            self.cat.setVisible(False)

    def mouseDoubleClickEvent(self, e):
        if self.rec.get("is_playlist"):
            self.page.open_playlist(self.rec)
        elif os.path.isfile(_full_path(self.rec)):
            self._play()
        super().mouseDoubleClickEvent(e)

    @staticmethod
    def _btn(icon: QPixmap, tip: str, slot) -> QPushButton:
        b = QPushButton()
        b.setObjectName("iconBtn")
        b.setIcon(icon)
        b.setIconSize(QSize(icon.width(), icon.height()))
        b.setToolTip(tip)
        b.setCursor(Qt.PointingHandCursor)
        b.setFixedSize(30, 28)
        b.clicked.connect(slot)
        return b

    def set_width(self, w: int):
        """Called by the page when the grid is laid out: the picture follows the card width."""
        if w == self._w:
            return
        self._w = w
        self.setFixedWidth(w)
        tw = max(80, w - 20)
        th = int(tw * 9 / 16)
        if self._src:
            pm = rounded_pixmap(self._src, tw, th, 10)
        else:
            c1, c2 = self.rec.get("thumb_colors") or ("#0a1a4a", "#1c4fa8")
            pm = make_thumb(c1, c2, tw, th)
        self.thumb.setPixmap(pm)
        self.thumb.setFixedSize(tw, th)

    def refresh_fav(self):
        cat = self.page.ctx.favorites.category_of(self.rec["id"])
        t = self.page.t
        self.b_fav.setIcon(make_star_icon(18, bool(cat)))
        self.b_fav.setToolTip(t(M.TIP_FAV_REMOVE if cat else M.TIP_FAV_ADD))
        self.cat.setText(self.page.ctx.favorites.label(cat) if cat else "")
        self.cat.setVisible(bool(cat) and not self.rec.get("_child"))

    def _sync_entry(self):
        """The Playlist Sync entry of this playlist (None = not set up for synchronisation)."""
        if not self.rec.get("is_playlist"):
            return None
        pid = self.rec.get("playlist_id") or playlist_id(self.rec.get("url", ""))
        return self.page.ctx.sync.find(pid) if pid else None

    def refresh_sync(self):
        """The sync button of a playlist is lit when the playlist is set up to synchronise (and switched on) (2.2.2)."""
        if not self.rec.get("is_playlist"):
            return
        e = self._sync_entry()
        on = bool(e and e.get("enabled", True))
        set_sync_button(self.b_play, on)
        self.b_play.setToolTip(self.page.t(M.TIP_SYNC_ON if on else M.TIP_SYNC))

    # --- actions ---------------------------------------------------------
    def _play(self):
        path = _full_path(self.rec)
        if os.path.isfile(path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        else:
            self.page.message(self.page.t(M.DL_FILE_MISSING))

    def _folder(self):
        path = _full_path(self.rec)
        d = os.path.expanduser(self.rec.get("save_dir", ""))
        if not self.rec.get("is_playlist") and os.path.isfile(path):
            reveal_file(path)
        elif os.path.isdir(d):
            QDesktopServices.openUrl(QUrl.fromLocalFile(d))
        else:
            self.page.message(self.page.t(M.ERR_NO_FOLDER))

    def _sync(self):
        """Sync now. A playlist that is not set up yet is also added to Playlist Sync (daily) and the button turns on."""
        sm = self.page.ctx.sync
        pid = self.rec.get("playlist_id") or playlist_id(self.rec.get("url", ""))
        e = self._sync_entry()
        if pid and e is None:
            sm.add(pid, self.rec["id"], self.rec.get("url", ""), self.rec.get("title", ""), "daily")
            self.page.changed.emit()                         # the Playlist Sync page / other page reload
        elif e is not None and not e.get("enabled", True):
            e["enabled"] = True
            sm.save()
            self.page.changed.emit()
        self.refresh_sync()
        self.page.sync_requested.emit(self.rec)

    def _again(self):
        self.page.redownload.emit(self.rec)

    def _details(self):
        self.page.show_details(self.rec, self._src)

    def _fav(self):
        self.page.toggle_favorite(self.rec)

    def _delete(self):
        self.page.delete_record(self.rec)


# ----------------------------------------------------------------------
class LibraryPage(QWidget):
    redownload = Signal(object)        # history record -> main window opens New Download with it
    changed = Signal()                 # favorites / history changed here -> the other page reloads
    _thumbs_done = Signal(str)         # worker thread -> pictures of an opened playlist are ready
    sync_requested = Signal(object)    # "Sync now" of a playlist card -> main window opens the sync window

    def __init__(self, ctx: AppContext, mode: str = "library"):
        super().__init__()
        self.ctx, self.mode = ctx, mode
        self.t = ctx.lang.tr
        self.cards: list[VideoCard] = []
        self._pix: dict = {}
        self._dirty = True
        self._rows = 0
        self._scale = 1.0
        self._style_key = -1
        self._kind = None              # vault folder filter: None / video / audio / playlist
        self._open = None              # the playlist record opened by double-click (None = the normal list)
        self._build()
        self._thumbs_done.connect(self._on_thumbs)
        self.search.textChanged.connect(lambda _=None: self.refresh())
        self.filter.currentIndexChanged.connect(lambda _=None: self.refresh())
        self.sort.currentIndexChanged.connect(lambda _=None: self.refresh())

    # ------------------------------------------------------------------
    def _build(self):
        t = self.t
        archive = self.mode == "archive"            # Archive: all downloads in vaults.  Library: favorites by category
        root = QHBoxLayout(self)
        root.setContentsMargins(22, 16, 22, 14)
        root.setSpacing(16)

        self.vault = QWidget()                              # left: My Digital Vault
        vl = QVBoxLayout(self.vault)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(6)
        self.vault_title = QLabel(t(M.LIB_VAULT))
        self.vault_title.setObjectName("pageTitle")
        vl.addWidget(self.vault_title)
        self.tiles = {}
        for kind, name in (("video", M.LIB_VIDEOS), ("audio", M.LIB_MUSIC), ("playlist", M.LIB_PLAYLISTS)):
            tile = FolderTile(kind, t(name))
            tile.clicked.connect(self._tile_clicked)
            vl.addWidget(tile, 1)
            self.tiles[kind] = tile
        root.addWidget(self.vault, 3)
        self.vault.setVisible(archive)

        right = QVBoxLayout()
        right.setSpacing(10)
        self.title = QLabel(t(M.LIB_RECENT if archive else M.ARCHIVE_TITLE))
        self.title.setObjectName("pageTitle")
        right.addWidget(self.title)
        self.back = QPushButton(t(M.LIB_BACK))               # shown while a playlist is opened
        self.back.setObjectName("btnBlue")
        self.back.setCursor(Qt.PointingHandCursor)
        self.back.clicked.connect(self.close_playlist)
        self.back.setVisible(False)
        right.addWidget(self.back, 0, Qt.AlignLeft)
        bar = QHBoxLayout()
        bar.setSpacing(10)
        self.search = QLineEdit()
        self.search.setPlaceholderText(t(M.DL_SEARCH))
        self.search.setMinimumWidth(90)
        self.sort = ArrowComboBox()
        for label, key in ((M.SORT_DATE, "date"), (M.SORT_SIZE, "size"), (M.SORT_NAME, "name")):
            self.sort.addItem(t(label), key)
        self.filter = ArrowComboBox()
        bar.addWidget(self.search, 3)
        bar.addWidget(self.sort, 2)
        if not archive:                                     # the category drop-down belongs to the Library only
            bar.addWidget(self.filter, 2)
        self.filter.setVisible(not archive)
        right.addLayout(bar)
        self.count = QLabel("")
        self.count.setObjectName("muted")
        right.addWidget(self.count)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)   # constant width -> stable grid
        body = QWidget()
        body.setStyleSheet("background: transparent;")
        self.grid = QGridLayout(body)
        self.grid.setContentsMargins(4, 4, 4, 4)
        self.grid.setSpacing(14)
        self.scroll.setWidget(body)
        right.addWidget(self.scroll, 1)
        self.empty = QLabel("")
        self.empty.setObjectName("emptyMsg")
        self.empty.setAlignment(Qt.AlignCenter)
        self.empty.setWordWrap(True)
        right.addWidget(self.empty, 1)
        root.addLayout(right, 7)

    def open_playlist(self, rec: dict):
        """Double-click on a playlist: its videos, in the playlist order, in this work area."""
        self._open = rec
        self.refresh()
        missing = [r for r in self._playlist_items(rec) if not r.get("thumb")]
        if missing:
            import threading
            threading.Thread(target=self._fetch_thumbs, args=([r["id"].split(":", 1)[1] for r in missing], rec["id"]),
                             daemon=True).start()

    def _fetch_thumbs(self, vids: list, rid: str):
        """Worker thread: the YouTube picture of each video -> data/history/thumbs/pl_<id>.img."""
        import urllib.request
        from app.paths import THUMBS_DIR
        got = False
        for vid in vids:
            try:
                THUMBS_DIR.mkdir(parents=True, exist_ok=True)
                with urllib.request.urlopen(f"https://i.ytimg.com/vi/{vid}/mqdefault.jpg", timeout=8) as r:
                    data = r.read()
                if data:
                    (THUMBS_DIR / f"pl_{vid}.img").write_bytes(data)
                    got = True
            except Exception:
                continue
        if got:
            self._thumbs_done.emit(rid)

    def _on_thumbs(self, rid: str):
        if self._open is not None and self._open.get("id") == rid:
            self._pix = {k: v for k, v in self._pix.items() if not k.startswith(rid + ":")}
            self.refresh()

    def close_playlist(self):
        self._open = None
        self.refresh()

    def _playlist_items(self, rec: dict) -> list:
        """The downloaded videos of a playlist record as card records, in playlist order (file number, else saved order)."""
        import re
        from app.paths import THUMBS_DIR
        items = []
        for i, (vid, v) in enumerate((rec.get("videos") or {}).items()):
            if v.get("state", "downloaded") != "downloaded":
                continue
            f = v.get("file", "")
            full = f if os.path.isabs(f) else os.path.join(os.path.expanduser(rec.get("save_dir", "")), f)
            m = re.match(r"\s*(\d+)", os.path.basename(f))
            ext = os.path.splitext(f)[1].lstrip(".").lower() or rec.get("extension", "")
            items.append(((int(m.group(1)) if m else 10 ** 6 + i, i), {
                "id": f"{rec['id']}:{vid}", "title": v.get("title", vid), "file_name": os.path.basename(full),
                "save_dir": os.path.dirname(full), "extension": ext, "quality": rec.get("quality", ""),
                "date": v.get("date", ""), "size": v.get("size", 0), "format": rec.get("format", ext),
                "url": "https://www.youtube.com/watch?v=" + vid, "is_playlist": False, "_child": True,
                "thumb": (f"pl_{vid}.img" if (THUMBS_DIR / f"pl_{vid}.img").is_file() else "")}))
        return [r for _k, r in sorted(items, key=lambda x: x[0])]

    def _tile_clicked(self, kind: str):
        self._open = None
        self._kind = kind                                    # 2.2.7: every click filters by that kind (no toggling back)
        for k, tile in self.tiles.items():
            tile.set_selected(k == self._kind)
        self.refresh()

    # ------------------------------------------------------------------
    # data -> cards
    # ------------------------------------------------------------------
    def mark_dirty(self):
        """History or favorites changed somewhere else; reloaded when the page is shown."""
        self._dirty = True
        if self.isVisible():
            self.refresh()

    def thumb_source(self, rec: dict):
        rid = rec["id"]
        if rid not in self._pix:
            path = self.ctx.history.thumb_path(rec)
            pm = QPixmap(path) if path else None
            self._pix[rid] = pm if pm is not None and not pm.isNull() else None
        return self._pix[rid]

    def _fill_filter(self):
        t, fav = self.t, self.ctx.favorites
        cur = self.filter.currentData() or FILTER_FAV
        self.filter.blockSignals(True)
        self.filter.clear()
        self.filter.addItem("★ " + t(M.DL_FILTER_FAV), FILTER_FAV)
        for c in fav.used_categories():
            ic = fav.icon_of(c)                                  # the category's own icon (a picture) beside its name
            if ic:
                self.filter.addItem(make_emoji_icon(ic, 22), c, "cat:" + c)
            else:
                self.filter.addItem(c, "cat:" + c)
        i = self.filter.findData(cur)
        self.filter.setCurrentIndex(i if i >= 0 else 0)
        self.filter.blockSignals(False)

    def _matches(self, rec: dict, text: str, flt: str) -> bool:
        cat = self.ctx.favorites.category_of(rec["id"])
        if self.mode == "library":                          # Library = favorites only (a category drop-down)
            if not cat:
                return False
            if flt.startswith("cat:") and cat != flt[4:]:
                return False
        if self._kind and kind_of(rec) != self._kind:
            return False
        if text:
            hay = " ".join(str(rec.get(k, "")) for k in ("title", "file_name", "url", "extension", "quality", "date")).lower()
            return text in hay
        return True

    def _sorted(self, recs: list) -> list:
        key = self.sort.currentData() or "date"
        if key == "size":
            return sorted(recs, key=lambda r: r.get("size", 0), reverse=True)
        if key == "name":
            return sorted(recs, key=lambda r: (r.get("title") or "").lower())
        return sorted(recs, key=lambda r: r.get("date", ""), reverse=True)     # newest first

    def _update_tiles(self):
        t, recs = self.t, self.ctx.history.records
        n = {"video": 0, "audio": 0, "playlist": 0}
        for r in recs:
            n[kind_of(r)] += 1
        self.tiles["video"].set_count(t(M.LIB_FILES, n=n["video"]))
        self.tiles["audio"].set_count(t(M.LIB_FILES, n=n["audio"]))
        self.tiles["playlist"].set_count(t(M.LIB_PL_COUNT, n=n["playlist"]))

    def refresh(self):
        self._dirty = False
        self._fill_filter()
        self._update_tiles()
        for c in self.cards:
            self.grid.removeWidget(c)
            c.deleteLater()
        self.cards = []
        if self._open is not None and self._open not in self.ctx.history.records:
            self._open = None                                 # the playlist was deleted meanwhile
        self.back.setVisible(self._open is not None)
        if self._open is not None:
            items = self._playlist_items(self._open)
            self.count.setText(f"{self._open.get('title', '')}  -  " + self.t(M.DL_FILES, count=len(items)))
            for rec in items[:MAX_CARDS]:
                self.cards.append(VideoCard(self, rec))
            self.scroll.setVisible(bool(self.cards))
            self.empty.setVisible(not self.cards)
            self.empty.setText(self.t(M.DL_EMPTY_FILTER))
            self._layout_cards()
            return
        alive = {r["id"] for r in self.ctx.history.records}
        self._pix = {k: v for k, v in self._pix.items() if k in alive}
        text = self.search.text().strip().lower()
        flt = self.filter.currentData() or FILTER_ALL
        recs = self._sorted([r for r in self.ctx.history.records if self._matches(r, text, flt)])
        total = len([r for r in self.ctx.history.records
                     if self.mode == "archive" or self.ctx.favorites.is_favorite(r["id"])])
        self.count.setText(self.t(M.DL_COUNT, n=total))
        for rec in recs[:MAX_CARDS]:
            self.cards.append(VideoCard(self, rec))
        has = bool(self.cards)
        self.scroll.setVisible(has)
        self.empty.setVisible(not has)
        self.empty.setText(self.t((M.DL_EMPTY if self.mode == "archive" else M.LIB_EMPTY_FAV) if total == 0
                                  else M.DL_EMPTY_FILTER))
        self._layout_cards()

    def _layout_cards(self):
        """Responsive grid: as many columns as fit, cards share the width."""
        if not self.cards:
            return
        gap = self.grid.spacing()
        avail = self.scroll.viewport().width() - 16
        min_w = int(200 * self._scale)
        cols = max(1, (avail + gap) // (min_w + gap))
        w = max(150, (avail - gap * (cols - 1)) // cols)
        while self.grid.count():
            self.grid.takeAt(0)
        for i in range(self._rows + 1):
            self.grid.setRowStretch(i, 0)
        for i, card in enumerate(self.cards):
            card.set_width(w)
            self.grid.addWidget(card, i // cols, i % cols, Qt.AlignTop | Qt.AlignLeft)
        self._rows = (len(self.cards) - 1) // cols + 1
        self.grid.setRowStretch(self._rows, 1)                       # push the cards to the top
        self.grid.setColumnStretch(cols, 1)

    def showEvent(self, e):
        if self._dirty:
            self.refresh()
        super().showEvent(e)

    def resizeEvent(self, e):
        self._scale = max(0.7, min(1.4, min(self.width() / 700.0, self.height() / 520.0)))
        key = int(self._scale * 20)
        if key != self._style_key:
            self._style_key = key
            self._apply_style()
        self._layout_cards()
        super().resizeEvent(e)

    def _apply_style(self):
        s = self._scale
        self.setStyleSheet(
            f"#vTitle{{font-size:{int(15 * s)}px;}} #vSub{{font-size:{int(12 * s)}px;}}"
            f" #vSize{{font-size:{int(13 * s)}px;}} #pageTitle{{font-size:{int(22 * s)}px;}}")

    # ------------------------------------------------------------------
    # actions of the cards
    # ------------------------------------------------------------------
    def message(self, text: str):
        exec_blurred(self, MessageDialog(self.ctx.lang, self.t(M.ERR_TITLE), text, self.window()))

    def show_details(self, rec: dict, pixmap=None):
        exec_blurred(self, DetailsDialog(self.ctx.lang, rec, pixmap, self.ctx.favorites.label(
            self.ctx.favorites.category_of(rec["id"])) if self.ctx.favorites.category_of(rec["id"]) else "",
            self.window()))

    def toggle_favorite(self, rec: dict):
        fav = self.ctx.favorites
        if fav.is_favorite(rec["id"]):
            fav.remove(rec["id"])
        elif not add_to_favorites(self.ctx, rec, self.window(), blur=True):
            return
        self.changed.emit()
        self.refresh()

    def delete_record(self, rec: dict):
        """Delete button: asks whether the physical file(s) go too. Yes = the entry AND the file(s) are deleted (for a
        playlist: all its files and its folder); No = only the entry is removed from the list."""
        t = self.t
        pl = bool(rec.get("is_playlist"))
        name = rec.get("title") or rec.get("file_name", "")
        ask = t(M.DEL_ASK_PL, count=rec.get("count", 0)) if pl else t(M.DEL_ASK_FILE)
        buttons = [("file", t(M.DEL_YES_PL if pl else M.DEL_YES_FILE), "btnRed"),
                   ("list", t(M.DEL_NO_FILE), "btnBlue"), ("cancel", t(M.BTN_CANCEL1), "btnOrange")]
        dlg = ChoiceDialog(self.ctx.lang, t(M.DEL_TITLE), f"{name}\n\n{ask}", buttons, self.window())
        exec_blurred(self, dlg)
        if dlg.choice not in ("list", "file"):
            return
        if dlg.choice == "file":
            _n, errors = delete_files(rec, protect=[self.ctx.settings.download_dir()])
            if errors:
                self.message(t(M.DEL_PARTIAL, detail="; ".join(errors[:3])))
                if not pl:
                    return                                   # the file is still there: keep the entry
        if pl and rec.get("playlist_id"):
            self.ctx.sync.remove(rec["playlist_id"])         # a deleted playlist is not synchronized any more
        self.ctx.history.remove(rec["id"])
        self.ctx.favorites.remove(rec["id"])
        self.changed.emit()
        self.refresh()
