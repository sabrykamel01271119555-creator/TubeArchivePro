# =============================================================================
# TubeArchive Pro  |  Version 2.3.1  |  File: app/ui/main_window.py
# Version history of this file:
#   2.3.2 - reminds at start-up of the videos kept with 'Later' (failed downloads)
#   2.3.1 - the side links are Reviews, Help, About us (contact + donate moved into About us)
#   2.3.0 - the minimize button sends the program to the system tray (icon, Open / Exit menu)
#   2.3.0 - update_ctrl (Updates window, tool updates at startup / from Settings / after a failed download)
#   2.3.0 - blurred background without QGraphicsBlurEffect (fixes the UpdateLayeredWindowIndirect warning)
#   2.2.9 - the rating goes to feedback_form_url (Apps Script web app or Google form)
#   2.2.8 - rating: features text, Apps Script endpoint; splash numbers
#   2.2.7 - channel banner replaces 'Powered by'; due-playlists window (Sync now / Let me check / Later); click and tab sounds
#   2.2.3 - exit warning gets the number of paused downloads
#   2.2.2 - Downloads label of the side menu shows (running + waiting); Sync all and sync_changed wiring
#   2.0.5 - page_state / restore_page (language change keeps the work area); title bar re-checks button hover on resize
#   2.0.3 - Starts on New Download; gauge titles under the gauges (one font); Free space gauge shows the used part, number = free
#   2.0.2 - Exit window: the last rating is shown again; a new / changed rating is sent to the Google form
#   2.0.2 - Header = icon, name, version and the advertisement space (owner banner and footer ad removed);
#           back to the 1.0.14 look; gauges show the numbers of the scale ends
#   2.0.1 - Bright glass window; menu: Archive above Library; real Downloads page (queue); gauges: Downloaded = session
#           size vs free space at start, Free space = free vs partition, new Files gauge (running / running + waiting);
#           corner: downloads counter (title bar) and "Powered by Let's Have Fun" + Reviews / Help / About us /
#           Contact us / Donate links that open an info page in the work area; the online check (version, allowed
#           ads, counter) is made while the splash screen is shown
#   1.0.14 - Category changes refresh Library / Archive
#   1.0.13 - Update check + ads from the online folder (UpdateDialog Yes / No / don't show again); failure line in the log
#   1.0.12 - Language icon in the title bar (rebuilds the window); gauges panel with real values (network, app, downloaded, free space, disk I/O); ads refreshed from the web; notifications; working Settings page
#   1.0.11 - Playlist Sync page; one SyncController opens the sync window from New Download, Library, Archive and Playlist Sync
#   1.0.10 - Menu: New Download, Downloads (current + queue), Library (history), Archive (favorites),
#            Playlist Sync, Settings (Dashboard removed); pages change with a blur / grow-from-centre animation
#   1.0.9 - New side-menu item "Downloads" (history page); "Download again" opens New Download pre-filled
#   1.0.8 - Uses the real New Download page; exit check + 'Abort Downloads' use real downloads; gauges show the real speed
#   1.0.7 - Header banner uses assets/owner/banner.jpg; its width follows the picture's aspect ratio
#   1.0.6 - Responsive layout: _apply_scale() resizes header, banner, side menu, gauges panel and footer ad with the window
#   1.0.6 - Gauges panel uses stretch factors (5:5:3) instead of fixed minimum heights
#   1.0.0 - 1.0.5 - first version and earlier fixes (see CHANGELOG.md)
# =============================================================================
"""Main window (design guide: mainwindow-downloader.jpg).

Layout
  title bar
  header      : icon + name + version | owner banner
  body        : side menu | work area (stacked pages) + footer ads | gauges panel
"""
from PySide6.QtCore import QEvent, QObject, QPointF, QRectF, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import (QColor, QDesktopServices, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap,
                           QRadialGradient)
from PySide6.QtWidgets import (QAbstractButton, QApplication, QDialog, QMenu, QSystemTrayIcon, QFrame, QHBoxLayout, QLabel, QPushButton,
                               QSizeGrip, QVBoxLayout, QWidget)

from ..context import AppContext
from .. import sounds
from ..msg import M
from ..paths import APP_VERSION, OWNER_DIR
from ..ads import load_counter, load_links, local_ads, parse_version
from ..sysmon import NET_STEPS, DISK_STEPS, SIZE_STEPS, SysMonitor, auto_max, human_size
from .actions import exec_blurred
from .dialogs import ChoiceDialog, ExitWarningDialog, MessageDialog, RatingDialog, UpdateDialog
from .downloads_page import DownloadsPage
from .icons import make_app_icon, make_app_qicon
from .info_page import InfoPage
from .library_page import LibraryPage
from .new_download_page import NewDownloadPage
from .settings_page import SettingsPage
from .update_flow import UpdateController
from .sync_flow import SyncController
from .sync_page import SyncPage
from .widgets import GAUGE_TITLE_PX, AdBanner, ChannelBanner, MiniGauge, MorphStack, NavButton, SpeedGauge, WinButton


class Shell(QWidget):
    """Rounded glass background of the whole window."""
    radius = 18

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        g = QLinearGradient(r.topLeft(), r.bottomRight())
        g.setColorAt(0, QColor(14, 42, 118, 245))
        g.setColorAt(0.55, QColor(9, 28, 88, 247))
        g.setColorAt(1, QColor(6, 20, 66, 250))
        p.setBrush(g)
        p.setPen(QPen(QColor(110, 190, 255, 150), 1.6))
        p.drawRoundedRect(r, self.radius, self.radius)


class TitleBar(QWidget):
    def __init__(self, win, title: str):
        super().__init__()
        self.win = win
        self.setFixedHeight(46)
        h = QHBoxLayout(self)
        h.setContentsMargins(16, 6, 10, 0)
        h.setSpacing(10)
        ic = QLabel()
        ic.setPixmap(make_app_icon(28))
        txt = QLabel(title)
        txt.setObjectName("winTitle")
        h.addWidget(ic)
        h.addWidget(txt)
        h.addStretch(1)
        self.counter = QLabel("")                              # downloads counter of the program (online folder)
        self.counter.setObjectName("counterPill")
        self.counter.setVisible(False)
        h.addWidget(self.counter)
        self.lang_btn = WinButton("lang")                      # language icon: choose the interface language
        self.lang_btn.setToolTip(win.ctx.lang.tr(M.TIP_LANGUAGE))
        self.lang_btn.clicked.connect(lambda: win.show_language_menu(self.lang_btn))
        h.addWidget(self.lang_btn)
        for kind, fn in (("min", win.minimize_to_tray), ("max", win.toggle_max), ("close", win.close)):
            b = WinButton(kind)
            b.clicked.connect(fn)
            h.addWidget(b)

    def set_counter(self, total: int, tip: str):
        self.counter.setVisible(total > 0)
        self.counter.setText(f"\u2B07  {total:,}")
        self.counter.setToolTip(tip)

    def resizeEvent(self, e):
        """The window size changed (maximise / restore / drag): the buttons are at new places, so forget the old hover."""
        super().resizeEvent(e)
        self.refresh_buttons()
        QTimer.singleShot(0, self.refresh_buttons)

    def refresh_buttons(self):
        for b in self.findChildren(WinButton):
            b.sync_hover()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton and self.win.windowHandle():
            self.win.windowHandle().startSystemMove()

    def mouseDoubleClickEvent(self, e):
        self.win.toggle_max()


class ClickSound(QObject):
    """Application event filter: every click on a button (not a disabled one) plays the click sound (2.2.7)."""

    def eventFilter(self, obj, ev):
        if ev.type() == QEvent.MouseButtonRelease and isinstance(obj, QAbstractButton) and obj.isEnabled() \
                and ev.button() == Qt.LeftButton and obj.rect().contains(ev.position().toPoint()):
            sounds.play("click")
        return False


CHANNEL_URL = "https://www.youtube.com/@LetsHaveFun-ActiveMind"
CHANNEL_BANNER = OWNER_DIR / "channel_banner.jpg"


class MainWindow(QWidget):
    language_changed = Signal(str)        # main.py builds a new window in the new language
    NAV = [("new", M.NAV_NEW), ("downloads", M.NAV_DOWNLOADS), ("archive", M.NAV_QUEUE),
           ("library", M.NAV_LIBRARY), ("playlist", M.NAV_PLAYLIST), ("settings", M.NAV_SETTINGS)]
    INFO_LINKS = [("reviews", M.LNK_REVIEWS), ("help", M.LNK_HELP), ("about", M.LNK_ABOUT)]     # 2.3.1: contact + donate are in About us

    def __init__(self, ctx: AppContext):
        super().__init__()
        self.ctx = ctx
        self._exit_running = False
        self._real_speed = 0.0            # MB/s of this application (real downloads)
        self._force_close = False         # True when the window is rebuilt (language change): no exit questions
        self.mon = SysMonitor()
        self._free_at_start = None        # free space of the save partition when the program started (gauge 'Downloaded')
        self._online_tries = 0
        self._scale = 0.0                 # current UI scale (see _apply_scale)
        self._info_kind = None            # Reviews/Help/... shown in the work area (None = a normal page)
        self._logo_px = 0
        self.gauge_caps = []              # (label, base font px) of the gauges panel
        tr = ctx.lang.tr
        st = ctx.settings
        sounds.attach(st)                                          # 2.2.7: sound effects (Settings: on / off)
        sounds.preload()                                           # 2.3.0: loaded once, no delay when played
        app = QApplication.instance()
        if app is not None and not hasattr(app, "_click_sound"):
            app._click_sound = ClickSound(app)
            app.installEventFilter(app._click_sound)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowIcon(make_app_qicon())
        title = f"{tr(M.APP_NAME)} (v{APP_VERSION})"
        self.setWindowTitle(title)
        self.resize(int(st.get("window_width", 1180)), int(st.get("window_height", 740)))
        self.setMinimumSize(1020, 660)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self.shell = Shell()
        outer.addWidget(self.shell)
        root = QVBoxLayout(self.shell)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self.title_bar = TitleBar(self, title)
        root.addWidget(self.title_bar)
        root.addWidget(self._build_header(ctx))
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        body.addWidget(self._build_sidebar(ctx))
        body.addWidget(self._build_center(ctx), 1)
        body.addWidget(self._build_gauges(ctx))
        root.addLayout(body, 1)

        self.grip = QSizeGrip(self)
        self.select_page(self.page_index("new"))          # New Download is the start page
        self._apply_scale()
        mgr = self.new_page.mgr
        mgr.task_changed.connect(lambda _t: self._update_nav_count())      # 'Downloads (n)': running + waiting
        mgr.group_changed.connect(lambda _g: self._update_nav_count())
        self._update_nav_count()
        self.new_page.show_downloads.connect(lambda: self.select_page(self.page_index("downloads")))
        self.new_page.history_changed.connect(self.library_page.mark_dirty)
        self.new_page.history_changed.connect(self.archive_page.mark_dirty)
        self.library_page.redownload.connect(self._redownload)
        self.archive_page.redownload.connect(self._redownload)
        self.library_page.changed.connect(self.archive_page.mark_dirty)
        self.archive_page.changed.connect(self.library_page.mark_dirty)
        self.new_page.history_changed.connect(self.sync_page.mark_dirty)
        self.library_page.changed.connect(self.sync_page.mark_dirty)
        self.archive_page.changed.connect(self.sync_page.mark_dirty)
        # 'Sync now' from every place opens the same sync window
        self.sync_ctrl = SyncController(ctx, self.new_page)
        for src in (self.new_page, self.library_page, self.archive_page, self.sync_page):
            src.sync_requested.connect(self.sync_ctrl.run)
        self.sync_ctrl.started.connect(lambda: self.select_page(self.page_index("new")))
        self.sync_page.add_requested.connect(self._add_playlist)
        self.sync_page.sync_all_requested.connect(self.sync_ctrl.run_all)
        for pg in (self.library_page, self.archive_page):
            self.sync_page.sync_changed.connect(pg.mark_dirty)

        self.settings_page.saved.connect(self._settings_saved)
        for pg in (self.library_page, self.archive_page):
            self.settings_page.favorites_changed.connect(pg.mark_dirty)
        self.settings_page.language_requested.connect(self.change_language)
        self.update_ctrl = UpdateController(ctx, self, lambda: bool(self.active_download_percents()), self._reload_tools)
        self.settings_page.update_requested.connect(lambda: self.update_ctrl.check(True))
        self.new_page.tools_check_requested.connect(self.update_ctrl.check_after_error)

        # gauges: real numbers once a second
        self.gauge_timer = QTimer(self, interval=1000)
        self.gauge_timer.timeout.connect(self._sample_gauges)
        self.gauge_timer.start()
        # online check: made ONCE while the splash screen was shown (new version, allowed ads, downloads counter)
        self.title_bar.set_counter(0, "")
        self._show_counter(load_counter())
        self.online_timer = QTimer(self, interval=500)
        self.online_timer.timeout.connect(self._poll_online)
        self.online_timer.start()
        QTimer.singleShot(900, self._notify_due_playlists)
        QTimer.singleShot(2500, self._remind_failed)             # 2.3.2: videos kept with 'Later' 

    # ------------------------------------------------------------------
    def _build_header(self, ctx):
        """Header: application icon, name, the version below it (smaller) and the advertisement space for the rest."""
        tr, st = ctx.lang.tr, ctx.settings
        box = self.header_box = QWidget()
        box.setFixedHeight(100)
        h = QHBoxLayout(box)
        h.setContentsMargins(26, 6, 26, 10)
        h.setSpacing(14)
        logo = self.logo = QLabel()
        logo.setPixmap(make_app_icon(64))
        names = QVBoxLayout()
        names.setSpacing(0)
        names.addStretch(1)
        name = self.name_lbl = QLabel(tr(M.APP_NAME))
        name.setObjectName("appName")
        ver = self.ver_lbl = QLabel(tr(M.VERSION, version=APP_VERSION))
        ver.setObjectName("appVer")
        names.addWidget(name)
        names.addWidget(ver)
        names.addStretch(1)
        h.addWidget(logo)
        h.addLayout(names)
        # the advertisement space takes the rest of the header (the owner banner of earlier versions is gone)
        ads = ctx.resources.ads if st.get("ads_enabled", True) else []
        self.ad_banner = self.footer_ad = AdBanner(tr(M.AD_PLACEHOLDER), ads, int(st.get("ads_rotate_seconds", 8)), fit=True)
        self.ad_banner.links = load_links()
        self.ad_banner.setFixedHeight(84)
        h.addWidget(self.ad_banner, 1)
        return box

    def _build_sidebar(self, ctx):
        tr = ctx.lang.tr
        side = self.sidebar = QFrame()
        side.setObjectName("sidebar")
        side.setFixedWidth(238)
        v = QVBoxLayout(side)
        v.setContentsMargins(6, 38, 6, 14)
        v.setSpacing(8)
        self.nav_buttons: list[NavButton] = []
        for i, (kind, msg) in enumerate(self.NAV):
            b = NavButton(kind, tr(msg))
            b.clicked.connect(lambda i=i: (sounds.play("tab"), self.select_page(i)))
            v.addWidget(b)
            self.nav_buttons.append(b)
        v.addStretch(1)
        # 2.2.7: the channel banner replaces "Powered by Let's Have Fun"; a click opens the YouTube channel
        self.channel_banner = ChannelBanner(CHANNEL_BANNER, CHANNEL_URL, tr(M.CHANNEL_TIP))
        v.addWidget(self.channel_banner)
        # five small links: Reviews, Help, About us, Contact us, Donate -> an info page in the work area
        self.info_buttons = {}
        links = QVBoxLayout()
        links.setContentsMargins(8, 4, 4, 0)
        links.setSpacing(0)
        for chunk in (self.INFO_LINKS,):
            row = QHBoxLayout()
            row.setSpacing(2)
            for kind, msg in chunk:
                btn = QPushButton(tr(msg))
                btn.setObjectName("sideLink")
                btn.setCursor(Qt.PointingHandCursor)
                btn.clicked.connect(lambda _=False, k=kind: self.show_info(k))
                self.info_buttons[kind] = btn
                row.addWidget(btn)
            row.addStretch(1)
            links.addLayout(row)
        v.addLayout(links)
        return side

    def _build_center(self, ctx):
        tr, st = ctx.lang.tr, ctx.settings
        wrap = QWidget()
        v = QVBoxLayout(wrap)
        v.setContentsMargins(14, 0, 14, 14)
        v.setSpacing(10)
        panel = QFrame()
        panel.setObjectName("centerPanel")
        pv = QVBoxLayout(panel)
        pv.setContentsMargins(0, 0, 0, 0)
        self.stack = MorphStack()
        self.new_page = NewDownloadPage(ctx)
        self.downloads_page = DownloadsPage(ctx)
        self.library_page = LibraryPage(ctx, "library")
        self.archive_page = LibraryPage(ctx, "archive")
        self.stack.addWidget(self.new_page)                            # 0  New Download
        self.stack.addWidget(self.downloads_page)                      # 1  Downloads (queue)
        self.stack.addWidget(self.archive_page)                        # 2  Archive (everything downloaded: 3 vaults)
        self.stack.addWidget(self.library_page)                        # 3  Library (favorite categories only)
        self.sync_page = SyncPage(ctx)
        self.stack.addWidget(self.sync_page)                           # 4  Playlist Sync
        self.settings_page = SettingsPage(ctx)
        self.stack.addWidget(self.settings_page)                       # 5  Settings
        self.info_page = InfoPage(ctx)
        self.INFO_INDEX = self.stack.addWidget(self.info_page)         # 6  Reviews / Help / About us / Contact us / Donate
        pv.addWidget(self.stack)
        v.addWidget(panel, 1)
        return wrap

    def _build_gauges(self, ctx):
        tr = ctx.lang.tr
        panel = self.gauge_panel = QFrame()
        panel.setObjectName("panel")
        panel.setFixedWidth(284)
        v = QVBoxLayout(panel)
        v.setContentsMargins(12, 14, 12, 14)
        v.setSpacing(4)

        def cap(text, obj="gaugeCaption"):
            lb = QLabel(text)
            lb.setObjectName(obj)
            lb.setAlignment(Qt.AlignCenter)
            self.gauge_caps.append((lb, 19 if obj == "panelTitle" else 17))
            return lb

        v.addWidget(cap(tr(M.ANALYTICS), "panelTitle"))
        v.addSpacing(4)
        mbs, gb = tr(M.UNIT_MBS), tr(M.UNIT_GB)
        # upper part: speed of the computer's network | speed of this application
        self.g_net = MiniGauge(tr(M.G_NET), "#27d3ff")
        self.g_app = MiniGauge(tr(M.G_APP), "#1fd16a")
        # middle part: downloaded since the program started | free space of the save directory's partition
        self.g_total = MiniGauge(tr(M.G_TOTAL), "#b57bff")
        self.g_free = MiniGauge(tr(M.G_FREE), "#ffa800")
        for pair in ((self.g_net, self.g_app), (self.g_total, self.g_free)):
            row = QHBoxLayout()
            row.setSpacing(2)
            for g in pair:
                row.addWidget(g)
            v.addLayout(row, 4)
        # lower part: disk I/O | files downloading now compared with downloading + waiting
        self.g_disk = SpeedGauge(100, mbs, tr(M.G_DISK))
        self.g_queue = MiniGauge(tr(M.G_QUEUE), "#ff5fa8")
        low = QHBoxLayout()
        low.setSpacing(2)
        low.addWidget(self.g_disk, 1)
        low.addWidget(self.g_queue, 1)
        v.addLayout(low, 5)
        self._unit_mbs, self._unit_gb, self._unit_mb = mbs, gb, tr(M.UNIT_MB)
        self._unit_files = tr(M.UNIT_FILES)
        panel_wrap = QWidget()
        wl = QVBoxLayout(panel_wrap)
        wl.setContentsMargins(0, 0, 14, 14)
        wl.addWidget(panel)
        return panel_wrap

    # ------------------------------------------------------------------
    def page_index(self, kind: str) -> int:
        return next(i for i, (k, _m) in enumerate(self.NAV) if k == kind)

    def _add_playlist(self):
        """'Add Playlist' of the Playlist Sync page: a playlist is added by downloading it once."""
        self.select_page(self.page_index("new"))
        self.new_page._log("info", M.SYP_ADD_HINT)

    def _redownload(self, rec: dict):
        """'Download again' button of the Downloads page -> New Download with the same link / folder."""
        self.select_page(self.page_index("new"))
        self.new_page.prefill(rec)

    def select_page(self, index: int):
        self._info_kind = None
        self.stack.setCurrentIndex(index)
        for i, b in enumerate(self.nav_buttons):
            b.set_active(i == index)

    def _update_nav_count(self):
        """The Downloads label of the side menu shows how many files are downloading now + waiting (2.2.2)."""
        try:
            running, waiting = self.new_page.mgr.queue.counts()
        except Exception:                                   # noqa: BLE001
            return
        n = running + waiting
        base = self.ctx.lang.tr(M.NAV_DOWNLOADS)
        text = f"{base} ({n})" if n else base
        b = self.nav_buttons[self.page_index("downloads")]
        if b.text != text:
            b.set_text(text)

    def page_state(self):
        """Which work area is shown now: (page index, info kind or None). Used to keep the place after a language change."""
        return self.stack.currentIndex(), self._info_kind

    def restore_page(self, state):
        """Show again the work area saved by page_state() (no fade: the window was just rebuilt)."""
        if not state:
            return
        index, kind = state
        if kind:
            self.show_info(kind)
        elif 0 <= index < self.stack.count():
            self.select_page(index)

    def show_info(self, kind: str):
        """A link of the corner (Reviews, Help, About us, Contact us, Donate): shown in the work area."""
        self._info_kind = kind
        self.info_page.show_kind(kind)
        self.stack.setCurrentIndex(self.INFO_INDEX)
        for b in self.nav_buttons:
            b.set_active(False)

    def _show_app_speed(self):
        mbs = self.downloads_mgr.queue.speed() / 1e6
        mx = auto_max(mbs, NET_STEPS)
        self.g_app.set_state(mbs / mx, f"{mbs:.1f}", self._unit_mbs, f"{mx:g}")

    @property
    def downloads_mgr(self):
        return self.ctx.downloads

    def _size_text(self, nbytes: float) -> str:
        """'85 GB' / '700 MB' for the ends of a gauge scale."""
        text, unit = human_size(nbytes)
        return f"{text} {self._unit_gb if unit == 'GB' else self._unit_mb}"

    def _sample_gauges(self):
        try:
            self._sample_gauges_impl()
        except Exception:                                  # noqa: BLE001
            import traceback
            traceback.print_exc()

    def _sample_gauges_impl(self):
        """Once a second: network speed, disk I/O, downloaded size, free space (see app/sysmon.py)."""
        s = self.mon.sample(self.ctx.settings.download_dir())
        mx = auto_max(s["net"], NET_STEPS)
        self.g_net.set_state(s["net"] / mx, f"{s['net']:.1f}", self._unit_mbs, f"{mx:g}")
        self._show_app_speed()
        if self._free_at_start is None and s["free"]:
            self._free_at_start = float(s["free"])                      # free space of the partition when we started
        total = self.downloads_mgr.queue.downloaded_bytes()             # downloaded since the program started
        text, unit = human_size(total)
        frac = total / self._free_at_start if self._free_at_start else 0.0
        self.g_total.set_state(frac, text, self._unit_gb if unit == "GB" else self._unit_mb, self._size_text(self._free_at_start or 0))
        text, unit = human_size(s["free"])
        # the arc shows the USED part of the partition, the number is the free space (no red warning colour)
        frac = (1.0 - s["free"] / s["total"]) if s["total"] else 0.0
        self.g_free.set_state(frac, text, self._unit_gb if unit == "GB" else self._unit_mb, self._size_text(s["total"]))
        self.g_disk.maximum = auto_max(s["disk"], DISK_STEPS)
        self.g_disk.set_value(s["disk"])
        running, waiting = self.downloads_mgr.queue.counts()           # files downloading / (downloading + waiting)
        all_files = running + waiting
        self.g_queue.set_state(running / all_files if all_files else 0.0, f"{running}/{all_files}", self._unit_files,
                               str(all_files))

    # ------------------------------------------------------------------
    # settings, language, ads, notifications
    # ------------------------------------------------------------------
    def _settings_saved(self):
        """Settings page saved / restored the settings."""
        self.new_page.apply_defaults()
        self._ads_updated(local_ads(), 0, load_links())
        self.ctx.downloads.queue.pump()                    # a higher 'max concurrent downloads' starts waiting videos at once

    def show_language_menu(self, anchor):
        menu = QMenu(self)
        for code, name in self.ctx.lang.available.items():
            act = menu.addAction(("✓  " if code == self.ctx.lang.code else "      ") + name)
            act.triggered.connect(lambda _=False, c=code: self.change_language(c))
        menu.exec(anchor.mapToGlobal(anchor.rect().bottomLeft()))

    def change_language(self, code: str):
        """Language icon / Settings: the whole window is rebuilt in the chosen language (main.py)."""
        if code == self.ctx.lang.code:
            return
        if self.active_download_percents():
            exec_blurred(self, MessageDialog(self.ctx.lang, self.ctx.lang.tr(M.TIP_LANGUAGE),
                                             self.ctx.lang.tr(M.LANG_BUSY), self, info=True))
            return
        self.ctx.settings.set("language", code)
        self.ctx.settings.save()
        self.language_changed.emit(code)

    def force_close(self):
        self._force_close = True
        self.close()

    def _ads_updated(self, files, downloaded: int = 0, links=None):
        on = bool(self.ctx.settings.get("ads_enabled", True))
        self.ad_banner.set_paths(list(files or []) if on else [], links)
        if downloaded:
            self.new_page._log("info", M.LG_ADS, n=len(files))

    def _poll_online(self):
        """The online check (made while the splash screen was shown) may still be running: wait for it."""
        self._online_tries += 1
        if self.ctx.online_ready:
            self.online_timer.stop()
            self._check_done(self.ctx.online)
        elif self._online_tries > 240:                      # 2 minutes
            self.online_timer.stop()

    def _show_counter(self, data):
        """Corner counter of the downloads of the program (downloads_counter.txt of the online folder)."""
        tr = self.ctx.lang.tr
        self.title_bar.set_counter(0, "")                  # 2.3.0: the number of users is only shown on the splash screen
        return
        if not data or not data.get("total"):
            self.title_bar.set_counter(0, "")
            return
        tip = [tr(M.CNT_TIP)]
        tip += [f"{label}: {n:,}" if label else f"{n:,}" for label, n in data.get("rows", [])]
        if data.get("source") in ("cache", "baseline"):
            tip.append(tr(M.CNT_OFFLINE))
        self.title_bar.set_counter(int(data["total"]), "\n".join(tip))

    def _check_done(self, r: dict):
        """The online folder was read: show the allowed ads, the counter, and tell about a higher program version."""
        self._ads_updated(r.get("files"), r.get("downloaded", 0), r.get("links"))
        self._show_counter(r.get("counter") or load_counter())
        if r.get("error") and not r.get("files"):
            self.new_page._log("warn", M.LG_ADS_FAIL, detail=r["error"])
        if not getattr(self.ctx, "tools_checked", False):                         # 2.3.0: tools are checked once at startup (silent unless an update exists)
            self.ctx.tools_checked = True
            if self.ctx.settings.get("update_notify", True):
                QTimer.singleShot(1500, lambda: self.update_ctrl.check(False))
        ver = r.get("version")
        if not ver:
            return
        self.new_page._log("info", M.LG_UPDATE, v=ver)
        if self.ctx.update_asked or not self.ctx.settings.get("update_notify", True):
            return
        self.ctx.update_asked = True                       # once per run (also after a language change)
        dlg = UpdateDialog(self.ctx.lang, ver, APP_VERSION, self)
        exec_blurred(self, dlg)
        if dlg.dont_show:
            self.ctx.settings.set("update_notify", False)
            self.ctx.settings.save()
        if dlg.choice == "yes" and r.get("version_url"):
            QDesktopServices.openUrl(QUrl(r["version_url"]))      # the download page of the new version

    def _remind_failed(self):
        try:
            self.new_page.remind_failed()
        except Exception:                                  # noqa: BLE001
            import traceback
            traceback.print_exc()

    def _notify_due_playlists(self):
        try:
            self._notify_due_playlists_impl()
        except Exception:                                  # noqa: BLE001
            import traceback
            traceback.print_exc()

    def _notify_due_playlists_impl(self):
        """'Notify me when a playlist has new videos to sync': playlists whose next sync date has come."""
        if not self.ctx.settings.get("notify_new_videos", True):
            return
        due = [e for e in self.ctx.sync.entries if self.ctx.sync.is_due(e)]
        if not due:
            return
        tr = self.ctx.lang.tr
        names = "\n".join("-  " + e["title"] for e in due[:6]) + (f"\n...  (+{len(due) - 6})" if len(due) > 6 else "")
        dlg = ChoiceDialog(self.ctx.lang, tr(M.DUE_TITLE), tr(M.DUE_TEXT, n=len(due), names=names),
                           [("now", tr(M.DUE_NOW), "btnGreen"), ("check", tr(M.DUE_CHECK), "btnBlue"),
                            ("later", tr(M.DUE_LATER), "btnOrange")], self)
        exec_blurred(self, dlg)
        recs = [r for r in (self.ctx.history.find(e.get("rec_id", "")) for e in due) if r]
        if dlg.choice == "now":                              # in the background: only the new videos are added to the downloads
            self.sync_ctrl.run_background(recs)
        elif dlg.choice == "check":                          # one window per playlist: all videos compared, the user chooses
            for rec in recs:
                if self.sync_ctrl.run(rec) in ("busy", "error"):
                    break

    # --- 2.3.0: the minimize button sends the program to the system tray ------------------------------------------
    def minimize_to_tray(self):
        """Hide the window and show the tray icon (left click / 'Open' brings it back, 'Exit' closes it like the X button).
        Downloads keep running. Without a system tray the window is minimized to the task bar as before."""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            self.showMinimized()
            return
        tr = self.ctx.lang.tr
        if getattr(self, "_tray", None) is None:
            tray = QSystemTrayIcon(make_app_qicon(), self)
            tray.setToolTip(tr(M.APP_NAME))
            menu = QMenu()
            menu.addAction(tr(M.TRAY_OPEN), self.restore_from_tray)
            menu.addAction(tr(M.TRAY_EXIT), self._exit_from_tray)
            tray.setContextMenu(menu)
            tray.activated.connect(lambda reason: self.restore_from_tray()
                                   if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick) else None)
            self._tray, self._tray_menu = tray, menu
        self._tray.show()
        self.hide()
        if not getattr(self, "_tray_told", False):
            self._tray_told = True
            self._tray.showMessage(tr(M.APP_NAME), tr(M.TRAY_RUNNING), QSystemTrayIcon.Information, 3000)

    def restore_from_tray(self):
        if getattr(self, "_tray", None) is not None:
            self._tray.hide()
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _exit_from_tray(self):
        self.restore_from_tray()
        self.close()                                       # the normal exit check (running downloads, rating window)

    def _remove_tray(self):
        if getattr(self, "_tray", None) is not None:
            self._tray.hide()

    def toggle_max(self):
        self.showNormal() if self.isMaximized() else self.showMaximized()

    def changeEvent(self, e):
        # changeEvent fires inside __init__ (setWindowFlags) before self.shell exists
        shell = getattr(self, "shell", None)
        if shell is not None:
            shell.radius = 0 if self.isMaximized() else 18
            shell.update()
        super().changeEvent(e)

    def resizeEvent(self, e):
        grip = getattr(self, "grip", None)
        if grip is not None:
            grip.move(self.width() - grip.width() - 4, self.height() - grip.height() - 4)
            self._apply_scale()
        super().resizeEvent(e)

    def _apply_scale(self):
        """Make the whole interface follow the window size.

        s = 1.0 at the design size (1180 x 740). The header, banner, side menu, gauges
        panel and footer ad grow / shrink with the window (limits 0.85 .. 1.35); the
        gauges themselves are drawn relative to the space they get.
        """
        s = max(0.85, min(1.35, min(self.width() / 1180.0, self.height() / 740.0)))
        if abs(s - self._scale) < 0.01:
            return
        self._scale = s
        self.header_box.setFixedHeight(int(100 * s))
        px = int(64 * s)
        if px != self._logo_px:
            self._logo_px = px
            self.logo.setPixmap(make_app_icon(px))
        self.name_lbl.setStyleSheet(f"font-size: {int(26 * s)}px;")
        self.ver_lbl.setStyleSheet(f"font-size: {max(10, int(11 * s))}px;")
        self.ad_banner.setFixedHeight(int(84 * s))
        self.sidebar.setFixedWidth(int(238 * s))
        for b in self.nav_buttons:
            b.set_scale(s)
        self.gauge_panel.setFixedWidth(int(284 * s))
        for g in (self.g_net, self.g_app, self.g_total, self.g_free, self.g_queue, self.g_disk):
            g.title_px = max(9, int(GAUGE_TITLE_PX * s))                # the same title font for every gauge
            g.update()
        for lb, base in self.gauge_caps:
            lb.setStyleSheet(f"font-size: {max(11, int(base * s))}px;")

    # ------------------------------------------------------------------
    # closing the application
    # ------------------------------------------------------------------
    def active_download_percents(self) -> list[float]:
        """Progress (%) of every real download that is still running (New Download tab).
        The demo rows of the Downloader tab are only decoration and are not counted."""
        return self.new_page.active_percent()

    def abort_all_downloads(self):
        """'Abort Downloads' of the exit window: stop yt-dlp and delete the partial files."""
        self.new_page.cancel_for_exit()

    def _reload_tools(self):
        """After a tool update: find yt-dlp / ffmpeg again (the user tools folder comes first) and give them to the queue."""
        res = self.ctx.resources
        res.load()
        self.new_page.mgr.sync_tools(res.ytdlp, res.ffmpeg_dir)
        self.sync_ctrl._fetcher.ytdlp = res.ytdlp

    def _blur_background(self, on: bool):
        """Dim + blur the window while a glass dialog is open. 2.3.0: a picture of the window is blurred by scaling it down and
        up and shown by a label on top of it - the old QGraphicsBlurEffect on the translucent window made Windows write
        'UpdateLayeredWindowIndirect failed ... (The parameter is incorrect.)' to the console (the effect paints 30 px
        outside the window)."""
        cur = getattr(self, "_blur_label", None)
        if cur is not None:
            cur.hide()
            cur.deleteLater()
            self._blur_label = None
        if not on:
            return
        pm = self.shell.grab()
        size = pm.size()
        if size.isEmpty():
            return
        for div in (4, 2):                                               # two steps give a smoother blur
            pm = pm.scaled(max(1, size.width() // div), max(1, size.height() // div), Qt.IgnoreAspectRatio,
                           Qt.SmoothTransformation)
        pm = pm.scaled(size, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        pm.setDevicePixelRatio(self.shell.devicePixelRatioF())
        lab = QLabel(self)
        lab.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        lab.setPixmap(pm)
        lab.setGeometry(self.shell.geometry())
        lab.show()
        lab.raise_()
        lab.repaint()
        self._blur_label = lab

    def request_exit(self) -> bool:
        """True = the application may close."""
        lang = self.ctx.lang
        running = self.active_download_percents()
        self._blur_background(True)
        try:
            if running:
                paused = self.new_page.mgr.queue.counts_by_state()["paused"]
                dlg = ExitWarningDialog(lang, len(running), round(sum(running) / len(running)), self, paused=paused)
                if dlg.exec() == QDialog.Accepted:
                    self.abort_all_downloads()
                    return True
                return False                       # "Back"
            fb = self.ctx.feedback
            dlg = RatingDialog(lang, self, previous=fb.current())
            dlg.exec()
            if dlg.action == "submit" and dlg.rating:
                fb.save_rating(dlg.rating, dlg.feedback_text, APP_VERSION, dlg.features_text)      # kept locally, shown at the next exit
            if dlg.action in ("submit", "skip"):
                self._send_rating()
            return dlg.action in ("submit", "skip")  # X button = stay
        finally:
            self._blur_background(False)

    def _send_rating(self):
        """A new / changed rating (or one that could not be sent before) goes to the Google form. Waits a few seconds at most."""
        import threading
        st = self.ctx.settings
        cur = self.ctx.feedback.current()
        url = str(st.get("feedback_form_url", "") or "").strip()
        if not cur or cur.get("sent") or not url:
            return
        th = threading.Thread(target=self.ctx.feedback.send,         # Apps Script web app (JSON) or Google form
                              args=(url, st.get("feedback_form_fields", {}), self.ctx.lang.code), daemon=True)
        th.start()
        th.join(6)

    def closeEvent(self, e):
        if self._force_close:
            for tm in (self.online_timer, self.gauge_timer):
                tm.stop()
            self._remove_tray()
            e.accept()
            return
        if self._exit_running:
            e.ignore()
            return
        self._exit_running = True
        try:
            allowed = self.request_exit()
        finally:
            self._exit_running = False
        if allowed:
            for tm in (self.online_timer, self.gauge_timer):
                tm.stop()
            self._remove_tray()
            e.accept()
        else:
            e.ignore()
