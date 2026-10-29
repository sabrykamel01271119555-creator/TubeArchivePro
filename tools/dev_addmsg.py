"""Developer helper: python3 tools/dev_addmsg.py spec.json
spec.json = [["CONST_NAME", "English text", "Arabic text"], ...]
Appends the constants to app/msg.py (class M) and the texts to data/languages/en.json + ar.json with the next MSG number."""
import json
import re
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
msg_py = root / "app" / "msg.py"
text = msg_py.read_text(encoding="utf-8")
used = {k for k in re.findall(r'"(MSG_\d+)"', text)}
nxt = max(int(x[4:]) for x in used) + 1
names = set(re.findall(r"^\s+(\w+)\s*=\s*\"MSG_", text, re.M))
files = {c: root / "data" / "languages" / f"{c}.json" for c in ("en", "ar")}
data = {c: json.loads(p.read_text(encoding="utf-8")) for c, p in files.items()}
lines = []
for const, en, ar in json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")):
    if const in names:
        print("skip (exists):", const)
        continue
    key = f"MSG_{nxt:03d}"
    nxt += 1
    lines.append(f'    {const} = "{key}"\n')
    data["en"]["messages"][key] = en
    data["ar"]["messages"][key] = ar
text = text.rstrip("\n") + "\n" + "".join(lines)
msg_py.write_text(text, encoding="utf-8")
for c, p in files.items():
    p.write_text(json.dumps(data[c], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("added", len(lines))
