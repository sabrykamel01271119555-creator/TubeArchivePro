# =============================================================================
# TubeArchive Pro  |  Version 2.3.0  |  File: app/feedback.py
# Version history of this file:
#   2.3.0 - install register (install_id, installation_date, version, os, language, country) = the number of users; the rating
#           carries rating_date / new_features; sheet columns: install_id installation_date version os language country
#           rating_date rating feedback new_features
#   2.2.9 - ONE setting feedback_form_url: an Apps Script web app address (script.google.com/macros/...) is posted as JSON with the
#           keys of feedback_form_fields (date, version, os, rating, feedback, newfeatures); a Google form address is posted as a form
#   2.2.8 - Apps Script endpoint (feedback_endpoint_url): JSON with install id, version, OS, language, rating, comment and the wanted
#           new features; the old Google form stays as a fallback
#   2.0.2 - The last rating is kept in data/feedback/my_rating.json and shown again in the exit window; a rating that
#           is new or changed is sent to the Google form (feedback_form_url / feedback_form_fields in the settings)
#   1.0.6 - No functional change (version header added)
#   1.0.0 - 1.0.5 - first version and earlier fixes (see CHANGELOG.md)
# =============================================================================
"""Ratings typed in the exit window.

data/feedback/feedback.json   history of every submitted rating  [{"rating": 4, "comment": "...", "version": "2.0.2", "date": ".."}]
data/feedback/my_rating.json  the LAST rating {"rating", "comment", "version", "date", "sent"}; the exit window shows it again.
                              "sent" is False until the Google form accepted it (then it is retried at the next exit).
Google form: settings `feedback_form_url` (the form's link, .../viewform or .../formResponse) and
`feedback_form_fields` {"rating": "entry.123456", "comment": "entry.234567", "version": "entry.345678"}.
Both stay empty until the form exists; then the rating is only kept locally.
"""
import json
import platform
import urllib.parse
import urllib.request
from datetime import datetime

from .paths import FEEDBACK_FILE

MY_RATING_FILE = FEEDBACK_FILE.parent / "my_rating.json"


def form_response_url(url: str) -> str:
    """.../viewform?usp=... -> .../formResponse (the address that accepts the answers)."""
    url = (url or "").strip()
    if "/viewform" in url:
        url = url.split("/viewform", 1)[0] + "/formResponse"
    return url


def post_form(url: str, fields: dict, values: dict, timeout: float = 8) -> bool:
    """Sends one answer to a Google form. fields = {"rating": "entry.1", ...}, values = {"rating": 4, ...}."""
    url = form_response_url(url)
    data = {fields[k]: str(v) for k, v in values.items() if fields.get(k)}
    if not url or not data:
        return False
    try:
        req = urllib.request.Request(url, data=urllib.parse.urlencode(data).encode("utf-8"),
                                     headers={"User-Agent": "Mozilla/5.0", "Content-Type": "application/x-www-form-urlencoded"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return 200 <= r.status < 400
    except Exception:                       # noqa: BLE001  (offline / form closed: the rating is sent next time)
        return False


def post_json(url: str, payload: dict, timeout: float = 10) -> bool:
    """Sends one rating to the Apps Script web app (the answer is {"status": "success"})."""
    url = (url or "").strip()
    if not url:
        return False
    try:
        req = urllib.request.Request(url, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                                     headers={"User-Agent": "Mozilla/5.0", "Content-Type": "text/plain;charset=utf-8"})
        with urllib.request.urlopen(req, timeout=timeout) as r:          # (Apps Script answers through a redirect)
            return json.loads(r.read(20_000).decode("utf-8", "replace")).get("status") == "success"
    except Exception:                       # noqa: BLE001
        return False


SCRIPT_FIELDS = {"install_id": "install_id", "installation_date": "installation_date", "version": "version", "os": "os",
                 "language": "language", "country": "country", "rating_date": "rating_date", "rating": "rating",
                 "feedback": "feedback", "new_features": "new_features"}
INSTALL_FILE = FEEDBACK_FILE.parent / "install.json"


def is_script_url(url: str) -> bool:
    """An Apps Script web app (script.google.com/macros/.../exec) takes JSON; a Google form takes form fields."""
    return "script.google.com/macros" in (url or "")


def country_code() -> str:
    """Country of the Windows region settings ('EG', 'US' ...): no internet lookup, only the computer's own setting."""
    try:
        from PySide6.QtCore import QLocale
        name = QLocale.system().name()                      # 'ar_EG'
        if "_" in name:
            return name.split("_")[1][:2].upper()
    except Exception:                                       # noqa: BLE001
        pass
    try:
        import locale
        name = locale.getlocale()[0] or ""
        if "_" in name and len(name.split("_")[1]) == 2:
            return name.split("_")[1].upper()
    except Exception:                                       # noqa: BLE001
        pass
    return ""


def os_text() -> str:
    try:
        return f"{platform.system()} {platform.release()} ({platform.version()})"
    except Exception:                       # noqa: BLE001
        return ""


class FeedbackManager:
    def __init__(self, history_file=FEEDBACK_FILE, my_file=MY_RATING_FILE):
        self.history_file, self.my_file = history_file, my_file

    # --- history -----------------------------------------------------------
    def install_id(self) -> str:
        """A random anonymous id of this installation (so a changed rating replaces the old row, not a second one)."""
        p = self.my_file.parent / "install_id.txt"
        try:
            text = p.read_text(encoding="utf-8").strip()
            if len(text) >= 16:
                return text
        except OSError:
            pass
        import uuid
        text = uuid.uuid4().hex
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text, encoding="utf-8")
        except OSError:
            pass
        return text

    # --- the install register (counts the users) -----------------------------
    def installation_date(self) -> str:
        """Day of the first start (kept in data/feedback/install.json)."""
        try:
            d = json.loads(INSTALL_FILE.read_text(encoding="utf-8"))
            if isinstance(d, dict) and d.get("installation_date"):
                return str(d["installation_date"])
        except (OSError, ValueError):
            pass
        d = {"installation_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "registered_version": ""}
        self._save_install(d)
        return d["installation_date"]

    def _save_install(self, d: dict):
        try:
            INSTALL_FILE.parent.mkdir(parents=True, exist_ok=True)
            INSTALL_FILE.write_text(json.dumps(d, indent=2), encoding="utf-8")
        except OSError:
            pass

    def needs_register(self, version: str) -> bool:
        """True at the first start and after every update of the program (the register keeps the newest version)."""
        self.installation_date()
        try:
            return json.loads(INSTALL_FILE.read_text(encoding="utf-8")).get("registered_version") != version
        except (OSError, ValueError):
            return True

    def register(self, url: str, names: dict, language: str, version: str) -> bool:
        """Sends install id / dates / version / OS / language / country (no rating) to the Apps Script web app."""
        if not is_script_url(url) or not self.needs_register(version):
            return False
        keys = {**SCRIPT_FIELDS, **{k: v for k, v in (names or {}).items() if k in SCRIPT_FIELDS and v}}
        values = {"install_id": self.install_id(), "installation_date": self.installation_date(), "version": version,
                  "os": os_text(), "language": language, "country": country_code()}
        if not post_json(url, {keys[k]: v for k, v in values.items()}):
            return False
        d = {"installation_date": values["installation_date"], "registered_version": version}
        self._save_install(d)
        return True

    def add(self, rating: int, comment: str, version: str, features: str = ""):
        try:
            data = json.loads(self.history_file.read_text(encoding="utf-8"))
            if not isinstance(data, list):
                data = []
        except (OSError, ValueError):
            data = []
        data.append({"rating": rating, "comment": comment.strip(), "features": (features or "").strip(), "version": version,
                     "date": datetime.now().strftime("%Y-%m-%d %H:%M")})
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        self.history_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    # --- the last rating ---------------------------------------------------
    def current(self):
        """The rating given before {"rating", "comment", ...} or None."""
        try:
            d = json.loads(self.my_file.read_text(encoding="utf-8"))
            return d if isinstance(d, dict) and int(d.get("rating", 0)) > 0 else None
        except (OSError, ValueError, TypeError):
            return None

    def save_rating(self, rating: int, comment: str, version: str, features: str = "") -> bool:
        """Keeps the rating. True = it is new or changed (or the last one was never sent): it has to be sent."""
        comment = (comment or "").strip()
        old = self.current()
        features = (features or "").strip()
        same = bool(old) and int(old["rating"]) == int(rating) and (old.get("comment") or "") == comment \
            and (old.get("features") or "") == features
        if same and old.get("sent"):
            return False
        sent = bool(same and old.get("sent"))
        rec = {"rating": int(rating), "comment": comment, "features": features, "version": version,
               "date": datetime.now().strftime("%Y-%m-%d %H:%M"), "sent": sent}
        try:
            self.my_file.parent.mkdir(parents=True, exist_ok=True)
            self.my_file.write_text(json.dumps(rec, indent=2, ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass
        if not same:
            self.add(rating, comment, version, features)
        return True

    def mark_sent(self):
        d = self.current()
        if d:
            d["sent"] = True
            try:
                self.my_file.write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")
            except OSError:
                pass

    def send_endpoint(self, endpoint: str, language: str = "", names: dict | None = None) -> bool:
        """Sends the last rating to the Apps Script web app as JSON; marks it as sent when it was accepted.
        names = {"rating": "rating", ...}: the JSON key of each value (setting feedback_form_fields); empty = default names."""
        d = self.current()
        if not d or not (endpoint or "").strip():
            return False
        keys = {**SCRIPT_FIELDS, **{k: v for k, v in (names or {}).items() if k in SCRIPT_FIELDS and v}}
        values = {"install_id": self.install_id(), "installation_date": self.installation_date(),
                  "version": d.get("version", ""), "os": os_text(), "language": language, "country": country_code(),
                  "rating_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "rating": int(d["rating"]),
                  "feedback": d.get("comment", ""), "new_features": d.get("features", "")}
        ok = post_json(endpoint, {keys[k]: v for k, v in values.items()})
        if ok:
            self.mark_sent()
        return ok

    def send(self, url: str, fields: dict, language: str = "") -> bool:
        """Sends the last rating (Apps Script web app -> JSON, Google form -> form fields); marks it as sent when accepted."""
        if is_script_url(url):
            return self.send_endpoint(url, language, fields)
        d = self.current()
        if not d or not url:
            return False
        ok = post_form(url, fields or {}, {"rating": d["rating"], "comment": d.get("comment", ""),
                                           "version": d.get("version", ""), "newfeatures": d.get("features", ""),
                                           "os": os_text()})
        if ok:
            self.mark_sent()
        return ok
