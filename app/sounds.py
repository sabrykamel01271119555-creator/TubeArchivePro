# =============================================================================
# TubeArchive Pro  |  Version 2.3.0  |  File: app/sounds.py
# Version history of this file:
#   2.3.0 - sounds are loaded once at start (QSoundEffect, no delay when played); new softer sounds ('glass' theme);
#           winsound is only the fallback
#   2.2.7 - Created: sound effects (click, tab, done, warning). Files: assets/sounds/<name>.wav; on / off in Settings
#           (sounds_enabled). Windows: winsound (asynchronous); elsewhere QSoundEffect when available.
# =============================================================================
"""Short sound effects. `play("click" | "tab" | "done" | "warning")` never raises and never blocks."""
import os
import time

from .paths import APP_DIR

SOUND_DIR = APP_DIR / "assets" / "sounds"
NAMES = ("click", "tab", "done", "warning")
MIN_GAP = 0.04            # seconds: the same sound is not started twice at once

_settings = None
_cache: dict = {}
_last: dict = {}


def attach(settings):
    """The settings manager decides whether sounds are on (`sounds_enabled`, default on)."""
    global _settings
    _settings = settings


def enabled() -> bool:
    try:
        return bool(_settings.get("sounds_enabled", True)) if _settings is not None else True
    except Exception:                                   # noqa: BLE001
        return True


def preload() -> bool:
    """Load every sound once (after the QApplication exists), so that playing it later has no delay."""
    try:
        from PySide6.QtCore import QUrl
        from PySide6.QtMultimedia import QSoundEffect
    except Exception:                                    # noqa: BLE001  (QtMultimedia missing: winsound is used)
        return False
    for n in NAMES:
        p = SOUND_DIR / f"{n}.wav"
        if p.is_file() and n not in _cache:
            fx = QSoundEffect()
            fx.setSource(QUrl.fromLocalFile(str(p)))
            fx.setVolume(0.65)
            _cache[n] = fx
    return bool(_cache)


def play(name: str) -> bool:
    """Start the sound `name`; True when it was started."""
    if name not in NAMES or not enabled():
        return False
    now = time.monotonic()
    if now - _last.get(name, 0) < MIN_GAP:
        return False
    _last[name] = now
    path = SOUND_DIR / f"{name}.wav"
    if not path.is_file():
        return False
    fx = _cache.get(name)
    if fx is not None:
        try:
            fx.play()
            return True
        except Exception:                                # noqa: BLE001
            pass
    try:
        if os.name == "nt":
            import winsound
            winsound.PlaySound(str(path), winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT)
            return True
        from PySide6.QtCore import QUrl                  # other systems: QtMultimedia when it is installed
        from PySide6.QtMultimedia import QSoundEffect
        fx = _cache.get(name)
        if fx is None:
            fx = _cache[name] = QSoundEffect()
            fx.setSource(QUrl.fromLocalFile(str(path)))
        fx.play()
        return True
    except Exception:                                    # noqa: BLE001
        return False
