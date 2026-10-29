# =============================================================================
# TubeArchive Pro  |  Version 2.3.0  |  File: app/toolupdate.py
# Version history of this file:
#   2.3.0 - Created: checks and installs new versions of yt-dlp and ffmpeg (ffprobe, ffplay) into the user tools folder
# =============================================================================
"""Tool updates (no Qt here, so it can be tested).

  check_tools()            -> list of items that have a newer version (or are not installed):
                              {"key": "yt-dlp" | "ffmpeg", "name", "cur", "new", "url", "size", "stamp", "sha_url"}
  update_tools(items, progress, cancelled) -> downloads and installs them into USER_TOOLS_DIR
                              progress(done_bytes, total_bytes) - one running total for everything (no file names are shown)
  ytdlp_version(exe)       -> installed version text or ''

yt-dlp : GitHub releases of yt-dlp/yt-dlp (yt-dlp.exe + SHA2-256SUMS, the file is checked)
ffmpeg : GitHub releases of BtbN/FFmpeg-Builds (win64 gpl zip; ffmpeg.exe, ffprobe.exe, ffplay.exe are taken from its bin folder).
         The builds have no version number: the date of the file is stored (tools.json) and compared. A ffmpeg that was put
         into tools/ by hand is accepted as it is (nobody is forced to download 150 MB).
The new files are written to the user tools folder (%APPDATA%\\TubeArchivePro\\tools) which is searched BEFORE the tools of the
program folder - the program folder may be read only.
"""
import hashlib
import json
import os
import subprocess
import tempfile
import urllib.request
import zipfile
from pathlib import Path

from .paths import USER_TOOLS_DIR

UA = "TubeArchivePro-Updater"
YTDLP_API = "https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest"
FFMPEG_API = "https://api.github.com/repos/BtbN/FFmpeg-Builds/releases/latest"
FFMPEG_ASSET = "ffmpeg-master-latest-win64-gpl.zip"
FFMPEG_FILES = ("ffmpeg.exe", "ffprobe.exe", "ffplay.exe")
STATE_FILE = "tools.json"
NO_WINDOW = 0x08000000 if os.name == "nt" else 0


class UpdateError(Exception):
    pass


class Cancelled(Exception):
    pass


def _get_json(url: str, timeout: int = 15):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read(2_000_000).decode("utf-8", "replace"))


def _state(folder: Path) -> dict:
    try:
        d = json.loads((Path(folder) / STATE_FILE).read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _save_state(folder: Path, d: dict):
    Path(folder).mkdir(parents=True, exist_ok=True)
    (Path(folder) / STATE_FILE).write_text(json.dumps(d, indent=2), encoding="utf-8")


def tool_version(exe, args=("--version",)) -> str:
    """First line of `exe --version` ('' when it does not run)."""
    if not exe:
        return ""
    cmd = list(exe) if isinstance(exe, (list, tuple)) else [str(exe)]
    try:
        r = subprocess.run(cmd + list(args), capture_output=True, timeout=20, creationflags=NO_WINDOW)
        return (r.stdout.decode("utf-8", "replace").strip().splitlines() or [""])[0].strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def ytdlp_version(exe) -> str:
    return tool_version(exe)


def ffmpeg_version(exe) -> str:
    line = tool_version(exe, ("-version",))                 # 'ffmpeg version N-1234-gabc Copyright ...'
    parts = line.split()
    return parts[2] if len(parts) > 2 and parts[0] == "ffmpeg" else line


def _asset(release: dict, name: str) -> dict | None:
    return next((a for a in release.get("assets", []) if a.get("name") == name), None)


def check_ytdlp(exe, api: str = None) -> dict | None:
    """The yt-dlp item when a newer release exists (or yt-dlp is missing), else None."""
    rel = _get_json(api or YTDLP_API)
    new = str(rel.get("tag_name", "")).strip()
    a = _asset(rel, "yt-dlp.exe")
    if not new or not a:
        raise UpdateError("no release information")
    cur = ytdlp_version(exe)
    if cur and cur == new:
        return None
    sums = _asset(rel, "SHA2-256SUMS")
    return {"key": "yt-dlp", "name": "yt-dlp", "cur": cur, "new": new, "url": a["browser_download_url"],
            "size": int(a.get("size", 0)), "stamp": new, "sha_url": sums["browser_download_url"] if sums else ""}


def check_ffmpeg(exe, folder: Path = None, api: str = None) -> dict | None:
    rel = _get_json(api or FFMPEG_API)
    a = _asset(rel, FFMPEG_ASSET)
    if not a:
        raise UpdateError("no release information")
    stamp = str(a.get("updated_at") or rel.get("published_at") or "")
    stored = _state(folder or USER_TOOLS_DIR).get("ffmpeg", "")
    cur = ffmpeg_version(exe)
    if exe and (not stored or stored >= stamp):            # installed by hand (no record) or already the newest
        return None
    return {"key": "ffmpeg", "name": "ffmpeg", "cur": cur, "new": stamp[:10] or "latest", "url": a["browser_download_url"],
            "size": int(a.get("size", 0)), "stamp": stamp, "sha_url": ""}


def check_tools(ytdlp_exe, ffmpeg_exe, folder: Path = None, ytdlp_api: str = None, ffmpeg_api: str = None) -> list:
    """Items that need an update. Raises UpdateError when yt-dlp's release cannot be read (ffmpeg problems are skipped)."""
    items = []
    try:
        it = check_ytdlp(ytdlp_exe, ytdlp_api)
    except UpdateError:
        raise
    except Exception as exc:                                # noqa: BLE001
        raise UpdateError(str(exc)[:160])
    if it:
        items.append(it)
    try:
        it = check_ffmpeg(ffmpeg_exe, folder, ffmpeg_api)
        if it:
            items.append(it)
    except Exception:                                       # noqa: BLE001  (ffmpeg is optional information)
        pass
    return items


def _download(url: str, dest: Path, add, cancelled, timeout: int = 30) -> str:
    """Streams url to dest; add(n) reports the bytes; returns the sha256 of the file."""
    h = hashlib.sha256()
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r, open(dest, "wb") as f:
        while True:
            if cancelled():
                raise Cancelled()
            chunk = r.read(256 * 1024)
            if not chunk:
                break
            f.write(chunk)
            h.update(chunk)
            add(len(chunk))
    return h.hexdigest()


def _replace(src: Path, dst: Path):
    """os.replace; a running exe is renamed away first (Windows allows renaming a file that is in use)."""
    try:
        os.replace(src, dst)
        return
    except OSError:
        pass
    old = dst.with_suffix(dst.suffix + ".old")
    try:
        if old.exists():
            old.unlink()
        if dst.exists():
            os.replace(dst, old)
        os.replace(src, dst)
    except OSError as exc:
        raise UpdateError(str(exc)[:160])


def update_tools(items: list, progress=lambda done, total: None, cancelled=lambda: False, folder: Path = None):
    """Downloads and installs the items. Raises Cancelled / UpdateError. The old file stays when anything fails."""
    folder = Path(folder or USER_TOOLS_DIR)
    folder.mkdir(parents=True, exist_ok=True)
    total = sum(max(0, int(i.get("size", 0))) for i in items) or 0
    done = [0]

    def add(n):
        done[0] += n
        progress(done[0], max(total, done[0]))
    state = _state(folder)
    progress(0, total)
    with tempfile.TemporaryDirectory(dir=str(folder)) as tmpd:
        tmp = Path(tmpd)
        for it in items:
            try:
                if it["key"] == "yt-dlp":
                    part = tmp / "yt-dlp.exe"
                    digest = _download(it["url"], part, add, cancelled)
                    want = _expected_sha(it.get("sha_url", ""), "yt-dlp.exe")
                    if want and want != digest:
                        raise UpdateError("checksum")
                    _replace(part, folder / "yt-dlp.exe")
                    state["yt-dlp"] = it["stamp"]
                else:
                    part = tmp / "ffmpeg.zip"
                    _download(it["url"], part, add, cancelled)
                    _install_ffmpeg_zip(part, tmp, folder)
                    state["ffmpeg"] = it["stamp"]
            except (Cancelled, UpdateError):
                raise
            except Exception as exc:                        # noqa: BLE001
                raise UpdateError(str(exc)[:160])
    _save_state(folder, state)
    progress(max(total, done[0]), max(total, done[0]))


def _expected_sha(url: str, name: str) -> str:
    if not url:
        return ""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=20) as r:
            text = r.read(200_000).decode("utf-8", "replace")
    except Exception:                                       # noqa: BLE001  (no checksum list: the download is accepted)
        return ""
    for line in text.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[-1].lstrip("*") == name:
            return parts[0].lower()
    return ""


def _install_ffmpeg_zip(zip_path: Path, tmp: Path, folder: Path):
    found = {}
    try:
        with zipfile.ZipFile(zip_path) as z:
            for info in z.infolist():
                base = os.path.basename(info.filename)
                if base in FFMPEG_FILES and "/bin/" in "/" + info.filename.replace("\\", "/"):
                    out = tmp / ("new_" + base)
                    with z.open(info) as src, open(out, "wb") as dst:
                        while True:
                            chunk = src.read(1024 * 1024)
                            if not chunk:
                                break
                            dst.write(chunk)
                    found[base] = out
    except zipfile.BadZipFile:
        raise UpdateError("bad zip file")
    if "ffmpeg.exe" not in found:
        raise UpdateError("ffmpeg.exe is not in the file")
    for base, out in found.items():
        _replace(out, folder / base)
