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
#ParamScroll QComboBox::drop-down {{ border: none; width: 22px; }}
#ParamScroll QComboBox QAbstractItemView {{
    background: #222e3c; color: {TEXT}; border: 1px solid {PANEL_BORDER};
    selection-background-color: {ACCENT}; selection-color: white;
}}
#ParamScroll QSpinBox::up-button, #ParamScroll QSpinBox::down-button,
#ParamScroll QDoubleSpinBox::up-button, #ParamScroll QDoubleSpinBox::down-button {{
    width: 16px; background: #344252; border: none;
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

QScrollBar:vertical {{ background: transparent; width: 11px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: #aeb7c3; border-radius: 5px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: #97a3b2; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
QScrollBar:horizontal {{ background: transparent; height: 11px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: #aeb7c3; border-radius: 5px; min-width: 30px; }}
"""
