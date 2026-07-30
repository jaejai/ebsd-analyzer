"""Reusable Qt widgets for the EBSD ODF Analyzer GUI."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QButtonGroup,
    QSizePolicy, QDialog,
)
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure


class PlotDialog(QDialog):
    """Large pop-up view of a plot, with matplotlib zoom/pan/save toolbar."""
    def __init__(self, fig_builder, title="Plot", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(1000, 760)
        lay = QVBoxLayout(self); lay.setContentsMargins(6, 6, 6, 6)
        fig = fig_builder()
        try:
            fig.set_layout_engine("constrained")
        except Exception:
            pass
        self.canvas = FigureCanvas(fig)
        self.toolbar = NavigationToolbar(self.canvas, self)
        lay.addWidget(self.toolbar)
        lay.addWidget(self.canvas, 1)


def mono(lbl: QLabel) -> QLabel:
    f = lbl.font(); f.setFamily("Consolas"); lbl.setFont(f); return lbl


class SectionLabel(QLabel):
    def __init__(self, text):
        super().__init__(text.upper()); self.setObjectName("SectionLabel")


# Bright label color for the dark sidebar — set directly on the widget so it
# always applies, regardless of stylesheet ancestor-selector matching.
PARAM_LABEL_CSS = "color:#e3eaf3; font-size:11px; font-weight:700; background:transparent;"


class ParamLabel(QLabel):
    """A parameter caption guaranteed readable on the dark sidebar."""
    def __init__(self, text):
        super().__init__(text)
        self.setStyleSheet(PARAM_LABEL_CSS)


class MetricCard(QFrame):
    """Small header metric card (value + label)."""
    def __init__(self, label, value, accent=False):
        super().__init__()
        self.setObjectName("MetricCardAccent" if accent else "MetricCard")
        self.setMinimumWidth(92)   # enough room for "2.41 um" / "TEXTURE J"
        lay = QVBoxLayout(self); lay.setContentsMargins(12, 5, 12, 5); lay.setSpacing(1)
        self.val = QLabel(value); self.val.setObjectName("MetricValueAccent" if accent else "MetricValue")
        self.val.setAlignment(Qt.AlignRight)
        self.lbl = QLabel(label.upper()); self.lbl.setObjectName("MetricLabel")
        self.lbl.setAlignment(Qt.AlignRight)
        lay.addWidget(self.val); lay.addWidget(self.lbl)

    def set_value(self, v):
        self.val.setText(str(v))


class StatCard(QFrame):
    """Larger result-pane stat card."""
    def __init__(self, label, value="-", accent=False):
        super().__init__()
        self.setObjectName("StatCardAccent" if accent else "StatCard")
        self.setMinimumWidth(124)
        lay = QVBoxLayout(self); lay.setContentsMargins(15, 12, 15, 12); lay.setSpacing(5)
        self.lbl = QLabel(label.upper()); self.lbl.setObjectName("StatLabel")
        self.val = QLabel(value); self.val.setObjectName("StatValueAccent" if accent else "StatValue")
        lay.addWidget(self.lbl); lay.addWidget(self.val)

    def set_value(self, v):
        self.val.setText(str(v))


class Card(QFrame):
    """White rounded card with optional title and a content layout."""
    def __init__(self, title=None, caption=None):
        super().__init__(); self.setObjectName("Card")
        self.v = QVBoxLayout(self); self.v.setContentsMargins(0, 0, 0, 0); self.v.setSpacing(0)
        if title is not None:
            head = QWidget(); hl = QHBoxLayout(head); hl.setContentsMargins(13, 9, 13, 9)
            t = QLabel(title); t.setObjectName("CardTitle"); hl.addWidget(t)
            if caption:
                hl.addStretch(1); c = QLabel(caption); c.setObjectName("CardCaption"); hl.addWidget(c)
            self.v.addWidget(head)
        self.body = QWidget(); self.body_l = QVBoxLayout(self.body)
        self.body_l.setContentsMargins(11, 4, 11, 11)
        self.v.addWidget(self.body)


class FigurePane(QFrame):
    """A titled card wrapping an embedded matplotlib canvas.

    Each new figure gets a FRESH FigureCanvas. Reassigning ``canvas.figure`` on
    an existing canvas does not rebind it cleanly and leaves the canvas drawing
    a stale buffer at the wrong size (renders as stripes / a thin sliver), so we
    replace the canvas widget every time instead.
    """
    def __init__(self, title="", caption=None, min_h=300):
        super().__init__(); self.setObjectName("Card")
        self._min_h = min_h
        self._title = title
        self._builder = None     # callable() -> Figure, for the zoom popup
        v = QVBoxLayout(self); v.setContentsMargins(0, 0, 0, 0); v.setSpacing(0)
        if title:
            head = QWidget(); hl = QHBoxLayout(head); hl.setContentsMargins(13, 9, 13, 9)
            t = QLabel(title); t.setObjectName("CardTitle"); hl.addWidget(t)
            hl.addStretch(1)
            hint = QLabel("click to enlarge ⤢"); hint.setObjectName("CardCaption")
            hl.addWidget(hint)
            if caption:
                c = QLabel(caption); c.setObjectName("CardCaption"); hl.addWidget(c)
            v.addWidget(head)
        # canvas host: we swap the canvas inside this layout
        self._host = QWidget()
        self._host_l = QVBoxLayout(self._host)
        self._host_l.setContentsMargins(8, 8, 8, 8)
        v.addWidget(self._host)
        self.setCursor(Qt.PointingHandCursor)

        self.figure = Figure(figsize=(4, 4))
        self.canvas = None
        self._install_canvas(self.figure)

    def set_builder(self, builder):
        """Store the figure-builder so a click can re-render it large."""
        self._builder = builder

    def mouseDoubleClickEvent(self, event):
        self._open_popup()

    def mousePressEvent(self, event):
        # single click on the figure also enlarges
        self._open_popup()

    def _open_popup(self):
        if self._builder is None:
            return
        dlg = PlotDialog(self._builder, title=self._title or "Plot", parent=self.window())
        dlg.show()

    def _install_canvas(self, fig: Figure):
        # remove the previous canvas widget entirely
        if self.canvas is not None:
            self._host_l.removeWidget(self.canvas)
            self.canvas.setParent(None)
            self.canvas.deleteLater()
        self.figure = fig
        self.canvas = FigureCanvas(fig)
        self.canvas.setMinimumHeight(self._min_h)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.canvas.setStyleSheet("background:#ffffff;")
        self._host_l.addWidget(self.canvas)

    def show_figure(self, fig: Figure):
        # constrained layout keeps colorbars/labels inside the axes box; a fresh
        # canvas then renders the whole figure scaled to the widget.
        try:
            fig.set_layout_engine("constrained")
        except Exception:
            pass
        self._install_canvas(fig)
        self.canvas.draw_idle()


class SegGroup(QWidget):
    """Row of mutually-exclusive segmented buttons; .value() -> selected key."""
    def __init__(self, options, default=None):
        super().__init__()
        lay = QHBoxLayout(self); lay.setContentsMargins(0, 0, 0, 0); lay.setSpacing(5)
        self.group = QButtonGroup(self); self.group.setExclusive(True)
        self._keys = {}
        for key, text in options:
            b = QPushButton(text); b.setObjectName("SegBtn"); b.setCheckable(True)
            b.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            self.group.addButton(b); lay.addWidget(b); self._keys[b] = key
            if key == default:
                b.setChecked(True)

    def value(self):
        b = self.group.checkedButton()
        return self._keys.get(b) if b else None


# convenience alias kept for app import symmetry
SegButton = SegGroup


class ChipButton(QPushButton):
    def __init__(self, text, checked=True):
        super().__init__(text); self.setObjectName("ChipBtn")
        self.setCheckable(True); self.setChecked(checked)


# Height of one boundary-editor row. The themed spin boxes are min-height 30 px
# and carry stacked +/- buttons, so rows need headroom or the values render
# clipped / rows overlap.
_ROW_H = 46

# Chrome the themed stylesheet puts around a spin box's text:
#   padding-right: 22 px  (reserved for the stacked +/- buttons)
#   padding: 7px 10px     (left/right text padding)
# plus a small frame allowance. Numeric fields must be at least
# text_width + _SPIN_CHROME wide or the value renders clipped.
_SPIN_CHROME = 22 + 10 + 10 + 6

# Extra slack so the caret and the last glyph never touch the field edge.
_SPIN_SLACK = 12


def _fit_spinbox(sp, widest_text):
    """Give a spin box the width its widest value actually needs.

    The themed stylesheet reserves a sizeable but not-known-in-advance amount of
    the widget for the stacked +/- buttons and text padding. Rather than assume
    a constant (an assumption that kept clipping the values), MEASURE the real
    chrome as `widget width - lineEdit width` once the widget is laid out, then
    demand text_width + that chrome. Falls back to the constant before the first
    layout pass, and is re-applied by `polish_widths()` afterwards.
    """
    text_px = sp.fontMetrics().horizontalAdvance(widest_text)
    chrome = sp.width() - sp.lineEdit().width() if sp.lineEdit().width() else 0
    if chrome <= 0:
        chrome = _SPIN_CHROME
    sp.setMinimumWidth(text_px + chrome + _SPIN_SLACK)
    sp._widest_text = widest_text          # remembered for polish_widths()
    return sp


class BoundaryEditor(QWidget):
    """Editable list of grain-boundary classes. The user sets how many boundaries
    to define; each row has a min/max angle, a colour and a line thickness. The
    grain-defining threshold is the highest row's min angle.

    .value() -> list of {"name","lo","hi","color","width"} dicts.
    """
    _PALETTE = ["blue", "black", "red", "green", "magenta", "orange"]

    def __init__(self, defaults=None):
        super().__init__()
        from PySide6.QtWidgets import (QSpinBox, QDoubleSpinBox, QComboBox,
                                       QGridLayout, QLabel)
        self._QDoubleSpinBox = QDoubleSpinBox
        self._QComboBox = QComboBox
        self._QLabel = QLabel
        self._rows = []
        self.v = QVBoxLayout(self); self.v.setContentsMargins(0, 0, 0, 0); self.v.setSpacing(6)

        # count selector row
        cnt_row = QHBoxLayout(); cnt_row.setSpacing(6)
        lab = QLabel("Boundaries:"); lab.setStyleSheet(PARAM_LABEL_CSS)
        self.count = QSpinBox(); self.count.setRange(1, 6)
        self.count.setValue(len(defaults) if defaults else 2)
        self.count.setMinimumWidth(74)
        cnt_row.addWidget(lab); cnt_row.addWidget(self.count); cnt_row.addStretch(1)
        cw = QWidget(); cw.setLayout(cnt_row); self.v.addWidget(cw)
        self._count_row = cw

        # convention hint — what lo/hi mean
        hint = QLabel("display classes, drawn where  lo° ≤ misorientation < hi°   ·   "
                      "grains split at the angle set above")
        hint.setStyleSheet("color:#9fb0c4; font-size:10px; font-style:italic;"
                           "background:transparent; padding:1px 0 3px;")
        hint.setWordWrap(True)
        hint.setMinimumHeight(26)
        self.v.addWidget(hint)
        self._hint = hint

        self._defaults = defaults or [
            {"name": "LAGB", "lo": 2.0, "hi": 15.0, "color": "blue", "width": 0.4},
            {"name": "HAGB", "lo": 15.0, "hi": 180.0, "color": "black", "width": 0.6},
        ]
        # rows live inside a replaceable host widget so a rebuild simply swaps the
        # whole host (no per-widget deleteLater timing hazards).
        self._host = None
        self._rebuild()
        self.count.valueChanged.connect(self._rebuild)

    def _rebuild(self):
        from PySide6.QtWidgets import (QLineEdit, QDoubleSpinBox, QComboBox,
                                       QLabel, QGridLayout)
        # replace the entire rows host
        if self._host is not None:
            self.v.removeWidget(self._host)
            self._host.setParent(None)
            self._host.deleteLater()
        self._rows = []
        host = QWidget()
        # Compact chrome for THIS table only: five themed columns cannot fit the
        # sidebar at the default padding, and squeezing a column is what clipped
        # the values. Narrower spin buttons + tighter text padding buy the room.
        host.setStyleSheet(
            "QDoubleSpinBox, QLineEdit, QComboBox { padding: 4px 5px; }"
            "QDoubleSpinBox { padding-right: 17px; }"
            "QDoubleSpinBox::up-button, QDoubleSpinBox::down-button { width: 15px; }"
            "QComboBox { padding-right: 20px; }"
            "QComboBox::drop-down { width: 18px; }")
        grid = QGridLayout(host)
        grid.setHorizontalSpacing(4); grid.setVerticalSpacing(7)
        # small margins so neither the header labels nor the last column sit
        # flush against the panel edge (the "name" header was being cut off)
        grid.setContentsMargins(3, 0, 6, 0)
        for c, h in enumerate(["name", "from lo°", "to hi°", "colour", "width"]):
            hl = QLabel(h); hl.setStyleSheet(
                "color:#9fb0c4;font-size:10px;font-weight:700;background:transparent;")
            grid.addWidget(hl, 0, c)
        # Only the name column may stretch/absorb slack. The four value columns
        # are pinned to their content width (set below) so the layout can never
        # squeeze a number until it clips.
        grid.setColumnStretch(0, 1)
        for c in (1, 2, 3, 4):
            grid.setColumnStretch(c, 0)
        n = self.count.value()
        for i in range(n):
            d = self._defaults[i] if i < len(self._defaults) else {
                "name": f"B{i+1}", "lo": 15.0 * i + 2.0, "hi": 180.0,
                "color": self._PALETTE[i % len(self._PALETTE)], "width": 0.5}
            # Min widths sized so the VALUE stays readable next to the +/- spin
            # buttons (which take ~22 px on the right of every spin box).
            name = QLineEdit(d["name"])
            # Sized from real font metrics like the numeric fields — a hard-coded
            # 44 px clipped "LAGB"/"HAGB" to "\GB". Same formula polish_widths()
            # uses, so the deferred pass never disagrees with the initial build.
            _w = max(d["name"], "HAGB", key=len)
            name.setMinimumWidth(name.fontMetrics().horizontalAdvance(_w + "_") + 16)
            lo = QDoubleSpinBox(); lo.setRange(0, 180); lo.setDecimals(0); lo.setValue(d["lo"])
            lo.setSuffix("°")
            hi = QDoubleSpinBox(); hi.setRange(0, 181); hi.setDecimals(0); hi.setValue(d["hi"])
            hi.setSuffix("°")
            col = QComboBox(); col.addItems(self._PALETTE)
            col.setCurrentText(d["color"] if d["color"] in self._PALETTE else "black")
            # width of the longest palette entry ("magenta") + drop-down + padding,
            # measured — a fixed 88 px rendered it as "magent".
            _widest = max(self._PALETTE,
                          key=lambda s: col.fontMetrics().horizontalAdvance(s))
            col.setMinimumWidth(col.fontMetrics().horizontalAdvance(_widest) + 64)
            wd = QDoubleSpinBox(); wd.setRange(0.1, 6.0); wd.setDecimals(1); wd.setSingleStep(0.1)
            wd.setValue(d["width"])
            # Size the numeric fields from REAL font metrics for their widest
            # possible value, plus the space the themed stylesheet takes for the
            # +/- spin buttons and the text padding. Hard-coded widths were what
            # clipped the numbers before.
            for sp, widest in ((lo, "180°"), (hi, "180°"), (wd, "6.0")):
                _fit_spinbox(sp, widest)
            # Pin the grid columns to those widths too. A minimum on the widget
            # alone is not enough: the layout will still squeeze a column when
            # the row is wider than the panel, which is what clipped the values.
            for c, w in ((0, name.minimumWidth()), (1, lo.minimumWidth()),
                         (2, hi.minimumWidth()), (3, col.minimumWidth()),
                         (4, wd.minimumWidth())):
                grid.setColumnMinimumWidth(c, max(grid.columnMinimumWidth(c), w))
            row = {"name": name, "lo": lo, "hi": hi, "color": col, "width": wd}
            # Fixed row height: without it a squeezing parent layout crushes the
            # rows and the numbers get clipped in half.
            for w in row.values():
                # Do NOT force a height here: the themed spin boxes need their
                # natural height (min-height 30 px + padding + stacked +/-
                # buttons). Forcing a smaller one makes rows overlap and clips
                # the values. Just stop them stretching vertically.
                w.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
                w.setMinimumHeight(_ROW_H)
            for c, key in enumerate(["name", "lo", "hi", "color", "width"]):
                grid.addWidget(row[key], i + 1, c)
            self._rows.append(row)
        self._host = host
        self.v.addWidget(host)
        # Reserve the vertical space the grid needs, computed EXPLICITLY (a
        # sizeHint taken here is stale — the themed spin boxes have not been
        # sized yet, which left the host too short and overlapped the rows).
        HEADER_H = 16
        VSPACE = 7
        rows_h = HEADER_H + VSPACE + n * (_ROW_H + VSPACE) + 4
        host.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        host.setFixedHeight(rows_h)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        # Height of the whole editor = the rows host plus everything stacked
        # above it (count row + hint) plus the layout spacing between them.
        # Measured, not guessed — an under-estimate clipped the last row.
        if getattr(self, "_hint", None) is not None:
            above = (self._count_row.sizeHint().height()
                     + self._hint.sizeHint().height()
                     + self.v.spacing() * 2)
        else:                       # first build, before the header widgets exist
            above = 96
        self.setFixedHeight(rows_h + above + 8)
        # Re-measure once Qt has laid the widgets out and the real stylesheet
        # chrome is known (see polish_widths).
        from PySide6.QtCore import QTimer
        QTimer.singleShot(0, self.polish_widths)

    def polish_widths(self):
        """Re-size the numeric fields once real geometry exists.

        Before the first layout pass a spin box cannot report how much space its
        stylesheet chrome (the +/- buttons and padding) takes, so the initial
        sizing uses an estimate. This runs afterwards, measures the true chrome,
        and pins both the widgets and the grid columns to it — this is what
        finally stops the angle / width values being clipped.
        """
        if not self._rows or self._host is None:
            return
        grid = self._host.layout()
        # numeric spin columns: text + the spin box's real chrome
        for c, key in {1: "lo", 2: "hi", 4: "width"}.items():
            need = 0
            for r in self._rows:
                sp = r[key]
                widest = getattr(sp, "_widest_text", sp.text())
                chrome = sp.width() - sp.lineEdit().width()
                if chrome <= 0:
                    chrome = _SPIN_CHROME
                need = max(need, sp.fontMetrics().horizontalAdvance(widest)
                           + chrome + _SPIN_SLACK)
            for r in self._rows:
                r[key].setMinimumWidth(need)
            grid.setColumnMinimumWidth(c, need)

        # name column: must hold the longest label the user has typed (and at
        # least "HAGB"), or it renders clipped like "\GB".
        need = 0
        for r in self._rows:
            le = r["name"]
            widest = max(le.text(), "HAGB", key=len)
            need = max(need, le.fontMetrics().horizontalAdvance(widest + "_") + 16)
        for r in self._rows:
            r["name"].setMinimumWidth(need)
        grid.setColumnMinimumWidth(0, need)

        # colour column: sized for the longest palette entry ("magenta"), plus
        # the drop-down arrow and padding — otherwise it renders as "magent".
        if self._rows:
            cb0 = self._rows[0]["color"]
            widest = max(self._PALETTE, key=lambda s: cb0.fontMetrics().horizontalAdvance(s))
            need = cb0.fontMetrics().horizontalAdvance(widest) + 64
            for r in self._rows:
                r["color"].setMinimumWidth(need)
            grid.setColumnMinimumWidth(3, need)

    def value(self):
        out = []
        for r in self._rows:
            out.append({"name": r["name"].text() or "bnd",
                        "lo": r["lo"].value(), "hi": r["hi"].value(),
                        "color": r["color"].currentText(),
                        "width": r["width"].value()})
        return out

    def set_value(self, boundaries):
        """Restore rows from a list of boundary dicts (used by JSON presets)."""
        if not boundaries:
            return
        self._defaults = [dict(b) for b in boundaries]
        n = max(1, min(len(self._defaults), self.count.maximum()))
        if self.count.value() == n:
            self._rebuild()            # same count -> refresh values in place
        else:
            self.count.setValue(n)     # triggers _rebuild via valueChanged
