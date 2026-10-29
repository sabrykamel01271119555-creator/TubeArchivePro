# =============================================================================
# TubeArchive Pro  |  Version 2.3.1  |  File: app/infodoc.py
# Version history of this file:
#   2.3.1 - About us = about + contact + donate in one page (load_about); rows (e-mail, phone numbers ...) without a frame
#   2.0.3 - description_html(): links in the description of a video
#   2.0.2 - Icon rows ([icon:name] Label :: value), plain facts line (~ text), {version} placeholder
#   2.0.1 - Created: turns the text files of the info pages (help, about us, contact us, donate, reviews) into
#           professional-looking HTML for the work area; parser for the reviews.txt file filled by a Google form
# =============================================================================
"""Info pages.  NO Qt in this file (tested on its own).

The pages are plain text files so they can be edited without touching the code:
    assets/info/help.en.txt  help.ar.txt  aboutus.en.txt  ...      (shipped with the setup, local)
    reviews.txt                                                    (downloaded from the online folder)

Text format (one item per line, blank line = new paragraph)
    # Title                 big page title            ## Section        section heading        ### Small heading
    - item                  bullet                    1. item           numbered step
    > note                  highlighted note          ---               divider
    Label :: value          a row (Email :: a@b.com)  [text](https://..) link;   bare web addresses and e-mails are links
    **bold**                bold text
    [icon:instapay] Label :: value   a row with a small picture (assets/info/icons/<name>.png)
    ~ Version {version} - 2026       a quiet centred line without any frame ({version} = the program version)
"""
import csv
import html
import io
import re
from pathlib import Path

from .paths import APP_VERSION, INFO_DIR

# colours (solid: the rich-text widget of Qt does not draw transparent colours well)
C_TITLE, C_TEXT, C_MUTED, C_LINK = "#ffffff", "#eef6ff", "#cfe3ff", "#ffe08a"
C_CARD, C_CARD_EDGE, C_ACCENT, C_NOTE = "#2a64c8", "#8fc4ff", "#ffc83d", "#1d4fa8"

_URL = re.compile(r"(?P<md>\[(?P<mt>[^\]]+)\]\((?P<mu>[^)\s]+)\))|(?P<url>https?://[^\s<>\"]+[^\s<>\".,;:!?)])|"
                  r"(?P<mail>[\w.+-]+@[\w-]+(?:\.[\w-]+)+)")
_BOLD = re.compile(r"\*\*(.+?)\*\*")


def inline(text: str) -> str:
    """Escapes the text and turns links, e-mail addresses and **bold** into HTML."""
    out, pos = [], 0
    for m in _URL.finditer(text):
        out.append(_bold(html.escape(text[pos:m.start()])))
        if m.group("md"):
            out.append(f'<a href="{html.escape(m.group("mu"), quote=True)}" style="color:{C_LINK};">'
                       f'{html.escape(m.group("mt"))}</a>')
        elif m.group("url"):
            u = m.group("url")
            out.append(f'<a href="{html.escape(u, quote=True)}" style="color:{C_LINK};">{html.escape(u)}</a>')
        else:
            a = m.group("mail")
            out.append(f'<a href="mailto:{a}" style="color:{C_LINK};">{a}</a>')
        pos = m.end()
    out.append(_bold(html.escape(text[pos:])))
    return "".join(out)


def _bold(escaped: str) -> str:
    return _BOLD.sub(r"<b>\1</b>", escaped)


def _card(inner: str, edge: str = C_CARD_EDGE, bg: str = C_CARD) -> str:
    return (f'<table width="100%" cellspacing="0" cellpadding="12" style="margin-bottom:10px;">'
            f'<tr><td style="background-color:{bg}; border:1px solid {edge};">{inner}</td></tr></table>')


def parse_blocks(text: str) -> list:
    """[(kind, payload)] kinds: title, h2, h3, p, ul, ol, note, rule, rows, facts."""
    blocks, para = [], []

    def flush():
        if para:
            blocks.append(("p", " ".join(para)))
            para.clear()

    def push(kind, item):
        flush()
        if blocks and blocks[-1][0] == kind and kind in ("ul", "ol", "rows"):
            blocks[-1][1].append(item)
        elif kind in ("ul", "ol", "rows"):
            blocks.append((kind, [item]))
        else:
            blocks.append((kind, item))

    for raw in (text or "").replace("\r\n", "\n").split("\n"):
        line = raw.strip()
        if not line:
            flush()
            continue
        if line.startswith("#") and not line.startswith("# #"):
            n = len(line) - len(line.lstrip("#"))
            push({1: "title", 2: "h2"}.get(n, "h3"), line[n:].strip())
        elif line in ("---", "***"):
            push("rule", "")
        elif line.startswith("~"):
            push("facts", line[1:].strip())
        elif line.startswith(">"):
            push("note", line[1:].strip())
        elif re.match(r"^[-*•]\s+", line):
            push("ul", re.sub(r"^[-*•]\s+", "", line))
        elif re.match(r"^\d+[.)]\s+", line):
            push("ol", re.sub(r"^\d+[.)]\s+", "", line))
        elif " :: " in line:
            k, v = line.split(" :: ", 1)
            push("rows", (k.strip(), v.strip()))
        else:
            para.append(line)
    flush()
    return blocks


def render_blocks(blocks: list) -> str:
    out = []
    for kind, data in blocks:
        if kind == "title":
            out.append(f'<table width="100%" cellspacing="0" cellpadding="14" style="margin-bottom:12px;"><tr>'
                       f'<td style="background-color:{C_NOTE}; border-bottom:3px solid {C_ACCENT};">'
                       f'<span style="font-size:26px; font-weight:bold; color:{C_TITLE};">{inline(data)}</span>'
                       f'</td></tr></table>')
        elif kind == "h2":
            out.append(f'<p style="margin-top:16px; margin-bottom:6px;"><span style="font-size:19px; '
                       f'font-weight:bold; color:{C_ACCENT};">&#9679;&nbsp;{inline(data)}</span></p>')
        elif kind == "h3":
            out.append(f'<p style="margin-top:10px; margin-bottom:3px;"><span style="font-size:16px; '
                       f'font-weight:bold; color:{C_TITLE};">{inline(data)}</span></p>')
        elif kind == "p":
            out.append(f'<p style="margin-top:2px; margin-bottom:8px; font-size:15px; color:{C_TEXT};">{inline(data)}</p>')
        elif kind == "ul":
            items = "".join(f'<li style="margin-bottom:4px;">{inline(i)}</li>' for i in data)
            out.append(f'<ul style="font-size:15px; color:{C_TEXT}; margin-top:2px;">{items}</ul>')
        elif kind == "ol":
            items = "".join(f'<li style="margin-bottom:4px;">{inline(i)}</li>' for i in data)
            out.append(f'<ol style="font-size:15px; color:{C_TEXT}; margin-top:2px;">{items}</ol>')
        elif kind == "note":
            out.append(_card(f'<span style="font-size:15px; color:{C_TITLE};">&#128161;&nbsp;{inline(data)}</span>',
                             edge=C_ACCENT, bg=C_NOTE))
        elif kind == "rule":
            out.append(f'<hr style="color:{C_CARD_EDGE};">')
        elif kind == "facts":
            out.append(f'<p align="center" style="margin-top:2px; margin-bottom:10px; font-size:14px; color:{C_MUTED};">'
                       f'{inline(data)}</p>')
        elif kind == "rows":
            rows = []
            has_icons = any(k.startswith("[icon:") for k, _v in data)
            for k, v in data:
                icon = re.match(r"\[icon:([\w-]+)\]\s*", k)
                pic = ""
                if icon:
                    f = Path(INFO_DIR) / "icons" / f"{icon.group(1)}.png"
                    if f.is_file():
                        pic = f'<img src="{f.as_uri()}" width="40" height="40">'
                    k = k[icon.end():]
                cell = f'<td width="52" style="padding:5px;">{pic}</td>' if has_icons else ""
                rows.append(f'<tr>{cell}'
                            f'<td width="28%" style="color:{C_MUTED}; font-size:15px; padding:5px;">{inline(k)}</td>'
                            f'<td style="color:{C_TITLE}; font-size:16px; font-weight:bold; padding:5px;">{inline(v)}</td></tr>')
            out.append(f'<table width="100%" cellspacing="0" cellpadding="4" style="margin-bottom:8px;">{"".join(rows)}</table>')
    return "".join(out)


_LINK_ONLY = re.compile(r"(?P<url>(?:https?://|www\.)[^\s<>\"]+[^\s<>\".,;:!?)\]])|(?P<mail>[\w.+-]+@[\w-]+(?:\.[\w-]+)+)")


def description_html(text: str, color: str = "#7fd0ff") -> str:
    """Plain video description -> HTML where every web address and e-mail address is a link and the line breaks stay
    (the Details window of the Archive / Library)."""
    lines = []
    for line in (text or "").replace("\r\n", "\n").split("\n"):
        out, pos = [], 0
        for m in _LINK_ONLY.finditer(line):
            out.append(html.escape(line[pos:m.start()]))
            if m.group("url"):
                u = m.group("url")
                href = u if u.lower().startswith("http") else "https://" + u
                out.append(f'<a href="{html.escape(href, quote=True)}" style="color:{color};">{html.escape(u)}</a>')
            else:
                a = m.group("mail")
                out.append(f'<a href="mailto:{a}" style="color:{color};">{a}</a>')
            pos = m.end()
        out.append(html.escape(line[pos:]))
        lines.append("".join(out))
    return "<br>".join(lines)


def scale_html(html_text: str, scale: float) -> str:
    """Multiplies every font-size of the page by `scale` (the info page follows the size of the work area)."""
    if abs(scale - 1.0) < 0.01:
        return html_text
    return re.sub(r"font-size:\s*(\d+)px", lambda m: f"font-size:{max(9, round(int(m.group(1)) * scale))}px", html_text)


def page_html(body: str, direction: str = "ltr") -> str:
    return (f'<html><body dir="{direction}" style="background-color:transparent; color:{C_TEXT}; '
            f'font-family:\'Segoe UI\', Tahoma, Arial;">{body}</body></html>')


def render_text(text: str, direction: str = "ltr") -> str:
    return page_html(render_blocks(parse_blocks(text)), direction)


# ----------------------------------------------------------------------
# local info files
# ----------------------------------------------------------------------
INFO_FILES = {"help": "help", "about": "aboutus", "contact": "contactus", "donate": "donate"}


def info_path(kind: str, lang: str, folder: Path = INFO_DIR) -> Path | None:
    """assets/info/<name>.<lang>.txt, else <name>.en.txt, else <name>.txt (None when nothing exists)."""
    name = INFO_FILES.get(kind, kind)
    for cand in (f"{name}.{lang}.txt", f"{name}.en.txt", f"{name}.txt"):
        p = Path(folder) / cand
        if p.is_file():
            return p
    return None


def load_info(kind: str, lang: str, folder: Path = INFO_DIR) -> str:
    p = info_path(kind, lang, folder)
    if p is None:
        return ""
    try:
        return p.read_text(encoding="utf-8-sig").replace("{version}", APP_VERSION)
    except OSError:
        return ""


def load_about(lang: str, folder: Path = INFO_DIR) -> str:
    """The About us page = about us + contact us + donate (one tab). The titles of the last two become sections."""
    parts = []
    for i, kind in enumerate(("about", "contact", "donate")):
        text = load_info(kind, lang, folder)
        if not text:
            continue
        if i:
            text = re.sub(r"^#\s+", "## ", text.lstrip(), count=1)
        parts.append(text.strip())
    return "\n\n".join(parts)


# ----------------------------------------------------------------------
# reviews (the rating sheet through the Apps Script, or reviews.txt of the online folder)
# ----------------------------------------------------------------------
def _rating_of(field: str):
    f = field.strip()
    stars = f.count("★") or f.count("*")
    if stars and not re.search(r"[A-Za-z0-9]", f.replace("*", "")):
        return float(min(5, stars))
    m = re.fullmatch(r"([0-5](?:[.,]\d)?)(?:\s*(?:/|out of)\s*5)?(?:\s*stars?)?", f, re.I)
    return float(m.group(1).replace(",", ".")) if m else None


def _split_row(line: str) -> list:
    for sep in ("\t", "|", ";"):
        if sep in line:
            return [x.strip() for x in line.split(sep)]
    try:
        return [x.strip() for x in next(csv.reader(io.StringIO(line)))]
    except (csv.Error, StopIteration):
        return [line.strip()]


def parse_reviews(text: str) -> list:
    """-> [{"name", "rating" (0 when unknown), "comment", "date"}], newest first when dates are sortable.
    Accepted: one review per line 'name | rating | comment | date' (also tab, ';' or csv; the columns may be in any
    order: the number 0-5 / stars is the rating, a date is the date, the first text is the name, the rest the comment), or blocks
    separated by a blank line with lines 'Name: ...', 'Rating: ...', 'Comment: ...', 'Date: ...'."""
    text = (text or "").replace("\r\n", "\n").strip()
    out = []
    if re.search(r"^\s*(name|rating|comment|review|date)\s*[:=]", text, re.I | re.M):
        for blk in re.split(r"\n\s*\n", text):
            d = {"name": "", "rating": 0.0, "comment": "", "date": ""}
            for line in blk.splitlines():
                m = re.match(r"\s*(name|rating|stars|comment|review|date)\s*[:=]\s*(.*)", line, re.I)
                if not m:
                    d["comment"] = (d["comment"] + " " + line.strip()).strip()
                    continue
                k, v = m.group(1).lower(), m.group(2).strip()
                if k == "name":
                    d["name"] = v
                elif k in ("rating", "stars"):
                    d["rating"] = _rating_of(v) or 0.0
                elif k == "date":
                    d["date"] = v
                else:
                    d["comment"] = (d["comment"] + " " + v).strip()
            if d["name"] or d["comment"]:
                out.append(d)
        return out
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        fields = [f for f in _split_row(line) if f != ""]
        if not fields:
            continue
        if fields[0].lower() in ("name", "timestamp", "date") and len(fields) > 1 and out == []:
            if all(not re.search(r"\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}", f) for f in fields):
                continue                                    # header row of a sheet export
        d = {"name": "", "rating": 0.0, "comment": "", "date": ""}
        rest = []
        for f in fields:
            r = _rating_of(f)
            if r is not None and not d["rating"] and len(f) <= 12:
                d["rating"] = r
            elif re.search(r"\d{1,4}[/.-]\d{1,2}[/.-]\d{1,4}", f) and len(f) <= 28 and not d["date"]:
                d["date"] = f
            else:
                rest.append(f)
        if len(rest) == 1:
            d["comment"] = rest[0]
        elif rest:                                          # first text = name, the rest = comment (Google form order)
            d["name"] = rest[0]
            d["comment"] = " ".join(rest[1:])
        if d["name"] or d["comment"]:
            out.append(d)
    return out


def stars_html(rating: float) -> str:
    n = int(round(max(0.0, min(5.0, rating))))
    return (f'<span style="color:{C_ACCENT}; font-size:18px;">{"&#9733;" * n}</span>'
            f'<span style="color:#9fbfe8; font-size:18px;">{"&#9734;" * (5 - n)}</span>')


def render_reviews(reviews: list, title: str, summary: str, empty: str, direction: str = "ltr") -> str:
    """HTML of the reviews page: title, average, one card per review."""
    body = [render_blocks([("title", title)])]
    if not reviews:
        body.append(_card(f'<span style="font-size:16px; color:{C_TITLE};">{html.escape(empty)}</span>'))
        return page_html("".join(body), direction)
    rated = [r["rating"] for r in reviews if r["rating"]]
    if rated:
        avg = sum(rated) / len(rated)
        body.append(_card(f'<span style="font-size:30px; font-weight:bold; color:{C_TITLE};">{avg:.1f}</span>&nbsp;&nbsp;'
                          f'{stars_html(avg)}&nbsp;&nbsp;<span style="font-size:14px; color:{C_MUTED};">'
                          f'{html.escape(summary.format(n=len(reviews)))}</span>', edge=C_ACCENT, bg=C_NOTE))
    for r in reviews:
        head = f'<b style="font-size:17px; color:{C_TITLE};">{html.escape(r["name"] or "-")}</b>'
        if r["rating"]:
            head += f'&nbsp;&nbsp;{stars_html(r["rating"])}'
        if r["date"]:
            head += f'&nbsp;&nbsp;<span style="font-size:13px; color:{C_MUTED};">{html.escape(r["date"])}</span>'
        comment = f'<br><span style="font-size:15px; color:{C_TEXT};">{inline(r["comment"])}</span>' if r["comment"] else ""
        body.append(_card(head + comment))
    return page_html("".join(body), direction)
