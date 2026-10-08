"""Live price chart for the current 15-minute window, drawn with QPainter (no QtCharts dependency)."""

from datetime import datetime, timedelta

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

from btc15_widget.gui import theme
from btc15_widget.gui.series import WINDOW_SECONDS, ChartPoint, y_range
from btc15_widget.render import ET

LABEL_EVERY = 120  # seconds between time labels
MARGIN_LEFT, MARGIN_RIGHT, MARGIN_TOP, MARGIN_BOTTOM = 64, 16, 12, 26
GRID_LINES = 4


def map_point(p: ChartPoint, start: datetime, width: float, height: float, lo: float, hi: float) -> tuple[float, float]:
    """Pixel position of a point inside a plot area `width` x `height` (y grows downward, `hi` at the top)."""
    x = (p.t - start.timestamp()) / WINDOW_SECONDS * width
    y = height / 2 if hi == lo else (hi - p.price) / (hi - lo) * height
    return x, y


def time_labels(start: datetime, local_time: bool) -> list[tuple[int, str]]:
    """(seconds from window start, label) every two minutes, e.g. (120, '5:02pm')."""
    out = []
    for offset in range(0, WINDOW_SECONDS, LABEL_EVERY):
        t = start + timedelta(seconds=offset)
        t = t.astimezone() if local_time else t.astimezone(ET)
        out.append((offset, f"{t.hour % 12 or 12}:{t.minute:02d}{'am' if t.hour < 12 else 'pm'}"))
    return out


class PriceChart(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.points: list[ChartPoint] = []
        self.start: datetime | None = None
        self.beat: float | None = None
        self.caption = ""
        self.local_time = False
        self.y_bounds: tuple[float, float] = (0.0, 1.0)
        self.setMinimumHeight(200)

    @property
    def empty(self) -> bool:
        return not self.points

    def set_data(self, points: list[ChartPoint], start: datetime, beat: float | None, caption: str,
                 local_time: bool = False) -> None:
        self.points, self.start, self.beat, self.caption, self.local_time = points, start, beat, caption, local_time
        self.y_bounds = y_range(points, beat)
        self.update()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        area = QRectF(MARGIN_LEFT, MARGIN_TOP, max(10, self.width() - MARGIN_LEFT - MARGIN_RIGHT),
                      max(10, self.height() - MARGIN_TOP - MARGIN_BOTTOM))
        muted = QColor(theme.MUTED)
        small = QFont(self.font())
        small.setPixelSize(12)
        painter.setFont(small)
        if self.start is None or self.empty:
            painter.setPen(muted)
            painter.drawText(area, Qt.AlignmentFlag.AlignCenter, "Waiting for price data")
            return
        lo, hi = self.y_bounds
        dotted = QPen(QColor(theme.MUTED).darker(160), 1, Qt.PenStyle.DotLine)
        for i in range(GRID_LINES + 1):  # dotted horizontal grid with price labels, as on Polymarket's chart
            y = area.top() + area.height() * i / GRID_LINES
            painter.setPen(dotted)
            painter.drawLine(QPointF(area.left(), y), QPointF(area.right(), y))
            painter.setPen(muted)
            painter.drawText(QRectF(0, y - 9, MARGIN_LEFT - 8, 18), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                             f"${hi - (hi - lo) * i / GRID_LINES:,.0f}")
        for offset, label in time_labels(self.start, self.local_time):
            x = area.left() + offset / WINDOW_SECONDS * area.width()
            painter.drawText(QRectF(x - 30, area.bottom() + 6, 60, 16), Qt.AlignmentFlag.AlignCenter, label)

        def at(p: ChartPoint) -> QPointF:
            x, y = map_point(p, self.start, area.width(), area.height(), lo, hi)
            return QPointF(area.left() + x, area.top() + y)

        if self.beat is not None:  # the price to beat: dashed line across the window
            _, by = map_point(ChartPoint(int(self.start.timestamp()), self.beat), self.start, area.width(), area.height(), lo, hi)
            painter.setPen(QPen(QColor(theme.TEXT), 1.2, Qt.PenStyle.DashLine))
            painter.drawLine(QPointF(area.left(), area.top() + by), QPointF(area.right(), area.top() + by))
        path = QPainterPath()
        coords = [at(p) for p in self.points]
        path.moveTo(coords[0])
        for c in coords[1:]:
            path.lineTo(c)
        last = self.points[-1]
        above = self.beat is None or last.price >= self.beat
        fill = QColor("#1f5fd6" if above else "#e0620d")  # blue above the price to beat, orange below
        fill.setAlpha(46)
        shade = QPainterPath(path)
        shade.lineTo(QPointF(coords[-1].x(), area.bottom()))
        shade.lineTo(QPointF(coords[0].x(), area.bottom()))
        shade.closeSubpath()
        painter.fillPath(shade, fill)
        painter.setPen(QPen(QColor(theme.TEXT), 1.75, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        painter.drawPath(path)
        painter.setPen(Qt.PenStyle.NoPen)  # the latest price: Bitcoin-orange dot
        painter.setBrush(QColor(theme.BTC_ORANGE))
        painter.drawEllipse(coords[-1], 5, 5)
        if self.caption:
            painter.setPen(muted)
            painter.drawText(QRectF(area.left(), 0, area.width(), MARGIN_TOP + 2), Qt.AlignmentFlag.AlignRight, self.caption)
