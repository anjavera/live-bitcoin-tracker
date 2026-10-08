"""Up / Down odds as percent and cents with a split probability bar. Read-only: no trading controls."""

from PySide6.QtCore import QRectF
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QVBoxLayout, QWidget

from live_bitcoin_tracker.gui import theme
from live_bitcoin_tracker.gui.viewmodel import OddsVM


class _Bar(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.fraction: float | None = None
        self.setFixedHeight(10)

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect())
        painter.setPen(QColor(0, 0, 0, 0))
        painter.setBrush(QColor(theme.MUTED).darker(300))
        painter.drawRoundedRect(rect, 5, 5)
        if self.fraction is not None:
            up = QRectF(rect.left(), rect.top(), rect.width() * self.fraction, rect.height())
            painter.setBrush(QColor(theme.UP))
            painter.drawRoundedRect(up, 5, 5)
            down = QRectF(up.right(), rect.top(), rect.width() - up.width(), rect.height())
            painter.setBrush(QColor(theme.DOWN))
            painter.drawRoundedRect(down, 5, 5)


class OddsCard(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("card")
        self.up_name, self.down_name = QLabel("Up"), QLabel("Down")
        self.up_value, self.down_value = QLabel("—"), QLabel("—")
        self.up_value.setStyleSheet(f"color: {theme.UP}; font-weight: 700;")
        self.down_value.setStyleSheet(f"color: {theme.DOWN}; font-weight: 700;")
        self.up_cents, self.down_cents = QLabel("—"), QLabel("—")
        self.spread_label = QLabel("")
        self.spread_label.setObjectName("muted")
        self.state_pill = QLabel("")
        self.state_pill.setObjectName("pill")
        self.state_pill.setStyleSheet(f"background: {theme.BTC_ORANGE}; color: {theme.PAGE}; border-radius: 10px; padding: 2px 10px;")
        self.state_pill.hide()
        self.stale_label = QLabel("")
        self.stale_label.setObjectName("muted")
        self.bar = _Bar()
        grid = QGridLayout()
        for row, widgets in enumerate(((self.up_name, self.up_value, self.up_cents), (self.down_name, self.down_value, self.down_cents))):
            for col, w in enumerate(widgets):
                grid.addWidget(w, row, col)
        grid.setColumnStretch(0, 1)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 14, 20, 14)
        layout.addLayout(grid)
        layout.addWidget(self.bar)
        layout.addWidget(self.spread_label)
        layout.addWidget(self.stale_label)
        layout.addWidget(self.state_pill)

    @property
    def bar_fraction(self) -> float | None:
        return self.bar.fraction

    def set_vm(self, vm: OddsVM) -> None:
        dash = "—"
        self.up_value.setText(dash if vm.up_pct is None else f"{vm.up_pct}%")
        self.down_value.setText(dash if vm.down_pct is None else f"{vm.down_pct}%")
        self.up_cents.setText(dash if vm.up_cents is None else f"{vm.up_cents}¢")
        self.down_cents.setText(dash if vm.down_cents is None else f"{vm.down_cents}¢")
        self.bar.fraction = None if vm.up_pct is None else vm.up_pct / 100
        self.bar.update()
        self.spread_label.setText(f"{dash}" if vm.spread_text == dash else vm.spread_text)
        self.stale_label.setText("stale" if vm.stale else "")
        self.state_pill.setText(vm.state_label or "")
        self.state_pill.setVisible(bool(vm.state_label))
