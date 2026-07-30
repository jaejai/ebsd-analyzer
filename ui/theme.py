"""Visual theme for the EBSD Analyzer desktop app.

Dark slate sidebar + light work area + accent blue. Tuned for STRONG contrast:
every input and button has a clearly visible border and background, and label
text is bright enough to read on the dark panel.
"""

ACCENT = "#3B82F6"          # brighter, higher-contrast blue
ACCENT_HOVER = "#2f6fe0"
ACCENT_SOFT = "rgba(59,130,246,0.22)"
NAV_BG = "#1b2430"          # sidebar
PANEL = "#2c3a4b"          # input background on the sidebar (clearly lighter than NAV_BG)
PANEL_BORDER = "#586a80"   # visible input border (lighter for contrast)
LABEL = "#d4dde8"          # readable label text on dark
TEXT = "#f2f6fb"           # input text on dark
SECTION = "#aab8c9"        # section headers (brighter than before)
MUTED = "#9aa7b8"
MAIN_BG = "#eef0f3"

# ---------------------------------------------------------------------------
# Spin-button / combo arrow glyphs.
# Qt's CSS border-triangle trick is unreliable on sub-control arrows (it often
# renders up and down identically or falls back to a native glyph). Drawing the
# glyphs as real SVG images is reliable, so we write tiny SVGs to a temp dir at
# import time and reference them by path in the stylesheet. Spin steppers use
# clear "+" / "-" marks; the combo uses a down chevron.
# ---------------------------------------------------------------------------
import os as _os
import tempfile as _tempfile

_GLYPH_DIR = _os.path.join(_tempfile.gettempdir(), "ebsd_ui_glyphs")
_os.makedirs(_GLYPH_DIR, exist_ok=True)


def _write_svg(name, body):
    p = _os.path.join(_GLYPH_DIR, name)
    with open(p, "w", encoding="utf-8") as f:
        f.write(body)
    return p.replace("\\", "/")   # Qt url() wants forward slashes


_DARK = "#101821"
# bold "+" and "-" (minus) glyphs, chunky enough to read at ~11px
_PLUS = f'''<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16">
<rect x="6.5" y="2" width="3" height="12" rx="1.5" fill="{_DARK}"/>
<rect x="2" y="6.5" width="12" height="3" rx="1.5" fill="{_DARK}"/></svg>'''
_MINUS = f'''<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16">
<rect x="2" y="6.5" width="12" height="3" rx="1.5" fill="{_DARK}"/></svg>'''
_CHEVRON = f'''<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16">
<path d="M3 5.5 L8 10.5 L13 5.5" stroke="{_DARK}" stroke-width="2.6" fill="none"
stroke-linecap="round" stroke-linejoin="round"/></svg>'''

UP_ARROW = _write_svg("plus.svg", _PLUS)     # spin up  -> "+"
DOWN_ARROW = _write_svg("minus.svg", _MINUS)  # spin down -> "-"
CHEVRON = _write_svg("chevron.svg", _CHEVRON)

STYLESHEET = f"""
* {{ font-family: 'Segoe UI', sans-serif; font-size: 12px; }}

QMainWindow, QWidget {{ background: {MAIN_BG}; color: #1a2230; }}

/* ---------- header ---------- */
#Header {{ background: #ffffff; border-bottom: 1px solid #d7dce3; }}
#Logo {{ font-size: 16px; font-weight: 800; letter-spacing: 0.5px; color: #1a2230; }}
#LogoSub {{ font-size: 10px; font-weight: 600; letter-spacing: 0.5px; color: #7a8696; }}
#FileChip {{
    background: #eef2f7; border: 1px solid #cfd6df; border-radius: 7px;
    padding: 6px 12px; color: #2c3540; font-family: Consolas, monospace; font-size: 12px;
}}

/* ---------- metric cards (header) ---------- */
#MetricCard {{ background: #f7f9fb; border: 1px solid #d7dce3; border-radius: 7px; }}
#MetricCardAccent {{ background: {ACCENT_SOFT}; border: 1px solid {ACCENT}; border-radius: 7px; }}
#MetricValue {{ font-family: Consolas, monospace; font-size: 15px; font-weight: 800; color: #1a2230; }}
#MetricValueAccent {{ font-family: Consolas, monospace; font-size: 15px; font-weight: 800; color: {ACCENT_HOVER}; }}
#MetricLabel {{ font-family: Consolas, monospace; font-size: 8px; font-weight: 700; letter-spacing: 0.3px; color: #6b7787; }}

/* ---------- sidebar shell ---------- */
#Sidebar {{ background: {NAV_BG}; }}
#Nav, #RunFooter {{ background: {NAV_BG}; }}
#ParamScroll {{ background: {NAV_BG}; border: none; }}
/* All plain containers in the param area paint dark. Buttons/inputs below use
   type+id selectors placed AFTER this rule, so they override it and stay
   visible. (Equal-specificity rules: the later one wins.) */
#ParamScroll QWidget {{ background: {NAV_BG}; }}
#ParamHost, #ParamStack, #ParamPage, #RowCont {{ background: {NAV_BG}; }}
#SectionLabel {{ font-family: Consolas, monospace; font-size: 10.5px; font-weight: 800;
    letter-spacing: 1.5px; color: {SECTION}; padding: 2px 0 6px; background: transparent; }}

/* nav buttons */
#NavBtn {{
    text-align: left; border: none; border-left: 3px solid transparent;
    border-radius: 0 7px 7px 0; padding: 9px 10px; color: #dde5ef;
    background: transparent; font-size: 12.5px;
}}
#NavBtn:hover {{ background: rgba(255,255,255,0.07); color: #ffffff; }}
#NavBtn:checked {{ background: {ACCENT_SOFT}; color: #ffffff; border-left: 3px solid {ACCENT}; font-weight: 600; }}

/* sidebar labels + inputs — high contrast */
#Sidebar QLabel {{ color: {LABEL}; font-size: 11px; font-weight: 600; }}
#Sidebar QLineEdit, #Sidebar QComboBox, #Sidebar QSpinBox, #Sidebar QDoubleSpinBox,
#ParamScroll QLineEdit, #ParamScroll QComboBox, #ParamScroll QSpinBox, #ParamScroll QDoubleSpinBox {{
    background: {PANEL}; border: 1px solid {PANEL_BORDER}; border-radius: 6px;
    color: {TEXT}; padding: 7px 10px; font-family: Consolas, monospace; font-size: 12.5px;
    selection-background-color: {ACCENT};
}}
#ParamScroll QLineEdit:focus, #ParamScroll QComboBox:focus,
#ParamScroll QSpinBox:focus, #ParamScroll QDoubleSpinBox:focus {{ border: 1px solid {ACCENT}; }}
#ParamScroll QComboBox::drop-down {{ border: none; width: 22px;
    background: #c4d0e0; border-top-right-radius: 5px; border-bottom-right-radius: 5px; }}
#ParamScroll QComboBox::drop-down:hover {{ background: {ACCENT}; }}
#ParamScroll QComboBox::down-arrow {{ image: url("{CHEVRON}"); width: 11px; height: 11px; }}
#ParamScroll QComboBox QAbstractItemView {{
    background: #222e3c; color: {TEXT}; border: 1px solid {PANEL_BORDER};
    selection-background-color: {ACCENT}; selection-color: white;
}}
/* Spin buttons: up-button pinned to the top-right, down-button to the bottom-
   right, each carrying a DISTINCT arrow glyph drawn as an SVG image (border-
   triangle CSS is unreliable on Qt sub-controls and renders both arrows the
   same — an image always renders the intended up vs down shape). */
#ParamScroll QSpinBox, #ParamScroll QDoubleSpinBox {{ padding-right: 22px; min-height: 30px; }}
#ParamScroll QSpinBox::up-button, #ParamScroll QDoubleSpinBox::up-button {{
    subcontrol-origin: border; subcontrol-position: top right;
    width: 20px; height: 15px; background: #c4d0e0; border: none;
    border-top-right-radius: 5px;
}}
#ParamScroll QSpinBox::down-button, #ParamScroll QDoubleSpinBox::down-button {{
    subcontrol-origin: border; subcontrol-position: bottom right;
    width: 20px; height: 15px; background: #b6c2d3; border: none;
    border-bottom-right-radius: 5px;
}}
#ParamScroll QSpinBox::up-button:hover, #ParamScroll QDoubleSpinBox::up-button:hover,
#ParamScroll QSpinBox::down-button:hover, #ParamScroll QDoubleSpinBox::down-button:hover {{ background: {ACCENT}; }}
#ParamScroll QSpinBox::up-arrow, #ParamScroll QDoubleSpinBox::up-arrow {{
    image: url("{UP_ARROW}"); width: 12px; height: 12px;
}}
#ParamScroll QSpinBox::down-arrow, #ParamScroll QDoubleSpinBox::down-arrow {{
    image: url("{DOWN_ARROW}"); width: 12px; height: 12px;
}}
#ParamScroll QCheckBox {{ color: {LABEL}; font-size: 12px; spacing: 7px; }}
#ParamScroll QCheckBox::indicator {{ width: 16px; height: 16px; border: 1px solid {PANEL_BORDER};
    border-radius: 4px; background: {PANEL}; }}
#ParamScroll QCheckBox::indicator:checked {{ background: {ACCENT}; border: 1px solid {ACCENT}; }}

/* segmented buttons (type+id so they beat the broad #ParamScroll QWidget bg) */
QPushButton#SegBtn {{ border: 1px solid {PANEL_BORDER}; border-radius: 6px; padding: 7px 4px; color: {LABEL};
    background: {PANEL}; font-family: Consolas, monospace; font-size: 11.5px; font-weight: 600; }}
QPushButton#SegBtn:hover {{ border: 1px solid {ACCENT}; }}
QPushButton#SegBtn:checked {{ background: {ACCENT}; color: #ffffff; border: 1px solid {ACCENT}; }}

/* phi2 chips */
QPushButton#ChipBtn {{ border: 1px solid {PANEL_BORDER}; border-radius: 6px; padding: 5px 10px;
    color: {LABEL}; background: {PANEL}; font-family: Consolas, monospace;
    font-size: 11.5px; font-weight: 700; }}
QPushButton#ChipBtn:checked {{ background: {ACCENT}; color: #ffffff; border: 1px solid {ACCENT}; }}

QPushButton#AdvToggle {{ text-align: left; border: none; background: transparent; color: #9fc3ff;
    font-family: Consolas, monospace; font-size: 11px; font-weight: 800; letter-spacing: 1px; padding: 8px 2px; }}
QPushButton#AdvToggle:hover {{ color: {ACCENT}; }}

/* secondary button (Browse) — visible on the dark sidebar */
QPushButton#BrowseBtn {{ background: #44576e; color: {TEXT}; border: 1px solid {PANEL_BORDER};
    border-radius: 6px; padding: 7px 16px; font-size: 12px; font-weight: 700; }}
QPushButton#BrowseBtn:hover {{ background: #516882; border: 1px solid {ACCENT}; }}

/* run footer */
#RunFooter {{ border-top: 1px solid #2e3a49; }}
#RunBtn {{ background: {ACCENT}; color: white; border: none; border-radius: 7px;
    padding: 12px 0; font-size: 13px; font-weight: 700; }}
#RunBtn:hover {{ background: {ACCENT_HOVER}; }}
#RunBtn:disabled {{ background: #45556a; color: #9aa7b8; }}
#RunAllBtn {{ background: #2f3d4e; color: {TEXT}; border: 1px solid {PANEL_BORDER};
    border-radius: 7px; padding: 10px 0; font-size: 12.5px; font-weight: 600; }}
#RunAllBtn:hover {{ background: #394a5e; border: 1px solid {ACCENT}; }}
#RunAllBtn:disabled {{ color: #6b7787; }}
#RunProg {{ border: 1px solid #2e3a49; background: #131a23; border-radius: 4px; height: 8px;
    text-align: center; color: transparent; }}
#RunProg::chunk {{ background: {ACCENT}; border-radius: 3px; }}

/* ---------- main work area ---------- */
#Main, #ResultScroll {{ background: {MAIN_BG}; }}
#ResultScroll {{ border: none; }}
#ResultScroll > QWidget > QWidget {{ background: {MAIN_BG}; }}
#Kicker {{ color: {ACCENT_HOVER}; font-family: Consolas, monospace; font-size: 10px; font-weight: 800; letter-spacing: 1.5px; }}
#StageTitle {{ font-size: 23px; font-weight: 700; color: #1a2230; }}
#StageDesc {{ font-size: 13px; color: #5c6775; }}

#Card {{ background: #ffffff; border: 1px solid #d7dce3; border-radius: 10px; }}
#CardTitle {{ font-size: 12.5px; font-weight: 700; color: #2c3540; }}
#CardCaption {{ font-family: Consolas, monospace; font-size: 10.5px; color: #7a8696; }}

#StatCard {{ background: #ffffff; border: 1px solid #d7dce3; border-radius: 9px; }}
#StatCardAccent {{ background: {ACCENT_SOFT}; border: 1px solid {ACCENT}; border-radius: 9px; }}
#StatLabel {{ font-family: Consolas, monospace; font-size: 10px; font-weight: 700; letter-spacing: 0.5px; color: #6b7787; }}
#StatValue {{ font-family: Consolas, monospace; font-size: 22px; font-weight: 800; color: #1a2230; }}
#StatValueAccent {{ font-family: Consolas, monospace; font-size: 22px; font-weight: 800; color: {ACCENT_HOVER}; }}

#LogView {{ background: #ffffff; border: 1px solid #d7dce3; border-radius: 8px;
    font-family: Consolas, monospace; font-size: 11px; color: #3a4350; padding: 4px; }}

/* main footer */
#MainFooter {{ background: {MAIN_BG}; }}
#BackBtn {{ border: 1px solid #c2cad4; background: white; border-radius: 7px; padding: 9px 20px;
    font-size: 12.5px; font-weight: 600; color: #2c3540; }}
#BackBtn:hover {{ border: 1px solid {ACCENT}; }}
#BackBtn:disabled {{ color: #aab2bd; border: 1px solid #dde1e7; }}
#NextBtn {{ border: none; background: {ACCENT}; border-radius: 7px; padding: 9px 22px;
    font-size: 12.5px; font-weight: 700; color: white; }}
#NextBtn:hover {{ background: {ACCENT_HOVER}; }}
#StageCount {{ font-family: Consolas, monospace; font-size: 11px; color: #7a8696; }}

/* Scrollbars: a visible track + a high-contrast handle so they read clearly on
   BOTH the dark sidebar and the light work area. Arrow step-buttons kept off. */
QScrollBar:vertical {{ background: rgba(120,135,155,0.18); width: 13px; margin: 2px; border-radius: 6px; }}
QScrollBar::handle:vertical {{ background: #8794a6; border: 1px solid #6b7787; border-radius: 6px; min-height: 34px; }}
QScrollBar::handle:vertical:hover {{ background: {ACCENT}; border: 1px solid {ACCENT}; }}
QScrollBar:horizontal {{ background: rgba(120,135,155,0.18); height: 13px; margin: 2px; border-radius: 6px; }}
QScrollBar::handle:horizontal {{ background: #8794a6; border: 1px solid #6b7787; border-radius: 6px; min-width: 34px; }}
QScrollBar::handle:horizontal:hover {{ background: {ACCENT}; border: 1px solid {ACCENT}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; background: none; border: none; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: none; }}
"""
