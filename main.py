# =============================================================================
# TubeArchive Pro  |  Version 2.2.8  |  File: main.py
# Version history of this file:
#   2.3.0 - the splash screen stays until its counter animation is finished
#   2.2.8 - the splash screen gets the numbers of the last online check (users, versions, rating)
#   2.2.7 - the splash screen is the first thing shown (the main window module is imported afterwards)
#   2.3.0 - installed program: migrate_old_data() at start (data lives in %APPDATA%\TubeArchivePro)
#   2.0.5 - Language change keeps the work area that was open (page_state / restore_page)
#   2.0.4 - Qt warning 'QFont::setPointSize: Point size <= 0' is written once with the place in the program that
#           caused it to data/error.log (instead of filling the console); other Qt messages are printed as before
#   1.0.12 - Language change rebuilds the main window (language icon / Settings)
#   1.0.10 - Valid default font (fixes "QFont::setPointSize: Point size <= 0" message)
#   1.0.6 - No functional change (version header added)
#   1.0.0 - 1.0.5 - first version and earlier fixes (see CHANGELOG.md)
# =============================================================================
"""TubeArchive Pro - entry point.

Flow: splash screen -> StartupLoader loads default settings, current settings,
language files, resources and history -> main window opens -> splash closes.
"""
import sys

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QMessageBox

from app.context import AppContext
from app.loader import StartupLoader
from app.paths import APP_NAME
from app.ui.splash import SplashScreen
from app.ui.theme import STYLE


def _install_error_log():
    """Every uncaught error is written to data/error.log (and printed), so a problem can be reported."""
    import traceback
    from datetime import datetime
    from app.paths import DATA_DIR

    def hook(kind, value, tb):
        text = "".join(traceback.format_exception(kind, value, tb))
        sys.stderr.write(text)
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            with open(DATA_DIR / "error.log", "a", encoding="utf-8") as f:
                f.write(f"--- {datetime.now():%Y-%m-%d %H:%M:%S} ---\n{text}\n")
        except OSError:
            pass
    sys.excepthook = hook


def _install_qt_log():
    """The Qt warning 'QFont::setPointSize: Point size <= 0 (-1)' is harmless (a widget styled in pixels has no point
    size) but noisy. It is written ONCE per place to data/error.log together with the Python stack, so that its
    source can be found and fixed; every other Qt message is printed as usual."""
    import traceback
    from datetime import datetime
    from PySide6.QtCore import qInstallMessageHandler
    from app.paths import DATA_DIR
    seen = set()

    def handler(_mode, _ctx, msg):
        if "Point size <= 0" not in msg:
            sys.stderr.write(msg + "\n")
            return
        frames = traceback.extract_stack()[:-1]
        mine = [f for f in frames if "TubeArchivePro" in f.filename or f.filename.endswith(("main.py",)) or "/app/" in f.filename.replace("\\", "/")]
        key = tuple((f.filename, f.lineno) for f in mine[-3:])
        if key in seen:
            return
        seen.add(key)
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            with open(DATA_DIR / "error.log", "a", encoding="utf-8") as fh:
                fh.write(f"--- {datetime.now():%Y-%m-%d %H:%M:%S} Qt warning: {msg}\n")
                fh.write("".join(traceback.format_list(mine[-8:])) + "\n")
        except OSError:
            pass
    qInstallMessageHandler(handler)


def show_error(text: str):
    """Error window with readable text (the program style paints labels white) + a copy in data/error.log."""
    from app.paths import DATA_DIR
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(DATA_DIR / "error.log", "a", encoding="utf-8") as f:
            f.write(text + "\n")
    except OSError:
        pass
    box = QMessageBox(QMessageBox.Critical, APP_NAME, text)
    box.setStyleSheet("QLabel { color: #111111; } QPushButton { color: #111111; }")
    box.exec()


def main() -> int:
    from app.paths import FROZEN, migrate_old_data
    if FROZEN:                                  # installed program: take over the data of an older portable copy once
        migrate_old_data()
    _install_error_log()
    _install_qt_log()
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setFont(QFont("Segoe UI", 10))        # a real point size: widgets styled in px otherwise report point size -1
    app.setStyleSheet(STYLE)

    ctx = AppContext()
    try:
        from app.stats import splash_data
        stats = splash_data()
    except Exception:                         # noqa: BLE001  (the splash works without the numbers)
        stats = {}
    splash = SplashScreen(ctx.lang, stats)
    splash.show()
    app.processEvents()                       # 2.2.7: the splash screen is painted before anything else is done
    holder = {}

    def open_window(geometry=None):
        from app.ui.main_window import MainWindow          # 2.2.7: the big window module is loaded after the splash screen is visible
        # Arabic (or any rtl language) mirrors the whole interface
        app.setLayoutDirection(Qt.RightToLeft if ctx.lang.is_rtl else Qt.LeftToRight)
        win = MainWindow(ctx)
        win.language_changed.connect(change_language)
        if geometry is not None:
            win.setGeometry(geometry)
        win.show()
        holder["window"] = win
        return win

    def change_language(code: str):
        """Language icon / Settings: load the language and rebuild the window (same place and size)."""
        old = holder.get("window")
        ctx.lang.load(code)
        try:
            state = old.page_state() if old else None         # stay in the same work area (2.0.5)
            new = open_window(old.geometry() if old else None)
            new.restore_page(state)
        except Exception:                                  # noqa: BLE001
            import traceback
            show_error(traceback.format_exc())
            return
        if old:
            old.force_close()
            old.deleteLater()

    def on_done():
        wait = splash.remaining_ms()          # 2.3.0: the counter / bar animation is shown completely first
        if wait > 0:
            QTimer.singleShot(wait, _open_main)
        else:
            _open_main()

    def _open_main():
        try:
            open_window()
        except Exception as exc:   # never leave the splash hanging on an error
            import traceback
            splash.close()
            show_error(traceback.format_exc())
            app.quit()
            return
        splash.close()

    def on_failed(msg: str):
        splash.close()
        show_error(msg)
        app.quit()

    loader = StartupLoader(ctx)
    loader.progress.connect(splash.set_progress)
    loader.done.connect(on_done)
    loader.failed.connect(on_failed)
    loader.start()
    holder["loader"] = loader
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
