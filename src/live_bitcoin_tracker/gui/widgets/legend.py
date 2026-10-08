"""Colour key: the nine blue (+) and orange (-) change bands and the green/red result marks."""

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel

from live_bitcoin_tracker import colors
from live_bitcoin_tracker.gui import theme
from live_bitcoin_tracker.gui.viewmodel import LEGEND_BANDS


def _mid(i: int) -> float:
    lowers = (0, *colors.BAND_EDGES[:-1])
    top = colors.BAND_EDGES[i] if i < len(colors.BAND_EDGES) - 1 else colors.BAND_EDGES[-1] * 1.5
    return (lowers[i] + top) / 2


class LegendBar(QFrame):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.swatches: dict[str, list[QColor]] = {"blue": [], "orange": []}
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._tag("Result:"))
        layout.addWidget(self._chip("UP", theme.UP))
        layout.addWidget(self._chip("DOWN", theme.DOWN))
        for name, sign, label in (("blue", 1, "Change +"), ("orange", -1, "Change −")):
            layout.addSpacing(12)
            layout.addWidget(self._tag(label))
            for i, band in enumerate(LEGEND_BANDS):
                fill = colors.net_color(sign * _mid(i), "dark")
                self.swatches[name].append(QColor(fill))
                layout.addWidget(self._chip(band, fill))
        layout.addStretch(1)

    @staticmethod
    def _tag(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("muted")
        return label

    @staticmethod
    def _chip(text: str, fill: str) -> QLabel:
        label = QLabel(text)
        label.setStyleSheet(f"background: {fill}; color: {colors.text_on(fill)}; border-radius: 6px; padding: 1px 6px; font-size: 11px;")
        return label
