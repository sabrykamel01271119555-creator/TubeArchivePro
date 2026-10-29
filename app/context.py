# =============================================================================
# TubeArchive Pro  |  Version 2.0.1  |  File: app/context.py
# Version history of this file:
#   2.3.2 - failed (videos that could not be downloaded)
#   2.0.1 - downloads (the download manager / queue shared by the pages); online check result; update_asked
#   1.0.12 - New: session_bytes
#   1.0.11 - New: sync
#   1.0.9 - New: favorites
#   1.0.6 - No functional change (version header added)
#   1.0.0 - 1.0.5 - first version and earlier fixes (see CHANGELOG.md)
# =============================================================================
"""One object that holds everything loaded at start-up."""
from .failed import FailedManager
from .favorites import FavoritesManager
from .feedback import FeedbackManager
from .history import HistoryManager
from .i18n import LanguageManager
from .resources import ResourceManager
from .settings import SettingsManager
from .sync import SyncManager


class AppContext:
    def __init__(self):
        self.settings = SettingsManager()
        self.lang = LanguageManager()
        self.history = HistoryManager()
        self.resources = ResourceManager()
        self.feedback = FeedbackManager()
        self.favorites = FavoritesManager()
        self.sync = SyncManager()
        self.failed = FailedManager()                 # 2.3.2: videos kept for 'Later'
        self.downloads = None             # DownloadManager (queue), created by the first page that needs it
        self.online = {}                  # result of the online check made while the splash screen is shown
        self.online_ready = False
        self.update_asked = False         # the 'new version' question is asked once per run
        self.session_bytes = 0.0          # (kept for old code) the queue now counts the downloaded bytes
        self.downloads = None             # DownloadManager (information + download queue), created by the first page
