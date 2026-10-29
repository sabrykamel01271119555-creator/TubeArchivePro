# =============================================================================
# TubeArchive Pro  |  Version 2.0.6  |  File: app/history.py
# Version history of this file:
#   2.3.2 - find_video() also finds a video downloaded inside a playlist; absorb_singles(): videos downloaded directly count as downloaded in the playlist record
#   2.0.6 - video_key() and find_video(): the same video is recognised from any form of its link
#   2.0.2 - delete_files(): physical files of a video / playlist (+ the playlist's own subfolder)
#   1.0.11 - Playlist records: playlist_id, videos {id: {...}}, last_sync; find_playlist(), extra fields
#   1.0.9 - Real records: new_record() (id, thumbnail file, size, format ...), find(), remove(),
#           newest-first ordering. Old records without an id get one when loaded.
#   1.0.6 - No functional change (version header added)
#   1.0.0 - 1.0.5 - first version and earlier fixes (see CHANGELOG.md)
# =============================================================================
"""Download history (old downloads), newest first.

Each record in data/history/history.json:
{
  "id": "a1b2c3...", "url": "...", "title": "...", "file_name": "...", "save_dir": "...",
  "extension": "mp4", "quality": "1080p", "date": "2026-10-16 23:51",
  "format": "MP4", "quality_value": 1080,          # what was chosen in the drop-downs (0 = Best)
  "size": 123456789, "duration": 100, "is_audio": false,
  "is_playlist": false, "count": 1, "thumb": "a1b2c3.img"   # file inside data/history/thumbs
}
Playlist records also have: "playlist_id", "videos": {"<video id>": {"title", "file", "size", "date",
"state": "downloaded" | "skipped"}} and "last_sync" (date of the last 'Sync now').
"""
import json
import os
import shutil
import uuid
from datetime import datetime

from .downloader import is_playlist_url, playlist_id
from .paths import HISTORY_FILE, THUMBS_DIR


def video_key(url: str) -> str:
    """A key that is the same for every form of a video link (watch?v=, youtu.be/, shorts/, embed/); other sites: the link."""
    from urllib.parse import parse_qs, urlparse
    try:
        u = urlparse((url or "").strip())
    except ValueError:
        return ""
    host = (u.hostname or "").lower().removeprefix("www.").removeprefix("m.")
    parts = [p for p in u.path.split("/") if p]
    vid = ""
    if host == "youtu.be" and parts:
        vid = parts[0]
    elif host.endswith("youtube.com") or host.endswith("youtube-nocookie.com"):
        if u.path.rstrip("/") == "/watch":
            vid = (parse_qs(u.query).get("v") or [""])[0]
        elif len(parts) >= 2 and parts[0] in ("shorts", "embed", "live", "v"):
            vid = parts[1]
    if vid:
        return "yt:" + vid
    return (host + u.path.rstrip("/") + ("?" + u.query if u.query else "")).lower() if host else ""


class HistoryManager:
    def __init__(self):
        self.records: list[dict] = []

    def load(self):
        HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        try:
            data = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
            self.records = [r for r in data if isinstance(r, dict)] if isinstance(data, list) else []
        except (OSError, ValueError):
            self.records = []
            self.save()
            return
        changed = False
        for r in self.records:
            if not r.get("id"):
                r["id"] = uuid.uuid4().hex
                changed = True
        if changed:
            self.save()

    def add(self, record: dict):
        record.setdefault("id", uuid.uuid4().hex)
        self.records.insert(0, record)
        self.save()

    def save(self):
        HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        HISTORY_FILE.write_text(
            json.dumps(self.records, indent=2, ensure_ascii=False), encoding="utf-8")

    # ------------------------------------------------------------------
    def new_record(self, *, url: str, title: str, file_name: str, save_dir: str, fmt: str,
                   quality: str, quality_value: int, size: int, duration=None, is_audio=False,
                   is_playlist=False, count=1, thumb_bytes: bytes | None = None, extra: dict | None = None) -> dict:
        """Build a record for a finished download, save its thumbnail and add it to the history."""
        rid = uuid.uuid4().hex
        thumb = ""
        if thumb_bytes:
            try:
                THUMBS_DIR.mkdir(parents=True, exist_ok=True)
                (THUMBS_DIR / f"{rid}.img").write_bytes(thumb_bytes)
                thumb = f"{rid}.img"
            except OSError:
                thumb = ""
        rec = {
            "id": rid, "url": url, "title": title, "file_name": file_name, "save_dir": save_dir,
            "extension": fmt.lower(), "quality": quality or "", "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "format": fmt.upper(), "quality_value": int(quality_value or 0), "size": int(size or 0),
            "duration": duration, "is_audio": bool(is_audio), "is_playlist": bool(is_playlist),
            "count": int(count or 1), "thumb": thumb,
        }
        if is_playlist:
            rec["playlist_id"] = playlist_id(url)
            rec.setdefault("videos", {})
        rec.update(extra or {})
        self.add(rec)
        return rec

    def sorted_records(self) -> list[dict]:
        """Newest first (date text 'YYYY-MM-DD HH:MM' sorts correctly; stable for equal dates)."""
        return sorted(self.records, key=lambda r: r.get("date", ""), reverse=True)

    def find_playlist(self, url: str) -> dict | None:
        """The history record of a playlist that was downloaded before (same list= id), newest first."""
        pid = playlist_id(url) if is_playlist_url(url) else ""
        if not pid:
            return None
        for r in self.sorted_records():
            if r.get("is_playlist") and (r.get("playlist_id") or playlist_id(r.get("url", ""))) == pid:
                return r
        return None

    @staticmethod
    def file_key(rec: dict) -> str:
        """One key per file on disk (folder + file name); '' for a playlist (it has no single file)."""
        if rec.get("is_playlist") or not rec.get("file_name"):
            return ""
        return os.path.normcase(os.path.normpath(os.path.join(os.path.expanduser(rec.get("save_dir", "")), rec["file_name"])))

    def same_file(self, rec: dict) -> list:
        """The OTHER records that point to the same file as `rec` (the history keeps one entry per file)."""
        key = self.file_key(rec)
        return [r for r in self.records if key and r is not rec and r.get("id") != rec.get("id") and self.file_key(r) == key]

    def dedupe_files(self) -> dict:
        """Keep only the newest record of every file. Returns {removed id: kept id} (favorites follow it). 2.0.7"""
        newest = {}
        for r in sorted(self.records, key=lambda r: r.get("date", "")):
            k = self.file_key(r)
            if k:
                newest[k] = r
        mapping = {}
        for r in list(self.records):
            k = self.file_key(r)
            if k and newest[k] is not r:
                mapping[r["id"]] = newest[k]["id"]
                self.records.remove(r)
        if mapping:
            self.save()
        return mapping

    def find_video(self, url: str) -> dict | None:
        """The newest record of a single video downloaded before (same video id / same link), or None (2.0.5)."""
        key = video_key(url)
        if not key:
            return None
        for r in self.sorted_records():
            if not r.get("is_playlist") and video_key(r.get("url", "")) == key:
                return r
        vid = key.removeprefix("yt:")
        for r in self.sorted_records():                      # 2.3.2: downloaded as a part of a playlist
            v = (r.get("videos") or {}).get(vid) if r.get("is_playlist") else None
            if v and v.get("state", "downloaded") == "downloaded":
                f = v.get("file", "")
                pseudo = dict(r)
                pseudo.update({"is_playlist": False, "title": v.get("title", r.get("title", "")), "date": v.get("date", r.get("date", "")),
                               "size": v.get("size", 0), "file_name": os.path.basename(f), "url": "https://www.youtube.com/watch?v=" + vid})
                if os.path.isabs(f):
                    pseudo["save_dir"] = os.path.dirname(f)
                return pseudo
        return None

    def absorb_singles(self, rec: dict, ids) -> int:
        """2.3.2: videos of this playlist that were downloaded directly (a single link) count as downloaded in the playlist
        record, so a sync does not download them again. Returns how many were added."""
        vids = rec.setdefault("videos", {})
        wanted = {i for i in ids if i not in vids or vids[i].get("state") not in ("downloaded",)}
        n = 0
        for r in self.records:
            if r.get("is_playlist"):
                continue
            key = video_key(r.get("url", ""))
            vid = key.removeprefix("yt:") if key.startswith("yt:") else ""
            if vid in wanted and vids.get(vid, {}).get("state") != "skipped":
                path = os.path.join(os.path.expanduser(r.get("save_dir", "")), r.get("file_name", ""))
                if os.path.isfile(path):
                    vids[vid] = {"title": r.get("title", vid), "file": path, "size": r.get("size", 0),
                                 "date": r.get("date", ""), "state": "downloaded"}
                    wanted.discard(vid)
                    n += 1
        if n:
            self.save()
        return n

    def find(self, rid: str) -> dict | None:
        return next((r for r in self.records if r.get("id") == rid), None)

    def remove(self, rid: str):
        rec = self.find(rid)
        if not rec:
            return
        self.records.remove(rec)
        if rec.get("thumb"):
            try:
                (THUMBS_DIR / rec["thumb"]).unlink()
            except OSError:
                pass
        self.save()

    @staticmethod
    def thumb_path(rec: dict) -> str | None:
        if rec.get("thumb"):
            p = THUMBS_DIR / rec["thumb"]
            if p.exists():
                return str(p)
        return None


def delete_files(rec: dict, protect=()) -> tuple:
    """Deletes the physical files of a history record (2.0.2: Delete button -> "delete the file(s) too").
    A video / audio: its file.  A playlist: every downloaded video of it and, when the playlist has its own subfolder,
    that folder too (a folder that is not marked as the playlist's own is only removed when it is empty).
    `protect` = folders that must never be removed (the download folder).
    Returns (number of files deleted, [error texts])."""
    deleted, errors = 0, []
    folder = os.path.expanduser(rec.get("save_dir", ""))
    paths = []
    if rec.get("is_playlist"):
        paths = [v.get("file", "") for v in (rec.get("videos") or {}).values() if v.get("file")]
    elif rec.get("file_name"):
        paths = [os.path.join(folder, rec["file_name"])]
    for path in paths:
        try:
            if os.path.isfile(path):
                os.remove(path)
                deleted += 1
        except OSError as exc:
            errors.append(f"{os.path.basename(path)}: {exc}")
    if rec.get("is_playlist") and folder and os.path.isdir(folder):
        norm = lambda x: os.path.normcase(os.path.abspath(os.path.expanduser(str(x))))      # noqa: E731
        me = norm(folder)
        prot = [norm(x) for x in protect]
        safe = (me not in prot and os.path.dirname(me) != me                 # not the download folder, not a drive root
                and not any(x == me or x.startswith(me + os.sep) for x in prot))   # and it does not contain it
        if safe:
            try:
                if rec.get("subfolder"):
                    shutil.rmtree(folder)                    # the playlist's own folder: everything in it goes
                else:
                    os.rmdir(folder)                         # only when it is empty
            except OSError as exc:
                if rec.get("subfolder"):
                    errors.append(f"{os.path.basename(folder)}: {exc}")
    return deleted, errors
