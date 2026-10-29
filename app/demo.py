# =============================================================================
# TubeArchive Pro  |  Version 1.0.13  |  File: app/demo.py
# Version history of this file:
#   1.0.13 - demo_mode (default false): real-data mode; purge_demo removes the samples of earlier versions
#   1.0.11 - 14 samples (4 playlists with known videos), demo sync schedule; seeding is controlled by
#            "demo_data" and "demo_seed_version" (can add the new samples to a history that holds only demo data)
#   1.0.10 - Created: demo history + demo favorites so the Library and Archive pages can be tested
# =============================================================================
"""DEMO data for testing the Library, Archive and Playlist Sync pages.

Samples are written to history.json (marked "demo": true), some are put in favorites and the four
playlists are put in the sync list. This happens when the history holds no real download yet and
"demo_seed_version" is lower than DEMO_VERSION. Set "demo_mode": true (current_settings.json) to get them; by default
(real-data mode) they are not created and old samples are removed (purge_demo). The sample files do not exist on disk (Play shows 'file not found'); delete the
samples in the Library page when you do not need them.
"""
from datetime import datetime, timedelta

DEMO_VERSION = 2
FMT = "%Y-%m-%d %H:%M"

# (title, ext, quality, quality_value, size MB, minutes, kind, colour1, colour2, days ago, favorite category)
SAMPLES = [
    ("Cyberpunk Cinematic Journey", "mp4", "4K", 0, 1620, 24, "video", "#c2185b", "#1a237e", 0, "Cinema"),
    ("Relaxing Lo-Fi Mix", "mp3", "320 kbps", 320, 82, 62, "audio", "#e6a23c", "#3a2b66", 1, "Music"),
    ("Sci-Fi Game Montage", "mp4", "4K", 0, 1637, 18, "video", "#0d47a1", "#00acc1", 1, "Cinema"),
    ("Sci-Fi Game Montage (Full HD)", "mkv", "1080p", 1080, 1137, 18, "video", "#37474f", "#ff7043", 2, None),
    ("Marvel Cinematic Universe: History", "mp4", "1080p", 1080, 2500, 96, "video", "#7a3fb0", "#c0392b", 3, "Cinema"),
    ("Cyberpunk 2077 Full OST Soundtrack", "mp3", "256 kbps", 256, 780, 190, "audio", "#e6d40a", "#222a44", 4, "Music"),
    ("4K Nature Relaxing Video 10 Hours", "mkv", "4K", 0, 8200, 600, "video", "#2f8a3c", "#7fd1c8", 6, None),
    ("Space Documentary [Scientific Channel]", "mp4", "1080p", 1080, 350, 52, "video", "#0a1233", "#c56a1c", 9, "Science"),
    ("AI & Machine Learning Course (24 lectures)", "mp4", "720p", 720, 6400, 0, "playlist", "#12306b", "#3a7bd5", 12, "Science"),
    ("Best Piano Collection", "wav", "44.1 kHz", 44100, 410, 75, "audio", "#5d4037", "#ffb74d", 15, None),
    ("Learn Python in 1 Hour", "webm", "480p", 480, 140, 61, "video", "#1b5e20", "#fdd835", 21, None),
    ("Cooking Playlist: Easy Dinners", "mp4", "1080p", 1080, 3100, 0, "playlist", "#bf360c", "#ffcc80", 30, None),
    ("Relaxing Lo-Fi Beats", "mp3", "192 kbps", 192, 640, 0, "playlist", "#6a1b9a", "#26c6da", 5, "Music"),
    ("Cyberpunk & Synthwave Mix", "mp4", "1080p", 1080, 2900, 0, "playlist", "#ad1457", "#4527a0", 7, None),
]

# demo sync schedule: title -> (schedule, enabled, days since last sync)
SYNC = {
    "Relaxing Lo-Fi Beats": ("daily", True, 2),                  # due
    "Cyberpunk & Synthwave Mix": ("daily", True, 0),
    "AI & Machine Learning Course (24 lectures)": ("weekly", True, 3),
    "Cooking Playlist: Easy Dinners": ("monthly", False, 10),    # paused
}


def _videos(title: str, n: int, size: int, now: datetime) -> dict:
    return {f"{title[:4].strip().lower()}{k:02d}": {
        "title": f"{title.split(' (')[0]} - Part {k}", "file": f"{k:02d} - Part {k}.mp4",
        "size": size // n, "date": (now - timedelta(days=3 + k)).strftime(FMT), "state": "downloaded"}
        for k in range(1, n + 1)}


def purge_demo(ctx) -> bool:
    """Real-data mode (demo_mode false): the sample records of earlier versions are removed from the history, the
    favorites and the sync list. Real downloads are never touched. Returns True when something was removed."""
    ids = {r["id"] for r in ctx.history.records if r.get("demo")}
    if not ids:
        return False
    ctx.history.records = [r for r in ctx.history.records if r["id"] not in ids]
    for rid in ids:
        ctx.favorites.items.pop(rid, None)
    ctx.sync.entries = [e for e in ctx.sync.entries if e.get("rec_id") not in ids]
    ctx.history.save()
    ctx.favorites.save()
    ctx.sync.save()
    ctx.settings.set("demo_seed_version", 0)
    ctx.settings.save()
    return True


def seed_demo(ctx) -> bool:
    """Create / complete the demo records. Returns True when something was written."""
    st = ctx.settings
    if not st.get("demo_mode", False) or st.get("demo_seed_version", 0) >= DEMO_VERSION:
        return False
    if any(not r.get("demo") for r in ctx.history.records):          # real downloads exist: never touch
        st.set("demo_seed_version", DEMO_VERSION)
        st.save()
        return False
    now = datetime.now()
    by_id = {r["id"]: i for i, r in enumerate(ctx.history.records)}
    for i, (title, ext, q, qv, mb, minutes, kind, c1, c2, days, cat) in enumerate(SAMPLES, 1):
        pl = kind == "playlist"
        rid = f"demo-{i:02d}"
        rec = {
            "id": rid, "url": f"https://www.youtube.com/{'playlist?list=DEMO' if pl else 'watch?v=DEMO'}{i:02d}",
            "title": title, "file_name": "" if pl else f"{title}.{ext}", "save_dir": str(st.download_dir()),
            "extension": ext, "quality": q, "quality_value": qv, "format": ext.upper(),
            "size": mb * 1024 * 1024, "duration": minutes * 60 or None, "is_audio": ext in ("mp3", "wav"),
            "is_playlist": pl, "count": 5 if pl else 1, "thumb": "", "thumb_colors": [c1, c2], "demo": True,
            "date": (now - timedelta(days=days, minutes=i * 7)).strftime(FMT),
        }
        if pl:
            rec["playlist_id"] = f"DEMO{i:02d}"
            rec["videos"] = _videos(title, 5, rec["size"], now)
        if rid in by_id:
            ctx.history.records[by_id[rid]] = rec
        else:
            ctx.history.records.append(rec)
        if cat and rid not in ctx.favorites.items:
            if cat not in ctx.favorites.categories:
                ctx.favorites.categories.append(cat)
            ctx.favorites.items[rid] = cat
        if title in SYNC:
            sched, on, ago = SYNC[title]
            last = now - timedelta(days=ago)
            from .sync import add_schedule
            ctx.sync.entries = [e for e in ctx.sync.entries if e["playlist_id"] != rec["playlist_id"]]
            ctx.sync.entries.append({
                "playlist_id": rec["playlist_id"], "rec_id": rid, "url": rec["url"], "title": title,
                "schedule": sched, "enabled": on, "added": (now - timedelta(days=20)).strftime(FMT),
                "last_sync": last.strftime(FMT), "next_sync": add_schedule(last, sched).strftime(FMT)})
    ctx.history.save()
    ctx.favorites.save()
    ctx.sync.save()
    st.set("demo_seed_version", DEMO_VERSION)
    st.save()
    return True
