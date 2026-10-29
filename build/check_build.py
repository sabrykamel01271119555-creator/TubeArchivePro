"""Checks (and prepares) everything the build needs.  Used by build.bat.  Exit code 0 = ready, 1 = something is missing.
Version 2.3.2.  Run from the project folder:  python build\\check_build.py"""
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from app.paths import APP_VERSION, TOOLS_DIR  # noqa: E402
from app.resources import find_tool  # noqa: E402

NEEDED = ("yt-dlp", "ffmpeg", "ffprobe")


def main() -> int:
    ok = True
    print(f"TubeArchive Pro version {APP_VERSION}")
    for name in NEEDED:
        exe = TOOLS_DIR / f"{name}.exe"
        if not exe.is_file():
            found = find_tool(name)                      # e.g. tools\\ffmpeg-...-full_build\\bin\\ffmpeg.exe
            if found and Path(found).suffix.lower() == ".exe":
                shutil.copy2(found, exe)
                print(f"  copied {name}.exe from {found}")
        if exe.is_file():
            print(f"  OK       tools\\{name}.exe  ({exe.stat().st_size // (1024 * 1024)} MB)")
        else:
            ok = False
            print(f"  MISSING  tools\\{name}.exe   (see build\\BUILD_GUIDE.md, step 3)")
    if not (ROOT / "build" / "TubeArchivePro.ico").is_file():
        print("  note     build\\TubeArchivePro.ico not found: the program and the setup will use the default icon")
    for rel in ("data/languages/en.json", "data/languages/ar.json", "data/config/default_settings.json",
                "data/downloads_baseline.txt", "assets/info"):
        if not (ROOT / rel).exists():
            ok = False
            print(f"  MISSING  {rel}")
    try:
        import PySide6, psutil, PyInstaller  # noqa: F401,E401
        print("  OK       PySide6, psutil, PyInstaller are installed")
    except ImportError as exc:
        ok = False
        print(f"  MISSING  python package: {exc}   (build.bat runs: pip install -r requirements.txt)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
