"""The strip: one small cell per past window (96, 24 or 30), left half = result colour, right half = net-change colour."""

from dataclasses import dataclass

from PySide6.QtCore import QPoint, QRect, QRectF, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QToolTip, QWidget

from live_bitcoin_tracker.gui import theme
from live_bitcoin_tracker.gui.viewmodel import RowVM

CELLS = 96
GAP = 3


def per_row(count: int) -> int:
    """Cells per row: 96 -> 4 rows of 24, 24 -> one row, 30 -> two rows of 15."""
    return count if count <= 24 else 24 if count % 24 == 0 else 15


@dataclass(frozen=True)
class StripCell:
    result: QColor | None
    change: QColor | None
    tip: str


class StripWidget(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.cells: list[StripCell] = []
        self.count = CELLS
        self.setMouseTracking(True)
        self.setMinimumHeight(120)

    def set_rows(self, rows: list[RowVM], count: int = CELLS) -> None:
        """One cell for each of the first `count` rows (the live row is not part of the strip)."""
        self.count = count
        self.cells = [StripCell(QColor(r.result_fill) if r.result_fill else None,
                                QColor(r.chg_fill) if r.chg_fill else None,
                                f"{r.label}  {r.chg_text}") for r in rows[:count]]
        self.update()

    def cell_rect(self, i: int) -> QRect:
        across = per_row(self.count)
        rows = -(-self.count // across)
        size = max(6, min((self.width() - GAP) // across, (self.height() - GAP) // rows)) - GAP
        return QRect(GAP + (i % across) * (size + GAP), GAP + (i // across) * (size + GAP), size, size)

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
