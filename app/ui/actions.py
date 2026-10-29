# =============================================================================
# TubeArchive Pro  |  Version 2.2.8  |  File: app/ui/actions.py
# Version history of this file:
#   2.2.8 - passes the category icons to the Add to Favorites window
#   1.0.9 - Created: helpers shared by the New Download and Downloads pages
#           (quality badge, reveal file in Explorer, 'Add to favorites' flow, dialog with blurred background)
# =============================================================================
"""Small actions used by more than one page."""
import os
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QDialog

from ..context import AppContext
from ..downloader import is_audio
from ..msg import M
from .dialogs import FavoriteDialog


def badge_text(quality: str, fmt: str) -> str:
    """Text of the small quality badge (success window)."""
    if is_audio(fmt):
        return fmt.upper()
    if quality == "4K":
        return "4K"
    if quality.endswith("p") and quality[:-1].isdigit():
        return "HD" if int(quality[:-1]) >= 720 else "SD"
    return "HD"


def card_tag(quality: str, fmt: str) -> str:
    """Badge on the thumbnail of the Downloads page: 4K, 2K, Full HD, HD, 480p, MP3 ..."""
    if is_audio(fmt):
        return fmt.upper()
    if quality in ("4K", "8K"):
        return quality
    if quality.endswith("p") and quality[:-1].isdigit():
        h = int(quality[:-1])
        return "2K" if h >= 1440 else "Full HD" if h >= 1080 else "HD" if h >= 720 else quality
    return "HD" if not quality else quality


def reveal_file(path: str):
    """Open the folder and select the file (Explorer); other systems just open the folder."""
    if sys.platform == "win32":
        subprocess.Popen(f'explorer /select,"{os.path.normpath(path)}"')
    else:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(path).parent)))


def exec_blurred(widget, dialog) -> int:
    """Run a dialog while the main window is blurred (like the other glass windows)."""
    win = widget.window()
    blur = getattr(win, "_blur_background", None)
    if blur:
        blur(True)
    try:
        return dialog.exec()
    finally:
        if blur:
            blur(False)


def add_to_favorites(ctx: AppContext, rec: dict, parent, blur: bool = False) -> bool:
    """Ask for a category (existing or new) and put the video in it. True = added."""
    fav, t = ctx.favorites, ctx.lang.tr
    default = t(M.FAV_DEFAULT)
    cats = list(fav.categories)
    cur = fav.category_of(rec["id"])
    if cur in cats:                                   # the current category is offered first
        cats.remove(cur)
        cats.insert(0, cur)
    dlg = FavoriteDialog(ctx.lang, cats, default, parent, icons=fav.icons)
    ok = (exec_blurred(parent, dlg) if blur else dlg.exec()) == QDialog.Accepted
    if not ok or not dlg.category:
        return False
    fav.add(rec["id"], dlg.category)
    return True
