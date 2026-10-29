# =============================================================================
# TubeArchive Pro  |  Version 2.3.0  |  File: app/ads.py
# Version history of this file:
#   2.3.0 - read_text_file opens encrypted files (app/secure.py)
#   2.2.8 - total_users.txt ('1.0.0 = 25' lines) + the download counts of the release .exe files = users per version (parse_user_totals,
#           build_user_stats); the counter carries the per-version list for the splash screen
#   2.2.6 - Ads list format: one line per ad "number  source  url" (source = where the image is downloaded from, url = the
#           address opened by a click; the number is the display order); update check = the .exe files listed in the
#           GitHub folder ("TubeArchivePro x.y.z.exe"); parse_version also reads "TubeArchivePro_Setup_x.y.z"
#   2.3.0 - CACHE_DIR / BASELINE_FILE come from paths (user data / shipped file)
#   2.2.1 - GitHub: an ad is downloaded again when its fingerprint (sha of the contents listing) differs from the stored one
#           (even if the size is the same); the downloads counter counts only the setup files (.exe) of the releases
#   2.2.0 - GitHub as the online folder: files of a repository folder (contents API), newest version from the releases,
#           downloads counter = download_count of the release files (+ optional earlier total), download_count of one file
#   2.0.2 - Drive folder: several pages are tried + debug file; a missing <prefix>-YYYY-MM.txt shows all ads of the month
#   2.0.1 - Allowed ads: only the ads listed in tubearchivepro-YYYY-MM.txt are downloaded / shown (all other gifs are
#           removed); downloads_counter.txt -> counter in the corner (cached, offline baseline); read_text_file /
#           fetch_remote_text (reviews.txt); check runs while the splash screen is shown
#   1.0.14 - Link: online_folder_url (Google Drive folder); checked once at start
#   1.0.14 - Google Drive folders (embedded folder view); a .txt file gives the link of each ad (click opens it);
#            checked once, when the program starts
#   1.0.13 - Reads the folder page (4shared or any web folder): finds a newer program version
#            (tubearchivepro_v1.xx.xx.exe) and downloads every ad of this month; diagnostic log
#   1.0.12 - New: downloads the partner ads (animated GIFs) of the current month from a web link
# =============================================================================
"""Update check + partner advertisements.

One web folder (the link `online_folder_url`) holds:
  * the program:  tubearchivepro_v1.xx.xx.exe   -> a higher version than ours is reported to the user
  * the ads:      tubearchivepro-YYYY-MM_<x>.gif -> every file of the current month is downloaded to assets/ads

The folder can be a 4shared / 4s.io folder page or any web page / directory index that links the files.
`sync_ads` is Qt-free (tested without Qt); `AdsFetcher` runs it in a background thread.
Every step is written to data/updates.log, so a problem can be reported.
"""
import json
import re
import threading
import urllib.error
import urllib.request
from datetime import datetime
from html import unescape
from pathlib import Path
from urllib.parse import quote, unquote, urljoin, urlparse

from .paths import ADS_DIR, BASELINE_FILE, CACHE_DIR, DATA_DIR
from .secure import decrypt_if_needed

ALLOWED = "ads_allowed.json"              # {"month": "2026-10", "files": [...]}: the ads that may be shown
COUNTER_NAME = "downloads_counter.txt"    # on the online folder: the number of downloads of the program

MAX_ADS = 30                       # most files looked for in one month
MAX_BYTES = 40 * 1024 * 1024       # a bigger "gif" is ignored
LINKS = "ads_links.json"            # gif file name -> address (from the .txt files)
META = "ads_meta.json"             # size / etag / last-modified of the downloaded files
SHARE_HOSTS = ("4shared.com", "4s.io")
DRIVE_HOST = "drive.google.com"
GITHUB_API = "https://api.github.com"      # (tests point this to a local server)
GITHUB_HOSTS = ("github.com", "www.github.com")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0 Safari/537.36")


def month_tag(prefix: str, now: datetime | None = None) -> str:
    now = now or datetime.now()
    return f"{prefix}-{now:%Y}-{now:%m}"


def parse_version(text: str):
    """'tubearchivepro_v1.0.13.exe' or the 4shared name 'tubearchivepro_v1_0_13' -> (1, 0, 13); else None."""
    m = re.search(r"tubearchivepro[\s_\-]*(?:setup[\s_\-]*)?v?(\d+)[._](\d+)[._](\d+)", text or "", re.I)
    return tuple(int(x) for x in m.groups()) if m else None


def version_text(v) -> str:
    return ".".join(str(x) for x in v)


def is_share(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return any(host == h or host.endswith("." + h) for h in SHARE_HOSTS)


def _open(url: str, headers: dict | None = None, timeout: float = 15):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9",
                                               **(headers or {})})
    return urllib.request.urlopen(req, timeout=timeout)


def _page(url: str) -> str:
    with _open(url, {"Accept": "text/html,application/xhtml+xml,*/*;q=0.8"}) as r:
        return r.read(3_000_000).decode("utf-8", "replace")


def _size_after(html: str, pos: int):
    """File size written near a link on a folder page ('9,542 KB', '9.3 MB') -> bytes or None."""
    m = re.search(r"([\d][\d.,]*)\s*(KB|MB|GB)\b", html[pos:pos + 900], re.I)
    if not m:
        return None
    try:
        n = float(m.group(1).replace(",", ""))
    except ValueError:
        return None
    return int(n * {"kb": 1024, "mb": 1024 ** 2, "gb": 1024 ** 3}[m.group(2).lower()])


def list_remote(html: str, base: str) -> list:
    """Links of a folder page -> [{'name', 'url', 'size'}] (name = text of the link or the last part of its address)."""
    out, seen = [], set()
    for m in re.finditer(r'<a\b[^>]*?href\s*=\s*["\']([^"\']+)["\'][^>]*>(.*?)</a>', html, re.I | re.S):
        url = urljoin(base, unescape(m.group(1)))
        if url in seen:
            continue
        seen.add(url)
        slug = unquote(urlparse(url).path.rsplit("/", 1)[-1])
        slug = re.sub(r"\.html?$", "", slug, flags=re.I) if is_share(url) else slug
        text = re.sub(r"<[^>]+>", "", unescape(m.group(2))).strip()
        out.append({"name": slug, "text": text, "url": url, "size": _size_after(html, m.end())})
    return out


def pick(entries: list, tag: str) -> list:
    """The ad files of this month: names that start with 'tubearchivepro-YYYY-MM_'."""
    rx = re.compile(re.escape(tag) + r"_", re.I)
    got = []
    for e in entries:
        for cand in (e["text"], e["name"]):
            if cand and rx.match(cand.strip()) and not cand.strip().lower().endswith((".txt", ".exe")):
                name = cand.strip()
                got.append({**e, "file": re.sub(r"[^\w.\-]", "_", name if name.lower().endswith(".gif") else name + ".gif")})
                break
    uniq = {g["file"].lower(): g for g in got}
    return sorted(uniq.values(), key=lambda g: g["file"].lower())[:MAX_ADS]


def newest_version(entries: list, current: tuple):
    """Highest tubearchivepro_vX.Y.Z entry that is higher than `current` -> (version, entry) or (None, None)."""
    best = (None, None)
    for e in entries:
        v = parse_version(e["text"]) or parse_version(e["name"])
        if v and v > current and (best[0] is None or v > best[0]):
            best = (v, e)
    return best


# ----------------------------------------------------------------------
# GitHub repository: ads / text files = a folder of the repository, versions + downloads counter = the releases
# ----------------------------------------------------------------------
def is_github(url: str) -> bool:
    return (urlparse((url or "").strip()).hostname or "").lower() in GITHUB_HOSTS


def parse_github(url: str) -> dict:
    """https://github.com/<owner>/<repo>[/tree/<branch>/<folder>] -> {"owner", "repo", "ref", "path"}
    (ref "" = the default branch, path "" = the root of the repository)."""
    parts = [unquote(x) for x in urlparse(url.strip()).path.split("/") if x]
    if len(parts) < 2:
        raise ValueError("GitHub address needs owner and repository")
    owner, repo = parts[0], re.sub(r"\.git$", "", parts[1])
    ref, path = "", ""
    if len(parts) >= 4 and parts[2] in ("tree", "blob"):
        ref, path = parts[3], "/".join(parts[4:])
    return {"owner": owner, "repo": repo, "ref": ref, "path": path}


def _github_json(url: str):
    try:
        with _open(url, {"Accept": "application/vnd.github+json"}, 20) as r:
            return json.loads(r.read(5_000_000).decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        if e.code in (403, 429):
            raise OSError("GitHub limit reached (60 requests per hour without a token): try later") from e
        raise OSError(f"GitHub answered {e.code}") from e
    except json.JSONDecodeError as e:
        raise ValueError("GitHub answer is not JSON") from e


def list_github(base: str, log: list | None = None) -> list:
    """The files of the repository folder -> the same entries as list_remote: {'name', 'text', 'url', 'size'}.
    'url' is the raw download address, so the normal download code (ETag, size check) is used."""
    g = parse_github(base)
    url = f"{GITHUB_API}/repos/{g['owner']}/{g['repo']}/contents/{quote(g['path'])}"
    if g["ref"]:
        url += f"?ref={quote(g['ref'])}"
    data = _github_json(url)
    if isinstance(data, dict):                                   # a single file was given
        data = [data]
    out = [{"name": d["name"], "text": d["name"], "url": d.get("download_url") or "", "size": d.get("size"),
            "sha": d.get("sha") or ""}
           for d in data if isinstance(d, dict) and d.get("type") == "file" and d.get("download_url")]
    if log is not None:
        log.append(f"  github folder {g['owner']}/{g['repo']}/{g['path']}: {len(out)} files")
    return out


def github_releases(base: str, max_pages: int = 5) -> list:
    """All published releases of the repository (newest first)."""
    g = parse_github(base)
    out = []
    for page in range(1, max_pages + 1):
        data = _github_json(f"{GITHUB_API}/repos/{g['owner']}/{g['repo']}/releases?per_page=100&page={page}")
        if not isinstance(data, list):
            break
        out += [r for r in data if isinstance(r, dict) and not r.get("draft")]
        if len(data) < 100:
            break
    return out


SKIP_ASSETS = (".txt", ".sha256", ".sha512", ".md5", ".sig", ".asc", ".md")      # not counted as downloads of the program
COUNT_ASSETS = (".exe",)                                  # 2.2.1: only the setup file (.exe) of a release is counted


def release_version(rel: dict):
    m = re.search(r"(\d+)\.(\d+)\.(\d+)", str(rel.get("tag_name") or rel.get("name") or ""))
    return tuple(int(x) for x in m.groups()) if m else None


def asset_downloads(releases: list, name: str) -> int:
    """How many times the file `name` (any release) was downloaded: the sum of GitHub's download_count."""
    want = name.strip().lower()
    return sum(int(a.get("download_count", 0)) for r in releases for a in r.get("assets", [])
               if str(a.get("name", "")).lower() == want)


def file_download_count(base: str, name: str) -> int:
    """Online: how many times the release file `name` was downloaded (e.g. 'TubeArchivePro_2.1.0.zip')."""
    return asset_downloads(github_releases(base), name)


def github_stats(releases: list, current: tuple | None = None) -> dict:
    """-> {"version": 'x.y.z' newest published (not pre-) release higher than `current` or "", "version_url",
    "rows": [(tag, downloads)], "total"}. Downloads = download_count of every release file except checksums / text."""
    rows, best = [], (None, None)
    for r in releases:
        n = sum(int(a.get("download_count", 0)) for a in r.get("assets", [])
                if str(a.get("name", "")).lower().endswith(COUNT_ASSETS))
        v = release_version(r)
        rows.append((str(r.get("tag_name") or r.get("name") or "?"), n))
        if v and not r.get("prerelease") and (best[0] is None or v > best[0]):
            best = (v, r)
    out = {"version": "", "version_url": "", "rows": rows, "total": sum(n for _t, n in rows), "latest": ""}
    if best[0]:
        out["latest"] = version_text(best[0])
        if current is None or best[0] > current:
            out["version"] = version_text(best[0])
            allf = [a for a in best[1].get("assets", []) if not str(a.get("name", "")).lower().endswith(SKIP_ASSETS)]
            files = [a for a in allf if str(a.get("name", "")).lower().endswith(COUNT_ASSETS)] or allf      # the setup first
            out["version_url"] = (files[0].get("browser_download_url") if files else "") or best[1].get("html_url", "")
    return out


# ----------------------------------------------------------------------
# Google Drive folder ("anyone with the link"): its embedded view is a plain HTML list of the files
# ----------------------------------------------------------------------
def is_drive(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return host == "drive.google.com" or host.endswith(".drive.google.com")


def drive_folder_id(url: str) -> str:
    m = re.search(r"/folders/([\w-]+)", url) or re.search(r"[?&]id=([\w-]+)", url)
    return m.group(1) if m else ""


def parse_drive_folder(html: str) -> list:
    """Embedded folder view (or the normal folder page) -> [{'name', 'text', 'url', 'id', 'size'}]."""
    out, seen = [], set()

    def add(fid, name):
        name = unescape(name).strip()
        if fid and name and fid not in seen and not name.startswith("http"):
            seen.add(fid)
            out.append({"name": name, "text": name, "id": fid, "size": None,
                        "url": f"https://drive.google.com/file/d/{fid}/view"})

    for blk in re.split(r'(?=<div[^>]+class="[^"]*flip-entry")', html):
        fid = re.search(r'id="entry-([\w-]+)"', blk) or re.search(r"/file/d/([\w-]+)", blk)
        title = re.search(r'class="flip-entry-title"[^>]*>([^<]+)<', blk)
        if fid and title:
            add(fid.group(1), title.group(1))
    if not out:                                           # the normal folder page keeps the list inside a script
        for m in re.finditer(r'\["([\w-]{20,})",\["[\w-]+"\],"([^"\\]+\.[A-Za-z0-9]{2,4})"', html):
            add(m.group(1), m.group(2))
    return out


def _save_debug(name: str, html: str):
    """The page that could not be understood is kept in data/ so that it can be looked at."""
    try:
        (DATA_DIR / name).write_text(html[:400_000], encoding="utf-8")
    except OSError:
        pass


def list_drive(base: str, log: list | None = None) -> list:
    """Files of a shared Google Drive folder. Several pages are tried (the embedded list, the same with the
    language set, the normal folder page); the first one that shows files wins."""
    fid = drive_folder_id(base)
    if not fid:
        return []
    tries = [f"https://drive.google.com/embeddedfolderview?id={fid}",
             f"https://drive.google.com/embeddedfolderview?id={fid}&hl=en",
             f"https://drive.google.com/drive/folders/{fid}?hl=en",
             f"https://drive.google.com/drive/folders/{fid}"]
    last = ""
    for u in tries:
        try:
            html = _page(u)
        except (OSError, ValueError) as e:
            if log is not None:
                log.append(f"  page {u.split('google.com')[-1][:60]} failed: {e}")
            continue
        last = html
        entries = parse_drive_folder(html)
        if log is not None:
            log.append(f"  page {u.split('google.com')[-1][:60]}: {len(html)} bytes, {len(entries)} files")
        if entries:
            return entries
    if last:
        _save_debug("drive_page_debug.html", last)
        if log is not None:
            log.append("  no file was found in the folder pages (saved: data/drive_page_debug.html). "
                       "Is the folder shared with 'Anyone with the link'?")
    return []


def drive_urls(fid: str) -> list:
    return [f"https://drive.usercontent.google.com/download?id={fid}&export=download&confirm=t",
            f"https://drive.google.com/uc?export=download&id={fid}"]


def fetch_drive_bytes(fid: str, log: list, limit: int = MAX_BYTES):
    for u in drive_urls(fid):
        try:
            with _open(u, {"Accept": "*/*"}, 90) as r:
                data = r.read(limit + 1)
            if len(data) <= limit:
                return data
        except (OSError, ValueError) as e:
            log.append(f"  failed {u[:100]}: {e}")
    return None


# ----------------------------------------------------------------------
# the .txt files: which web address each ad opens when it is clicked
# ----------------------------------------------------------------------
IMG_EXT = (".gif", ".png", ".jpg", ".jpeg", ".webp")
URL_RX = re.compile(r"https?://[^\s\"'<>,;|]+")


def direct_url(url: str) -> str:
    """A page address of GitHub / Google Drive -> the address that gives the file itself."""
    u = (url or "").strip()
    p = urlparse(u)
    host = (p.hostname or "").lower()
    if host in GITHUB_HOSTS:
        parts = [x for x in p.path.split("/") if x]
        if len(parts) >= 5 and parts[2] in ("blob", "raw"):
            return "https://raw.githubusercontent.com/" + "/".join(parts[:2] + parts[3:])
    if is_drive(u):
        m = re.search(r"/file/d/([\w-]+)", p.path) or re.search(r"[?&]id=([\w-]+)", p.query)
        if m:
            return f"https://drive.google.com/uc?export=download&id={m.group(1)}"
    return u


def parse_ad_list(text: str) -> list:
    """The monthly list (TubeArchivePro-YYYY-MM.txt), one ad per line:  number  source  url
    number = display order, source = where the image is downloaded from, url = opened when the user clicks the ad
    (separators: spaces, tab, comma, semicolon or |). -> [{'num', 'source', 'url'}] sorted by number; [] when the
    text is not in this format (a line needs a source and a click address, or a source that is an image file)."""
    rows, used = [], set()
    for line in (text or "").splitlines():
        line = line.strip().lstrip("-*\u2022 ").strip()
        if not line or line.startswith("#"):
            continue
        urls = [u.rstrip(".)") for u in URL_RX.findall(line)]
        if not urls:
            continue
        src = urls[0]
        if len(urls) < 2 and not urlparse(src).path.lower().endswith(IMG_EXT):
            continue
        m = re.match(r"\s*(?:no\.?|#)?\s*(\d+)\b", line[:line.find(urls[0])], re.I)
        n = int(m.group(1)) if m else None
        if n is None or n in used:
            n = max(used | {0}) + 1
        used.add(n)
        rows.append({"num": n, "source": src, "url": urls[1] if len(urls) > 1 else ""})
    return sorted(rows, key=lambda r: r["num"])[:MAX_ADS]


def is_image(data: bytes) -> bool:
    return data.startswith((b"GIF8", b"\x89PNG", b"\xff\xd8\xff")) or (data[:4] == b"RIFF" and data[8:12] == b"WEBP")


def _num(text: str):
    m = re.search(r"(\d+)\s*(?:\.gif|\.txt)?\s*$", text.strip(), re.I)
    return int(m.group(1)) if m else None


def parse_links(texts: dict, gifs: list) -> dict:
    """texts = {txt file name: content}, gifs = ad file names -> {gif file name: web address}.
    * a txt named like the gif (tubearchivepro-2026-10_3.txt for ..._3.gif) holds that ad's address
    * any other txt of the month: one ad per line - 'name_or_number <address>' - or only addresses,
      which are given to the ads in order (sorted by number)"""
    links = {}
    gifs = sorted(gifs, key=lambda g: (_num(g) or 0, g.lower()))
    by_stem = {g.rsplit(".", 1)[0].lower(): g for g in gifs}
    by_num = {}
    for g in gifs:
        by_num.setdefault(_num(g), g)
    bare = []
    for name, content in sorted(texts.items()):
        stem = name.rsplit(".", 1)[0].lower()
        urls = re.findall(r"https?://[^\s\"'<>]+", content or "")
        if stem in by_stem and urls:
            links[by_stem[stem]] = urls[0]
            continue
        for line in (content or "").splitlines():
            m = re.search(r"https?://[^\s\"'<>]+", line)
            if not m:
                continue
            head = re.sub(r"[\s=:,;|>\-]+$", "", line[:m.start()]).strip()
            g = by_stem.get(head.rsplit(".", 1)[0].lower()) if head else None
            if g is None and head and _num(head) is not None:
                g = by_num.get(_num(head))
            if g:
                links[g] = m.group(0)
            else:
                bare.append(m.group(0))
    free = [g for g in gifs if g not in links]
    for g, u in zip(free, bare):
        links[g] = u
    return links


def load_links(folder: Path = ADS_DIR) -> dict:
    """{full path of the gif: address} saved by the last check (works offline)."""
    try:
        d = json.loads((Path(folder) / LINKS).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {str(Path(folder) / k): v for k, v in d.items() if (Path(folder) / k).exists()}


# ----------------------------------------------------------------------
def _gif_candidates(entry: dict) -> list:
    """Addresses that may hold the file. A normal web folder: the link itself.
    A 4shared page: the page is read and its download / picture addresses are tried."""
    if not is_share(entry["url"]):
        return [entry["url"]]
    try:
        html = _page(entry["url"])
    except (OSError, ValueError):
        return []
    html = unescape(html).replace("\\/", "/").replace("\\u0026", "&")
    found = []
    pats = (r'https?://[^"\'\s<>\\]*(?:directDownload|/download/|/dwnld/|download\.jsp)[^"\'\s<>\\]*',
            r'https?://dc\d+\.4shared\.com/(?:download|img)/[^"\'\s<>\\]+')
    for pat in pats:
        for u in re.findall(pat, html, re.I):
            if u not in found:
                found.append(u)
    for u in list(found):                                   # the same picture without the size part
        v = re.sub(r"/s\d+/", "/", u)
        if v != u and v not in found:
            found.append(v)
    return found


def _download_gif(entry: dict, path: Path, meta: dict, log: list) -> bool:
    """Try the candidate addresses; keep the first valid GIF that is about the size listed on the folder page."""
    listed = entry.get("size")
    best = None
    for u in _gif_candidates(entry):
        try:
            with _open(u, {"Referer": entry["url"], "Accept": "image/gif,image/*;q=0.9,*/*;q=0.5"}, 60) as r:
                data = r.read(MAX_BYTES + 1)
        except (OSError, ValueError) as e:
            log.append(f"  failed {u[:110]}: {e}")
            continue
        ok = len(data) <= MAX_BYTES and data.startswith(b"GIF8")
        log.append(f"  {'gif' if ok else 'not a gif'} {len(data)} bytes {u[:110]}")
        if not ok:
            continue
        if not listed or len(data) >= listed * 0.7:
            best = data
            break
        if best is None or len(data) > len(best):
            best = data                                   # smaller than listed: only if nothing better comes
    if best is None:
        return False
    tmp = path.with_suffix(".part")
    tmp.write_bytes(best)
    tmp.replace(path)
    meta[path.name] = {"size": len(best), "listed": listed or 0}
    return True


def _load_meta(folder: Path) -> dict:
    try:
        return json.loads((folder / META).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _load_allowed(folder: Path):
    try:
        d = json.loads((Path(folder) / ALLOWED).read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else None
    except (OSError, ValueError):
        return None


def local_ads(folder: Path = ADS_DIR, now: datetime | None = None) -> list:
    """The ads that may be shown: the gifs listed by the allowed-ads file of THIS month (older downloads and ads
    that are not listed are never shown). Without any allowed-ads record every gif of the folder is used."""
    files = sorted(str(p) for p in Path(folder).glob("*.gif"))
    d = _load_allowed(folder)
    if d is None:
        return files
    now = now or datetime.now()
    if d.get("month") != f"{now:%Y-%m}":
        return []
    allowed = {str(n).lower() for n in d.get("files", [])}
    return [f for f in files if Path(f).name.lower() in allowed]


def _txt_stem(entry: dict) -> str:
    name = (entry.get("text") if str(entry.get("text", "")).lower().endswith(".txt") else entry.get("name", "")) or ""
    name = name.strip()
    return name[:-4].lower() if name.lower().endswith(".txt") else ""


def parse_allowed(text: str, gifs: list) -> set:
    """tubearchivepro-YYYY-MM.txt -> the file names of the ads that are allowed (paid) this month.
    One ad per line: the gif name (with or without .gif) or only its number; an address after it is the link."""
    by_name = {g.lower(): g for g in gifs}
    by_stem = {g.rsplit(".", 1)[0].lower(): g for g in gifs}
    by_tail = {g.rsplit(".", 1)[0].split("_", 1)[-1].lower(): g for g in gifs}      # "summer" -> ..._summer.gif
    by_num = {}
    for g in gifs:
        by_num.setdefault(_num(g), g)
    allowed = set()
    for line in (text or "").splitlines():
        line = line.strip().lstrip("-*\u2022 ").strip()
        if not line or line.startswith("#"):
            continue
        m = re.search(r"https?://", line)
        head = (line[:m.start()] if m else line).strip(" \t=:,;|>-")
        if not head:
            continue
        token = re.split(r"[\s,;|]+", head)[0]
        g = by_name.get(token.lower()) or by_stem.get(token.rsplit(".", 1)[0].lower()) or by_tail.get(token.lower())
        if g is None and token.isdigit():
            g = by_num.get(int(token))
        if g:
            allowed.add(g)
    return allowed


# ----------------------------------------------------------------------
# text files of the online folder (downloads_counter.txt, reviews.txt ...)
# ----------------------------------------------------------------------
def list_entries(base: str) -> list:
    if is_github(base):
        return list_github(base)
    return list_drive(base) if is_drive(base) else list_remote(_page(base), base)


def read_text_file(base: str, filename: str, entries: list | None = None, log: list | None = None):
    """The text of `filename` from the online folder (None when it is not there)."""
    log = log if log is not None else []
    if entries is None:
        entries = list_entries(base)
    want = filename.lower()
    e = next((x for x in entries if (x.get("text", "").strip().lower() == want or x.get("name", "").strip().lower() == want)), None)
    if e is None:
        return None
    if e.get("id"):
        data = fetch_drive_bytes(e["id"], log, 400_000)
    else:
        try:
            with _open(e["url"], timeout=20) as r:
                data = r.read(400_001)
        except (OSError, ValueError) as ex:
            log.append(f"  failed {filename}: {ex}")
            data = None
    if data:
        data = decrypt_if_needed(data)                    # 2.3.0: encrypted files are opened here (plain files stay as they are)
    return data.decode("utf-8-sig", "replace") if data else None


def parse_counter(text: str) -> dict:
    """downloads_counter.txt -> {"total": N, "rows": [(label, number)]}.
    Lines: 'v1.0.12 = 320' / 'old versions: 1,250' / '980'. A line 'total = N' is used as the total;
    without it the total is the sum of all the numbers."""
    rows, explicit = [], None
    for line in (text or "").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = re.search(r"(?<![\w.])(\d[\d,]*)\s*$", line)
        if not m:
            continue
        value = int(m.group(1).replace(",", ""))
        label = line[:m.start()].strip(" :=-\t")
        if label.lower().startswith(("total", "sum")):
            explicit = value
        else:
            rows.append((label, value))
    total = explicit if explicit is not None else sum(v for _l, v in rows)
    return {"total": total, "rows": rows}


USERS_FILE = "total_users.txt"          # on the online folder: '1.0.0 = 25' - users of versions that have no .exe release file


def parse_user_totals(text: str) -> dict:
    """total_users.txt -> {(1, 0, 0): 25, ...}. Lines: '1.0.0 = 25' (also ':' or a space, 'v1.0.0', 'x,xxx')."""
    out = {}
    for line in (text or "").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r"v?(\d+)\.(\d+)\.(\d+)\s*[=:\-\s]\s*(\d[\d,]*)\s*$", line, re.I)
        if m:
            out[tuple(int(x) for x in m.groups()[:3])] = int(m.group(4).replace(",", ""))
    return out


def build_user_stats(releases: list, totals: dict) -> dict:
    """Users per version = the download_count of the .exe files of a release; a version that has no .exe release file
    uses its number from total_users.txt. -> {"total", "versions": [("1.0.0", n), ...] (old -> new), "rows"}."""
    per = {}
    for r in releases:
        exe = [a for a in r.get("assets", []) if str(a.get("name", "")).lower().endswith(COUNT_ASSETS)]
        v = release_version(r)
        if exe and v:
            per[v] = per.get(v, 0) + sum(int(a.get("download_count", 0)) for a in exe)
    for v, n in totals.items():
        per.setdefault(v, n)
    items = sorted(per.items())
    return {"total": sum(n for _v, n in items), "versions": [(version_text(v), n) for v, n in items],
            "rows": [(f"v{version_text(v)}", n) for v, n in items]}


def save_counter(data: dict, cache_dir: Path = CACHE_DIR):
    try:
        Path(cache_dir).mkdir(parents=True, exist_ok=True)
        (Path(cache_dir) / "downloads_counter.json").write_text(
            json.dumps({**data, "date": f"{datetime.now():%Y-%m-%d %H:%M}"}, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass


def load_counter(cache_dir: Path = CACHE_DIR, baseline: Path = BASELINE_FILE):
    """The counter to show: the last online value; else the value shipped with the setup; else None (hidden)."""
    try:
        d = json.loads((Path(cache_dir) / "downloads_counter.json").read_text(encoding="utf-8"))
        if isinstance(d, dict) and int(d.get("total", 0)) > 0:
            return {"total": int(d["total"]), "rows": [tuple(r) for r in d.get("rows", [])], "source": "cache",
                    "versions": [tuple(x) for x in d.get("versions", [])]}
    except (OSError, ValueError, TypeError):
        pass
    try:
        d = parse_counter(Path(baseline).read_text(encoding="utf-8"))
        if d["total"] > 0:
            return {**d, "source": "baseline"}
    except OSError:
        pass
    return None


def fetch_remote_text(base: str, filename: str, cache_name: str, cache_dir: Path = CACHE_DIR) -> dict:
    """Downloads `filename` from the online folder; the text is kept in the cache folder and used again
    when the folder cannot be reached. -> {"text", "cached" (True = old copy), "error"}"""
    cache = Path(cache_dir) / cache_name
    log: list = []
    try:
        text = read_text_file(base, filename, None, log)
        if text is not None:
            try:
                cache.parent.mkdir(parents=True, exist_ok=True)
                cache.write_text(text, encoding="utf-8")
            except OSError:
                pass
            return {"text": text, "cached": False, "error": ""}
        err = "not found"
    except (OSError, ValueError) as e:
        err = str(e)
    try:
        return {"text": cache.read_text(encoding="utf-8"), "cached": True, "error": err}
    except OSError:
        return {"text": "", "cached": False, "error": err}


def sync_ads(base_url: str, prefix: str = "tubearchivepro", folder: Path = ADS_DIR,
             now: datetime | None = None, current_version: tuple | None = None,
             require_allowed: bool = True, cache_dir: Path = CACHE_DIR) -> dict:
    """One check: newer program version? + download this month's ads (refresh changed ones, delete old ones).
    require_allowed: only the ads listed in <prefix>-YYYY-MM.txt are downloaded / kept (paid ads).
    Returns {"files", "downloaded", "error", "version", "version_url", "log", "links", "counter"}. Never raises."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    log = [f"{datetime.now():%Y-%m-%d %H:%M:%S}  check {base_url}"]
    out = {"files": local_ads(folder, now), "downloaded": 0, "error": "", "version": "", "version_url": "", "log": log,
           "counter": None}
    base = (base_url or "").strip()
    if not base:
        return out
    tag = month_tag(prefix, now)
    meta = _load_meta(folder)
    share = is_share(base)
    drive = is_drive(base)
    entries = []
    gh = is_github(base)
    stats = None
    rels = []
    try:
        if gh:
            entries = list_github(base, log)
        else:
            entries = list_drive(base, log) if is_drive(base) else list_remote(_page(base), base)
            log.append(f"  folder page: {len(entries)} {'files' if is_drive(base) else 'links'}")
    except (OSError, ValueError) as e:
        out["error"] = str(e)
        log.append(f"  folder page failed: {e}")
    if gh and current_version and entries:                 # 2.2.6: the program = a "TubeArchivePro x.y.z.exe" file of the folder
        v, e = newest_version([x for x in entries if x["name"].lower().endswith(".exe")], current_version)
        if v:
            out["version"], out["version_url"] = version_text(v), e["url"]
            log.append(f"  newer version {out['version']}: {e['url']}")
    if gh:                                                 # downloads counter (and the version when the folder has no newer .exe)
        try:
            rels = github_releases(base)
            stats = github_stats(rels, current_version)
            if stats["version"] and not out["version"]:
                out["version"], out["version_url"] = stats["version"], stats["version_url"]
                log.append(f"  newer version {out['version']}: {out['version_url']}")
            log.append(f"  releases: downloads {stats['total']} {stats['rows'][:6]}")
        except (OSError, ValueError) as e:
            out["error"] = out["error"] or str(e)
            log.append(f"  releases failed: {e}")
    elif current_version:
        v, e = newest_version(entries, current_version)
        if v:
            out["version"], out["version_url"] = version_text(v), e["url"]
            log.append(f"  newer version {out['version']}: {e['url']}")
    ads = pick(entries, tag)
    log.append(f"  ads of {tag}: {[a['file'] for a in ads]}")
    if gh and stats is not None:                           # GitHub: real count of the release files (+ earlier total, optional)
        before = 0
        users = None
        try:
            if entries and any(e["name"].lower() == USERS_FILE for e in entries):      # 2.2.8: users per version
                utext = read_text_file(base, USERS_FILE, entries, log)
                if utext:
                    users = build_user_stats(rels, parse_user_totals(utext))
            text = read_text_file(base, COUNTER_NAME, entries, log) if entries and users is None else None
            if text:                                       # downloads_counter.txt = downloads before GitHub (e.g. Google Drive)
                before = parse_counter(text)["total"]
        except (OSError, ValueError):
            pass
        rows = list(stats["rows"]) + ([("earlier", before)] if before else [])
        out["counter"] = {"total": stats["total"] + before, "rows": rows}
        if users:
            out["counter"] = {"total": users["total"], "rows": users["rows"], "versions": users["versions"]}
        save_counter(out["counter"], cache_dir)
        log.append(f"  counter: {out['counter']['total']}")
    elif entries:                                          # the downloads counter shown in the corner
        try:
            text = read_text_file(base, COUNTER_NAME, entries, log)
        except (OSError, ValueError):
            text = None
        if text:
            out["counter"] = parse_counter(text)
            save_counter(out["counter"], cache_dir)
            log.append(f"  {COUNTER_NAME}: total {out['counter']['total']}")
        else:
            log.append(f"  {COUNTER_NAME}: not found")
    allowed_names = None
    list_links = None
    a_entry = next((e for e in entries if _txt_stem(e) == tag.lower()), None) if entries else None
    if a_entry is not None:                                # 2.2.6: "number source url" lines
        try:
            lst = parse_ad_list(read_text_file(base, a_entry["text"] if a_entry["text"].lower().endswith(".txt")
                                               else a_entry["name"], entries, log) or "")
        except (OSError, ValueError):
            lst = []
        if lst:
            ads = [{"file": f"{tag}_{r['num']:02d}.gif", "url": direct_url(r["source"]), "size": None, "listed": True}
                   for r in lst]
            list_links = {a["file"]: r["url"] for a, r in zip(ads, lst) if r["url"]}
            allowed_names = {a["file"] for a in ads}
            log.append(f"  ad list {a_entry['name']}: {[(r['num'], r['source']) for r in lst]}")
    if list_links is not None:
        pass
    elif require_allowed and entries:                      # only the paid ads of this month: the list is <tag>.txt
        if a_entry is None:
            allowed_names = {a["file"] for a in ads}
            log.append(f"  {tag}.txt not found: every ad of this month is shown")
        else:
            try:
                text = read_text_file(base, a_entry["text"] if a_entry["text"].lower().endswith(".txt") else a_entry["name"],
                                      entries, log)
            except (OSError, ValueError):
                text = None
            if text is None:                               # could not be read: keep the list of the last check
                prev = _load_allowed(folder)
                allowed_names = set(prev.get("files", [])) if prev and prev.get("month") == f"{(now or datetime.now()):%Y-%m}" else set()
                log.append(f"  {tag}.txt could not be read: the last allowed list is used")
            else:
                allowed_names = parse_allowed(text, [a["file"] for a in ads])
                log.append(f"  allowed ads: {sorted(allowed_names)}")
        low_ok = {n.lower() for n in allowed_names}
        ads = [a for a in ads if a["file"].lower() in low_ok]
    if not ads and not share and not entries:             # plain server without a page: _1, _2, _3 ... until one is missing
        b = base if base.endswith("/") else base + "/"
        ads = [{"file": f"{tag}_{i}.gif", "url": urljoin(b, quote(f"{tag}_{i}.gif")), "size": None, "probe": True}
               for i in range(1, MAX_ADS + 1)]
    wanted = []
    for ad in ads:
        path = folder / ad["file"]
        m = meta.get(ad["file"], {})
        sha = ad.get("sha") or ""                          # GitHub: the exact fingerprint of the online file
        if sha and path.exists() and m.get("sha") == sha:
            wanted.append(ad["file"])                      # same fingerprint as the file we hold: unchanged
            continue
        if ad.get("size") and not sha and path.exists() and abs(path.stat().st_size - ad["size"]) <= ad["size"] * 0.03:
            wanted.append(ad["file"])                      # same size as listed: unchanged
            continue
        if share and path.exists() and m.get("listed") and ad.get("size") == m["listed"]:
            wanted.append(ad["file"])
            continue
        if drive:
            if path.exists() and m.get("id") == ad.get("id"):
                wanted.append(ad["file"])                  # same Drive file as before
                continue
            data = fetch_drive_bytes(ad["id"], log)
            if data is None or not data.startswith(b"GIF8"):
                log.append(f"  {ad['file']}: not downloaded ({'not a gif' if data else 'no data'})")
                if path.exists():
                    wanted.append(ad["file"])
                continue
            tmp = path.with_suffix(".part")
            tmp.write_bytes(data)
            tmp.replace(path)
            meta[ad["file"]] = {"id": ad["id"], "size": len(data)}
            out["downloaded"] += 1
            wanted.append(ad["file"])
            continue
        hdr = {}
        if not share and path.exists() and not sha:         # (with a fingerprint the file is fetched without conditions)
            if m.get("etag"):
                hdr["If-None-Match"] = m["etag"]
            if m.get("modified"):
                hdr["If-Modified-Since"] = m["modified"]
        try:
            if share:
                ok = _download_gif(ad, path, meta, log)
                if ok:
                    out["downloaded"] += 1
                    wanted.append(ad["file"])
                continue
            with _open(ad["url"], hdr, 30) as r:
                data = r.read(MAX_BYTES + 1)
                if len(data) > MAX_BYTES or not (is_image(data) if ad.get("listed") else data.startswith(b"GIF8")):
                    if ad.get("listed") and path.exists():
                        wanted.append(ad["file"])
                    continue
                tmp = path.with_suffix(".part")
                tmp.write_bytes(data)
                tmp.replace(path)
                meta[ad["file"]] = {"etag": r.headers.get("ETag", ""), "modified": r.headers.get("Last-Modified", ""),
                                    "size": len(data), "sha": sha}
                out["downloaded"] += 1
                wanted.append(ad["file"])
        except urllib.error.HTTPError as e:
            if (e.code == 304 or ad.get("listed")) and path.exists():
                wanted.append(ad["file"])
            elif e.code in (404, 403, 410) and ad.get("probe"):
                break                                      # the numbered list ended
        except (OSError, ValueError) as e:
            out["error"] = str(e)
            log.append(f"  failed {ad['file']}: {e}")
            if ad.get("listed") and path.exists():
                wanted.append(ad["file"])                  # the source is not reachable now: keep the earlier copy
            if ad.get("probe"):
                break
    if entries and (require_allowed or list_links is not None) and allowed_names is not None:      # keep only the allowed ads, remove the others
        pat = re.compile(re.escape(prefix) + r"-\d{4}-\d{2}_.*\.gif$", re.I)
        low = {w.lower() for w in wanted}
        for p in folder.glob("*.gif"):
            if pat.match(p.name) and p.name.lower() not in low:
                try:
                    p.unlink()
                except OSError:
                    pass
                meta.pop(p.name, None)
        try:
            (folder / ALLOWED).write_text(json.dumps({"month": f"{(now or datetime.now()):%Y-%m}",
                                                      "files": sorted(wanted)}), encoding="utf-8")
            (folder / META).write_text(json.dumps(meta, indent=1), encoding="utf-8")
        except OSError:
            pass
    elif wanted:                                           # the old downloaded ads (other months) are removed
        pat = re.compile(re.escape(prefix) + r"-\d{4}-\d{2}_.*\.gif$", re.I)
        low = {w.lower() for w in wanted}
        for p in folder.glob("*.gif"):
            if pat.match(p.name) and p.name.lower() not in low:
                try:
                    p.unlink()
                except OSError:
                    pass
                meta.pop(p.name, None)
        try:
            (folder / META).write_text(json.dumps(meta, indent=1), encoding="utf-8")
        except OSError:
            pass
    out["files"] = local_ads(folder, now)
    if list_links is not None:
        try:
            (folder / LINKS).write_text(json.dumps(list_links, indent=1), encoding="utf-8")
        except OSError:
            pass
    elif ads:
        _update_links(entries, ads, folder, tag, drive, log)
    out["links"] = load_links(folder)
    log.append(f"  downloaded {out['downloaded']}, local ads {len(out['files'])}")
    return out


def _update_links(entries: list, ads: list, folder: Path, tag: str, drive: bool, log: list):
    """Read this month's .txt files and save {gif: address} next to the gifs."""
    rx = re.compile(re.escape(tag), re.I)
    texts = {}
    for e in entries:
        name = e["text"] if e["text"].lower().endswith(".txt") else e["name"]
        if name.lower().endswith(".txt") and rx.match(name.strip()):
            data = None
            if drive:
                data = fetch_drive_bytes(e["id"], log, 200_000)
            else:
                try:
                    with _open(e["url"], timeout=20) as r:
                        data = r.read(200_001)
                except (OSError, ValueError) as ex:
                    log.append(f"  failed {name}: {ex}")
            if data:
                texts[name.strip()] = data.decode("utf-8-sig", "replace")
    links = parse_links(texts, [a["file"] for a in ads])
    log.append(f"  link files: {sorted(texts)} -> {links}")
    if texts:
        try:
            (folder / LINKS).write_text(json.dumps(links, indent=1), encoding="utf-8")
        except OSError:
            pass


def write_log(lines: list):
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        (DATA_DIR / "updates.log").write_text("\n".join(lines) + "\n", encoding="utf-8")
    except OSError:
        pass


try:
    from PySide6.QtCore import QObject, Signal

    class AdsFetcher(QObject):
        """Runs sync_ads in a thread; `finished_check(dict)` arrives in the interface thread with
        {"files", "downloaded", "error", "version", "version_url", "log"}."""
        finished_check = Signal(object)

        def __init__(self, parent=None):
            super().__init__(parent)
            self._busy = False

        def refresh(self, url: str, prefix: str, current_version: tuple = (0, 0, 0)):
            if self._busy or not url:
                return
            self._busy = True
            threading.Thread(target=self._work, args=(url, prefix, current_version), daemon=True).start()

        def _work(self, url, prefix, current_version):
            try:
                r = sync_ads(url, prefix, current_version=current_version)
                write_log(r.get("log", []))
            except Exception as e:                              # noqa: BLE001
                r = {"files": local_ads(), "downloaded": 0, "version": "", "version_url": "", "error": str(e), "log": []}
            self._busy = False
            self.finished_check.emit(r)

    class TextFetcher(QObject):
        """Downloads a text file of the online folder in a thread: done(kind, {"text", "cached", "error"})."""
        done = Signal(str, object)

        def fetch(self, kind: str, base: str, filename: str, cache_name: str):
            threading.Thread(target=self._work, args=(kind, base, filename, cache_name), daemon=True).start()

        def _work(self, kind, base, filename, cache_name):
            try:
                r = fetch_remote_text(base, filename, cache_name)
            except Exception as e:                              # noqa: BLE001
                r = {"text": "", "cached": False, "error": str(e)}
            self.done.emit(kind, r)
except ImportError:          # tests without Qt
    pass
