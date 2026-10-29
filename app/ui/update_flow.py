# =============================================================================
# TubeArchive Pro  |  Version 2.3.0  |  File: app/ui/update_flow.py
# Version history of this file:
#   2.3.0 - Created: 'Updates' window (application + tools), progress window, check after a failed download
# =============================================================================
"""Update flow of the main window.

  check(manual=True)      'Check for updates now' (Settings): 'Checking...' -> Updates window (always shown)
  check(manual=False)     at startup: silent; the window is shown only when something can be updated
  check_after_error()     a download failed for a reason that an old yt-dlp can cause: the tools are checked (once per run);
                          the window opens only when an update exists
The tools are installed by app/toolupdate.py into the user tools folder; nothing is installed while downloads run.
"""
import threading

from PySide6.QtCore import QObject, QTimer, QUrl, Signal
from PySide6.QtGui import QDesktopServices

from .. import toolupdate
from ..msg import M
from ..paths import APP_VERSION
from ..resources import find_tool
from .actions import exec_blurred
from .dialogs import BusyDialog, MessageDialog, UpdateProgressDialog, UpdatesDialog


class UpdateController(QObject):
    checked = Signal(object, object)        # (tool items or None, error text)
    progress = Signal(int, int)
    finished = Signal(str)                  # '' = done, 'cancelled', else the error text

    def __init__(self, ctx, window, busy_downloads, reload_tools):
        """busy_downloads() -> True while a download runs; reload_tools() re-reads the tool paths after an update."""
        super().__init__(window)
        self.ctx, self.win = ctx, window
        self.busy_downloads, self.reload_tools = busy_downloads, reload_tools
        self._error_checked = False
        self._running = False
        self._cancel = False
        self._manual = False
        self._busy = None
        self._prog = None
        self._items = None
        self.checked.connect(self._on_checked)
        self.progress.connect(self._on_progress)
        self.finished.connect(self._on_finished)

    def _log(self, kind, msg, **kw):
        try:
            self.win.new_page._log(kind, msg, **kw)
        except Exception:                                   # noqa: BLE001
            pass

    # --- check ---------------------------------------------------------------------------------------------
    def check(self, manual: bool = True, reason: str = ""):
        if self._running:
            return
        self._running, self._manual, self._reason = True, manual, reason
        res = self.ctx.resources
        ytdlp = res.ytdlp
        ffmpeg = find_tool("ffmpeg", res.ffmpeg_dir) if res.ffmpeg_dir else None
        threading.Thread(target=self._work, args=(ytdlp, ffmpeg), daemon=True).start()
        if manual:
            self._busy = BusyDialog(self.ctx.lang, self.ctx.lang.tr(M.UPD_CHECKING), self.win)
            exec_blurred(self.win, self._busy)
            self._busy = None

    def check_after_error(self):
        """A failed download: look for a newer yt-dlp once per run."""
        if self._error_checked or self._running:
            return
        self._error_checked = True
        self._log("info", M.LG_UPD_ERR_CHECK)
        self.check(manual=False, reason="error")

    def _work(self, ytdlp, ffmpeg):
        try:
            items = toolupdate.check_tools(ytdlp, ffmpeg)
            self.checked.emit(items, "")
        except Exception as exc:                            # noqa: BLE001
            self.checked.emit(None, str(exc))

    def _on_checked(self, items, error):
        self._running = False
        if self._busy is not None:
            self._busy.finish()
        t = self.ctx.lang.tr
        if items is None:
            if self._manual:
                QTimer.singleShot(0, lambda: self._show(None))
            return
        self._items = items
        if self._reason == "error" and not items:
            self._log("info", M.LG_UPD_ERR_OK)
        if items:
            self._log("info", M.LG_UPD_TOOLS_AVAILABLE)
        if self._manual or items:
            QTimer.singleShot(0, lambda: self._show(items))

    # --- the window ------------------------------------------------------------------------------------------
    def _show(self, items):
        t = self.ctx.lang.tr
        online = getattr(self.ctx, "online", None) or {}
        new_ver = online.get("version")
        app_new = bool(new_ver)
        app_line = (t(M.UPD_APP_AVAILABLE, new=new_ver, cur=APP_VERSION) if app_new
                    else t(M.UPD_APP_CURRENT, cur=APP_VERSION))
        lines = None if items is None else [
            t(M.UPD_TOOL_LINE if i["cur"] else M.UPD_TOOL_NEW, name=i["name"], cur=i["cur"], new=i["new"]) for i in items]
        dlg = UpdatesDialog(self.ctx.lang, app_line, app_new, lines, self.win)
        exec_blurred(self.win, dlg)
        if dlg.update_app and online.get("version_url"):
            QDesktopServices.openUrl(QUrl(online["version_url"]))
        if dlg.update_tools and items:
            self.install(items)

    # --- install -----------------------------------------------------------------------------------------------
    def install(self, items):
        t = self.ctx.lang.tr
        if self.busy_downloads():
            exec_blurred(self.win, MessageDialog(self.ctx.lang, t(M.UPD_TITLE), t(M.UPD_BUSY), self.win, info=True))
            return
        self._cancel = False
        self._running = True
        threading.Thread(target=self._install_work, args=(items,), daemon=True).start()
        self._prog = UpdateProgressDialog(self.ctx.lang, self.win)
        exec_blurred(self.win, self._prog)
        if self._prog.cancelled:
            self._cancel = True
        self._prog = None

    def _install_work(self, items):
        try:
            toolupdate.update_tools(items, lambda d, tot: self.progress.emit(int(d), int(tot)), lambda: self._cancel)
            self.finished.emit("")
        except toolupdate.Cancelled:
            self.finished.emit("cancelled")
        except Exception as exc:                            # noqa: BLE001
            self.finished.emit(str(exc) or "error")

    def _on_progress(self, done, total):
        if self._prog is not None:
            self._prog.set_progress(done, total)

    def _on_finished(self, result):
        self._running = False
        if self._prog is not None:
            self._prog.finish()
        QTimer.singleShot(0, lambda: self._finish_message(result))

    def _finish_message(self, result):
        t = self.ctx.lang.tr
        if result == "cancelled":
            text = t(M.UPD_CANCELLED)
        elif result:
            text = t(M.UPD_FAIL, detail=result)
        else:
            self.reload_tools()
            text = t(M.UPD_DONE_TOOLS)
        exec_blurred(self.win, MessageDialog(self.ctx.lang, t(M.UPD_TITLE), text, self.win, info=not result or result == "cancelled"))
