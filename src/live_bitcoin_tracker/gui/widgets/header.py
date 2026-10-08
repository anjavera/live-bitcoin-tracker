"""Top card: title, price to beat, current price, gap and the countdown with its ring coin."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from live_bitcoin_tracker.gui import theme
from live_bitcoin_tracker.gui.viewmodel import HeaderVM
from live_bitcoin_tracker.gui.widgets.coin import CoinWidget


def _label(text: str = "", name: str = "") -> QLabel:
    label = QLabel(text)
    if name:
        label.setObjectName(name)
    return label


class HeaderCard(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("card")
        self.title = _label("BTC UP OR DOWN 15M", "muted")
        self.beat_caption, self.price_caption = _label("Price to beat", "muted"), _label("Current price", "muted")
        self.beat_label, self.price_label = _label("—", "big"), _label("—", "big")
        self.gap_label, self.source_label = _label(""), _label("", "muted")
        self.countdown_label = _label("--:--", "title")
        self.coin = CoinWidget()
        grid = QGridLayout()
        grid.addWidget(self.beat_caption, 0, 0)
        grid.addWidget(self.price_caption, 0, 1)
        grid.addWidget(self.beat_label, 1, 0)
        price_row = QHBoxLayout()
        price_row.addWidget(self.price_label)
        price_row.addWidget(self.gap_label)
        price_row.addStretch(1)
        grid.addLayout(price_row, 1, 1)
        grid.addWidget(self.source_label, 2, 1)
        grid.setColumnStretch(1, 1)
        left = QVBoxLayout()
        left.addWidget(self.title)
        left.addLayout(grid)
        right = QVBoxLayout()
        right.addWidget(self.coin, 0, Qt.AlignmentFlag.AlignHCenter)
        right.addWidget(self.countdown_label, 0, Qt.AlignmentFlag.AlignHCenter)
        outer = QHBoxLayout(self)
        outer.setContentsMargins(20, 16, 20, 16)
        outer.addLayout(left, 1)
        outer.addLayout(right)

    def set_vm(self, vm: HeaderVM) -> None:
        self.price_label.setText(f"≈ {vm.price_text}" if vm.approx and vm.source else vm.price_text)
        self.beat_label.setText(vm.beat_text)
        self.gap_label.setText(vm.gap_text if vm.gap_text != "—" else "—")
        colour = theme.UP if vm.gap_sign > 0 else theme.DOWN if vm.gap_sign < 0 else theme.MUTED
        self.gap_label.setStyleSheet(f"color: {colour}; font-weight: 600;")
        self.source_label.setText(vm.caption)
        self.countdown_label.setText(vm.countdown)
        self.coin.set_progress(vm.elapsed_fraction, vm.lean)
