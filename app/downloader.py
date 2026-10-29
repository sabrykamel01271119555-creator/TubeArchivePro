# =============================================================================
# TubeArchive Pro  |  Version 2.3.1  |  File: app/downloader.py
# Version history of this file:
#   2.3.1 - 2K / 4K / 8K (4320) in the quality list, h264_args(): MP4 = H.264 + AAC (setting mp4_h264)
#   2.0.9 - log_fetch(): data/fetch.log records every Check
#   2.0.2 - The expected size is refined while downloading (real size of each stream, format_sizes())
#   2.0.1 - One video per process (playlists are split by the queue): index_text() 01 / 001 numbering,
#           safe_name(), out_template, per-process rate limit, description saved from yt-dlp, stable size ratio,
#           playlist entries carry their own url; engine_options() no longer uses -N (concurrency = queue)
#   1.0.14 - engine_options(): Settings -> yt-dlp options (-N, --limit-rate, metadata, retries, audio); extra_args
#   1.0.12 - Playlist count ignores private / deleted videos
#   1.0.11 - Playlists: playlist_id(), entries list in fetch_info, optional playlist folder, selected
#            playlist items (sync), force overwrite, "id|path" lines so each downloaded video is known
#   1.0.8 - Created: yt-dlp command builder, info fetch, size estimate, progress parser,
#           error translation, DownloadJob (start / pause / resume / cancel + cleanup)
# =============================================================================
"""Download engine logic.  NO Qt in this file, so it can be tested on its own.

The Qt side (signals for the interface) is app/download_manager.py.

How a download works
  * the command line utility (yt-dlp.exe) is started in the background (no console window);
  * everything it prints is read line by line; progress lines are parsed, error lines are
    translated to an error CODE (the interface turns the code into a message in the user's language);
  * PAUSE  = the process (and ffmpeg children) is suspended, NOT terminated;
  * CANCEL = the process tree is killed and the temporary folder with all partial files is deleted.
    yt-dlp is told to keep partial files in that temporary folder (-P temp:...), and moves the
    finished file to the save folder only when it is complete.
"""
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path
from urllib.parse import parse_qs, urlparse

try:                      # needed to suspend/resume the process tree on Windows
    import psutil
except ImportError:       # pragma: no cover
    psutil = None

IS_WIN = sys.platform == "win32"
NO_WINDOW = 0x08000000 if IS_WIN else 0          # CREATE_NO_WINDOW: never flash a console

VIDEO_FORMATS = ["MP4", "MKV", "WEBM", "AVI"]
AUDIO_FORMATS = ["MP3", "WAV"]
VIDEO_HEIGHTS = [144, 240, 360, 480, 720, 1080, 1440, 2160, 4320]     # 1440 = 2K, 2160 = 4K, 4320 = 8K
MP3_BITRATES = [320, 256, 192, 128, 96, 64]                      # kbps
WAV_RATES = [48000, 44100, 22050]                                # Hz

PROGRESS_PREFIX = "TAPROG"
PROGRESS_TEMPLATE = ("download:" + PROGRESS_PREFIX +
                     "|%(progress.status)s|%(progress.downloaded_bytes)s|%(progress.total_bytes)s"
                     "|%(progress.total_bytes_estimate)s|%(progress.speed)s|%(progress.eta)s"
                     "|%(info.playlist_index)s|%(info.n_entries)s")


class EngineError(Exception):
    def __init__(self, code: str, detail: str = ""):
        super().__init__(f"{code}: {detail}")
        self.code, self.detail = code, detail


# ----------------------------------------------------------------------
# small helpers
# ----------------------------------------------------------------------
def _exe_list(exe) -> list:
    return list(exe) if isinstance(exe, (list, tuple)) else [str(exe)]


def is_audio(fmt: str) -> bool:
    return fmt.upper() in AUDIO_FORMATS


def looks_like_url(text: str) -> bool:
    return bool(re.match(r"^https?://\S+\.\S+", text.strip(), re.I))


def is_playlist_url(url: str) -> bool:
    """Only a real playlist page (/playlist?list=...) is treated as a playlist.
    A video link that also carries &list=... downloads just that one video."""
    try:
        u = urlparse(url.strip())
    except ValueError:
        return False
    return u.path.rstrip("/").lower() == "/playlist" and "list=" in u.query


def playlist_id(url: str) -> str:
    """The list=... value of a playlist link ('' when there is none)."""
    try:
        return (parse_qs(urlparse(url.strip()).query).get("list") or [""])[0]
    except ValueError:
        return ""


def pad_width(count: int) -> int:
    """Digits of the playlist index: 2 for fewer than 10 videos (01), 3 for 10-99 (001), 4 for 100-999 ..."""
    return len(str(max(1, int(count or 1)))) + 1


def index_text(index: int, count: int) -> str:
    """'01', '002', '0015' ... the position of a video in its playlist."""
    return str(int(index)).zfill(pad_width(count))


_BAD_NAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def safe_name(text: str, fallback: str = "Playlist") -> str:
    """A folder name that Windows accepts."""
    name = _BAD_NAME.sub("_", str(text or "")).strip().rstrip(". ")
    return (name or fallback)[:120]


def tpl_escape(text: str) -> str:
    """Literal text inside a yt-dlp output template (a % must be doubled)."""
    return str(text).replace("%", "%%")


def video_url(entry: dict, default: str = "") -> str:
    """Address of a playlist entry: its own url, else the YouTube watch page of its id."""
    if entry.get("url"):
        return entry["url"]
    if entry.get("id"):
        return f"https://www.youtube.com/watch?v={entry['id']}"
    return default


def fmt_size(n) -> str:
    if not n:
        return "-"
    n = float(n)
    if n >= 1024 ** 3:
        return f"{n / 1024 ** 3:.2f} GB"
    if n >= 1024 ** 2:
        return f"{n / 1024 ** 2:.0f} MB"
    return f"{n / 1024:.0f} KB"


def fmt_time(seconds) -> str:
    s = int(seconds or 0)
    h, r = divmod(s, 3600)
    m, sec = divmod(r, 60)
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m:02d}:{sec:02d}"


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


# ----------------------------------------------------------------------
# formats / quality
# ----------------------------------------------------------------------
def max_height(info) -> int:
    if not info:
        return 0
    return int(info.get("max_height") or 0)


def quality_options(fmt: str, max_h: int = 0) -> list:
    """Values for the quality drop-down. Video: 0 = best, then heights (ascending).
    MP3: kbps.  WAV: sample rate in Hz."""
    f = fmt.upper()
    if f == "MP3":
        return list(MP3_BITRATES)
    if f == "WAV":
        return list(WAV_RATES)
    hs = [h for h in VIDEO_HEIGHTS if not max_h or h <= max_h] or [VIDEO_HEIGHTS[0]]
    return [0] + hs


def parse_quality(value) -> int:
    """A saved quality as a number: 720, "720", "1080p", "4K", "Best" (or anything unknown) -> 0 = best.
    Old settings files hold text such as "1080p" in default_quality."""
    if isinstance(value, bool):
        return 0
    if isinstance(value, (int, float)):
        return max(0, int(value))
    text = str(value or "").strip().lower().replace("kbps", "").replace("khz", "").strip()
    if text in ("2k", "1440p"):
        return 1440
    if text in ("4k", "2160p"):
        return 2160
    if text in ("8k", "4320p"):
        return 4320
    digits = text[:-1] if text.endswith("p") else text
    return int(digits) if digits.isdigit() else 0


def height_label(h: int) -> str:
    """144p ... 1080p, then 2K (1440p), 4K (2160p), 8K (4320p)."""
    return "8K" if h >= 4320 else "4K" if h >= 2160 else "2K" if h == 1440 else f"{h}p"


def quality_label(fmt: str, q: int):
    """Language-neutral label. Returns None for 'Best' (the interface translates that one)."""
    f = fmt.upper()
    if f == "MP3":
        return f"{q} kbps"
    if f == "WAV":
        return f"{q / 1000:g} kHz"
    return height_label(q) if q else None


def effective_height(info, q: int) -> int:
    mh = max_height(info)
    if q == 0:
        return mh
    return min(q, mh) if mh else q


def build_format_args(fmt: str, quality: int) -> list:
    f = fmt.upper()
    if f == "MP3":
        return ["-f", "bestaudio/best", "-x", "--audio-format", "mp3", "--audio-quality", f"{quality}K"]
    if f == "WAV":
        return ["-f", "bestaudio/best", "-x", "--audio-format", "wav",
                "--postprocessor-args", f"ExtractAudio:-ar {quality}"]
    h = f"[height<={quality}]" if quality else ""
    if f == "MP4":
        sel = f"bv*{h}[ext=mp4]+ba[ext=m4a]/bv*{h}+ba/b{h}/b"
        return ["-f", sel, "--merge-output-format", "mp4"]
    if f == "WEBM":
        sel = f"bv*{h}[ext=webm]+ba[ext=webm]/bv*{h}+ba/b{h}/b"
        return ["-f", sel, "--merge-output-format", "webm"]
    sel = f"bv*{h}+ba/b{h}/b"
    if f == "AVI":                       # yt-dlp cannot merge into avi: download as mkv then re-encode
        return ["-f", sel, "--merge-output-format", "mkv", "--recode-video", "avi"]
    return ["-f", sel, "--merge-output-format", "mkv"]


def build_download_cmd(exe, url, out_dir, tmp_dir, fmt, quality, is_playlist, ffmpeg_dir, list_file,
                       playlist_folder=True, playlist_items=None, force=False, extra_args=None,
                       out_template=None, desc_file=None) -> list:
    cmd = _exe_list(exe) + [
        "--newline", "--no-colors", "--windows-filenames", "--no-mtime", "--trim-filenames", "150",
        "--progress", "--progress-template", PROGRESS_TEMPLATE,
        "-P", f"home:{out_dir}", "-P", f"temp:{tmp_dir}",
        "--print-to-file", "after_move:%(id)s|%(filepath)s", str(list_file)]
    if ffmpeg_dir:
        cmd += ["--ffmpeg-location", str(ffmpeg_dir)]
    if desc_file:                                            # the description of the video (one JSON line)
        cmd += ["--print-to-file", "after_move:%(description)j", str(desc_file)]
    cmd += build_format_args(fmt, quality)
    if force:
        cmd.append("--force-overwrites")
    if out_template:                                         # one video of a playlist (made by the queue)
        cmd += ["--no-playlist", "-o", out_template]
    elif is_playlist:
        if playlist_items:                                   # sync: only these positions of the playlist
            cmd += ["--playlist-items", ",".join(str(i) for i in playlist_items)]
        out = ("%(playlist_title)s/%(playlist_index)s - %(title)s.%(ext)s" if playlist_folder
               else "%(title)s.%(ext)s")
        cmd += ["--yes-playlist", "-o", out]
    else:
        cmd += ["--no-playlist", "-o", "%(title)s.%(ext)s"]
    if extra_args:
        cmd += list(extra_args)
    cmd.append(url)
    return cmd


def _vheight(f) -> int:
    return int(f.get("height") or 0)


def h264_args(info, quality: int) -> list:
    """MP4 that opens in Premiere / After Effects / DaVinci Resolve and on (almost) every TV and player: H.264 video + AAC sound.
    * the video offers H.264 (avc1) at the best height wanted -> that stream is downloaded as it is (no conversion);
    * the best streams are VP9 / AV1 (YouTube gives 1440p, 4K and 8K only in those) -> they are downloaded and converted to
      H.264 (yuv420p) + AAC with ffmpeg: slower, and the file is bigger;
    * nothing is known about the video (playlist entries) -> H.264 is preferred, the old choice is the fallback.
    Returns the yt-dlp arguments that replace the format choice ([] = keep it)."""
    h = f"[height<={quality}]" if quality else ""
    vids = [f for f in ((info or {}).get("formats") or [])
            if f.get("vcodec") not in (None, "none") and f.get("ext") != "mhtml" and _vheight(f)]
    if not vids:
        sel = (f"bv*{h}[vcodec^=avc1]+ba[ext=m4a]/bv*{h}[vcodec^=avc1]+ba/"
               f"bv*{h}[ext=mp4]+ba[ext=m4a]/bv*{h}+ba/b{h}/b")
        return ["-f", sel, "--merge-output-format", "mp4"]
    cand = [f for f in vids if not quality or _vheight(f) <= quality]
    if not cand:
        return []
    best = max(_vheight(f) for f in cand)
    if any(str(f.get("vcodec", "")).startswith(("avc1", "h264")) and _vheight(f) == best for f in cand):
        sel = (f"bv*[height<={best}][vcodec^=avc1]+ba[ext=m4a]/bv*[height<={best}][vcodec^=avc1]+ba/"
               f"b[height<={best}][vcodec^=avc1]/b[height<={best}]")
        return ["-f", sel, "--merge-output-format", "mp4"]
    return ["-f", f"bv*[height<={best}]+ba/b[height<={best}]", "--merge-output-format", "mkv", "--recode-video", "mp4",
            "--postprocessor-args",
            "VideoConvertor:-c:v libx264 -preset medium -crf 18 -pix_fmt yuv420p -c:a aac -b:a 192k -movflags +faststart"]


def engine_options(get, fmt: str, rate_kb: float = 0, info=None, quality: int = 0) -> list:
    """yt-dlp options that come from Settings. `get(key, default)` reads a setting.
      rate_kb         -> --limit-rate (KB/s of THIS process; the queue shares the bandwidth limit, 0 = none)
      embed_metadata  -> --embed-metadata (+ cover picture for mp4 / mkv / mp3)
      ytdlp_fallback  -> more retries for connection / fragment / extractor errors
      audio_convert   -> off = best quality instead of the chosen bitrate (mp3)
      mp4_h264        -> MP4 = H.264 + AAC (see h264_args)
      audio_extract   -> off = the downloaded video file is kept next to the extracted audio
    The number of videos downloaded at the same time (max_concurrent) is handled by app/dlqueue.py."""
    f = fmt.upper()
    args = []
    if rate_kb and rate_kb > 0:
        args += ["--limit-rate", f"{max(1, int(rate_kb))}K"]
    if get("embed_metadata", True):
        args.append("--embed-metadata")
        if f in ("MP4", "MKV", "MP3"):
            args += ["--embed-thumbnail", "--convert-thumbnails", "jpg"]
    if get("ytdlp_fallback", True):
        args += ["--retries", "10", "--fragment-retries", "10", "--extractor-retries", "3"]
    if f == "MP4" and get("mp4_h264", True):                # 2.3.1: H.264 + AAC (editors, TVs, players)
        args += h264_args(info, quality)
    if f == "MP3" and not get("audio_convert", True):
        args += ["--audio-quality", "0"]
    if f in ("MP3", "WAV") and not get("audio_extract", True):
        args.append("-k")
    return args


# ----------------------------------------------------------------------
# estimated size
# ----------------------------------------------------------------------
def estimate_size(info, fmt: str, quality: int):
    """Estimated size in bytes for the chosen format/quality (None if unknown)."""
    if not info or info.get("is_playlist"):
        return None
    dur = info.get("duration")
    f = fmt.upper()
    if f == "MP3":
        return int(dur * quality * 1000 / 8) if dur else None
    if f == "WAV":
        return int(dur * quality * 4) if dur else None            # 16-bit stereo

    def size(fm):
        s = fm.get("filesize") or fm.get("filesize_approx")
        if s:
            return int(s)
        tbr = fm.get("tbr")
        if tbr and dur:
            return int(tbr * 1000 / 8 * dur)
        return None

    def has(c):
        return c not in (None, "none")

    formats = [x for x in (info.get("formats") or []) if x.get("ext") != "mhtml"]
    vids = [x for x in formats if has(x.get("vcodec")) and not has(x.get("acodec"))]
    auds = [x for x in formats if has(x.get("acodec")) and not has(x.get("vcodec"))]
    both = [x for x in formats if has(x.get("vcodec")) and has(x.get("acodec"))]
    limit = quality or 10 ** 6
    key = lambda x: ((x.get("height") or 0), (x.get("tbr") or 0))      # noqa: E731
    cand = [x for x in vids if (x.get("height") or 0) <= limit]
    total = None
    if cand:
        total = size(max(cand, key=key))
        if total is not None and auds:
            a = size(max(auds, key=lambda x: x.get("abr") or x.get("tbr") or 0))
            total += a or 0
    else:
        comb = [x for x in both if (x.get("height") or 0) <= limit]
        if comb:
            total = size(max(comb, key=key))
    if total and f == "AVI":
        total = int(total * 1.3)                                     # re-encoding usually grows the file
    return total


# rough average speed of a finished video file (Mbit/s, picture + sound) per resolution: used to estimate a playlist
_MBIT_BY_HEIGHT = {144: 0.3, 240: 0.6, 360: 1.0, 480: 1.6, 720: 3.0, 1080: 5.5, 1440: 11.0, 2160: 22.0, 4320: 70.0}
SPACE_FACTOR = 2.0            # yt-dlp needs about twice the size: the parts + the merged / converted file


def available_heights(info) -> list:
    """The resolutions that the video really offers (ascending), e.g. [144, 360, 720, 1080]."""
    hs = {int(f.get("height") or 0) for f in ((info or {}).get("formats") or [])
          if f.get("vcodec") not in (None, "none") and f.get("ext") != "mhtml"}
    return sorted(h for h in hs if h > 0)


def _rate_bytes(fmt: str, quality: int) -> float:
    """Estimated bytes per second of the media for a format / quality (used when no real size is known)."""
    f = fmt.upper()
    if f == "MP3":
        return quality * 1000 / 8
    if f == "WAV":
        return quality * 4
    h = quality or 1080
    key = min(_MBIT_BY_HEIGHT, key=lambda x: abs(x - h))
    return _MBIT_BY_HEIGHT[key] * 125_000 * (1.3 if f == "AVI" else 1.0)


def estimate_playlist_size(entries, fmt: str, quality: int):
    """Estimated total bytes of a whole playlist from the durations of its videos (None when no duration is known)."""
    secs = sum(float(e.get("duration") or 0) for e in (entries or []))
    return int(secs * _rate_bytes(fmt, quality)) if secs else None


def size_table(info, formats=None) -> dict:
    """{(format, quality value): estimated bytes} for every container x every quality of one video; kept in memory by
    the New Download page so the lists, the size line and the free-space check do not read the video again."""
    if not info or info.get("is_playlist"):
        return {}
    table = {}
    for fmt in (formats or VIDEO_FORMATS + AUDIO_FORMATS):
        hs = available_heights(info)
        opts = quality_options(fmt, max(hs) if hs else 0)
        if not is_audio(fmt) and hs:
            opts = [0] + hs
        for q in opts:
            table[(fmt.upper(), q)] = estimate_size(info, fmt, q)
    return table


def free_bytes(path):
    """Free bytes of the partition that holds `path` (the folder may not exist yet). None when it cannot be read."""
    p = Path(os.path.expanduser(str(path)))
    while not p.exists() and p != p.parent:
        p = p.parent
    try:
        return shutil.disk_usage(str(p)).free
    except OSError:
        return None


def space_needed(est, factor: float = SPACE_FACTOR, extra: float = 0.0) -> int:
    """Bytes that must be free for a download of `est` bytes: the file twice (parts + merged file) + `extra`."""
    return int((est or 0) * factor + extra)


def drive_name(path) -> str:
    """'C:' for a Windows path, otherwise the mount point of the partition."""
    p = Path(os.path.expanduser(str(path)))
    if p.drive:
        return p.drive
    while not os.path.ismount(str(p)) and p != p.parent:
        p = p.parent
    return str(p)


def format_sizes(info, ids) -> list:
    """Sizes in bytes (None = unknown) of the streams that yt-dlp announced ('Downloading 2 format(s): 137+140')."""
    if not info:
        return []
    dur = info.get("duration")
    by_id = {str(f.get("format_id")): f for f in (info.get("formats") or [])}
    out = []
    for fid in ids:
        f = by_id.get(str(fid)) or {}
        size = f.get("filesize") or f.get("filesize_approx")
        if not size and f.get("tbr") and dur:
            size = f["tbr"] * 1000 / 8 * dur
        out.append(float(size) if size else None)
    return out


# ----------------------------------------------------------------------
# yt-dlp output -> data
# ----------------------------------------------------------------------
def parse_progress_line(line: str):
    line = line.strip()
    if not line.startswith(PROGRESS_PREFIX + "|"):
        return None
    p = line.split("|")
    if len(p) < 9:
        return None
    idx, cnt = _num(p[7]), _num(p[8])
    return {"status": p[1], "downloaded": _num(p[2]), "total": _num(p[3]), "total_est": _num(p[4]),
            "speed": _num(p[5]), "eta": _num(p[6]),
            "index": int(idx) if idx else None, "count": int(cnt) if cnt else None}


_ERROR_RULES = [
    ("private", r"private video|this video is private"),
    ("age", r"confirm your age|age-restricted|age restricted"),
    ("signin", r"not a bot|sign in to confirm|login required|cookies"),
    ("geo", r"not available in your country|geo.?restrict|blocked it in your country|not made this video available"),
    ("unavailable", r"video unavailable|this video is unavailable|has been removed|no longer available|"
                    r"account.*terminated|does not exist|copyright"),
    ("unsupported", r"unsupported url|is not a valid url|no video formats found|unable to extract"),
    ("rate", r"http error 429|too many requests"),
    ("format", r"requested format is not available|no such format"),
    ("ffmpeg", r"ffmpeg|ffprobe|postprocessing"),
    ("disk", r"permission denied|no space left|disk full|read-only file system|errno 13|errno 28|"
             r"unable to create directory|winerror 5\b"),
    ("network", r"getaddrinfo|temporary failure|timed out|timeout|http error 5\d\d|urlerror|"
                r"network is unreachable|connection (reset|refused|aborted)|name or service|"
                r"unable to download|ssl|incompleteread|remote end closed"),
]


def map_error(text: str):
    """Translate a raw yt-dlp error text into (code, short detail)."""
    low = text.lower()
    for code, pattern in _ERROR_RULES:
        if re.search(pattern, low):
            return code, ""
    detail = re.sub(r"^\s*ERROR:\s*", "", text.strip(), flags=re.I)
    detail = re.sub(r"\[[a-z:]+\]\s*[\w-]+:\s*", "", detail)       # drop "[youtube] abc123:" prefix
    return "unknown", detail[:160]


# ----------------------------------------------------------------------
# reading information about a link
# ----------------------------------------------------------------------
def download_bytes(url: str, timeout=15):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except Exception:           # noqa: BLE001  (a missing thumbnail is not an error)
        return None


def _thumb_url(data: dict) -> str:
    vid = None
    if str(data.get("extractor_key", "")).lower().startswith("youtube"):
        if data.get("_type") == "playlist":
            ent = next((e for e in (data.get("entries") or []) if e and e.get("id")), None)
            vid = ent.get("id") if ent else None
        else:
            vid = data.get("id")
    if vid:
        return f"https://i.ytimg.com/vi/{vid}/mqdefault.jpg"          # 16:9 jpg, no black bars
    if data.get("thumbnail"):
        return data["thumbnail"]
    th = data.get("thumbnails") or []
    return th[-1].get("url", "") if th else ""


def log_fetch(text: str):
    """Diagnostics of 'Check': every attempt and its result go to data/fetch.log (2.0.9). Never raises."""
    try:
        from datetime import datetime
        from .paths import DATA_DIR
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(DATA_DIR / "fetch.log", "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {text}\n")
    except Exception:                                   # noqa: BLE001
        pass


def fetch_info(exe, url: str, timeout: int = 90) -> dict:
    playlist = is_playlist_url(url)
    cmd = _exe_list(exe) + ["-J", "--no-warnings", "--no-colors"]
    cmd += ["--flat-playlist", "--yes-playlist"] if playlist else ["--no-playlist"]
    cmd.append(url)
    log_fetch("check: " + " ".join(cmd))
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=timeout, creationflags=NO_WINDOW)
    except FileNotFoundError:
        log_fetch("yt-dlp not found: " + str(exe))
        raise EngineError("no_ytdlp")
    except subprocess.TimeoutExpired:
        log_fetch("timeout after %s s" % timeout)
        raise EngineError("network", "timeout")
    except OSError as exc:
        log_fetch("cannot start yt-dlp: %r" % exc)
        raise EngineError("unknown", str(exc)[:160])
    out = r.stdout.decode("utf-8", "replace").strip()
    err = r.stderr.decode("utf-8", "replace")
    if r.returncode != 0 or not out:
        log_fetch("yt-dlp failed, code %s:\n%s" % (r.returncode, err.strip()[-1500:]))
        lines = [l for l in err.splitlines() if "ERROR" in l] or [err]
        code, detail = map_error(lines[-1])
        raise EngineError(code, detail)
    try:
        data = json.loads(out)
    except ValueError:
        raise EngineError("unsupported")
    is_pl = data.get("_type") == "playlist"
    entries = [e for e in (data.get("entries") or []) if e] if is_pl else []
    heights = [f.get("height") or 0 for f in (data.get("formats") or [])
               if f.get("vcodec") not in (None, "none") and f.get("ext") != "mhtml"]
    thumb_url = _thumb_url(data)
    yt = str(data.get("extractor_key", "")).lower().startswith("youtube")
    plist = []
    for pos, e in enumerate(entries, 1):                     # position = playlist_index used by yt-dlp
        title = e.get("title") or ""
        if not e.get("id") or title in ("[Private video]", "[Deleted video]"):
            continue
        plist.append({"id": str(e["id"]), "index": pos, "title": title or str(e["id"]),
                      "duration": e.get("duration"),
                      "url": e.get("url") or e.get("webpage_url") or video_url(e),
                      "thumb_url": f"https://i.ytimg.com/vi/{e['id']}/mqdefault.jpg" if yt else ""})
    return {
        "is_playlist": is_pl,
        "entries": plist,
        "playlist_id": (data.get("id") or "") if is_pl else "",
        "title": data.get("title") or data.get("id") or url,
        "description": "" if is_pl else (data.get("description") or ""),
        "duration": data.get("duration"),
        "count": len(plist) if is_pl else 1,
        "formats": data.get("formats") or [],
        "max_height": max(heights) if heights else 0,
        "thumb_url": thumb_url,
        "thumb_bytes": download_bytes(thumb_url) if thumb_url else None,
    }


# ----------------------------------------------------------------------
# one download (runs yt-dlp in the background)
# ----------------------------------------------------------------------
class DownloadJob:
    """Callbacks (all optional, called from a background thread except on_cancelled):
        on_progress(dict)            overall progress {percent, speed, eta, downloaded, total, item, items}
        on_log(level, key, params)   level = info / warn / error
        on_state(str)                'processing' when ffmpeg merges / converts
        on_finished(dict)            result {files, path, name, size, count, folder, quality}
        on_failed(code, detail)
        on_cancelled()
    """

    def __init__(self, exe, url, out_dir, fmt, quality, info=None, est_total=None, ffmpeg_dir=None,
                 on_progress=None, on_log=None, on_state=None, on_finished=None, on_failed=None,
                 on_cancelled=None, playlist_folder=True, playlist_items=None, force=False, extra_args=None,
                 out_template=None):
        self.playlist_folder, self.playlist_items, self.force = playlist_folder, playlist_items, force
        self.extra_args = extra_args
        self.out_template = out_template
        self.desc_file = None
        self.description = ""
        self.items: list = []                    # [(video id, file path)] of the finished videos
        self.exe, self.url, self.fmt, self.quality = exe, url, fmt.upper(), int(quality or 0)
        self.out_dir, self.info, self.est_total, self.ffmpeg_dir = Path(out_dir), info, est_total, ffmpeg_dir
        self.is_playlist = is_playlist_url(url)
        self.cb_progress, self.cb_log, self.cb_state = on_progress, on_log, on_state
        self.cb_finished, self.cb_failed, self.cb_cancelled = on_finished, on_failed, on_cancelled
        self.proc = None
        self.thread = None
        self.tmp_dir = None
        self.list_file = None
        self.paused = False
        self.finished = False
        self._cancelled = False
        self._done_bytes = 0.0
        self._cur_bytes = 0.0
        self._index = None
        self._last_error = None
        self._last_dest = None
        self._processing = False
        self._streams = []                       # announced size of each stream (video, audio ...)
        self._stream_done = []                   # real size of the streams that are finished
        self.percent = 0.0

    # --- helpers --------------------------------------------------------
    def _log(self, level, key, **params):
        if self.cb_log:
            self.cb_log(level, key, params)

    def alive(self) -> bool:
        return bool(self.proc) and self.proc.poll() is None

    # --- start ----------------------------------------------------------
    def start(self):
        self.tmp_dir = self.out_dir / f".tubearchive_tmp_{int(time.time() * 1000)}"
        self.tmp_dir.mkdir(parents=True, exist_ok=True)
        self.list_file = self.tmp_dir / "files.txt"
        self.desc_file = self.tmp_dir / "description.txt"
        cmd = build_download_cmd(self.exe, self.url, self.out_dir, self.tmp_dir, self.fmt, self.quality,
                                 self.is_playlist, self.ffmpeg_dir, self.list_file,
                                 self.playlist_folder, self.playlist_items, self.force, self.extra_args,
                                 self.out_template, self.desc_file)
        env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
        try:
            self.proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                         stdin=subprocess.DEVNULL, text=True, encoding="utf-8",
                                         errors="replace", bufsize=1, env=env, creationflags=NO_WINDOW)
        except (FileNotFoundError, PermissionError, OSError) as exc:
            self._cleanup_tmp()
            self.finished = True
            if self.cb_failed:
                self.cb_failed("no_ytdlp" if isinstance(exc, FileNotFoundError) else "unknown", str(exc))
            return
        self.thread = threading.Thread(target=self._reader, daemon=True)
        self.thread.start()

    # --- reading the output ---------------------------------------------
    def _reader(self):
        try:
            for raw in self.proc.stdout:
                self._handle(raw.rstrip("\r\n"))
        except Exception:        # noqa: BLE001
            pass
        rc = self.proc.wait()
        try:
            self.proc.stdout.close()
        except Exception:        # noqa: BLE001
            pass
        if self._cancelled:
            return
        self._finish(rc)

    def _handle(self, line: str):
        p = parse_progress_line(line)
        if p:
            self._progress(p)
            return
        if line.startswith("ERROR:") or " ERROR:" in line[:20]:
            self._last_error = map_error(line)
            code, detail = self._last_error
            if self.is_playlist:                       # one video of the playlist failed, keep going
                self._log("error", "err_" + code, detail=detail)
            return
        m = re.search(r"Downloading \d+ format\(s\):\s*(\S+)", line)
        if m and line.startswith("[info]"):
            self._streams = format_sizes(self.info, m.group(1).split("+"))
            self._stream_done = []
        m = re.search(r'\[Merger\] Merging formats into "(.+)"', line) or \
            re.search(r"\[ExtractAudio\] Destination: (.+)", line) or \
            re.search(r"\[download\] Destination: (.+)", line) or \
            re.search(r"\[download\] (.+) has already been downloaded", line)
        if m:
            self._last_dest = m.group(1).strip()
        if re.match(r"\[(Merger|ExtractAudio|VideoConvertor|VideoRemuxer|FFmpeg\w*|Fixup\w*)\]", line) \
                and not self._processing:
            self._processing = True
            self._log("info", "processing")
            if self.cb_state:
                self.cb_state("processing")

    def _progress(self, p: dict):
        if p["index"] != self._index:                  # next video of a playlist
            self._index = p["index"]
            self._done_bytes = self._cur_bytes = 0.0
            self._processing = False
        down = p["downloaded"] or 0.0
        if p["status"] == "finished":
            self._done_bytes += down
            self._cur_bytes = 0.0
            self._stream_done.append(down)
        else:
            self._cur_bytes = down
        overall = self._done_bytes + self._cur_bytes
        cur_total = p["total"] or p["total_est"]
        total_now = self._refined_total(cur_total)                 # best knowledge of the size right now
        if total_now:
            frac = min(0.99, overall / total_now)
        elif self.est_total:
            frac = min(0.99, overall / self.est_total)
        elif cur_total:
            frac = min(0.99, self._cur_bytes / cur_total) if p["status"] != "finished" else 0.99
        else:
            frac = self.percent / 100
        if self.is_playlist and p["index"] and p["count"]:
            pos, n = p["index"], p["count"]
            if self.playlist_items:                       # only some positions are downloaded (sync)
                n = len(self.playlist_items)
                pos = self.playlist_items.index(p["index"]) + 1 if p["index"] in self.playlist_items else 1
            frac = ((pos - 1) + frac) / n
        self.percent = max(self.percent, frac * 100) if not self.is_playlist else frac * 100
        speed = p["speed"] or 0.0
        eta = p["eta"]
        basis = total_now or self.est_total
        if basis and speed > 0 and not self.is_playlist:
            eta = max(0.0, (basis - overall) / speed)
        if self.cb_progress:
            item, items = p["index"], p["count"]
            if self.playlist_items and item in self.playlist_items:
                item, items = self.playlist_items.index(item) + 1, len(self.playlist_items)
            total = total_now if (total_now and not self.is_playlist) else self.est_total
            if cur_total and not self.is_playlist and not total_now:      # total = what is known now, never below what came
                known = self._done_bytes + cur_total
                total = max(self.est_total or 0, known) if self.est_total else known
            if total and overall > total:
                total = overall
            self.cb_progress({"percent": self.percent, "speed": speed, "eta": eta,
                              "downloaded": overall, "total": total or None,
                              "item": item, "items": items})

    def _refined_total(self, cur_total):
        """Expected size of the whole file from what is known NOW: finished streams count with their real size,
        the stream that is downloading with the size yt-dlp reports, the next streams with their announced size.
        Returns None when the announced sizes are not known (then the first estimate is used)."""
        if not self._streams:
            return None
        n_done = len(self._stream_done)
        total = 0.0
        for j, est in enumerate(self._streams):
            if j < n_done:
                total += self._stream_done[j]
            elif j == n_done:
                total += cur_total or est or self._cur_bytes
            else:
                if est is None:
                    return None
                total += est
        return total or None

    # --- end of the process ---------------------------------------------
    def _collect_files(self) -> list:
        files = []
        self.items = []
        try:
            for l in self.list_file.read_text(encoding="utf-8", errors="replace").splitlines():
                l = l.strip()
                vid = ""
                if "|" in l and not os.path.exists(l):          # "videoid|path" (see build_download_cmd)
                    vid, l = l.split("|", 1)
                if l and os.path.exists(l):
                    files.append(l)
                    self.items.append((vid, l))
        except OSError:
            pass
        if not files and self._last_dest and not self.is_playlist:
            cand = self._last_dest if os.path.isabs(self._last_dest) else str(self.out_dir / self._last_dest)
            if os.path.exists(cand):
                files.append(cand)
        return files

    def _read_description(self) -> str:
        try:
            line = self.desc_file.read_text(encoding="utf-8", errors="replace").strip().splitlines()[0]
            value = json.loads(line)
            return value if isinstance(value, str) else ""
        except (OSError, ValueError, IndexError, AttributeError):
            return ""

    def _finish(self, rc: int):
        files = self._collect_files()
        self.description = self._read_description() or ((self.info or {}).get("description") or "")
        ok = bool(files) and (rc == 0 or self.is_playlist)
        if rc == 0 and not files:
            ok = False
        self.finished = True
        self._cleanup_tmp()
        if ok:
            size = sum(os.path.getsize(f) for f in files if os.path.exists(f))
            result = {
                "files": files, "path": files[-1], "name": os.path.basename(files[-1]),
                "size": size, "count": len(files), "folder": str(Path(files[-1]).parent),
                "is_audio": is_audio(self.fmt), "is_playlist": self.is_playlist, "items": list(self.items),
                "description": self.description,
                "quality": (quality_label(self.fmt, self.quality) if is_audio(self.fmt)
                            else (height_label(effective_height(self.info, self.quality))
                                  if effective_height(self.info, self.quality) else None)),
            }
            self.percent = 100.0
            if self.cb_finished:
                self.cb_finished(result)
        else:
            code, detail = self._last_error or ("unknown", f"exit code {rc}")
            if self.cb_failed:
                self.cb_failed(code, detail)

    # --- pause / resume -------------------------------------------------
    def _tree(self):
        parent = psutil.Process(self.proc.pid)
        return [parent] + parent.children(recursive=True)

    def pause(self) -> bool:
        """Suspend yt-dlp (and ffmpeg). The download is NOT terminated."""
        if not self.alive() or self.paused:
            return False
        try:
            if psutil:
                for pr in self._tree():
                    pr.suspend()
            elif not IS_WIN:
                os.kill(self.proc.pid, signal.SIGSTOP)
            else:
                return False
        except Exception:        # noqa: BLE001
            return False
        self.paused = True
        return True

    def resume(self) -> bool:
        if not self.alive() or not self.paused:
            return False
        try:
            if psutil:
                for pr in self._tree():
                    pr.resume()
            elif not IS_WIN:
                os.kill(self.proc.pid, signal.SIGCONT)
            else:
                return False
        except Exception:        # noqa: BLE001
            return False
        self.paused = False
        return True

    # --- cancel ---------------------------------------------------------
    def _kill_tree(self):
        pid = self.proc.pid
        if psutil:
            try:
                parent = psutil.Process(pid)
                procs = parent.children(recursive=True) + [parent]
            except psutil.Error:
                procs = []
            for pr in procs:
                try:
                    pr.kill()
                except psutil.Error:
                    pass
        elif IS_WIN:
            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True,
                           creationflags=NO_WINDOW)
        else:
            try:
                os.kill(pid, signal.SIGKILL)
            except OSError:
                pass

    def _cleanup_tmp(self):
        if not self.tmp_dir:
            return
        for _ in range(15):                    # Windows may need a moment to release the files
            shutil.rmtree(self.tmp_dir, ignore_errors=True)
            if not self.tmp_dir.exists():
                return
            time.sleep(0.2)

    def cancel(self):
        """Stop the download, kill the utility and delete every partial file."""
        if self._cancelled or self.finished or not self.proc:
            return
        self._cancelled = True
        if self.alive():
            self._kill_tree()
        if self.thread:
            self.thread.join(8)
        try:
            self.proc.stdout.close()
        except Exception:        # noqa: BLE001
            pass
        self.finished = True
        self._cleanup_tmp()
        if self.cb_cancelled:
            self.cb_cancelled()
