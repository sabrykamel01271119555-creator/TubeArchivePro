# =============================================================================
# TubeArchive Pro  |  Version 2.3.1  |  File: app/stats.py
# Version history of this file:
#   2.3.1 - fetch_reviews / load_reviews / ReviewsFetcher: the real ratings + comments of the sheet (GET ?action=reviews)
#   2.3.0 - users = the installations registered in the rating sheet (install_id) + the old numbers of total_users.txt;
#           fetch_stats() reads users per version and the rating in one call
#   2.2.8 - Created: numbers shown on the splash screen (users, users per version, rating of the users)
# =============================================================================
"""Numbers for the splash screen. The splash appears before any network call, so it shows the numbers of the LAST online
check (cache) - or the shipped baseline the first time - and the background check refreshes them for the next start.

users      : the installations of the register (Apps Script web app, GET ?action=stats -> "users", "versions") + the numbers of the
             versions before the register existed (total_users.txt of the online folder, else data/splash_baseline.json)
rating     : {"average": 4.6, "count": 120} from the same call                                  -> rating_stats.json
"""
import json
import urllib.request
from pathlib import Path

from .ads import UA
from .paths import APP_DIR, CACHE_DIR

BASELINE_USERS = APP_DIR / "data" / "splash_baseline.json"      # {"versions": [["1.0.0", 25], ...]}
RATING_FILE = "rating_stats.json"


def _versions_key(v: str):
    return tuple(int(x) for x in str(v).replace("v", "").split(".") if x.isdigit())


BASE_FILE = "users_base.json"          # numbers of total_users.txt (the versions before the register), cached
USERS_FILE = "users_stats.json"        # {"users": N, "versions": {"2.2.8": 3}} of the register, cached


def _read_versions(path: Path) -> list:
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8")).get("versions", [])
        return [(str(v), int(n)) for v, n in raw]
    except (OSError, ValueError, TypeError, AttributeError):
        return []


def users_data(cache_dir: Path = CACHE_DIR, baseline: Path = BASELINE_USERS) -> dict:
    """{"total": N, "versions": [("1.0.0", 25), ...]}: the old numbers (online total_users.txt, else the shipped baseline) plus the
    users of the register per version (the last check; nothing the first time)."""
    base = _read_versions(Path(cache_dir) / BASE_FILE) or _read_versions(baseline)
    merged = dict(base)
    try:
        reg = json.loads((Path(cache_dir) / USERS_FILE).read_text(encoding="utf-8")).get("versions", {})
        for v, n in reg.items():
            merged[str(v)] = merged.get(str(v), 0) + int(n)
    except (OSError, ValueError, TypeError, AttributeError):
        pass
    versions = sorted(merged.items(), key=lambda x: _versions_key(x[0]))
    return {"total": sum(n for _v, n in versions), "versions": versions}


def fetch_users_base(base_url: str, cache_dir: Path = CACHE_DIR):
    """total_users.txt of the online folder ('1.0.0 = 25' lines) -> cache. None when it is not there."""
    from .ads import USERS_FILE as NAME, parse_user_totals, read_text_file, version_text
    try:
        text = read_text_file(base_url, NAME)
    except Exception:                                   # noqa: BLE001
        return None
    totals = parse_user_totals(text or "")
    if not totals:
        return None
    out = {"versions": [(version_text(v), n) for v, n in sorted(totals.items())]}
    try:
        Path(cache_dir).mkdir(parents=True, exist_ok=True)
        (Path(cache_dir) / BASE_FILE).write_text(json.dumps(out), encoding="utf-8")
    except OSError:
        pass
    return out


def fetch_rating(endpoint: str, cache_dir: Path = CACHE_DIR, timeout: float = 8):
    """GET <endpoint>?action=stats -> {"average", "count"}; saved for the next start. None when it did not work."""
    endpoint = (endpoint or "").strip()
    if not endpoint or "script.google.com/macros" not in endpoint and "127.0.0.1" not in endpoint:
        return None                                   # (a Google form address has no rating numbers)
    url = endpoint + ("&" if "?" in endpoint else "?") + "action=stats"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            d = json.loads(r.read(100_000).decode("utf-8", "replace"))
    except Exception:                                   # noqa: BLE001
        return None
    try:
        Path(cache_dir).mkdir(parents=True, exist_ok=True)
        if isinstance(d.get("versions"), dict):         # the users of the register
            (Path(cache_dir) / USERS_FILE).write_text(
                json.dumps({"users": int(d.get("users", 0)), "versions": d["versions"]}), encoding="utf-8")
    except (OSError, ValueError, TypeError, AttributeError):
        pass
    try:
        out = {"average": round(float(d["average"]), 2), "count": int(d["count"])}
        if out["count"] <= 0 or not 0 <= out["average"] <= 5:
            return None
        (Path(cache_dir) / RATING_FILE).write_text(json.dumps(out), encoding="utf-8")
    except (OSError, ValueError, TypeError, KeyError):
        return None
    return out


def load_rating(cache_dir: Path = CACHE_DIR):
    try:
        d = json.loads((Path(cache_dir) / RATING_FILE).read_text(encoding="utf-8"))
        return {"average": float(d["average"]), "count": int(d["count"])} if int(d["count"]) > 0 else None
    except (OSError, ValueError, KeyError, TypeError):
        return None


def splash_data() -> dict:
    """Everything the splash screen shows: {"total", "versions", "rating"}."""
    d = users_data()
    d["rating"] = load_rating()
    return d


# ----------------------------------------------------------------------
# reviews of the sheet (GET ?action=reviews -> {"reviews": [{"rating", "feedback", "date", "country", "version"}]})
# ----------------------------------------------------------------------
REVIEWS_FILE = "reviews_cache.json"


def fetch_reviews(endpoint: str, cache_dir: Path = CACHE_DIR, timeout: int = 12):
    """The latest ratings (with or without a comment) of the users; None when the script cannot be reached."""
    if not endpoint or "script.google.com/macros" not in endpoint and "127.0.0.1" not in endpoint:
        return None
    url = endpoint + ("&" if "?" in endpoint else "?") + "action=reviews"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            d = json.loads(r.read(2_000_000).decode("utf-8", "replace"))
        rows = [x for x in d.get("reviews", []) if isinstance(x, dict) and 1 <= int(x.get("rating", 0)) <= 5]
    except Exception:                                   # noqa: BLE001
        return None
    try:
        Path(cache_dir).mkdir(parents=True, exist_ok=True)
        (Path(cache_dir) / REVIEWS_FILE).write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass
    return rows


def load_reviews(cache_dir: Path = CACHE_DIR) -> list:
    try:
        rows = json.loads((Path(cache_dir) / REVIEWS_FILE).read_text(encoding="utf-8"))
        return rows if isinstance(rows, list) else []
    except (OSError, ValueError):
        return []


try:
    import threading
    from PySide6.QtCore import QObject, Signal

    class ReviewsFetcher(QObject):
        """done({"reviews": [...]}) or done({"reviews": None}) when the sheet cannot be reached (runs in a thread)."""
        done = Signal(object)

        def fetch(self, endpoint: str):
            threading.Thread(target=lambda: self.done.emit({"reviews": fetch_reviews(endpoint)}), daemon=True).start()
except ImportError:                                     # tests without Qt
    pass
