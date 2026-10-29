"""Creates build\\TubeArchivePro.ico from the program's own icon (app/ui/icons.make_app_icon) when it does not exist yet.
Version 2.3.2.  Sizes 16, 32, 48, 64, 128, 256 (PNG inside the .ico).  Used by build.bat; run:  python build\\make_icon.py"""
import os
import struct
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
OUT = ROOT / "build" / "TubeArchivePro.ico"
SIZES = (16, 32, 48, 64, 128, 256)


def main() -> int:
    if OUT.exists() and "--force" not in sys.argv:
        print("  OK       build\\TubeArchivePro.ico exists (use --force to make it again)")
        return 0
    from PySide6.QtCore import QBuffer, QByteArray, QIODevice
    from PySide6.QtWidgets import QApplication
    from app.ui.icons import make_app_icon
    app = QApplication.instance() or QApplication([])      # noqa: F841  (pixmaps need it)
    images = []
    for s in SIZES:
        ba = QByteArray()
        buf = QBuffer(ba)
        buf.open(QIODevice.WriteOnly)
        make_app_icon(s).save(buf, "PNG")
        images.append((s, bytes(ba)))
    head = struct.pack("<HHH", 0, 1, len(images))
    offset = 6 + 16 * len(images)
    entries, data = b"", b""
    for s, png in images:
        entries += struct.pack("<BBBBHHII", s % 256, s % 256, 0, 0, 1, 32, len(png), offset + len(data))
        data += png
    OUT.write_bytes(head + entries + data)
    print(f"  created  build\\TubeArchivePro.ico ({len(images)} sizes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
