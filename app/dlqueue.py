# =============================================================================
# TubeArchive Pro  |  Version 2.3.1  |  File: app/dlqueue.py
# Version history of this file:
#   2.3.2 - add_retry(): a failed video is tried again
#   2.3.1 - engine_options gets the video information and the quality (H.264 choice)
#   2.2.5 - discard_task / discard_group / discard_all / purge_discarded (cancel + remove from the list)
#   2.2.4 - a video whose Resume is waiting gets the next free place BEFORE the waiting videos
#   2.2.3 - A paused video holds no place of max_concurrent (a new video starts at once); Resume waits for a free place;
#           counts_by_state()
#   2.0.2 - playlist_concurrent (default 1): how many videos of one playlist run together
#   2.0.1 - Created: download queue. One yt-dlp process per video; at most `max_concurrent` (default 3) run
#           at the same time, the others wait and start as soon as a place is free. A playlist is a group of
#           videos (numbered 01 / 001 ...) that uses the same places; videos can be skipped one by one.
#           The bandwidth limit (speed_limit_mb, 0 = none) is shared by the running processes.
# =============================================================================
"""Download queue.  NO Qt in this file (tested on its own); the Qt signals are in app/download_manager.py.

Rules
  * every video (a single link, or one video of a playlist) is a Task = one yt-dlp process;
  * at most `max_concurrent` tasks run at the same time (Settings, read again at every start so a change
    applies at once); the others are "queued" and start in order when a place is free;
  * a playlist is a Group of tasks. Its videos use the same places, so a single playlist can download
    several videos at the same time; "one by one" (group.sequential) lets only one of them run;
  * `speed_limit_mb` (Settings, 0 = no limit) is divided between the download places: every process gets
    limit / max_concurrent as its own --limit-rate, so all running videos together never pass the limit
    (yt-dlp reads its rate only when it starts, so a share cannot follow videos that come and go).
Events (callback on_event(kind, object); called from worker threads):
  task / done / failed / cancelled -> Task      group / group_done -> Group      thumb -> Task
"""
import itertools
import threading
from pathlib import Path

from .downloader import (DownloadJob, download_bytes, engine_options, index_text, is_audio, safe_name,
                         tpl_escape, video_url)

ACTIVE = ("downloading", "processing", "paused")
RUNNING = ("downloading", "processing")        # these use a place of max_concurrent; a paused video does not (2.2.3)
TERMINAL = ("done", "failed", "skipped", "cancelled")
DEFAULT_CONCURRENT = 3
MAX_CONCURRENT = 10


class Task:
    """One video = one yt-dlp process."""

    def __init__(self, tid: int, url: str, title: str, fmt: str, quality: int, out_dir, **kw):
        self.id, self.url, self.title = tid, url, title
        self.fmt, self.quality, self.out_dir = fmt.upper(), int(quality or 0), Path(out_dir)
        self.group = kw.get("group")
        self.index = kw.get("index")                  # position in the playlist (1 based) or None
        self.vid = kw.get("vid", "")
        self.template = kw.get("template")            # output template (playlist videos)
        self.info = kw.get("info")
        self.est_total = kw.get("est_total")
        self.thumb_bytes = kw.get("thumb_bytes")
        self.thumb_url = kw.get("thumb_url", "")
        self.force = bool(kw.get("force", False))
        self.meta = kw.get("meta") or {}              # whatever the page wants to remember (history, sync ...)
        self.state = "queued"
        self.percent = 0.0
        self.downloaded = 0.0
        self.total = None
        self.speed = 0.0
        self.eta = None
        self.result = None
        self.error = None                             # (code, detail)
        self.job = None
        self.seq = 0                                  # order in which tasks were started
        self._skip = False
        self._before_pause = "downloading"
        self.discard = False                   # cancelled from the Downloads list: also removed from the list (2.2.5)
        self._resume_wanted = False            # 'Resume' was pressed but every place was taken: resumes when one is free

    @property
    def active(self) -> bool:
        return self.state in ACTIVE

    @property
    def finished(self) -> bool:
        return self.state in TERMINAL


class Group:
    """A playlist: its videos are Tasks."""

    def __init__(self, gid: int, title: str, **kw):
        self.id, self.title = gid, title
        self.tasks: list[Task] = []
        self.count = int(kw.get("count") or 0)        # videos of the whole playlist (numbering width)
        self.folder = kw.get("folder")                # where the files go
        self.url = kw.get("url", "")
        self.fmt = kw.get("fmt", "MP4")
        self.quality = int(kw.get("quality") or 0)
        self.thumb_bytes = kw.get("thumb_bytes")
        self.meta = kw.get("meta") or {}
        self.subfolder = False                        # True = the files are in a folder made for this playlist
        self.sequential = False                       # True = one video at a time ("one by one")
        self.state = "running"                        # running | done
        self.result = None
        self.cancelled = False
        self.discard = False                          # cancelled from the Downloads list: removed from the list, no history

    def counts(self) -> dict:
        c = {s: 0 for s in ("queued", "downloading", "processing", "paused", "done", "failed", "skipped", "cancelled")}
        for t in self.tasks:
            c[t.state] += 1
        c["active"] = c["downloading"] + c["processing"] + c["paused"]
        return c

    @property
    def percent(self) -> float:
        live = [t for t in self.tasks if t.state not in ("skipped", "cancelled")]
        return sum(t.percent for t in live) / len(live) if live else 0.0

    @property
    def current(self):
        """The video that was started last (its picture / numbers are shown on the playlist frame)."""
        started = [t for t in self.tasks if t.seq]
        return max(started, key=lambda t: t.seq) if started else None

    @property
    def speed(self) -> float:
        return sum(t.speed for t in self.tasks if t.state == "downloading")

    @property
    def downloaded(self) -> float:
        return sum((t.result or {}).get("size", 0) if t.state == "done" else t.downloaded for t in self.tasks)


class DownloadQueue:
    def __init__(self, ytdlp, ffmpeg_dir, get, on_event=None):
        self.ytdlp, self.ffmpeg_dir, self.get = ytdlp, ffmpeg_dir, get
        self.on_event = on_event or (lambda kind, obj: None)
        self.tasks: list[Task] = []
        self.groups: list[Group] = []
        self.finished_bytes = 0.0
        self._lock = threading.RLock()
        self._ids = itertools.count(1)
        self._seq = itertools.count(1)
        self._pumping = False
        self._again = False

    # --- settings ---------------------------------------------------------
    def max_concurrent(self) -> int:
        try:
            return max(1, min(MAX_CONCURRENT, int(self.get("max_concurrent", DEFAULT_CONCURRENT))))
        except (TypeError, ValueError):
            return DEFAULT_CONCURRENT

    def bandwidth_mb(self) -> float:
        try:
            return max(0.0, float(self.get("speed_limit_mb", 0) or 0))
        except (TypeError, ValueError):
            return 0.0

    # --- adding -----------------------------------------------------------
    def add_video(self, url, out_dir, fmt, quality, title="", info=None, est_total=None, thumb_bytes=None,
                  force=False, meta=None) -> Task:
        t = Task(next(self._ids), url, title or url, fmt, quality, out_dir, info=info, est_total=est_total,
                 thumb_bytes=thumb_bytes, force=force, meta=meta)
        with self._lock:
            self.tasks.append(t)
        self.on_event("task", t)
        self.pump()
        return t

    def add_retry(self, url, out_dir, fmt, quality, title="", template=None, index=None, vid="") -> Task:
        """A video that failed before is tried again (a playlist video keeps its output template, so it lands in the same place)."""
        t = Task(next(self._ids), url, title or url, fmt, quality, out_dir, template=template, index=index, vid=vid,
                 meta={"kind": "retry"})
        with self._lock:
            self.tasks.append(t)
        self.on_event("task", t)
        self.pump()
        return t

    def add_playlist(self, title, entries, out_dir, fmt, quality, subfolder=True, count=None, force=False,
                     thumb_bytes=None, url="", meta=None) -> Group:
        """entries = [{id, index, title, url, thumb_url}]  (index = position in the playlist).
        subfolder: the files go to <out_dir>/<playlist title>/ ; else straight into out_dir."""
        top = max([e.get("index") or 0 for e in entries] + [len(entries)])
        count = max(int(count or 0), top)
        folder = Path(out_dir) / safe_name(title) if subfolder else Path(out_dir)
        g = Group(next(self._ids), title, count=count, folder=folder, url=url, fmt=fmt.upper(), quality=quality,
                  thumb_bytes=thumb_bytes, meta=meta)
        g.subfolder = bool(subfolder)
        prefix = (tpl_escape(safe_name(title)) + "/") if subfolder else ""
        with self._lock:
            self.groups.append(g)
            for n, e in enumerate(entries, 1):
                idx = int(e.get("index") or n)
                tpl = f"{prefix}{index_text(idx, count)} - %(title)s.%(ext)s"
                t = Task(next(self._ids), video_url(e, url), e.get("title") or e.get("id") or url, fmt, quality, out_dir,
                         group=g, index=idx, vid=str(e.get("id", "")), template=tpl, force=force,
                         thumb_url=e.get("thumb_url", ""), est_total=e.get("est_total"))
                g.tasks.append(t)
                self.tasks.append(t)
        self.on_event("group", g)
        self.pump()
        return g

    # --- the pump: starts waiting videos while there is a free place ---------
    def pump(self):
        with self._lock:
            if self._pumping:
                self._again = True
                return
            self._pumping = True
        try:
            while True:
                self._again = False
                self._start_waiting()
                if not self._again:
                    break
        finally:
            self._pumping = False

    def _start_waiting(self):
        while True:
            with self._lock:
                running = [t for t in self.tasks if t.state in RUNNING]       # paused videos do not hold a place
                if len(running) >= self.max_concurrent():
                    return
                wanted = next((t for t in self.tasks if t.state == "paused" and t._resume_wanted), None)
                if wanted is not None and self._do_resume(wanted):   # Resume was pressed: it comes before the waiting videos
                    continue
                nxt = next((t for t in self.tasks if t.state == "queued" and self._allowed(t, running)), None)
                if nxt is None:
                    return
                self._start(nxt, self.max_concurrent())

    def playlist_limit(self) -> int:
        """Videos of ONE playlist that may download together (Settings, default 1; never above max_concurrent)."""
        try:
            n = int(self.get("playlist_concurrent", 1))
        except (TypeError, ValueError):
            n = 1
        return max(1, min(n, self.max_concurrent()))

    def _allowed(self, t: Task, running: list) -> bool:
        if not t.group:
            return True
        cap = 1 if t.group.sequential else self.playlist_limit()
        return sum(1 for r in running if r.group is t.group) < cap

    def _start(self, t: Task, share: int):
        t.state = "downloading"
        t.seq = next(self._seq)
        mb = self.bandwidth_mb()
        rate_kb = (mb * 1024.0 / share) if mb else 0
        extra = engine_options(self.get, t.fmt, rate_kb, t.info, t.quality)
        t.job = DownloadJob(
            self.ytdlp, t.url, t.out_dir, t.fmt, t.quality, info=t.info, est_total=t.est_total,
            ffmpeg_dir=self.ffmpeg_dir, force=t.force or bool(self.get("overwrite_existing", False)),
            extra_args=extra, out_template=t.template,
            on_progress=lambda d, t=t: self._progress(t, d),
            on_state=lambda s, t=t: self._processing(t, s),
            on_finished=lambda r, t=t: self._finished(t, r),
            on_failed=lambda code, detail, t=t: self._failed(t, code, detail),
            on_cancelled=lambda t=t: self._cancelled(t))
        self.on_event("task", t)
        if not t.thumb_bytes and t.thumb_url:                 # the picture of the video that just started
            threading.Thread(target=self._fetch_thumb, args=(t,), daemon=True).start()
        t.job.start()

    def _fetch_thumb(self, t: Task):
        data = download_bytes(t.thumb_url)
        if data:
            t.thumb_bytes = data
            self.on_event("thumb", t)

    # --- events of the processes ---------------------------------------------
    def _progress(self, t: Task, d: dict):
        if t.finished:
            return
        t.percent = d.get("percent", t.percent)
        t.downloaded = d.get("downloaded") or t.downloaded
        t.total = d.get("total") or t.total
        t.speed = d.get("speed") or 0.0
        t.eta = d.get("eta")
        self.on_event("task", t)

    def _processing(self, t: Task, state: str):
        if state == "processing" and t.state == "downloading":
            t.state, t.speed = "processing", 0.0
            self.on_event("task", t)

    def _finished(self, t: Task, r: dict):
        with self._lock:
            t.state, t.result, t.percent, t.speed, t.eta = "done", r, 100.0, 0.0, None
            t.downloaded = t.total = float(r.get("size") or 0)
            self.finished_bytes += t.downloaded
            t.job = None
        self.on_event("done", t)
        self._after(t)

    def _failed(self, t: Task, code: str, detail: str):
        with self._lock:
            t.state, t.error, t.speed, t.eta, t.job = "failed", (code, detail), 0.0, None, None
        self.on_event("failed", t)
        self._after(t)

    def _cancelled(self, t: Task):
        with self._lock:
            t.state = "skipped" if t._skip else "cancelled"
            t.speed, t.eta, t.job = 0.0, None, None
        self.on_event("cancelled", t)
        self._after(t)

    def _after(self, t: Task):
        self._check_group(t.group)
        self.pump()

    def _check_group(self, g):
        if g is None:
            return
        with self._lock:
            if g.state == "done" or not all(t.finished for t in g.tasks):
                return
            g.state = "done"
            done = [t for t in g.tasks if t.state == "done"]
            files = [t.result["path"] for t in done]
            g.result = {
                "files": files, "path": files[-1] if files else "", "name": g.title,
                "size": sum(t.result.get("size", 0) for t in done), "count": len(done),
                "folder": str(g.folder), "is_audio": is_audio(g.fmt), "is_playlist": True,
                "items": [(t.vid, t.result["path"]) for t in done],
                "descriptions": {t.vid: t.result.get("description", "") for t in done if t.vid},
                "failed": sum(1 for t in g.tasks if t.state == "failed"),
                "skipped": sum(1 for t in g.tasks if t.state in ("skipped", "cancelled")),
                "quality": next((t.result.get("quality") for t in done if t.result.get("quality")), None),
            }
        self.on_event("group_done", g)

    # --- control ---------------------------------------------------------------
    @staticmethod
    def _stop_async(t: Task):
        job = t.job
        if job is not None:
            threading.Thread(target=job.cancel, daemon=True).start()

    def skip(self, t: Task):
        """'Skip this one' (playlist details window): a waiting video is dropped, a running one is stopped."""
        with self._lock:
            if t.finished:
                return
            t._skip = True
            if t.state == "queued":
                t.state = "skipped"
                waiting = True
            else:
                waiting = False
        if waiting:
            self.on_event("cancelled", t)
            self._after(t)
        else:
            self._stop_async(t)

    def cancel_task(self, t: Task):
        with self._lock:
            if t.finished:
                return
            waiting = t.state == "queued"
            if waiting:
                t.state = "cancelled"
        if waiting:
            self.on_event("cancelled", t)
            self._after(t)
        else:
            self._stop_async(t)

    def discard_task(self, t: Task):
        """Cancel a video and remove it from the list as soon as it has stopped."""
        t.discard = True
        self.cancel_task(t)

    def discard_group(self, g: Group):
        g.discard = True
        for t in g.tasks:
            t.discard = True
        self.cancel_group(g)

    def discard_all(self):
        """Cancel every unfinished video / playlist and remove them from the list when they have stopped."""
        for g in list(self.groups):
            if g.state != "done":
                self.discard_group(g)
        for t in list(self.tasks):
            if t.group is None and not t.finished:
                self.discard_task(t)

    def purge_discarded(self) -> int:
        """Removes the discarded videos / playlists that have stopped. Returns how many rows went away."""
        with self._lock:
            gone_g = [g for g in self.groups if g.discard and g.state == "done"]
            gone_t = [t for t in self.tasks if (t.discard and t.finished and t.group is None) or t.group in gone_g]
            self.tasks = [t for t in self.tasks if t not in gone_t]
            self.groups = [g for g in self.groups if g not in gone_g]
        return len(gone_g) + len([t for t in gone_t if t.group is None])

    def cancel_group(self, g: Group):
        g.cancelled = True
        for t in list(g.tasks):
            self.cancel_task(t)

    def cancel_all(self, wait: bool = False):
        """Everything stops (Cancel all / exit). wait=True returns when the partial files are deleted."""
        for g in list(self.groups):
            g.cancelled = True
        todo = [t for t in list(self.tasks) if not t.finished]
        jobs = []
        for t in todo:
            with self._lock:
                if t.state == "queued":
                    t.state = "cancelled"
                    jobs.append(None)
                else:
                    jobs.append(t.job)
            if t.state == "cancelled" and t.job is None:
                self.on_event("cancelled", t)
                self._after(t)
        for job in jobs:
            if job is None:
                continue
            if wait:
                job.cancel()
            else:
                threading.Thread(target=job.cancel, daemon=True).start()

    def pause_task(self, t: Task, pump: bool = True) -> bool:
        if t.state in ("downloading", "processing") and t.job and t.job.pause():
            t._before_pause, t.state, t.speed = t.state, "paused", 0.0
            t._resume_wanted = False
            self.on_event("task", t)
            if pump:
                self.pump()                                # the place is free: a waiting / new video starts first
            return True
        return False

    def _do_resume(self, t: Task) -> bool:
        if t.state == "paused" and t.job and t.job.resume():
            t.state, t._resume_wanted = t._before_pause, False
            self.on_event("task", t)
            return True
        return False

    def resume_task(self, t: Task) -> bool:
        """Resume a paused video. A paused video holds no place, so a video added meanwhile may have taken them all; then
        this one waits (still shown paused) and resumes by itself at the next free place, before the waiting videos."""
        if t.state != "paused" or not t.job:
            return False
        with self._lock:
            full = sum(1 for x in self.tasks if x.state in RUNNING) >= self.max_concurrent()
            if full:
                t._resume_wanted = True
                self.on_event("task", t)
                return True
        return self._do_resume(t)

    def pause_all(self) -> int:
        """Pause every running video; the waiting ones stay waiting (a video added later still starts: paused ones hold no place)."""
        return sum(1 for t in list(self.tasks) if self.pause_task(t, pump=False))

    def resume_all(self) -> int:
        return sum(1 for t in list(self.tasks) if self.resume_task(t))

    def set_sequential(self, g: Group, on: bool):
        g.sequential = bool(on)
        self.on_event("group", g)
        self.pump()

    def clear_finished(self) -> int:
        """Removes the finished videos / playlists from the list. Returns how many rows went away."""
        with self._lock:
            gone_groups = [g for g in self.groups if g.state == "done"]
            gone = [t for t in self.tasks if t.finished and (t.group is None or t.group.state == "done")]
            self.tasks = [t for t in self.tasks if t not in gone]
            self.groups = [g for g in self.groups if g not in gone_groups]
        return len([t for t in gone if t.group is None]) + len(gone_groups)

    # --- numbers for the interface ---------------------------------------------
    def counts(self) -> tuple:
        """(videos running, videos waiting)"""
        with self._lock:
            return (sum(1 for t in self.tasks if t.state in ACTIVE),
                    sum(1 for t in self.tasks if t.state == "queued"))

    def counts_by_state(self) -> dict:
        """Files (every video of a playlist is one file): downloading now / paused / waiting in the queue."""
        with self._lock:
            return {"downloading": sum(1 for t in self.tasks if t.state in RUNNING),
                    "paused": sum(1 for t in self.tasks if t.state == "paused"),
                    "waiting": sum(1 for t in self.tasks if t.state == "queued")}

    def speed(self) -> float:
        """bytes / second of all running videos"""
        return sum(t.speed for t in list(self.tasks) if t.state == "downloading")

    def downloaded_bytes(self) -> float:
        """Everything downloaded since the program started (finished videos + what is on its way)."""
        return self.finished_bytes + sum(t.downloaded for t in list(self.tasks) if t.state in ACTIVE)

    def busy(self) -> bool:
        return any(not t.finished for t in self.tasks)

    def active_percents(self) -> list:
        """One number per unfinished link / playlist (the exit window)."""
        out = [t.percent for t in self.tasks if t.group is None and not t.finished]
        out += [g.percent for g in self.groups if g.state != "done"]
        return out

    def top_items(self) -> list:
        """Rows of the Downloads page in the order they were added: single videos and playlists."""
        with self._lock:
            order = []
            seen = set()
            for t in self.tasks:
                if t.group is None:
                    order.append(t)
                elif t.group.id not in seen:
                    seen.add(t.group.id)
                    order.append(t.group)
            return order
