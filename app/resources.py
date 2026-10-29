# =============================================================================
# TubeArchive Pro  |  Version 2.3.0  |  File: app/resources.py
# Version history of this file:
#   2.3.0 - the user tools folder (tools downloaded by the update window) is searched before the program's tools folder
#   2.3.0 - only the user data folders are created (the program folder may be read only)
#   2.0.5 - tools/ is searched in sub-folders too (an extracted ffmpeg-...-full_build\bin folder works as it is)
#   2.0.1 - ads = only the allowed ads of this month (ads.local_ads); channel_logo (assets/owner/channel_logo.*)
#   1.0.8 - Finds yt-dlp (tools/ or PATH) and ffmpeg (tools/ or PATH): new ffmpeg_dir / ffmpeg_ok
#   1.0.6 - No functional change (version header added)
#   1.0.0 - 1.0.5 - first version and earlier fixes (see CHANGELOG.md)
# =============================================================================
"""Resource files: partner ad GIFs, owner banner, and the yt-dlp / ffmpeg executables."""
import shutil
from pathlib import Path

from .ads import local_ads
from .paths import (ADS_DIR, CONFIG_DIR, HISTORY_DIR, LANG_DIR, OWNER_DIR,
                    TOOLS_DIR, USER_TOOLS_DIR)


def find_tool(name: str, folder=None):
    """Path of `name`(.exe) inside tools/ - directly, or in any sub-folder (e.g. tools/ffmpeg-...-full_build/bin)."""
    folder = Path(folder or TOOLS_DIR)
    for fname in (name + ".exe", name):
        if (folder / fname).is_file():
            return str(folder / fname)
    if folder.is_dir():
        for fname in (name + ".exe", name):
            hits = sorted(folder.rglob(fname), key=lambda h: len(h.parts))
            hits = [h for h in hits if h.is_file()]
            if hits:
                return str(hits[0])
    return None


class ResourceManager:
    def __init__(self):
        self.ads: list[str] = []          # animated GIFs of partners
        self.owner_banner: str | None = None
        self.channel_logo: str | None = None   # round logo of the owner's YouTube channel (optional picture)
        self.ytdlp: str | None = None     # path to yt-dlp.exe if present
        self.ffmpeg_dir: str | None = None  # folder holding ffmpeg.exe (tools/) if present
        self.ffmpeg_ok = False            # ffmpeg found in tools/ or in the PATH

    def load(self):
        for d in (ADS_DIR, CONFIG_DIR, HISTORY_DIR):          # the folders the program writes in (user data folder)
            try:
                d.mkdir(parents=True, exist_ok=True)
            except OSError:
                pass
        self.ads = local_ads(ADS_DIR)                       # only the ads that are allowed this month
        self.owner_banner = None
        for ext in ("gif", "png", "jpg", "jpeg", "webp"):
            p = OWNER_DIR / f"banner.{ext}"
            if p.exists():
                self.owner_banner = str(p)
                break
        self.channel_logo = None
        for ext in ("png", "jpg", "jpeg", "webp", "gif"):
            p = OWNER_DIR / f"channel_logo.{ext}"
            if p.exists():
                self.channel_logo = str(p)
                break
        self.ytdlp = find_tool("yt-dlp", USER_TOOLS_DIR) or find_tool("yt-dlp") or shutil.which("yt-dlp")   # tools/ (any sub-folder), else installed system-wide
        found = find_tool("ffmpeg", USER_TOOLS_DIR) or find_tool("ffmpeg")
        if found:
            self.ffmpeg_dir, self.ffmpeg_ok = str(Path(found).parent), True
        else:
            self.ffmpeg_dir, self.ffmpeg_ok = None, bool(shutil.which("ffmpeg"))
