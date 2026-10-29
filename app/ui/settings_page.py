# =============================================================================
# TubeArchive Pro  |  Version 2.3.1  |  File: app/ui/settings_page.py
# Version history of this file:
#   2.3.2 - the page fits its frame at any window size (smaller minimum scale, more fitting steps)
#   2.3.1 - 'MP4 = H.264 + AAC' switch (mp4_h264)
#   2.3.0 - 'Check for updates now' button (update_requested)
#   2.3.0 - 'Share anonymous usage information' check box (share_usage)
#   2.2.7 - 'Sound effects' check box (sounds_enabled)
#   2.2.3 - auto_clear_completed check box
#   2.2.2 - Bigger fonts (MIN_SCALE 0.85, scroll instead of shrinking), two columns only from 820 px
#   2.0.5 - One font size for every text of the page (labels, boxes, check boxes, buttons); fit also measures wrapped
#           text and width, and runs when the page is shown
#   2.0.4 - Buttons use mnemonic_safe: 'Apply & Save' shows its &
#   2.0.3 - _fit(): the content is measured and the scale lowered until every card is visible (any window size)
#   2.0.2 - 'Videos of one playlist at the same time' (playlist_concurrent, default 1); settings changed elsewhere are
#           shown here at once (subscribe); text follows the height of the work area too
#   2.0.1 - The page follows the size of the work area (fonts, spacing, one / two columns) like New Download;
#           max concurrent downloads default 3 (1-10, one yt-dlp process each); 'Max network bandwidth' (0 = no limit)
#           is shared by all running downloads; the queue is told when a setting changed
#   1.0.14 - New design (Advanced Settings mock-up): Audio Quality, Default Save Location, Advanced Connection & Downloads,
#            Save & Apply / Reset to Default / Cancel; plus Interface & Video Defaults, Favorite Categories
#            (add / edit / delete with icons) and Notifications
#   1.0.13 - Notification: new program version (update_notify)
#   1.0.12 - New working Settings page: language, default folder / format / quality, notifications,
#            Save and Restore Defaults (current_settings.json / default_settings.json)
# =============================================================================
"""Settings: saved in data/config/current_settings.json; the factory values are in default_settings.json.
Favorite categories are saved at once in the favorites file (not by Save & Apply)."""
import os

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (QCheckBox, QDialog, QFileDialog, QFrame, QGridLayout, QHBoxLayout, QLabel,
                               QLineEdit, QPushButton, QScrollArea, QSlider, QSpinBox, QVBoxLayout, QWidget)

from ..context import AppContext
from ..downloader import (AUDIO_FORMATS, VIDEO_FORMATS, parse_quality, quality_label, quality_options)
from ..msg import M
from .actions import exec_blurred
from .dialogs import CategoryDialog, ChoiceDialog
from .icons import make_emoji_icon, make_trash_icon
from .theme import glow
from .widgets import ArrowComboBox, ToggleSwitch, mnemonic_safe


MIN_SCALE = 0.6             # 2.3.2: the cards shrink down to this scale so that the whole page fits the frame at any window size
                            # (below it the page scrolls instead)


class _Collector:
    """Collects the cards of one column; SettingsPage._relayout() puts them into the real layouts."""

    def __init__(self, store: list):
        self.store = store

    def addWidget(self, w):
        self.store.append(w)

    def addStretch(self, _n=1):
        pass


class SettingsPage(QWidget):
    saved = Signal()                      # settings were saved / restored -> the other pages read them again
    language_requested = Signal(str)      # the language was changed -> the main window rebuilds itself
    update_requested = Signal()          # 2.3.0: 'Check for updates now'
    favorites_changed = Signal()          # a category was added / edited / deleted

    def __init__(self, ctx: AppContext):
        super().__init__()
        self.ctx = ctx
        t = ctx.lang.tr
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 18, 24, 14)
        outer.setSpacing(10)
        title = QLabel(t(M.SET_TITLE))
        title.setObjectName("pageTitle")
        outer.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        holder = self.holder = QWidget()
        self.scroll = scroll
        self.cols = cols = QHBoxLayout(holder)
        cols.setContentsMargins(0, 0, 8, 0)
        cols.setSpacing(16)
        self.col_l, self.col_r = QVBoxLayout(), QVBoxLayout()
        for c in (self.col_l, self.col_r):
            c.setSpacing(14)
            cols.addLayout(c, 1)
        self._left_cards, self._right_cards = [], []              # cards of the left / right column (see _relayout)
        self._card_boxes = []
        self._scale, self._wide = 0.0, None
        left = _Collector(self._left_cards)
        right = _Collector(self._right_cards)

        # ================= left column =================
        card, g = self._card(t(M.ST_AUDIO))                                   # Audio Quality Settings
        self.audio_fmt = ArrowComboBox()
        for f in AUDIO_FORMATS:
            self.audio_fmt.addItem(f"{f} (.{f.lower()})", f)
        self.audio_fmt.currentIndexChanged.connect(lambda _i: self._fill_audio_quality())
        self.audio_q = ArrowComboBox()
        self.audio_q.currentIndexChanged.connect(lambda _i: self._hq())
        self.hq = QLabel("HQ")
        self.hq.setObjectName("hqBadge")
        self.hq.setAlignment(Qt.AlignCenter)
        self.hq.setFixedWidth(38)
        self.convert = ToggleSwitch()
        self.extract = ToggleSwitch()
        self._stack(g, 0, t(M.ST_AUDIO_FMT), self.audio_fmt)
        self._stack(g, 2, t(M.ST_AUDIO_BR), self.audio_q, self.hq)
        self._toggle(g, 4, t(M.ST_CONVERT), self.convert)
        self._toggle(g, 5, t(M.ST_EXTRACT), self.extract)
        left.addWidget(card)

        card, g = self._card(t(M.ST_INTERFACE))                               # Interface & Video Defaults
        self.lang = ArrowComboBox()
        for code, name in ctx.lang.available.items():
            self.lang.addItem(name, code)
        self.fmt = ArrowComboBox()
        for f in VIDEO_FORMATS:
            self.fmt.addItem(f"{f} · {t(M.ND_VIDEO_TAG)}", f)
        self.quality = ArrowComboBox()
        self.fmt.currentIndexChanged.connect(lambda _i: self._fill_video_quality())
        self.ads = QCheckBox(t(M.SET_ADS))
        self._stack(g, 0, t(M.SET_LANGUAGE), self.lang)
        self._stack(g, 2, t(M.ST_DEF_FORMAT), self.fmt)
        self._stack(g, 4, t(M.ST_DEF_QUALITY), self.quality)
        g.addWidget(self.ads, 6, 0, 1, 2)
        left.addWidget(card)

        card, g = self._card(t(M.ST_FAV))                                     # Favorite Categories
        self.cats = ArrowComboBox()
        self.cat_edit = self._mini("✎", t(M.ST_FAV_EDIT), self._edit_category)
        self.cat_del = self._mini("", t(M.ST_FAV_DEL), self._delete_category)
        self.cat_del.setIcon(make_trash_icon(18))
        row = QHBoxLayout()
        row.setSpacing(6)
        row.addWidget(self.cats, 1)
        row.addWidget(self.cat_edit)
        row.addWidget(self.cat_del)
        g.addLayout(row, 0, 0, 1, 2)
        add = QPushButton("+  " + t(M.ST_FAV_ADD))
        add.setObjectName("secondary")
        add.setCursor(Qt.PointingHandCursor)
        add.setMinimumHeight(38)
        add.clicked.connect(self._add_category)
        g.addWidget(add, 1, 0, 1, 2)
        self.fav_quiet = QCheckBox(t(M.ST_FAV_NOTIFY))
        g.addWidget(self.fav_quiet, 2, 0, 1, 2)
        left.addWidget(card)
        left.addStretch(1)

        # ================= right column =================
        card, g = self._card(t(M.ST_SAVE_LOC))                                # Default Save Location
        self.folder = QLineEdit()
        browse = QPushButton(t(M.ST_BROWSE))
        browse.setObjectName("btnBlue")
        browse.setCursor(Qt.PointingHandCursor)
        browse.setMinimumHeight(36)
        browse.clicked.connect(self._browse)
        self.subfolders = QCheckBox(t(M.ST_SUBFOLDERS))
        self.overwrite = QCheckBox(t(M.ST_OVERWRITE))
        g.addWidget(self.folder, 0, 0)
        g.addWidget(browse, 0, 1)
        g.addWidget(self.subfolders, 1, 0, 1, 2)
        g.addWidget(self.overwrite, 2, 0, 1, 2)
        g.setColumnStretch(0, 1)
        right.addWidget(card)

        card, g = self._card(t(M.ST_CONN))                                    # Advanced Connection & Downloads
        self.concurrent = QSpinBox()
        self.concurrent.setObjectName("smallSpin")
        self.concurrent.setRange(1, 10)                                        # one yt-dlp process each (default 3)
        self.pl_concurrent = QSpinBox()                                        # videos of ONE playlist at the same time
        self.pl_concurrent.setObjectName("smallSpin")
        self.pl_concurrent.setRange(1, 10)
        self.pl_concurrent.setToolTip(t(M.ST_PL_CONCURRENT_TIP))
        self.speed = QSlider(Qt.Horizontal)
        self.speed.setRange(0, 100)                                           # MB/s, 0 = No Limit
        self.speed_lbl = QLabel("")
        self.speed_lbl.setObjectName("setValue")
        self.speed.valueChanged.connect(self._speed_text)
        self.fallback = ToggleSwitch()
        self.embed = ToggleSwitch()
        lb = QLabel(t(M.ST_CONCURRENT))
        lb.setObjectName("setLabel")
        g.addWidget(lb, 0, 0)
        g.addWidget(self.concurrent, 0, 1)
        lb = QLabel(t(M.ST_PL_CONCURRENT))
        lb.setObjectName("setLabel")
        lb.setToolTip(t(M.ST_PL_CONCURRENT_TIP))
        g.addWidget(lb, 1, 0)
        g.addWidget(self.pl_concurrent, 1, 1)
        lb = QLabel(t(M.ST_SPEED))
        lb.setObjectName("setLabel")
        g.addWidget(lb, 2, 0)
        g.addWidget(self.speed_lbl, 2, 1, Qt.AlignRight)
        g.addWidget(self.speed, 3, 0, 1, 2)
        self._toggle(g, 4, t(M.ST_FALLBACK), self.fallback)
        self._toggle(g, 5, t(M.ST_EMBED), self.embed)
        self.h264 = ToggleSwitch()                                            # 2.3.1: MP4 = H.264 + AAC
        self._toggle(g, 6, t(M.ST_H264), self.h264)
        self.auto_clear = QCheckBox(t(M.ST_AUTO_CLEAR))                       # same option as the check box of Downloads
        g.addWidget(self.auto_clear, 7, 0, 1, 2)
        g.setColumnStretch(0, 1)
        right.addWidget(card)

        card, g = self._card(t(M.ST_NOTIFY))                                  # Notifications
        self.n_success = QCheckBox(t(M.ST_NOTIFY_SUCCESS))
        self.n_sync = QCheckBox(t(M.ST_NOTIFY_SYNC))
        self.n_new = QCheckBox(t(M.ST_NOTIFY_NEW))
        self.n_update = QCheckBox(t(M.ST_NOTIFY_UPDATE))
        self.n_sounds = QCheckBox(t(M.ST_SOUNDS))                            # 2.2.7: sound effects on / off
        self.n_share = QCheckBox(t(M.ST_SHARE_USAGE))                        # 2.3.0: install register on / off
        for r, cb in enumerate((self.n_success, self.n_sync, self.n_new, self.n_update, self.n_sounds, self.n_share)):
            g.addWidget(cb, r, 0)
        self.b_updates = QPushButton(t(M.ST_UPD_NOW))                         # 2.3.0: check for updates now
        self.b_updates.setObjectName("btnBlue")
        self.b_updates.setMinimumHeight(42)
        self.b_updates.setCursor(Qt.PointingHandCursor)
        self.b_updates.clicked.connect(self.update_requested.emit)
        g.addWidget(self.b_updates, 6, 0)
        right.addWidget(card)
        right.addStretch(1)

        scroll.setWidget(holder)
        outer.addWidget(scroll, 1)
        self.outer = outer
        self.title_lbl = title

        # ================= buttons =================
        self.status = QLabel("")
        self.status.setObjectName("setStatus")
        outer.addWidget(self.status)
        row = QHBoxLayout()
        row.setSpacing(16)
        for name, msg, col, fn in (("btnGreen", M.ST_APPLY, "#1fd16a", self.save),
                                   ("btnOrange", M.ST_RESET, "#ffa800", self.restore_defaults),
                                   ("btnRed", M.BTN_CANCEL1, "#ff2f72", self.discard)):
            b = QPushButton(mnemonic_safe(t(msg)))           # 'Apply & Save' keeps its &
            b.setObjectName(name)
            b.setMinimumHeight(48)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(fn)
            glow(b, col, 18)
            row.addWidget(b, 1)
        outer.addLayout(row)
        self.btn_row = row
        self._saving = False
        self.load()
        self._relayout(True)
        ctx.settings.subscribe(self._on_setting)                  # a 'don't show again' tick elsewhere shows here at once

    # ------------------------------------------------------------------ size of the work area
    def _relayout(self, wide: bool):
        """Two columns (like the mock-up) while there is room, one column in a narrow work area."""
        if wide == self._wide:
            return
        self._wide = wide
        for col in (self.col_l, self.col_r):
            while col.count():
                col.takeAt(0)
        first = self._left_cards if wide else self._left_cards + self._right_cards
        for w in first:
            self.col_l.addWidget(w)
        self.col_l.addStretch(1)
        if wide:
            for w in self._right_cards:
                self.col_r.addWidget(w)
            self.col_r.addStretch(1)
        self.cols.setStretch(1, 1 if wide else 0)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._fit()

    def showEvent(self, e):
        super().showEvent(e)
        QTimer.singleShot(0, self._fit)                       # the real size is known once the page is shown

    def _fit(self):
        """Every card must be visible at any window size: the page starts from the scale that suits the size of the
        work area, then the content is measured and the scale is lowered until it fits without scrolling (2.0.3)."""
        if getattr(self, "_fitting", False):
            return
        self._fitting = True
        try:
            self._relayout(self.width() >= 820)
            s = max(MIN_SCALE, min(1.35, min(self.width() / 760.0, self.height() / 700.0)))
            s = round(s * 20) / 20.0
            for _ in range(24):
                self._rescale(s)
                lay = self.holder.layout()
                lay.activate()
                avail = self.scroll.viewport().height()
                width = max(100, self.scroll.viewport().width())
                need = lay.sizeHint().height()
                if lay.hasHeightForWidth():                                   # wrapped texts need more height
                    need = max(need, lay.totalHeightForWidth(width))
                too_wide = lay.minimumSize().width() > width + 2
                if avail < 60 or (need + 10 <= avail and not too_wide) or s <= MIN_SCALE:
                    break
                s = round((s - 0.05) * 20) / 20.0
        finally:
            self._fitting = False

    def _rescale(self, s: float):
        """Fonts, spacing and control heights follow the size of the work area."""
        if abs(s - self._scale) < 0.02:
            return
        self._scale = s

        def r(x):
            return max(1, int(x * s))
        self.outer.setContentsMargins(r(22), r(14), r(22), r(10))
        self.outer.setSpacing(r(8))
        self.cols.setSpacing(r(14))
        for c in (self.col_l, self.col_r):
            c.setSpacing(r(12))
        for v, g in self._card_boxes:
            v.setContentsMargins(r(16), r(10), r(16), r(12))
            v.setSpacing(r(6))
            g.setHorizontalSpacing(r(10))
            g.setVerticalSpacing(r(6))
        self.setStyleSheet(f"""
            #pageTitle {{ font-size: {r(25)}px; }}
            #cardTitle {{ font-size: {r(21)}px; }}
            #setLabel, #setValue, #setStatus, QCheckBox, QLabel#hqBadge {{ font-size: {r(17)}px; }}
            QLineEdit, QComboBox, QSpinBox, QSpinBox#smallSpin, QComboBox QAbstractItemView
                {{ font-size: {r(17)}px; }}
            QLineEdit, QComboBox, QSpinBox {{ padding: {r(5)}px {r(8)}px; min-height: {r(24)}px; }}
            QPushButton#miniBtn, QPushButton#secondary, QPushButton#btnBlue {{ font-size: {r(17)}px; }}
            QPushButton#secondary {{ padding: {r(6)}px {r(12)}px; }}
            QPushButton#btnGreen, QPushButton#btnOrange, QPushButton#btnRed
                {{ font-size: {r(18)}px; padding: {r(6)}px {r(8)}px; }}
        """)
        for i in range(self.btn_row.count()):
            w = self.btn_row.itemAt(i).widget()
            if w:
                w.setMinimumHeight(r(44))
        self.speed_lbl.setMinimumWidth(r(70))

    # ------------------------------------------------------------------ building helpers
    def _card(self, title: str):
        f = QFrame()
        f.setObjectName("optCard")
        v = QVBoxLayout(f)
        v.setContentsMargins(18, 12, 18, 16)
        v.setSpacing(8)
        lb = QLabel(title)
        lb.setObjectName("cardTitle")
        v.addWidget(lb)
        g = QGridLayout()
        g.setHorizontalSpacing(12)
        g.setVerticalSpacing(8)
        g.setColumnStretch(0, 1)
        v.addLayout(g)
        self._card_boxes.append((v, g))
        return f, g

    @staticmethod
    def _stack(g: QGridLayout, row: int, text: str, widget, extra=None):
        """Label above a drop-down (like the mock-up); `extra` sits at the right of the drop-down."""
        lb = QLabel(text)
        lb.setObjectName("setLabel")
        g.addWidget(lb, row, 0, 1, 2)
        g.addWidget(widget, row + 1, 0)
        if extra is not None:
            g.addWidget(extra, row + 1, 1)

    @staticmethod
    def _toggle(g: QGridLayout, row: int, text: str, sw: ToggleSwitch):
        lb = QLabel(text)
        lb.setObjectName("setLabel")
        lb.setWordWrap(True)
        g.addWidget(lb, row, 0)
        g.addWidget(sw, row, 1, Qt.AlignRight)

    @staticmethod
    def _mini(text: str, tip: str, slot) -> QPushButton:
        b = QPushButton(text)
        b.setObjectName("miniBtn")
        b.setToolTip(tip)
        b.setFixedSize(38, 36)
        b.setCursor(Qt.PointingHandCursor)
        b.clicked.connect(slot)
        return b

    # ------------------------------------------------------------------ dependent controls
    def _fill_quality(self, combo, fmt: str, wanted):
        t = self.ctx.lang.tr
        combo.blockSignals(True)
        combo.clear()
        for q in quality_options(fmt, 0):
            combo.addItem(quality_label(fmt, q) or t(M.ND_BEST), q)
        i = combo.findData(wanted)
        combo.setCurrentIndex(i if i >= 0 else 0)
        combo.blockSignals(False)

    def _fill_audio_quality(self, wanted=None):
        wanted = wanted if wanted is not None else self.audio_q.currentData()
        self._fill_quality(self.audio_q, self.audio_fmt.currentData() or "MP3", wanted)
        self._hq()

    def _fill_video_quality(self, wanted=None):
        wanted = wanted if wanted is not None else self.quality.currentData()
        self._fill_quality(self.quality, self.fmt.currentData() or "MP4", wanted)

    def _hq(self):
        q = int(self.audio_q.currentData() or 0)
        fmt = self.audio_fmt.currentData() or "MP3"
        self.hq.setVisible((fmt == "MP3" and q >= 256) or (fmt == "WAV" and q >= 44100))

    def _speed_text(self, v: int):
        t = self.ctx.lang.tr
        self.speed_lbl.setText(t(M.ST_NOLIMIT) if v == 0 else t(M.ST_MBS, n=v))

    def refresh_categories(self, keep: str | None = None):
        fav = self.ctx.favorites
        self.cats.blockSignals(True)
        self.cats.clear()
        for c in fav.categories:
            ic = fav.icon_of(c)
            if ic:
                self.cats.addItem(make_emoji_icon(ic, 22), c, c)
            else:
                self.cats.addItem(c, c)
        if not fav.categories:
            self.cats.addItem(self.ctx.lang.tr(M.CAT_NONE), None)
        i = self.cats.findData(keep) if keep else 0
        self.cats.setCurrentIndex(max(0, i))
        self.cats.blockSignals(False)
        has = bool(fav.categories)
        self.cat_edit.setEnabled(has)
        self.cat_del.setEnabled(has)

    # ------------------------------------------------------------------ load / save
    def load(self):
        """Show the saved settings in the controls."""
        st = self.ctx.settings
        self.lang.setCurrentIndex(max(0, self.lang.findData(st.get("language", "en"))))
        self.folder.setText(str(st.download_dir()))
        self.fmt.blockSignals(True)
        self.fmt.setCurrentIndex(max(0, self.fmt.findData(st.get("default_format", "MP4"))))
        self.fmt.blockSignals(False)
        self._fill_video_quality(parse_quality(st.get("default_quality", 0)))
        self.audio_fmt.blockSignals(True)
        self.audio_fmt.setCurrentIndex(max(0, self.audio_fmt.findData(st.get("audio_format", "MP3"))))
        self.audio_fmt.blockSignals(False)
        self._fill_audio_quality(parse_quality(st.get("audio_quality", 320)))
        self.convert.setChecked(bool(st.get("audio_convert", True)))
        self.extract.setChecked(bool(st.get("audio_extract", True)))
        self.ads.setChecked(bool(st.get("ads_enabled", True)))
        self.auto_clear.setChecked(bool(st.get("auto_clear_completed", False)))
        self.subfolders.setChecked(bool(st.get("playlist_subfolders", True)))
        self.overwrite.setChecked(bool(st.get("overwrite_existing", False)))
        try:
            self.concurrent.setValue(int(st.get("max_concurrent", 3)))
            self.pl_concurrent.setValue(int(st.get("playlist_concurrent", 1)))
            self.speed.setValue(int(st.get("speed_limit_mb", 0)))
        except (TypeError, ValueError):
            self.concurrent.setValue(3)
            self.pl_concurrent.setValue(1)
            self.speed.setValue(0)
        self._speed_text(self.speed.value())
        self.fallback.setChecked(bool(st.get("ytdlp_fallback", True)))
        self.embed.setChecked(bool(st.get("embed_metadata", True)))
        self.h264.setChecked(bool(st.get("mp4_h264", True)))
        self.n_success.setChecked(bool(st.get("show_success_dialog", True)))
        self.n_sync.setChecked(bool(st.get("notify_sync_done", True)))
        self.n_new.setChecked(bool(st.get("notify_new_videos", True)))
        self.n_update.setChecked(bool(st.get("update_notify", True)))
        self.n_sounds.setChecked(bool(st.get("sounds_enabled", True)))
        self.n_share.setChecked(bool(st.get("share_usage", True)))
        self.fav_quiet.setChecked(not st.get("fav_notify", True))
        self.refresh_categories()

    def _browse(self):
        start = os.path.expanduser(self.folder.text().strip() or "~")
        path = QFileDialog.getExistingDirectory(self, self.ctx.lang.tr(M.ND_BROWSE_TITLE), start)
        if path:
            self.folder.setText(os.path.normpath(path))

    def save(self):
        st = self.ctx.settings
        self._saving = True                                       # our own changes do not need to be shown again
        folder = self.folder.text().strip() or str(st.defaults.get("download_dir", ""))
        old_lang = st.get("language", "en")
        for key, val in (("language", self.lang.currentData() or "en"), ("download_dir", folder),
                         ("default_format", self.fmt.currentData() or "MP4"),
                         ("default_quality", int(self.quality.currentData() or 0)),
                         ("audio_format", self.audio_fmt.currentData() or "MP3"),
                         ("audio_quality", int(self.audio_q.currentData() or 0)),
                         ("audio_convert", self.convert.isChecked()), ("audio_extract", self.extract.isChecked()),
                         ("ads_enabled", self.ads.isChecked()),
                         ("auto_clear_completed", self.auto_clear.isChecked()),
                         ("playlist_subfolders", self.subfolders.isChecked()),
                         ("overwrite_existing", self.overwrite.isChecked()),
                         ("max_concurrent", self.concurrent.value()), ("playlist_concurrent", self.pl_concurrent.value()),
                         ("speed_limit_mb", self.speed.value()),
                         ("ytdlp_fallback", self.fallback.isChecked()), ("embed_metadata", self.embed.isChecked()), ("mp4_h264", self.h264.isChecked()),
                         ("show_success_dialog", self.n_success.isChecked()),
                         ("notify_sync_done", self.n_sync.isChecked()),
                         ("notify_new_videos", self.n_new.isChecked()),
                         ("sounds_enabled", self.n_sounds.isChecked()),
                         ("share_usage", self.n_share.isChecked()),
                         ("update_notify", self.n_update.isChecked()),
                         ("fav_notify", not self.fav_quiet.isChecked())):
            st.set(key, val)
        self._saving = False
        st.save()
        self._done(M.ST_SAVED, old_lang)

    # key of the settings file -> (check box / switch, True when the box means the opposite of the setting)
    def _on_setting(self, key: str):
        """A setting was changed by another screen (e.g. 'Don't show this message again' in a window): show the same
        value here, so this page, the program and the configuration file always agree."""
        if self._saving:
            return
        if key == "*":
            self.load()
            return
        boxes = {"show_success_dialog": (self.n_success, False), "update_notify": (self.n_update, False),
                 "notify_sync_done": (self.n_sync, False), "notify_new_videos": (self.n_new, False),
                 "sounds_enabled": (self.n_sounds, False),
                 "fav_notify": (self.fav_quiet, True), "ads_enabled": (self.ads, False),
                 "auto_clear_completed": (self.auto_clear, False)}
        if key in boxes:
            box, inverse = boxes[key]
            box.setChecked(bool(self.ctx.settings.get(key, True)) != inverse)

    def restore_defaults(self):
        t = self.ctx.lang.tr
        dlg = ChoiceDialog(self.ctx.lang, t(M.ST_RESET), t(M.ST_RESTORE_ASK),
                           [("yes", t(M.ST_RESET), "btnOrange"), ("no", t(M.BTN_CANCEL1), "btnBlue")], self.window())
        exec_blurred(self, dlg)
        if dlg.choice != "yes":
            return
        old_lang = self.ctx.settings.get("language", "en")
        self.ctx.settings.reset_to_defaults()                 # copies default_settings.json -> current_settings.json
        self.load()
        self._done(M.ST_RESTORED, old_lang)

    def discard(self):
        """Cancel: the controls show the saved settings again."""
        self.load()
        self.status.setText(self.ctx.lang.tr(M.ST_DISCARDED))

    def _done(self, msg_id: str, old_lang: str):
        self.status.setText(self.ctx.lang.tr(msg_id))
        self.saved.emit()
        new_lang = self.ctx.settings.get("language", "en")
        if new_lang != old_lang:
            self.language_requested.emit(new_lang)

    # ------------------------------------------------------------------ favorite categories
    def _add_category(self):
        fav, t = self.ctx.favorites, self.ctx.lang.tr
        dlg = CategoryDialog(self.ctx.lang, t(M.CAT_TITLE), "", "", fav.categories, self.window())
        if exec_blurred(self, dlg) == QDialog.Accepted and fav.add_category(dlg.name, dlg.icon):
            self.refresh_categories(dlg.name)
            self.favorites_changed.emit()

    def _edit_category(self):
        fav, t = self.ctx.favorites, self.ctx.lang.tr
        old = self.cats.currentData()
        if not old:
            return
        others = [c for c in fav.categories if c != old]
        dlg = CategoryDialog(self.ctx.lang, t(M.CAT_EDIT_TITLE), old, fav.icon_of(old), others, self.window())
        if exec_blurred(self, dlg) == QDialog.Accepted and fav.edit_category(old, dlg.name, dlg.icon):
            self.refresh_categories(dlg.name)
            self.favorites_changed.emit()

    def _delete_category(self):
        fav, t = self.ctx.favorites, self.ctx.lang.tr
        name = self.cats.currentData()
        if not name:
            return
        dlg = ChoiceDialog(self.ctx.lang, t(M.ST_FAV_DEL), t(M.CAT_DEL_ASK, name=name),
                           [("del", t(M.CAT_DEL_BTN), "btnRed"), ("no", t(M.BTN_CANCEL1), "btnBlue")], self.window())
        exec_blurred(self, dlg)
        if dlg.choice == "del":
            fav.delete_category(name)
            self.refresh_categories()
            self.favorites_changed.emit()
