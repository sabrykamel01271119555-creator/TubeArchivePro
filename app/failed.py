# =============================================================================
# TubeArchive Pro  |  Version 2.3.2  |  File: app/failed.py
# Version history of this file:
#   2.3.2 - Created: videos that could not be downloaded (kept for 'Later' and reminded at the next start)
# =============================================================================
"""Videos that failed.   data/failed/failed.json

[{"id": "...", "url": "...", "title": "...", "fmt": "MP4", "quality": 0, "folder": "<save folder>", "template": "<output template>" | null,
  "index": 3 | null, "vid": "<video id>", "playlist": "<playlist title>" | "", "code": "unavailable", "detail": "", "date": "2026-10-28 11:00"}]

'Retry now' downloads them again at once; 'Later' keeps them here and the program reminds the user at the next start;
'Cancel' forgets them.
"""
import json
import uuid
from datetime import datetime

from .paths import FAILED_FILE


def entry_of(task) -> dict:
    """The data needed to download a failed task (app.dlqueue.Task) again."""
    code, detail = task.error or ("unknown", "")
    return {"id": uuid.uuid4().hex[:12], "url": task.url, "title": task.title or task.url, "fmt": task.fmt,
            "quality": int(task.quality or 0), "folder": str(task.out_dir), "template": task.template,
            "index": task.index, "vid": task.vid, "playlist": task.group.title if task.group is not None else "",
            "code": code, "detail": detail, "date": datetime.now().strftime("%Y-%m-%d %H:%M")}


class FailedManager:
    def __init__(self, path=None):
        self.path = path or FAILED_FILE
        self.entries: list[dict] = []

    def load(self):
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self.entries = [e for e in data if isinstance(e, dict) and e.get("url")] if isinstance(data, list) else []
        except (OSError, ValueError):
            self.entries = []

    def save(self):
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self.entries, indent=2, ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass

    def add(self, items: list):
        """Keeps the items for later (the same video + folder is kept once)."""
        have = {(e["url"], e.get("folder", "")) for e in self.entries}
        for it in items:
            if (it["url"], it.get("folder", "")) not in have:
                self.entries.append(it)
                have.add((it["url"], it.get("folder", "")))
        self.save()

    def remove(self, items: list):
        ids = {i["id"] for i in items}
        urls = {(i["url"], i.get("folder", "")) for i in items}
        self.entries = [e for e in self.entries if e["id"] not in ids and (e["url"], e.get("folder", "")) not in urls]
        self.save()

    def clear(self):
        self.entries = []
        self.save()
