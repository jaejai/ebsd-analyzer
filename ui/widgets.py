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
