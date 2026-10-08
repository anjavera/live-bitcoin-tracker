"""The coin: an orange ring that is the analog countdown, a white B in the middle."""

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget

from live_bitcoin_tracker.gui import theme

START_ANGLE = 90 * 16  # Qt measures in 1/16 degrees from 3 o'clock, counter-clockwise; 12 o'clock is 90 degrees
FULL_TURN = 360 * 16
USED_WITHOUT_LEAN = QColor("#9a6a2a")


def arc_spans(fraction: float) -> tuple[tuple[int, int], tuple[int, int]]:
    """((start, span) of the used arc, (start, span) of the arc still to go), clockwise from 12 o'clock."""
    f = min(max(fraction, 0.0), 1.0)
    used = round(FULL_TURN * f)
    return (START_ANGLE, -used), (START_ANGLE - used, -(FULL_TURN - used))


class CoinWidget(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.fraction = 0.0
        self.used_color = QColor(USED_WITHOUT_LEAN)
        self.setMinimumSize(72, 72)

    def set_progress(self, elapsed_fraction: float, lean: str | None) -> None:
        self.fraction = min(max(elapsed_fraction, 0.0), 1.0)
        self.used_color = QColor(theme.UP if lean == "UP" else theme.DOWN if lean == "DOWN" else USED_WITHOUT_LEAN)
        self.update()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        side = min(self.width(), self.height())
        width = max(4.0, side * 0.09)
        rect = QRectF((self.width() - side) / 2 + width, (self.height() - side) / 2 + width,
                      side - 2 * width, side - 2 * width)
        (used_start, used_span), (left_start, left_span) = arc_spans(self.fraction)
        for color, start, span in ((QColor(theme.BTC_ORANGE), left_start, left_span), (self.used_color, used_start, used_span)):
            pen = QPen(color, width)
            pen.setCapStyle(Qt.PenCapStyle.FlatCap)
            painter.setPen(pen)
            if span:
                painter.drawArc(rect, start, span)
        painter.setPen(QPen(QColor(theme.TEXT)))  # the white hand marks "now" on the ring
        hand = QPen(QColor(theme.TEXT), width * 1.1)
        hand.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(hand)
        painter.drawArc(rect, START_ANGLE - round(FULL_TURN * self.fraction) - 16 * 2, 16 * 4)
        font = QFont(self.font())
        font.setBold(True)
        font.setPixelSize(max(10, int(side * 0.42)))
        painter.setFont(font)
        painter.setPen(QColor(theme.TEXT))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "₿")
