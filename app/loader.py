# =============================================================================
# TubeArchive Pro  |  Version 2.3.0  |  File: app/loader.py
# Version history of this file:
#   2.3.2 - the start-up steps no longer wait 380 ms each (40 ms): the splash screen is shorter
#   2.3.0 - registers the installation (share_usage) and reads the users / rating numbers of the register
#   2.2.9 - the rating numbers come from feedback_form_url when it is an Apps Script address
#   2.2.8 - the background check also reads the rating of the users (feedback endpoint)
#   2.2.7 - the online check runs in the background (the splash screen no longer waits for it)
#   2.0.1 - Online check (new version, this month's allowed ads, downloads counter) runs during the splash screen
#   1.0.13 - Real-data mode: sample records are removed (purge_demo), only demo_mode creates them
#   1.0.11 - Loads the sync file
#   1.0.10 - Demo history / favorites are created on the first start (app/demo.py)
#   1.0.9 - The history step also loads the favorites file
#   1.0.6 - No functional change (version header added)
#   1.0.0 - 1.0.5 - first version and earlier fixes (see CHANGELOG.md)
# =============================================================================
"""Start-up loader: runs while the splash screen is visible."""
import threading

from PySide6.QtCore import QThread, Signal

from .context import AppContext
from .ads import local_ads, parse_version, sync_ads, write_log
from .demo import purge_demo, seed_demo
from .msg import M
from .paths import APP_VERSION, FROZEN
from .stats import fetch_rating, fetch_users_base

ONLINE_WAIT = 12          # seconds the splash screen waits for the online folder (the check goes on afterwards)


class StartupLoader(QThread):
    progress = Signal(int, str)   # percent, message id (the splash translates it)
    done = Signal()
    failed = Signal(str)

    def __init__(self, ctx: AppContext, step_delay_ms: int = 40):
        super().__init__()
        self.ctx = ctx
        self.delay = step_delay_ms

    def _load_language(self):
        self.ctx.lang.discover()
        self.ctx.lang.load(self.ctx.settings.get("language", "en"))

    def _load_history(self):
        self.ctx.history.load()
        self.ctx.favorites.load()
        moved = self.ctx.history.dedupe_files()                    # one history entry per file (2.0.7)
        for old, new in moved.items():
            cat = self.ctx.favorites.category_of(old)
            if cat:
                self.ctx.favorites.remove(old)
                if not self.ctx.favorites.is_favorite(new):
                    self.ctx.favorites.add(new, cat)
        self.ctx.sync.load()
        self.ctx.failed.load()
        if self.ctx.settings.get("demo_mode", False):
            seed_demo(self.ctx)
        else:
            purge_demo(self.ctx)

    def _online_work(self):
        c = self.ctx
        st = c.settings
        url = str(st.get("online_folder_url", "") or st.defaults.get("online_folder_url", "")).strip()
        try:
            if not url:
                raise ValueError("no online_folder_url")
            r = sync_ads(url, str(st.get("ads_prefix", "tubearchivepro")),
                         current_version=parse_version(f"tubearchivepro_v{APP_VERSION}") or (0, 0, 0))
            write_log(r.get("log", []))
            try:                                                # numbers for the next splash screen + the install register
                form = str(st.get("feedback_form_url", "") or "")
                fetch_users_base(url)
                if FROZEN and st.get("share_usage", True):      # only the installed program registers (not a developer run)
                    c.feedback.register(form, st.get("feedback_form_fields", {}), c.lang.code, APP_VERSION)
                fetch_rating(form)
            except Exception:                               # noqa: BLE001
                pass
        except Exception as e:                                  # noqa: BLE001
            r = {"files": local_ads(), "downloaded": 0, "version": "", "version_url": "", "error": str(e),
                 "log": [], "links": {}, "counter": None}
        c.online = r
        c.online_ready = True

    def _online_check(self):
        """The check runs in its own thread; the splash screen waits for it at most ONLINE_WAIT seconds."""
        self.ctx.online_ready = False
        th = threading.Thread(target=self._online_work, daemon=True)
        th.start()                                              # 2.2.7: no waiting - the main window polls ctx.online_ready

    def run(self):
        c = self.ctx
        steps = [
            (M.LOAD_DEFAULTS, c.settings.load_defaults),   # default setting file
            (M.LOAD_SETTINGS, c.settings.load_current),    # current (user) setting file
            (M.LOAD_LANG, self._load_language),            # language files
            (M.LOAD_RES, c.resources.load),                # resource files
            (M.LOAD_HISTORY, self._load_history),              # history file
            (M.LOAD_ONLINE, self._online_check),               # new version / allowed ads / downloads counter
        ]
        try:
            for i, (msg_id, fn) in enumerate(steps):
                self.progress.emit(int(i / len(steps) * 100), msg_id)
                fn()
                self.msleep(self.delay)
            self.progress.emit(100, M.READY)
            self.msleep(300)
            self.done.emit()
        except Exception as exc:   # noqa: BLE001
            self.failed.emit(str(exc))
