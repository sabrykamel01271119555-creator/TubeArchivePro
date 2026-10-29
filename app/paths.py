# =============================================================================
# TubeArchive Pro  |  Version 2.3.0  |  File: app/paths.py
# Version history of this file:
#   2.3.2 - failed-video window (Retry now / Later / Cancel), settings fit the frame, Sync all window per list, version 2.3.2
#   2.2.9 - APP_VERSION 2.2.9
#   2.2.8 - APP_VERSION 2.2.8
#   2.2.7 - APP_VERSION 2.2.7
#   2.2.6 - APP_VERSION 2.2.6 (the installer work of 2.3.0 stays in the code; the setup wizard itself is postponed)
#   2.3.0 - APP_VERSION 2.3.0. Program files (APP_DIR, read only) and user data (USER_DIR = %APPDATA%\TubeArchivePro when installed)
#           are separate; portable.txt; migrate_old_data()
#   2.2.5 - APP_VERSION 2.2.5
#   2.2.4 - APP_VERSION 2.2.4
#   2.2.3 - APP_VERSION 2.2.3
#   2.2.2 - APP_VERSION 2.2.2
#   2.2.1 - APP_VERSION 2.2.1
#   2.2.0 - APP_VERSION 2.2.0
#   2.1.1 - APP_VERSION 2.1.1
#   2.1.0 - APP_VERSION 2.1.0 (major)
#   2.0.12 - APP_VERSION 2.0.12
#   2.0.11 - APP_VERSION 2.0.11
#   2.0.10 - APP_VERSION 2.0.10
#   2.0.9 - APP_VERSION 2.0.9
#   2.0.8 - APP_VERSION 2.0.8
#   2.0.7 - APP_VERSION 2.0.7
#   2.0.6 - APP_VERSION 2.0.6
#   2.0.5 - APP_VERSION 2.0.5
#   2.0.4 - APP_VERSION 2.0.4
#   2.0.3 - APP_VERSION 2.0.3
#   2.0.2 - APP_VERSION 2.0.2
#   2.0.1 - APP_VERSION 2.0.1; INFO_DIR (help / about us / contact us / donate files)
#   1.0.14 - APP_VERSION 1.0.14
#   1.0.13 - APP_VERSION 1.0.13
#   1.0.12 - APP_VERSION 1.0.12
#   1.0.11 - APP_VERSION 1.0.11; new SYNC_FILE
#   1.0.10 - APP_VERSION 1.0.10
#   1.0.9 - APP_VERSION 1.0.9; new THUMBS_DIR and FAVORITES_FILE
#   1.0.8 - APP_VERSION set to 1.0.8
#   1.0.7 - APP_VERSION set to 1.0.7
#   1.0.6 - APP_VERSION set to 1.0.6 (shown in the title bar and header)
#   1.0.0 - 1.0.5 - first version and earlier fixes (see CHANGELOG.md)
# =============================================================================
"""Central place for every path the application uses.

Two kinds of folders (2.3.0, needed for the installed program):
  * APP_DIR   - the program itself, read only when installed in "C:\\Program Files": tools/, assets/info, assets/owner,
                data/languages, data/config/default_settings.json, data/downloads_baseline.txt   (shipped by the setup)
  * USER_DIR  - everything the program writes: settings, history, favorites, sync, feedback, cache, logs, downloaded ads.
                Installed program: %APPDATA%\\TubeArchivePro .   Run from the source folder (python main.py): the project folder
                (as before).   Portable: a file `portable.txt` next to TubeArchivePro.exe = USER_DIR is the program folder.
"""
import os
import shutil
import sys
from pathlib import Path

APP_NAME = "TubeArchive Pro"
APP_VERSION = "2.3.2"
USER_FOLDER_NAME = "TubeArchivePro"          # folder inside %APPDATA%


def resolve_user_dir(frozen: bool, app_dir: Path, appdata: str | None = None, portable: bool = False) -> Path:
    """Where the program writes its data (pure function, tested)."""
    if not frozen or portable:
        return Path(app_dir)
    base = appdata or os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    return Path(base) / USER_FOLDER_NAME


def _app_dir() -> Path:
    # When packaged (PyInstaller, one-folder build) the files live next to the .exe
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


FROZEN = bool(getattr(sys, "frozen", False))
APP_DIR = _app_dir()
BASE_DIR = APP_DIR                                   # (older name)
USER_DIR = resolve_user_dir(FROZEN, APP_DIR, portable=(APP_DIR / "portable.txt").exists())

# ---- shipped with the setup (read only) --------------------------------------------------
SHIPPED_DATA_DIR = APP_DIR / "data"
LANG_DIR = SHIPPED_DATA_DIR / "languages"
SHIPPED_CONFIG_DIR = SHIPPED_DATA_DIR / "config"
DEFAULT_SETTINGS_FILE = SHIPPED_CONFIG_DIR / "default_settings.json"
BASELINE_FILE = SHIPPED_DATA_DIR / "downloads_baseline.txt"
ASSETS_DIR = APP_DIR / "assets"
INFO_DIR = ASSETS_DIR / "info"        # help / about us / contact us / donate texts (shipped with the setup)
OWNER_DIR = ASSETS_DIR / "owner"      # banner.gif / banner.png of the program owner
TOOLS_DIR = APP_DIR / "tools"         # yt-dlp.exe, ffmpeg.exe, ffprobe.exe (shipped with the setup)
USER_TOOLS_DIR = USER_DIR / "tools"   # 2.3.0: tools downloaded by the update window; searched BEFORE TOOLS_DIR

# ---- written by the program (user data) ----------------------------------------------------
DATA_DIR = USER_DIR / "data"
CONFIG_DIR = DATA_DIR / "config"
CURRENT_SETTINGS_FILE = CONFIG_DIR / "current_settings.json"
HISTORY_DIR = DATA_DIR / "history"
HISTORY_FILE = HISTORY_DIR / "history.json"
FEEDBACK_FILE = DATA_DIR / "feedback" / "feedback.json"
THUMBS_DIR = HISTORY_DIR / "thumbs"                 # one small picture per history record
FAVORITES_FILE = DATA_DIR / "favorites" / "favorites.json"
FAILED_FILE = DATA_DIR / "failed" / "failed.json"        # 2.3.2: videos that could not be downloaded (Later)
SYNC_FILE = DATA_DIR / "sync" / "sync.json"            # synchronized playlists (schedule)
CACHE_DIR = DATA_DIR / "cache"
ADS_DIR = USER_DIR / "assets" / "ads"                 # partner animated GIFs go here


def migrate_old_data(src: Path = None, dst: Path = None) -> list:
    """Setup of an older portable version: its settings / history / favorites / sync / feedback / ads that sit next to the
    program are copied once to the user folder (only what is not there yet). Returns the copied names. Never raises."""
    src, dst = Path(src or APP_DIR), Path(dst or USER_DIR)
    copied = []
    if src.resolve() == dst.resolve():
        return copied
    items = [("data/config/current_settings.json", False), ("data/history", True), ("data/favorites", True),
             ("data/sync", True), ("data/feedback", True), ("assets/ads", True)]
    for rel, is_dir in items:
        a, b = src / rel, dst / rel
        try:
            if a.exists() and not b.exists():
                b.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(a, b) if is_dir else shutil.copy2(a, b)
                copied.append(rel)
        except OSError:
            pass
    return copied
