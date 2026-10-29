# =============================================================================
# TubeArchive Pro  |  Version 2.3.0  |  File: app/settings.py
# Version history of this file:
#   2.2.6 - a saved old Google Drive online_folder_url is replaced by the (GitHub) default
#   2.3.0 - default file write is guarded (read only program folder)
#   2.0.2 - subscribe(): screens are told when a setting changes (Settings page <-> 'don't show again' ticks)
#   2.0.1 - config_version: settings saved by an older version get the new default of max_concurrent (3) once
#   1.0.12 - reset_to_defaults keeps demo_seed_version and the window size
#   1.0.6 - No functional change (version header added)
#   1.0.0 - 1.0.5 - first version and earlier fixes (see CHANGELOG.md)
# =============================================================================
"""Default settings + current (user) settings, both stored as JSON files."""
import json
import os
from pathlib import Path

from .paths import CONFIG_DIR, CURRENT_SETTINGS_FILE, DEFAULT_SETTINGS_FILE

# Used only if default_settings.json is missing/corrupt.
_EMERGENCY_DEFAULTS = {"language": "en", "download_dir": "~/Videos/TubeArchive", "max_concurrent": 3}
CONFIG_VERSION = 2          # raised when an old setting must be replaced by a new default (see load_current)


class SettingsManager:
    def __init__(self):
        self.defaults: dict = {}
        self.current: dict = {}
        self._listeners: list = []           # functions called with the key when a setting changes ("*" = everything)

    # --- loading -----------------------------------------------------
    def load_defaults(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        try:
            self.defaults = json.loads(DEFAULT_SETTINGS_FILE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            self.defaults = dict(_EMERGENCY_DEFAULTS)
            try:                                              # (the installed program folder may be read only)
                DEFAULT_SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
                DEFAULT_SETTINGS_FILE.write_text(
                    json.dumps(self.defaults, indent=2, ensure_ascii=False), encoding="utf-8")
            except OSError:
                pass

    def load_current(self):
        """User settings override defaults; the file is created on first run."""
        try:
            user = json.loads(CURRENT_SETTINGS_FILE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            user = {}
        self.current = {**self.defaults, **user}
        if "drive.google.com" in str(user.get("online_folder_url", "")):      # 2.2.6: the old Google Drive link -> the GitHub default
            self.current["online_folder_url"] = self.defaults.get("online_folder_url", "")
        if user and int(user.get("config_version", 1)) < CONFIG_VERSION:
            self.current.pop("max_concurrent", None)               # 2.0.1: one yt-dlp process per video, default 3
            self.current["max_concurrent"] = self.defaults.get("max_concurrent", 3)
            self.current["config_version"] = CONFIG_VERSION
            self.save()
        if not CURRENT_SETTINGS_FILE.exists():
            self.save()

    # --- access ------------------------------------------------------
    def get(self, key, fallback=None):
        return self.current.get(key, self.defaults.get(key, fallback))

    def subscribe(self, fn):
        """fn(key) is called when a setting is changed by any part of the program (a 'don't show again' tick in a
        window, the Settings page ...), so that every screen shows the same value as the configuration file."""
        self._listeners.append(fn)

    def _notify(self, key):
        for fn in list(self._listeners):
            try:
                fn(key)
            except Exception:                  # noqa: BLE001  (a screen that cannot update must not break the others)
                pass

    def set(self, key, value):
        changed = self.current.get(key) != value
        self.current[key] = value
        if changed:
            self._notify(key)

    def save(self):
        CURRENT_SETTINGS_FILE.write_text(
            json.dumps(self.current, indent=2, ensure_ascii=False), encoding="utf-8")

    KEEP_ON_RESET = ("demo_seed_version", "window_width", "window_height", "config_version")   # not user preferences

    def reset_to_defaults(self):
        """'Restore Defaults': current_settings.json becomes a copy of default_settings.json."""
        kept = {k: self.current[k] for k in self.KEEP_ON_RESET if k in self.current}
        self.current = {**self.defaults, **kept}
        self.save()
        self._notify("*")

    def download_dir(self) -> Path:
        return Path(os.path.expanduser(str(self.get("download_dir"))))
