# TubeArchive Pro 2.3.1 - developer documentation

TubeArchive Pro is a Windows desktop program (Python 3.10+, PySide6 / Qt, yt-dlp, ffmpeg) that downloads videos, audio and playlists,
keeps an archive and a favorites library, keeps playlists in sync, and talks to an online GitHub folder (ads, versions, statistics) and a
Google Apps Script (ratings and install register).

| Document | Content |
|---|---|
| `FILE_STRUCTURE.md` | Every file of the project and its purpose |
| `MODULES.md` | For every Python file: version history, classes, functions / methods and what they do |
| `DATA_FILES.md` | Every file the program writes, and the formats of the online files |
| `ARCHITECTURE.md` | How the parts work together (start-up, download, sync, updates, statistics) |

## Conventions (must be kept)
1. Every code file starts with a header with its own version history (`# TubeArchive Pro | Version x.y.z | File: ...`).
2. Every visible text is a numbered message: `app/msg.py` (`M.NAME = "MSG_nnn"`) and the texts in `data/languages/<code>.json`.
   English and Arabic are always complete; a message missing in another language shows the English text. `tools/dev_addmsg.py` adds one.
3. No code in the window classes that belongs to the engine: engine = `app/*.py` (no Qt, testable), screens = `app/ui/*.py`.
4. `requirements.txt` lists every package. Tests: `python3 -m unittest discover -s tests` (Qt is replaced by `tests/qt_stub.py`,
   yt-dlp by `tests/fake_ytdlp.py`).
5. User data never goes into the program folder: `%APPDATA%\TubeArchivePro` (installed) - see `app/paths.py`.

## Run / build
- Run: `pip install -r requirements.txt` then `python main.py`.
- Build the program and the setup on Windows: `build/BUILD_GUIDE.md` (PyInstaller one-folder build + Inno Setup).
- Rebuild this documentation: `python tools/gen_docs.py docs`.
