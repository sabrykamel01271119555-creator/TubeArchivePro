# =============================================================================
# TubeArchive Pro  |  Version 2.3.0  |  File: app/i18n.py
# Version history of this file:
#   2.3.0 - languages are listed by meta.order (English, Arabic, then by number of speakers); a message that a language file
#           does not have is shown in English (not as its id)
#   1.0.6 - No functional change (version header added)
#   1.0.0 - 1.0.5 - first version and earlier fixes (see CHANGELOG.md)
# =============================================================================
"""Language manager: every language is one JSON file in data/languages/."""
import json

from .paths import LANG_DIR

# Only the splash messages need a built-in fallback, because the splash starts
# showing text before the language file has been read.
FALLBACK = {
    "MSG_001": "TubeArchive Pro",
    "MSG_002": "Loading",
    "MSG_003": "Loading default settings",
    "MSG_004": "Loading user settings",
    "MSG_005": "Loading language files",
    "MSG_006": "Loading resources",
    "MSG_007": "Loading download history",
    "MSG_008": "Ready",
}


class LanguageManager:
    def __init__(self):
        self.available: dict[str, str] = {}   # code -> display name
        self._files: dict[str, object] = {}
        self.messages: dict[str, str] = {}
        self.base: dict[str, str] = {}           # English: used for a message the chosen language does not have yet
        self.code = "en"
        self.direction = "ltr"

    def discover(self):
        """Find every <code>.json in data/languages (new languages appear automatically)."""
        self.available.clear()
        self._files.clear()
        found = []
        for f in sorted(LANG_DIR.glob("*.json")):
            try:
                meta = json.loads(f.read_text(encoding="utf-8")).get("meta", {})
            except (OSError, ValueError):
                continue
            found.append((int(meta.get("order", 999)), meta.get("name", f.stem), meta.get("code", f.stem), meta, f))
        for _order, _name, code, meta, f in sorted(found, key=lambda x: (x[0], x[1].lower())):
            self.available[code] = meta.get("name", code)
            self._files[code] = f
        return self.available

    def load(self, code: str) -> bool:
        if code not in self._files:
            code = "en" if "en" in self._files else next(iter(self._files), None)
        if code is None:
            return False
        data = json.loads(self._files[code].read_text(encoding="utf-8"))
        self.messages = data.get("messages", {})
        self.base = {}
        if code != "en" and "en" in self._files:
            try:
                self.base = json.loads(self._files["en"].read_text(encoding="utf-8")).get("messages", {})
            except (OSError, ValueError):
                self.base = {}
        self.direction = data.get("meta", {}).get("direction", "ltr")
        self.code = code
        return True

    @property
    def is_rtl(self) -> bool:
        return self.direction == "rtl"

    def tr(self, msg_id: str, **kwargs) -> str:
        text = self.messages.get(msg_id) or self.base.get(msg_id) or FALLBACK.get(msg_id, msg_id)
        if kwargs:
            try:
                return text.format(**kwargs)
            except (KeyError, IndexError):
                return text
        return text
