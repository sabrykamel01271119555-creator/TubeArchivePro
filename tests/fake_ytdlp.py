"""A fake yt-dlp used by the tests (prints the same kind of lines, writes the same files)."""
import json
import os
import sys
import time

a = sys.argv[1:]
url = a[-1]
if os.environ.get("FAKE_ARGLOG") and "-J" not in a:           # tests read the options each process got
    with open(os.environ["FAKE_ARGLOG"], "a") as f:
        f.write(json.dumps(a) + "\n")
PL = [("v1", "One"), ("v2", "Two"), ("v3", "Three"), ("v4", "Four"), ("v5", "Five")]
if "-J" in a and "playlist" in url and "bad" not in url:
    n = int(os.environ.get("FAKE_PL_COUNT", "5"))
    print(json.dumps({"_type": "playlist", "id": "PLX", "title": "My List", "extractor_key": "Generic",
                      "entries": [{"id": i, "title": t} for i, t in PL[:n]] + [{"id": "pv", "title": "[Private video]"}]}))
    sys.exit(0)
if "-J" in a:
    if "bad" in url:
        print("ERROR: [youtube] abc: Video unavailable", file=sys.stderr)
        sys.exit(1)
    print(json.dumps({"title": "Summer Vlog", "id": "abc", "duration": 100, "extractor_key": "Generic",
                      "thumbnail": "", "formats": [
        {"vcodec": "avc1", "acodec": "none", "height": 1080, "filesize": 80_000_000, "ext": "mp4", "tbr": 5000},
        {"vcodec": "avc1", "acodec": "none", "height": 2160, "filesize": 400_000_000, "ext": "mp4", "tbr": 20000},
        {"vcodec": "avc1", "acodec": "none", "height": 360, "filesize": 8_000_000, "ext": "mp4", "tbr": 500},
        {"vcodec": "none", "acodec": "mp4a", "abr": 128, "filesize": 2_000_000, "ext": "m4a"}]}))
    sys.exit(0)
home = next(x.split(":", 1)[1] for x in a if x.startswith("home:"))
tmp = next(x.split(":", 1)[1] for x in a if x.startswith("temp:"))
listfile = a[a.index("--print-to-file") + 2]
steps = int(os.environ.get("FAKE_STEPS", "10"))
if "fail" in url:
    print("ERROR: HTTP Error 429: Too Many Requests", file=sys.stderr, flush=True)
    sys.exit(1)
os.makedirs(tmp, exist_ok=True)
if "playlist" in url:
    n = int(os.environ.get("FAKE_PL_COUNT", "5"))
    items = [int(x) for x in a[a.index("--playlist-items") + 1].split(",")] if "--playlist-items" in a else range(1, n + 1)
    tpl = a[a.index("-o") + 1]
    sub = "My List" if "%(playlist_title)s" in tpl else ""
    os.makedirs(os.path.join(home, sub), exist_ok=True)
    for idx in items:
        vid, title = PL[idx - 1]
        for i in range(1, 4):
            print(f"TAPROG|downloading|{i * 100}|300|NA|300|{3 - i}|{idx}|{n}", flush=True)
            time.sleep(0.02)
        print(f"TAPROG|finished|300|300|NA|NA|NA|{idx}|{n}", flush=True)
        final = os.path.join(home, sub, f"{title}.mp4")
        open(final, "wb").write(b"z" * 2000)
        with open(listfile, "a", encoding="utf-8") as f:
            f.write(f"{vid}|{final}\n")
    sys.exit(0)
import re
m = re.search(r"[?&]v=([\w-]+)", url)
vid = m.group(1) if m else "abc"
title = "Summer Vlog" if not m else "Video " + vid
tpl = a[a.index("-o") + 1] if "-o" in a else "%(title)s.%(ext)s"
rel = tpl.replace("%(title)s", title).replace("%(ext)s", "mp4").replace("%%", "%")
part = os.path.join(tmp, title + ".f137.mp4.part")
for stream in range(2):
    total = 1000 * (stream + 1)
    for i in range(1, steps + 1):
        open(part, "ab").write(b"x" * 100)
        d = total * i // steps
        print(f"TAPROG|downloading|{d}|{total}|NA|{total}|{steps - i}|NA|NA", flush=True)
        time.sleep(0.1)
    print(f"TAPROG|finished|{total}|{total}|NA|NA|NA|NA|NA", flush=True)
final = os.path.join(home, rel)
print(f'[Merger] Merging formats into "{final}"', flush=True)
os.makedirs(os.path.dirname(final), exist_ok=True)
open(final, "wb").write(b"y" * 3000)
with open(listfile, "a", encoding="utf-8") as f:
    f.write((vid + "|" if m else "") + final + "\n")
prints = [i for i, x in enumerate(a) if x == "--print-to-file"]
if len(prints) > 1:
    with open(a[prints[1] + 2], "w", encoding="utf-8") as f:
        f.write(json.dumps("About " + title + "\nSecond line") + "\n")
