"""Colour key: the nine change bands (each chip is blue for a rise over orange for a fall) and the green/red result marks."""

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel

from live_bitcoin_tracker import colors
from live_bitcoin_tracker.gui import theme
from live_bitcoin_tracker.gui.viewmodel import LEGEND_BANDS, legend_bands
from live_bitcoin_tracker.timeframes import Timeframe


def _mid(i: int) -> float:
    lowers = (0, *colors.BAND_EDGES[:-1])
    top = colors.BAND_EDGES[i] if i < len(colors.BAND_EDGES) - 1 else colors.BAND_EDGES[-1] * 1.5
    return (lowers[i] + top) / 2


def _short(label: str) -> str:
    """'1000' -> '1k', '10000+' -> '10k+': keeps the key narrow enough for the smallest window."""
    plus = label.endswith("+")
    number = int(label.rstrip("+"))
    text = f"{number // 1000}k" if number >= 1000 and number % 1000 == 0 else str(number)
    return text + ("+" if plus else "")


class LegendBar(QFrame):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.swatches: dict[str, list[QColor]] = {"blue": [], "orange": []}
        self.band_labels: list[QLabel] = []
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addWidget(self._tag("Result"))
        layout.addWidget(self._chip("UP", theme.UP))
        layout.addWidget(self._chip("DOWN", theme.DOWN))
        layout.addSpacing(10)
        layout.addWidget(self._tag("Change $"))
        for i, band in enumerate(LEGEND_BANDS):
            blue, orange = colors.net_color(_mid(i), "dark"), colors.net_color(-_mid(i), "dark")
            self.swatches["blue"].append(QColor(blue))
            self.swatches["orange"].append(QColor(orange))
            chip = self._band_chip(_short(band), blue, orange)
            self.band_labels.append(chip)
            layout.addWidget(chip)
        layout.addWidget(self._tag("blue = up, orange = down"))
        layout.addStretch(1)

    def set_timeframe(self, timeframe: Timeframe) -> None:
        """Relabel the change bands in dollars for this frame (the colours stay: they are shades, not amounts)."""
        for chip, label in zip(self.band_labels, legend_bands(timeframe)):
            chip.setText(_short(label))

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

    @staticmethod
    def _band_chip(text: str, blue: str, orange: str) -> QLabel:
        label = QLabel(text)
        label.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:0, y2:1, "
                            f"stop:0 {blue}, stop:0.5 {blue}, stop:0.51 {orange}, stop:1 {orange}); "
                            f"color: {colors.text_on(blue)}; border-radius: 6px; padding: 2px 5px; font-size: 11px;")
        return label
