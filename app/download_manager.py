# =============================================================================
# TubeArchive Pro  |  Version 2.0.9  |  File: app/download_manager.py
# Version history of this file:
#   2.0.9 - unexpected Check errors go to data/fetch.log
#   2.0.1 - DownloadManager = information fetch + the download queue (app/dlqueue.py) as Qt signals
#   1.0.14 - start(extra_args)
#   1.0.11 - start() takes playlist options (folder, selected items, force); new InfoFetcher (sync check)
#   1.0.8 - Created: Qt bridge (signals) between the page and app/downloader.py
# =============================================================================
"""Qt side of the download engine: runs the work in background threads and reports to the
interface with signals. All the real logic is in app/downloader.py and app/dlqueue.py."""
import threading
import time

from PySide6.QtCore import QObject, Signal

from .dlqueue import DownloadQueue
from .downloader import EngineError, download_bytes, fetch_info

PROGRESS_GAP = 0.15          # seconds: a running video is reported at most this often


class DownloadManager(QObject):
    info_ready = Signal(int, object)        # token, info dict
    info_failed = Signal(int, str, str)     # token, error code, detail
    task_changed = Signal(object)           # a video of the queue changed (progress / state)
    task_done = Signal(object)              # a video finished
    task_failed = Signal(object)
    task_cancelled = Signal(object)         # cancelled or skipped
    group_changed = Signal(object)          # a playlist was added / changed
    group_done = Signal(object)             # every video of a playlist is finished
    thumb_ready = Signal(object)            # the picture of a video arrived

    def __init__(self, ytdlp: str | None, ffmpeg_dir: str | None, get=None):
        super().__init__()
        self.ytdlp, self.ffmpeg_dir = ytdlp, ffmpeg_dir
        self._token = 0
        self._last = {}                                  # task id -> (time, state) of the last progress report
        self.queue = DownloadQueue(ytdlp, ffmpeg_dir, get or (lambda k, d=None: d), self._event)

    # events of the queue come from worker threads; signals carry them to the interface thread
    def _event(self, kind: str, obj):
        if kind == "task":
            now, state = time.monotonic(), obj.state
            last = self._last.get(obj.id)
            if last and last[1] == state and now - last[0] < PROGRESS_GAP:
                return
            self._last[obj.id] = (now, state)
            self.task_changed.emit(obj)
        elif kind == "done":
            self.task_changed.emit(obj)
            self.task_done.emit(obj)
        elif kind == "failed":
            self.task_changed.emit(obj)
            self.task_failed.emit(obj)
        elif kind == "cancelled":
            self.task_changed.emit(obj)
            self.task_cancelled.emit(obj)
        elif kind == "group":
            self.group_changed.emit(obj)
        elif kind == "group_done":
            self.group_done.emit(obj)
        elif kind == "thumb":
            self.thumb_ready.emit(obj)

    def sync_tools(self, ytdlp, ffmpeg_dir):
        self.ytdlp = self.queue.ytdlp = ytdlp
        self.ffmpeg_dir = self.queue.ffmpeg_dir = ffmpeg_dir

    # --- information about a link -----------------------------------------
    def invalidate(self):
        """Ignore the result of any running info request."""
        self._token += 1

    def fetch(self, url: str):
        self._token += 1
        threading.Thread(target=self._fetch_worker, args=(self._token, url), daemon=True).start()

    def _fetch_worker(self, token: int, url: str):
        try:
            self.info_ready.emit(token, fetch_info(self.ytdlp, url))
        except EngineError as e:
            self.info_failed.emit(token, e.code, e.detail)
        except Exception as e:      # noqa: BLE001
            import traceback
            from .downloader import log_fetch
            log_fetch("unexpected error:\n" + traceback.format_exc())
            self.info_failed.emit(token, "unknown", str(e))


class InfoFetcher(QObject):
    """Reads a playlist in the background (for 'Sync now'), independent of the New Download page.
    ready(tag, info, thumbs)  thumbs = {video id: picture bytes} for the first few videos."""
    ready = Signal(object, object, object)
    failed = Signal(object, str, str)

    def __init__(self, ytdlp):
        super().__init__()
        self.ytdlp = ytdlp

    def fetch(self, tag, url: str, thumb_ids=lambda info: []):
        threading.Thread(target=self._work, args=(tag, url, thumb_ids), daemon=True).start()

    def _work(self, tag, url, thumb_ids):
        try:
            info = fetch_info(self.ytdlp, url)
            thumbs = {}
            by_id = {e["id"]: e for e in info.get("entries", [])}
            for vid in thumb_ids(info):
                u = (by_id.get(vid) or {}).get("thumb_url")
                data = download_bytes(u) if u else None
                if data:
                    thumbs[vid] = data
            self.ready.emit(tag, info, thumbs)
        except EngineError as e:
            self.failed.emit(tag, e.code, e.detail)
        except Exception as e:      # noqa: BLE001
            self.failed.emit(tag, "unknown", str(e))
