# =============================================================================
# TubeArchive Pro  |  Version 2.3.0  |  File: app/sync.py
# Version history of this file:
#   2.3.0 - 'yearly' schedule
#   1.0.11 - Created: playlists that are synchronized (schedule, last / next sync)
# =============================================================================
"""Playlist sync schedule.   data/sync/sync.json

[{"playlist_id": "PL...", "rec_id": "<history record id>", "url": "...", "title": "...",
  "schedule": "daily" | "weekly" | "monthly" | "yearly", "enabled": true,
  "last_sync": "2026-10-18 01:04", "next_sync": "2026-10-19 01:04", "added": "2026-10-18 01:04"}]

The videos that are already downloaded are kept in the history record (record["videos"]).
Next sync = last sync + 1 day / + 7 days / + 1 month.
"""
import calendar
import json
from datetime import datetime, timedelta

from .paths import SYNC_FILE

SCHEDULES = ("daily", "weekly", "monthly", "yearly")
FMT = "%Y-%m-%d %H:%M"


def now_text() -> str:
    return datetime.now().strftime(FMT)


def add_schedule(start: datetime, schedule: str) -> datetime:
    """start + 1 day / + 7 days / + 1 month / + 1 year (the day is cut to the end of a shorter month)."""
    if schedule == "weekly":
        return start + timedelta(days=7)
    if schedule == "monthly":
        month = start.month % 12 + 1
        year = start.year + (1 if start.month == 12 else 0)
        day = min(start.day, calendar.monthrange(year, month)[1])
        return start.replace(year=year, month=month, day=day)
    if schedule == "yearly":
        year = start.year + 1
        return start.replace(year=year, day=min(start.day, calendar.monthrange(year, start.month)[1]))
    return start + timedelta(days=1)


class SyncManager:
    def __init__(self):
        self.entries: list[dict] = []

    def load(self):
        try:
            data = json.loads(SYNC_FILE.read_text(encoding="utf-8"))
            self.entries = [e for e in data if isinstance(e, dict) and e.get("playlist_id")] \
                if isinstance(data, list) else []
        except (OSError, ValueError):
            self.entries = []

    def save(self):
        SYNC_FILE.parent.mkdir(parents=True, exist_ok=True)
        SYNC_FILE.write_text(json.dumps(self.entries, indent=2, ensure_ascii=False), encoding="utf-8")

    def find(self, playlist_id: str):
        return next((e for e in self.entries if e["playlist_id"] == playlist_id), None)

    def set_next(self, entry: dict, base: datetime | None = None):
        entry["next_sync"] = add_schedule(base or datetime.now(), entry.get("schedule", "daily")).strftime(FMT)

    def add(self, playlist_id: str, rec_id: str, url: str, title: str, schedule: str) -> dict:
        """Add (or update) a playlist; the first sync is due one period after now."""
        e = self.find(playlist_id)
        if e is None:
            e = {"playlist_id": playlist_id, "added": now_text()}
            self.entries.append(e)
        e.update(rec_id=rec_id, url=url, title=title, schedule=schedule if schedule in SCHEDULES else "daily",
                 enabled=True, last_sync=now_text())
        self.set_next(e)
        self.save()
        return e

    def synced_now(self, playlist_id: str):
        """A sync finished (or was skipped): remember it and schedule the next one."""
        e = self.find(playlist_id)
        if e:
            e["last_sync"] = now_text()
            self.set_next(e)
            self.save()

    def set_schedule(self, entry: dict, schedule: str):
        entry["schedule"] = schedule
        try:
            base = datetime.strptime(entry.get("last_sync", ""), FMT)
        except ValueError:
            base = datetime.now()
        self.set_next(entry, base)
        self.save()

    def remove(self, playlist_id: str):
        self.entries = [e for e in self.entries if e["playlist_id"] != playlist_id]
        self.save()

    @staticmethod
    def is_due(entry: dict) -> bool:
        try:
            return entry.get("enabled", True) and datetime.strptime(entry["next_sync"], FMT) <= datetime.now()
        except (KeyError, ValueError):
            return False
