# =============================================================================
# TubeArchive Pro  |  Version 2.3.1  |  File: tools/gen_docs.py
# Version history of this file:
#   2.3.0 - Created: builds the documentation (file structure, purpose of every file, its classes and functions)
# =============================================================================
"""python3 tools/gen_docs.py [output folder]     (default: TubeArchivePro_docs_build next to the project)

Reads every .py file with the ast module (nothing is imported or run), takes the module docstring, the version history header,
every class / function / method with the first line of its docstring, and adds the hand-written PURPOSE of each file below.
Writes FILE_STRUCTURE.md, MODULES.md (generated) + README.md, ARCHITECTURE.md, DATA_FILES.md (hand-written, tools/docs_src/)
"""
import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PURPOSE = {
 "main.py": "Program start: creates the Qt application, shows the splash screen, runs the loader thread, opens the main window.",
 "app/__init__.py": "Marks the folder as the `app` package.",
 "app/paths.py": "Every folder / file location (program folder = read only, user data folder = %APPDATA%\\\\TubeArchivePro when installed), APP_VERSION, FROZEN.",
 "app/context.py": "AppContext: the one object that holds settings, language, resources, history, favorites, sync, feedback, download manager.",
 "app/settings.py": "Reads / writes the default and the user settings files (data/config/*.json).",
 "app/i18n.py": "Language manager: finds data/languages/*.json, loads a language, translates message ids, English fallback.",
 "app/msg.py": "The numbered message ids (class M): every visible text is MSG_nnn; the texts live in the language files.",
 "app/loader.py": "Start-up worker thread: loads settings, language, resources, history; reads the online folder, registers the install, fetches rating numbers.",
 "app/resources.py": "Finds yt-dlp / ffmpeg (user tools folder first), ads and owner pictures.",
 "app/ads.py": "The online GitHub folder: ad list, ad pictures, newest program version, users per version, counter cache; opens encrypted files.",
 "app/stats.py": "Numbers of the splash screen: users per version (register + old numbers) and the rating average (Apps Script GET ?action=stats).",
 "app/feedback.py": "Rating storage, install id / install register, JSON post to the Apps Script web app (or a Google form).",
 "app/secure.py": "Light encryption (HMAC-SHA256 stream + MAC) for the online text files.",
 "app/toolupdate.py": "Checks and installs new yt-dlp / ffmpeg builds into the user tools folder (no Qt, testable).",
 "app/downloader.py": "yt-dlp command lines, link analysis (video / playlist), information fetch, size estimates, error mapping, formats and qualities.",
 "app/dlqueue.py": "The download queue: one yt-dlp process per video, concurrency, pause / resume / cancel, playlists as groups, bandwidth sharing.",
 "app/download_manager.py": "Qt wrapper around the queue and the information reader (signals for the pages); InfoFetcher reads playlists in the background.",
 "app/history.py": "History of finished downloads (records, videos of a playlist, thumbnails, duplicate search by video id / playlist id).",
 "app/favorites.py": "Favorite categories and which video is in which category (icons per category).",
 "app/sync.py": "Playlist sync schedule (daily / weekly / monthly / yearly, last / next sync, enabled).",
 "app/sounds.py": "Sound effects (click, tab, done, warning): QSoundEffect with winsound fallback, on / off setting.",
 "app/sysmon.py": "System numbers for the gauges: network speed, disk activity, free space, process memory.",
 "app/infodoc.py": "Help / About / Contact / Donate texts (local files, simple markup -> HTML).",
 "app/demo.py": "Sample rows shown before the first real download (demo data).",
 "app/ui/__init__.py": "Marks the folder as the `app.ui` package.",
 "app/ui/main_window.py": "The main window: title bar, side menu, pages, gauges, ads, tray icon, exit flow, blurred background, update controller.",
 "app/ui/splash.py": "Splash screen: slow users counter, rating stars, bar that fills version by version.",
 "app/ui/theme.py": "The global style sheet (QSS) and glow helper.",
 "app/ui/widgets.py": "Custom widgets: navigation buttons, banners, toggle switch, arrow combo box, elided label, gauges, fade between pages.",
 "app/ui/icons.py": "All icons are drawn with QPainter (app icon, play, warning, check, sync, star, emoji icons, thumbnails).",
 "app/ui/dialogs.py": "Every glass dialog: message, choice, busy (with info), sync, sync-done, playlist setup, rating, favorite, updates, update progress, exit warning.",
 "app/ui/actions.py": "Shared actions of the pages: exec_blurred, add to favorites, reveal file, badge text.",
 "app/ui/new_download_page.py": "New Download page: link check, playlist question for video links, formats / qualities, start, queue, history records, sync start.",
 "app/ui/downloads_page.py": "Downloads page: live list of running / waiting / finished files and playlists with their controls.",
 "app/ui/library_page.py": "Archive and Library pages: cards of what was downloaded, filters, sorting, favorites, per-playlist sync button.",
 "app/ui/sync_page.py": "Playlist Sync page: table of synchronized playlists, switches, schedules, Sync now / Sync all.",
 "app/ui/sync_flow.py": "Sync controller: checks a playlist, shows the busy / sync / nothing-new windows, background sync of due playlists.",
 "app/ui/update_flow.py": "Update controller: Updates window, tool update progress, check at start-up / from Settings / after a failed download.",
 "app/ui/settings_page.py": "Settings page: folders, quality, connection, notifications, sounds, usage sharing, favorites categories, language.",
 "app/ui/info_page.py": "Help / About us / Contact us / Donate pages.",
 "app/ui/pages.py": "Small shared page helpers and placeholders.",
 "owner_tools/feedback_apps_script.gs": "Google Apps Script web app for your sheet: registers installs, stores ratings, returns users / rating statistics.",
 "owner_tools/encrypt_online.py": "Owner tool: encrypts / decrypts the text files of the online folder.",
 "tools/dev_addmsg.py": "Developer helper: adds a numbered message to msg.py and the language files.",
 "tools/gen_docs.py": "Builds this documentation from the source code.",
 "build/TubeArchivePro.spec": "PyInstaller recipe (one-folder program).",
 "build/build.bat": "One click: tests -> PyInstaller -> Inno Setup.",
 "build/check_build.py": "Checks that everything the build needs is present.",
 "build/installer.iss": "Inno Setup script: wizard languages, components (program languages), files, shortcuts, update check, uninstall.",
 "build/installer_settings.iss": "Owner settings of the installer (name, publisher, website, GitHub repository).",
 "build/BUILD_GUIDE.md": "How to build the .exe and the setup on Windows.",
 "build/INSTALL_INFO.txt": "Text shown by the setup before installation.",
 "build/LICENSES.txt": "Licenses of the included tools (yt-dlp, ffmpeg, Qt).",
 "PROGRESS_*.md": "Notes of an earlier development step.",
 "requirements.txt": "Python packages needed (PySide6 ...).",
 "CHANGELOG.md": "What changed in each version.",
 "README.md": "Short description and how to run.",
 "FEATURE_MAP.md": "Which feature lives in which file / message numbers.",
 "GITHUB_SETUP.md": "How to prepare the GitHub repository / online folder.",
 "PROJECT_GUIDE.md": "Conventions of the project (headers, messages, tests, delivery).",
 "data/config/default_settings.json": "Factory settings (the user's own values are saved in current_settings.json).",
 "data/downloads_baseline.txt": "Old download counter numbers used offline.",
 "data/splash_baseline.json": "Users per version shown on the splash screen before the first online check.",
 "assets/sounds/*.wav": "Sound effects.",
 "assets/owner/*": "Owner banner and channel banner pictures.",
 "assets/info/*.txt": "Help, About us, Contact us, Donate texts in English and Arabic.",
 "data/languages/*.json": "One file per interface language (meta + messages MSG_001...).",
 "tests/*": "Automatic tests (python3 -m unittest discover -s tests); qt_stub.py replaces Qt, fake_ytdlp.py replaces yt-dlp.",
}

SKIP = {"__pycache__", ".venv", ".git", "cache", "dist", "work", "output"}


def purpose_of(rel: str) -> str:
    if rel in PURPOSE:
        return PURPOSE[rel]
    for pat, text in PURPOSE.items():
        if "*" in pat and Path(rel).match(pat):
            return text
    return ""


def humanize(name: str) -> str:
    """No docstring: the words of the name (`_on_ready` -> 'on ready')."""
    return "*" + " ".join(w for w in re.split(r"[_.]+", name.split(".")[-1]) if w) + "*"


def first_line(doc):
    return (doc or "").strip().splitlines()[0].strip() if doc else ""


def describe(path: Path):
    src = path.read_text(encoding="utf-8")
    tree = ast.parse(src)
    header = [l[1:].strip() for l in src.splitlines()[:40] if l.startswith("#") and re.match(r"#\s+\d", l)]
    out = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            out.append(("class", node.name, first_line(ast.get_docstring(node)), node.lineno))
            for sub in node.body:
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    out.append(("method", f"{node.name}.{sub.name}", first_line(ast.get_docstring(sub)), sub.lineno))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out.append(("function", node.name, first_line(ast.get_docstring(node)), node.lineno))
    return first_line(ast.get_docstring(tree)), header, out, len(src.splitlines())


def files():
    for p in sorted(ROOT.rglob("*")):
        rel = p.relative_to(ROOT)
        if p.is_file() and not (set(rel.parts) & SKIP) and p.suffix != ".pyc" and "docs" not in rel.parts[:1] and "docs_src" not in rel.parts:
            if rel.parts[:2] in (("assets", "ads"),) or rel.parts[:3] == ("assets", "info", "icons"):
                continue
            yield rel.as_posix(), p


def main(out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    tree_lines, modules = [], []
    for rel, p in files():
        note = purpose_of(rel)
        tree_lines.append(f"| `{rel}` | {note or '-'} |")
        if p.suffix == ".py":
            doc, header, items, n = describe(p)
            sec = [f"## `{rel}`  ({n} lines)", "", note or doc or "", ""]
            if header:
                sec += ["Version history (newest first):", ""] + [f"- {h}" for h in header[:8]] + [""]
            if items:
                sec += ["| Kind | Name | What it does |", "|---|---|---|"]
                sec += [f"| {k} | `{name}` | {d or humanize(name)} |" for k, name, d, _ln in items]
                sec.append("")
            modules.append("\n".join(sec))
    (out_dir / "FILE_STRUCTURE.md").write_text(
        "# File structure and purpose of every file\n\n| File | Purpose |\n|---|---|\n" + "\n".join(tree_lines) + "\n", encoding="utf-8")
    (out_dir / "MODULES.md").write_text("# Modules: classes and functions\n\nGenerated by tools/gen_docs.py from the source code.\n\n"
                                       + "\n".join(modules), encoding="utf-8")
    src = Path(__file__).resolve().parent / "docs_src"
    for f in sorted(src.glob("*.md")):                       # hand-written documents
        (out_dir / f.name).write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
    print("written to", out_dir)


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent / "TubeArchivePro_docs_build")
