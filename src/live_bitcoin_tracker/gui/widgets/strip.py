"""The 96-window strip: one small cell per window, left half = result colour, right half = net-change colour."""

from dataclasses import dataclass

from PySide6.QtCore import QPoint, QRect, QRectF, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QToolTip, QWidget

from live_bitcoin_tracker.gui import theme
from live_bitcoin_tracker.gui.viewmodel import RowVM

PER_ROW = 24
CELLS = 96
GAP = 3


@dataclass(frozen=True)
class StripCell:
    result: QColor | None
    change: QColor | None
    tip: str


class StripWidget(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.cells: list[StripCell] = []
        self.setMouseTracking(True)
        self.setMinimumHeight(120)

    def set_rows(self, rows: list[RowVM]) -> None:
        self.cells = [StripCell(QColor(r.result_fill) if r.result_fill else None,
                                QColor(r.chg_fill) if r.chg_fill else None,
                                f"{r.label}  {r.chg_text}") for r in rows[:CELLS]]
        self.update()

    def cell_rect(self, i: int) -> QRect:
        rows = -(-CELLS // PER_ROW)
        size = max(6, min((self.width() - GAP) // PER_ROW, (self.height() - GAP) // rows)) - GAP
        return QRect(GAP + (i % PER_ROW) * (size + GAP), GAP + (i // PER_ROW) * (size + GAP), size, size)

    def tooltip_at(self, point: QPoint) -> str | None:
        for i, cell in enumerate(self.cells):
            if self.cell_rect(i).contains(point):
                return cell.tip
        return None

    def event(self, event) -> bool:
        if event.type() == event.Type.ToolTip:
            tip = self.tooltip_at(event.pos())
            QToolTip.showText(event.globalPos(), tip, self) if tip else QToolTip.hideText()
            return True
        return super().event(event)

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setPen(Qt.PenStyle.NoPen)
        for i, cell in enumerate(self.cells):
            rect = QRectF(self.cell_rect(i))
            if cell.result is None and cell.change is None:  # a gap or an unsettled window
                painter.setBrush(QColor(theme.MUTED).darker(300))
                painter.drawRoundedRect(rect, 3, 3)
                continue
            half = rect.width() / 2
            painter.setBrush(cell.result or QColor(theme.CARD))
            painter.drawRoundedRect(QRectF(rect.left(), rect.top(), half + 2, rect.height()), 3, 3)
            painter.setBrush(cell.change or QColor(theme.CARD))
            painter.drawRoundedRect(QRectF(rect.left() + half, rect.top(), half, rect.height()), 3, 3)
