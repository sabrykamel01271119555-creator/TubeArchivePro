# =============================================================================
# TubeArchive Pro  |  Version 2.3.1  |  File: app/ui/info_page.py
# Version history of this file:
#   2.3.1 - About us shows about + contact + donate; Reviews = the real ratings of the sheet (Apps Script action=reviews)
#   2.0.2 - Text size follows the work area (FontScaler + scale_html)
#   2.0.1 - Created: work-area page for the five links of the side menu corner (Reviews, Help, About us, Contact us,
#           Donate). Help / About / Contact / Donate = local text files (assets/info); Reviews = reviews.txt
#           downloaded from the online folder (last copy is used when offline).
# =============================================================================
"""One page that shows the text of a link of the side-menu corner as formatted HTML (app/infodoc.py)."""
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QTextBrowser, QVBoxLayout, QWidget

from ..ads import TextFetcher
from ..context import AppContext
from ..infodoc import load_about, load_info, parse_reviews, render_reviews, render_text, scale_html
from ..stats import ReviewsFetcher, load_reviews
from ..msg import M
from .widgets import FontScaler

TITLES = {"reviews": M.LNK_REVIEWS, "help": M.LNK_HELP, "about": M.LNK_ABOUT,
          "contact": M.LNK_CONTACT, "donate": M.LNK_DONATE}
REVIEWS_FILE = "reviews.txt"


class InfoPage(FontScaler, QWidget):
    def __init__(self, ctx: AppContext):
        super().__init__()
        self.ctx = ctx
        self.t = ctx.lang.tr
        self.kind = ""
        self._token = 0
        self._html = ""                   # the page as rendered at scale 1 (re-scaled when the work area changes)
        v = QVBoxLayout(self)
        v.setContentsMargins(20, 14, 20, 12)
        v.setSpacing(8)
        head = QHBoxLayout()
        self.title = QLabel("")
        self.title.setObjectName("pageTitle")
        self.refresh_btn = QPushButton(self.t(M.INFO_REFRESH))
        self.refresh_btn.setObjectName("secondary")
        self.refresh_btn.setCursor(Qt.PointingHandCursor)
        self.refresh_btn.clicked.connect(self._load_reviews)
        head.addWidget(self.title, 1)
        head.addWidget(self.refresh_btn)
        v.addLayout(head)
        self.status = QLabel("")
        self.status.setObjectName("setStatus")
        v.addWidget(self.status)
        frame = QFrame()
        frame.setObjectName("infoBox")
        fl = QVBoxLayout(frame)
        fl.setContentsMargins(6, 6, 6, 6)
        self.view = QTextBrowser()
        self.view.setObjectName("infoView")
        self.view.setFrameShape(QFrame.NoFrame)
        self.view.setOpenLinks(False)
        self.view.anchorClicked.connect(lambda url: QDesktopServices.openUrl(QUrl(url)))
        fl.addWidget(self.view)
        v.addWidget(frame, 1)
        self.fetcher = TextFetcher(self)
        self.fetcher.done.connect(self._reviews_done)
        self.sheet = ReviewsFetcher(self)                 # 2.3.1: the ratings of the sheet
        self.sheet.done.connect(self._sheet_done)

    def _show_html(self, html_text: str):
        self._html = html_text
        self.view.setHtml(scale_html(html_text, self._fs_scale or 1.0))

    def on_font_scale(self, s: float):
        if self._html:
            self.view.setHtml(scale_html(self._html, s))

    # ------------------------------------------------------------------
    def _direction(self) -> str:
        return "rtl" if self.ctx.lang.is_rtl else "ltr"

    def show_kind(self, kind: str):
        """Called by the main window when a link of the corner is clicked."""
        if kind in ("contact", "donate"):                 # one tab: About us
            kind = "about"
        self.kind = kind
        self.title.setText(self.t(TITLES.get(kind, M.LNK_HELP)))
        self.status.setText("")
        self.refresh_btn.setVisible(kind == "reviews")
        if kind == "reviews":
            self._load_reviews()
            return
        text = load_about(self.ctx.lang.code) if kind == "about" else load_info(kind, self.ctx.lang.code)
        if text:
            self._show_html(render_text(text, self._direction()))
        else:
            self._show_html(render_text("# " + self.t(TITLES.get(kind, M.LNK_HELP)) + "\n" + self.t(M.INFO_MISSING),
                                         self._direction()))

    def _folder_url(self) -> str:
        st = self.ctx.settings
        return str(st.get("online_folder_url", "") or st.defaults.get("online_folder_url", "")).strip()

    def _script_url(self) -> str:
        url = str(self.ctx.settings.get("feedback_form_url", "") or "").strip()
        return url if "script.google.com/macros" in url else ""

    def _load_reviews(self):
        self.status.setText(self.t(M.INFO_LOADING))
        self.refresh_btn.setEnabled(False)
        self._show_html(render_text("# " + self.t(M.LNK_REVIEWS) + "\n" + self.t(M.INFO_LOADING), self._direction()))
        if self._script_url():                                   # the real ratings written by the users (the sheet)
            self.sheet.fetch(self._script_url())
            return
        self.fetcher.fetch("reviews", self._folder_url(), REVIEWS_FILE, REVIEWS_FILE)

    def _sheet_done(self, r: dict):
        self.refresh_btn.setEnabled(True)
        if self.kind != "reviews":
            return
        t = self.t
        rows = r.get("reviews")
        if rows is None:                                         # offline: the last copy
            rows = load_reviews()
            self.status.setText(t(M.INFO_CACHED) if rows else t(M.INFO_FAILED))
        else:
            self.status.setText("")
        user = t(M.INFO_USER)
        reviews = [{"name": (f"{user} · {x['country']}" if x.get("country") else user), "rating": float(x["rating"]),
                    "comment": x.get("feedback", ""), "date": str(x.get("date", ""))[:10]} for x in rows or []]
        self._show_html(render_reviews(reviews, t(M.LNK_REVIEWS), t(M.INFO_REVIEWS_SUMMARY), t(M.INFO_REVIEWS_EMPTY),
                                       self._direction()))

    def _reviews_done(self, kind: str, r: dict):
        if kind != "reviews":
            return
        self.refresh_btn.setEnabled(True)
        if self.kind != "reviews":
            return
        t = self.t
        text = r.get("text") or ""
        if not text:
            self.status.setText(t(M.INFO_FAILED))
        elif r.get("cached"):
            self.status.setText(t(M.INFO_CACHED))
        else:
            self.status.setText("")
        self._show_html(render_reviews(parse_reviews(text), t(M.LNK_REVIEWS), t(M.INFO_REVIEWS_SUMMARY),
                                       t(M.INFO_FAILED) if r.get("error") and not text else t(M.INFO_REVIEWS_EMPTY),
                                       self._direction()))
