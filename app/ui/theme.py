# =============================================================================
# TubeArchive Pro  |  Version 2.2.7  |  File: app/ui/theme.py
# Version history of this file:
#   2.2.7 - iconBtnOff (sync button of a playlist that is not synchronised: normal border, no background)
#   2.2.6 - lit sync button is fully green
#   2.2.3 - progress bar colours by state (done / paused / failed)
#   2.2.2 - iconBtnOn (lit sync button)
#   2.0.2 - font_qss() / area_scale(): pages and windows scale their texts with the size of their area
#   2.0.2 - Back to the 1.0.14 look (the glass style of 2.0.1 is removed); keeps the styles of sideLink, counterPill, info page
#   2.0.1 - (glass style - withdrawn in 2.0.2); styles: sideLink, counterPill, info page
#   1.0.14 - Styles: slider, mini buttons, icon picker
#   1.0.12 - Styles: settings labels / status, menus
#   1.0.11 - Styles: sync window, playlist options, Playlist Sync page (status badges, ON/OFF switch)
#   1.0.10 - Combo box drop-down area 30 px (arrow is drawn by ArrowComboBox)
#   1.0.9 - Styles: Downloads page cards, icon buttons, favorite button, combo box in dialogs
#   1.0.8 - Styles for the New Download page, success window and disabled buttons
#   1.0.6 - No functional change (version header added)
#   1.0.0 - 1.0.5 - first version and earlier fixes (see CHANGELOG.md)
# =============================================================================
"""Colours and the global style sheet."""
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QGraphicsDropShadowEffect

CYAN = "#27d3ff"
BLUE = "#2f7bff"
ORANGE = "#ffb02e"


def glow(widget, color: str = CYAN, blur: int = 22):
    fx = QGraphicsDropShadowEffect(widget)
    fx.setBlurRadius(blur)
    fx.setOffset(0, 0)
    fx.setColor(QColor(color))
    widget.setGraphicsEffect(fx)


def _action_button(name, c1, c2, border):
    return f"""
    QPushButton#{name} {{
        background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 {c1}, stop:1 {c2});
        border: 1px solid {border}; border-radius: 7px; color: white;
        font-size: 15px; padding: 9px 6px; }}
    QPushButton#{name}:hover {{ border: 2px solid white; }}
    QPushButton#{name}:pressed {{ padding-top: 11px; }}"""


STYLE = """
QWidget { color: #eaf4ff; font-family: "Segoe UI", "Segoe UI Variable", Tahoma, Arial; font-size: 13px; }
QToolTip { background: #0c2a6b; color: white; border: 1px solid #27d3ff; }

#appName   { font-size: 26px; font-weight: 700; color: #f2f8ff; }
#appVer    { font-size: 11px; color: #8fb6e8; }
#winTitle  { font-size: 17px; color: #e6f1ff; }

QFrame#panel, QFrame#centerPanel {
    background: rgba(8, 28, 84, 0.50);
    border: 1px solid rgba(90, 170, 255, 0.35); border-radius: 14px; }
QFrame#sidebar { background: rgba(6, 22, 70, 0.45); border-right: 1px solid rgba(90,170,255,0.25); }

#panelTitle { font-size: 19px; color: #f0f7ff; }
#gaugeCaption { font-size: 17px; color: #f0f7ff; }
#pageTitle { font-size: 22px; font-weight: 600; color: #f0f7ff; }
#muted { color: #8fb6e8; }
#poweredBy { color: #9cc3f2; font-size: 12px; }
#poweredName { color: #eaf4ff; font-size: 20px; }
#comingSoon { font-size: 18px; color: #8fb6e8; }

QFrame#dlItem { background: rgba(70, 110, 190, 0.40); border: 1px solid rgba(120,190,255,0.55); border-radius: 10px; }
QLabel#dlTitle { font-size: 18px; color: #f4f9ff; }
QLabel#dlStat  { font-size: 15px; color: #27d3ff; }
QLabel#dlSub   { font-size: 14px; color: #bcd4f2; }
QLabel#badgeFmt { border: 1px solid #27d3ff; border-radius: 4px; padding: 0 6px; color: #27d3ff; font-size: 14px; background: rgba(5,25,80,0.5); }
QLabel#badgeQ   { border: 1px solid #ffb02e; border-radius: 4px; padding: 0 6px; color: #ffd27a; font-size: 14px; background: rgba(40,25,5,0.4); }
QProgressBar#dlBar { background: rgba(5, 20, 60, 0.85); border: none; border-radius: 4px; }
QProgressBar#dlBar::chunk { border-radius: 4px;
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #1d6bff, stop:1 #27d3ff); }

QProgressBar#dlBarTotal { background: rgba(5, 20, 60, 0.85); border: none; border-radius: 5px; }
QProgressBar#dlBarTotal::chunk { border-radius: 5px;
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #1d6bff, stop:1 #27d3ff); }
QProgressBar#dlBar[st="done"]::chunk, QProgressBar#dlBarTotal[st="done"]::chunk {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #12b85a, stop:1 #46ff9a); }
QProgressBar#dlBar[st="paused"]::chunk, QProgressBar#dlBarTotal[st="paused"]::chunk {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #d98200, stop:1 #ffc24d); }
QProgressBar#dlBar[st="failed"]::chunk { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #c4143f, stop:1 #ff5c85); }
QPlainTextEdit#log { background: rgba(2, 10, 40, 0.92); border: 1px solid rgba(90,170,255,0.4);
    border-radius: 6px; color: #38ff6a; font-family: Consolas, "Courier New", monospace; font-size: 13px; padding: 4px; }

QLineEdit, QComboBox, QSpinBox {
    background: rgba(4, 18, 60, 0.85); border: 1px solid rgba(90,170,255,0.5);
    border-radius: 8px; padding: 7px 10px; min-height: 22px; selection-background-color: #1d6bff; }
QLineEdit:focus, QComboBox:focus, QSpinBox:focus { border: 1px solid #27d3ff; }
QComboBox::drop-down { border: none; width: 30px; subcontrol-origin: padding; subcontrol-position: center right; }
QComboBox QAbstractItemView { background: #0b2466; border: 1px solid #27d3ff; selection-background-color: #1d6bff; color: white; }
QCheckBox { spacing: 8px; }
QCheckBox::indicator { width: 20px; height: 20px; border-radius: 5px; border: 1px solid #27d3ff; background: rgba(4,18,60,0.85); }
QCheckBox::indicator:checked { background: #27d3ff; }

QPushButton#primary, QPushButton#secondary {
    border-radius: 8px; padding: 9px 22px; font-size: 14px; color: white; }
QPushButton#primary { background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #2f8bff, stop:1 #1558d6); border: 1px solid #7cc4ff; }
QPushButton#secondary { background: rgba(30, 80, 170, 0.55); border: 1px solid rgba(120,190,255,0.6); }
QPushButton#primary:hover, QPushButton#secondary:hover { border: 1px solid white; }

QTableWidget { background: rgba(4,18,60,0.6); border: 1px solid rgba(90,170,255,0.4); border-radius: 10px;
    gridline-color: rgba(90,170,255,0.18); alternate-background-color: rgba(30,70,150,0.25); }
QHeaderView::section { background: rgba(20, 70, 170, 0.7); color: #eaf4ff; padding: 8px; border: none; font-size: 13px; }
QTableWidget::item:selected { background: rgba(39,211,255,0.35); }

QScrollArea { background: transparent; border: none; }
QScrollArea > QWidget > QWidget { background: transparent; }
QScrollBar:vertical { background: transparent; width: 8px; margin: 2px; }
QScrollBar::handle:vertical { background: rgba(140,190,255,0.45); border-radius: 4px; min-height: 30px; }
QScrollBar::add-line, QScrollBar::sub-line { height: 0; width: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }
""" + _action_button("btnGreen", "#2bd96f", "#119a4a", "#7dffb0") \
    + _action_button("btnOrange", "#ffb030", "#d27a00", "#ffd98a") \
    + _action_button("btnRed", "#ff2f72", "#c4104a", "#ff8fb4") \
    + _action_button("btnBlue", "#2b8cff", "#1157d2", "#8fd0ff")

STYLE += """
#dlgTitle { font-size: 34px; font-weight: 700; color: #ffffff; }
#dlgBrand { font-size: 40px; font-weight: 700; color: #ffffff; }
#dlgWarn  { font-size: 30px; font-weight: 700; color: #ff8a4d; }
#dlgText  { font-size: 21px; color: #f4f8ff; }
#dlgPill  { font-size: 20px; color: #e6eeff; background: rgba(255,255,255,0.10); border-radius: 14px; padding: 8px 26px; }
#rateSub  { font-size: 19px; color: #e6f2ff; }
#rateLabel { font-size: 20px; color: #ffffff; min-height: 28px; }
QTextEdit#feedback { background: rgba(3,14,50,0.85); border: 1px solid rgba(120,190,255,0.55); border-radius: 10px;
    color: #eaf4ff; font-size: 17px; padding: 8px; }
QPushButton#outline { background: rgba(20,70,150,0.35); border: 1px solid #27d3ff; border-radius: 10px;
    color: white; font-size: 17px; }
QPushButton#outline:hover { background: rgba(39,211,255,0.25); }
"""

STYLE += """
#fieldLabel { font-size: 19px; font-weight: 600; color: #f2f8ff; }
#setLabel { font-size: 16px; color: #e6f2ff; }
#setStatus { font-size: 15px; color: #7dffb0; padding-left: 10px; }
QMenu { background: rgb(12,40,100); color: #f0f7ff; border: 1px solid #27d3ff; padding: 4px; font-size: 15px; }
QMenu::item { padding: 7px 22px; border-radius: 6px; }
QMenu::item:selected { background: #1f78ff; }
QPushButton#iconPick { font-size: 24px; background: rgba(30,80,170,0.45); border: 1px solid rgba(120,190,255,0.5); border-radius: 10px; }
QPushButton#iconPick:checked { background: rgba(255,200,70,0.35); border: 2px solid #ffc84a; }
QPushButton#iconPick:hover { border: 1px solid white; }
QPushButton#miniBtn { background: rgba(30,80,170,0.55); border: 1px solid rgba(120,190,255,0.6); border-radius: 8px; font-size: 18px; color: white; }
QPushButton#miniBtn:hover { border: 1px solid white; }
QPushButton#miniBtn:disabled { color: #8fb0d8; background: rgba(70,90,130,0.45); }
QSlider::groove:horizontal { height: 8px; border-radius: 4px; background: rgba(8,24,70,0.85); border: 1px solid rgba(90,170,255,0.4); }
QSlider::sub-page:horizontal { border-radius: 4px; background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #1a8cff, stop:1 #35e0ff); }
QSlider::handle:horizontal { width: 8px; margin: -8px 0; border-radius: 3px; background: #7fe3ff; border: 1px solid white; }
QSpinBox#smallSpin { min-width: 56px; max-width: 70px; font-size: 18px; qproperty-alignment: AlignCenter; }
#hqBadge { background: rgba(10,20,40,0.85); color: #ffd36b; border: 1px solid #ffd36b; border-radius: 6px; font-weight: bold; font-size: 14px; padding: 4px 0; }
#setValue { font-size: 16px; color: #cfe7ff; }
QFrame#optCard { background: rgba(80,110,190,0.30); border: 1px solid rgba(140,190,255,0.45); border-radius: 14px; }
#cardTitle { font-size: 18px; color: #f4f9ff; }
QLineEdit#urlEdit { font-size: 17px; border: 2px solid #27d3ff; border-radius: 14px; padding: 8px 14px;
    background: rgba(8,28,84,0.75); }
QPushButton#roundGo { border-radius: 30px; border: 2px solid #ffb0bb;
    background: qradialgradient(cx:0.4, cy:0.3, radius:0.9, fx:0.4, fy:0.3, stop:0 #ff7a7a, stop:1 #c4101f); }
QPushButton#roundGo:hover { border: 2px solid white; }
QPushButton#roundGo:disabled { background: #5a3a48; border: 2px solid #7a5a66; }
QLabel#thumb { border: 1px solid rgba(39,211,255,0.85); border-radius: 10px; background: #04123a; }
QLabel#ndStat { font-size: 19px; color: #27d3ff; font-weight: 600; }
QLabel#ndSub { font-size: 15px; color: #c4dcf8; }
QLabel#ndTitle { font-size: 19px; color: #f4f9ff; }
QFrame#infoBox { background: rgba(4,18,60,0.80); border: 1px solid rgba(120,190,255,0.40); border-radius: 14px; }
QLabel#infoKey { font-size: 20px; color: #bcd4f2; }
QLabel#infoVal { font-size: 20px; color: #ffffff; }
QCheckBox#dontShow { font-size: 19px; color: #e6f2ff; }
QPushButton#btnGreen:disabled, QPushButton#btnOrange:disabled, QPushButton#btnRed:disabled,
QPushButton#btnBlue:disabled { background: rgba(70,90,130,0.55); border: 1px solid rgba(150,170,210,0.4);
    color: rgba(255,255,255,0.45); }
QLineEdit:disabled, QComboBox:disabled { color: #8fb0d8; }
QPushButton#playBtn { border-radius: 10px; font-size: 19px; color: white; border: 1px solid #aef2ff;
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #35e2ff, stop:1 #0aa4d8); }
QPushButton#openBtn { border-radius: 10px; font-size: 19px; color: white; border: 1px solid rgba(255,225,170,0.8);
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 rgba(190,160,120,0.75), stop:1 rgba(120,100,90,0.75)); }
QPushButton#okBtn { border-radius: 10px; font-size: 19px; color: white; border: 2px solid #ff8fa8;
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 rgba(190,80,100,0.85), stop:1 rgba(140,50,80,0.85)); }
QPushButton#playBtn:hover, QPushButton#openBtn:hover, QPushButton#okBtn:hover { border: 2px solid white; }
"""

STYLE += """
QPushButton#favBtn { border-radius: 10px; font-size: 19px; color: #2a1a00; font-weight: 600; border: 2px solid #ffe699;
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #ffd54d, stop:1 #e6a100); }
QPushButton#favBtn:hover { border: 2px solid white; }
QPushButton#favBtn:disabled { color: #fff3cc; background: rgba(120,100,40,0.55); border: 1px solid rgba(255,220,120,0.5); }
QFrame#vCard { background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 rgba(60,110,200,0.50), stop:1 rgba(14,40,120,0.55));
    border: 1px solid rgba(130,200,255,0.50); border-radius: 14px; }
QFrame#vCard:hover { border: 2px solid #27d3ff; background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
    stop:0 rgba(80,140,230,0.60), stop:1 rgba(20,60,160,0.65)); }
QLabel#vTitle { font-size: 16px; color: #f4f9ff; font-weight: 600; }
QLabel#vSub { font-size: 13px; color: #bcd4f2; }
QLabel#vSize { font-size: 14px; color: #ffffff; }
QLabel#vBadge { font-size: 14px; font-weight: 700; color: #ffd27a; background: rgba(20,14,0,0.72);
    border: 1px solid #ffb02e; border-radius: 6px; padding: 1px 7px; margin: 6px; }
QLabel#vCat { font-size: 12px; color: #2a1a00; background: #ffc400; border-radius: 6px; padding: 1px 7px; margin: 6px; }
QPushButton#iconBtn { background: rgba(255,255,255,0.10); border: 1px solid rgba(160,210,255,0.45); border-radius: 9px; }
QPushButton#iconBtn:hover { background: rgba(39,211,255,0.35); border: 1px solid #aef2ff; }
QPushButton#iconBtnOn { background: #1fd16a; border: 2px solid #8dffc0; border-radius: 9px; }
QPushButton#iconBtnOn:hover { background: #2ee67c; border: 2px solid #ffffff; }
QPushButton#iconBtnOff { background: transparent; border: 1px solid rgba(160,210,255,0.45); border-radius: 9px; }
QPushButton#iconBtnOff:hover { background: rgba(39,211,255,0.22); border: 1px solid #aef2ff; }
QPushButton#iconBtn:disabled { background: rgba(255,255,255,0.04); border: 1px solid rgba(160,210,255,0.15); }
QLabel#emptyMsg { font-size: 20px; color: #9cc3f2; }
"""

STYLE += """
QFrame#syncHead { background: rgba(4,18,60,0.80); border: 2px solid #ffb02e; border-radius: 16px; }
QLabel#syncHeadText { font-size: 30px; font-weight: 700; }
QFrame#syncList { background: rgba(4,18,60,0.70); border: 1px solid rgba(120,190,255,0.45); border-radius: 12px; }
QLabel#syncSection { font-size: 20px; color: #f4f9ff; }
QFrame#syncRow { background: rgba(80,110,190,0.38); border: 1px solid rgba(140,190,255,0.5); border-radius: 10px; }
QLabel#syncTitle { font-size: 19px; color: #ffffff; }
QLabel#syncInfo { font-size: 14px; color: #c4dcf8; }
QLabel#newBadge { font-size: 13px; font-weight: 700; color: #bfe6ff; background: rgba(20,70,170,0.9); border-radius: 5px; padding: 1px 6px; margin: 4px; }
QLabel#prevBadge { font-size: 14px; color: #0b3a1a; background: #a8f0b8; border-radius: 7px; padding: 1px 10px; }
QCheckBox#rowCheck::indicator { width: 26px; height: 26px; border-radius: 6px; border: 2px solid #27d3ff; background: rgba(4,18,60,0.85); }
QCheckBox#rowCheck::indicator:checked { background: #27d3ff; }
QPushButton#yelBtn, QPushButton#bluBtn, QPushButton#grnBtn { border-radius: 7px; border: 1px solid rgba(255,255,255,0.55); }
QPushButton#yelBtn { background: #f2b52c; } QPushButton#bluBtn { background: #1f8cff; } QPushButton#grnBtn { background: #22b85a; }
QPushButton#yelBtn:hover, QPushButton#bluBtn:hover, QPushButton#grnBtn:hover { border: 2px solid white; }
QPushButton#toggle { border-radius: 14px; font-size: 14px; font-weight: 700; min-width: 64px; min-height: 28px; padding: 0 8px;
    color: #9aa8bd; background: rgba(90,100,120,0.8); border: 1px solid rgba(190,200,220,0.5); }
QPushButton#toggle:checked { color: #04331a; background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #1fd16a, stop:1 #7dffb0); border: 1px solid #aef2ff; }
QLabel#stOk, QLabel#stIdle, QLabel#stOff, QLabel#stDue { font-size: 14px; border-radius: 9px; padding: 2px 10px; }
QLabel#stOk { color: #eafff1; background: rgba(31,180,100,0.85); border: 1px solid #7dffb0; }
QLabel#stIdle { color: #e6f2ff; background: rgba(31,110,230,0.7); border: 1px solid #8fd0ff; }
QLabel#stOff { color: #cfd6e2; background: rgba(110,120,140,0.7); border: 1px solid #aab4c6; }
QLabel#stDue { color: #2a1a00; background: #ffb02e; border: 1px solid #ffe0a0; }
QLabel#colHead { font-size: 16px; color: #f4f9ff; }
QLabel#syncPill { font-size: 22px; color: #ffffff; background: rgba(255,255,255,0.10); border: 1px solid rgba(190,220,255,0.5);
    border-radius: 12px; padding: 10px 16px; }
"""

STYLE += """
QPushButton#sideLink { background: transparent; border: none; color: #fff3c4; font-size: 12px; padding: 2px 5px; text-decoration: underline; }
QPushButton#sideLink:hover { color: #ffffff; background: rgba(255,255,255,0.20); border-radius: 6px; }
QLabel#counterPill { font-size: 14px; font-weight: 700; color: #ffffff; background: rgba(255,255,255,0.22);
    border: 1px solid rgba(255,255,255,0.75); border-radius: 12px; padding: 2px 12px; }
QTextBrowser#infoView { background: transparent; border: none; selection-background-color: #ffc83d; selection-color: #102a5c; }
"""


# ----------------------------------------------------------------------
# 2.0.2: every page / window follows the size of the area it is shown in
# ----------------------------------------------------------------------
import re as _re

_RULE = _re.compile(r"([^{}]+)\{([^{}]*)\}")
_FONT = _re.compile(r"font-size:\s*(\d+)px")
_FONT_CACHE: dict = {}


def font_qss(scale: float) -> str:
    """The font sizes of the global style sheet multiplied by `scale`: a page / window that sets this style sheet
    shows every text of the theme (titles, labels, buttons, cards ...) in the size that fits its area."""
    key = round(scale * 20)
    if key not in _FONT_CACHE:
        k = key / 20.0
        rules = []
        for sel, body in _RULE.findall(STYLE):
            m = _FONT.search(body)
            if m:
                rules.append(f"{sel.strip()} {{ font-size: {max(8, round(int(m.group(1)) * k))}px; }}")
        _FONT_CACHE[key] = "\n".join(rules)
    return _FONT_CACHE[key]


def area_scale(width: int, height: int, base_w: float = 660.0, base_h: float = 520.0,
               lo: float = 0.7, hi: float = 1.5) -> float:
    """Scale of an area compared with its design size (steps of 0.05)."""
    s = max(lo, min(hi, min(width / base_w, height / base_h)))
    return round(s * 20) / 20.0
