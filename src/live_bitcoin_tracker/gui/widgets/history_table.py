"""The 24-hour history table: a read-only QTableView over a model whose colours come from the view-model rows."""

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import QAbstractItemView, QHeaderView, QTableView

from live_bitcoin_tracker import colors
from live_bitcoin_tracker.gui import theme
from live_bitcoin_tracker.gui.viewmodel import RowVM, window_column_title

COLUMNS = ["Window (ET)", "Open", "Close", "Chg $", "Chg %", "Result"]
ALIGN_CENTER = Qt.AlignmentFlag.AlignCenter
ALIGN_RIGHT = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
ALIGN_LEFT = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter


class HistoryModel(QAbstractTableModel):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._rows: list[RowVM] = []
        self._local_time = False

    def set_rows(self, rows: list[RowVM]) -> None:
        if rows == self._rows:
            return  # repainted every second: leave the view (and the user's scroll position) alone
        self.beginResetModel()
        self._rows = rows
        self.endResetModel()

    def set_local_time(self, local_time: bool) -> None:
        self._local_time = local_time
        self.headerDataChanged.emit(Qt.Orientation.Horizontal, 0, 0)

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(COLUMNS)

    def headerData(self, section: int, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole and 0 <= section < len(COLUMNS):
            return window_column_title(self._local_time) if section == 0 else COLUMNS[section]
        return None

    def flags(self, index: QModelIndex):
        return Qt.ItemFlag.ItemIsEnabled if index.isValid() else Qt.ItemFlag.NoItemFlags

    def _fill(self, row: RowVM, col: int) -> str | None:
        return row.chg_fill if col in (3, 4) else row.result_fill if col == 5 else None

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self._rows) or not 0 <= index.column() < len(COLUMNS):
            return None
        row, col = self._rows[index.row()], index.column()
        if role == Qt.ItemDataRole.DisplayRole:
            return (row.label, row.open_text, row.close_text, row.chg_text, row.pct_text, row.result_text)[col]
        if role == Qt.ItemDataRole.BackgroundRole:
            fill = self._fill(row, col)
            return QColor(fill) if fill else None
        if role == Qt.ItemDataRole.ForegroundRole:
            fill = self._fill(row, col)
            if fill:
                return QColor(colors.text_on(fill))
            if col == 5 and row.result_text in ("UP?", "DOWN?"):  # provisional lean: coloured text, no fill
                return QColor(theme.UP if row.result_text == "UP?" else theme.DOWN)
            if col in (3, 4, 5) and not row.live and row.result_text in ("none", "gap", "-"):
                return QColor(theme.MUTED)
            return None
        if role == Qt.ItemDataRole.TextAlignmentRole:
            return ALIGN_LEFT if col == 0 else ALIGN_RIGHT if col in (1, 2) else ALIGN_CENTER
        if role == Qt.ItemDataRole.FontRole:
            font = QFont()
            font.setBold(row.live or col == 5)
            return font
        return None


class HistoryTable(QTableView):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._model = HistoryModel(self)
        self._follow = True  # start on the newest row
        self.setModel(self._model)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setShowGrid(True)
        self.verticalHeader().hide()
        self.verticalHeader().setDefaultSectionSize(26)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)

    def set_local_time(self, local_time: bool) -> None:
        self._model.set_local_time(local_time)

    def follow_newest(self) -> None:
        """Jump to the newest row on the next update (used when another time frame is shown)."""
        self._follow = True

    def set_rows(self, rows: list[RowVM]) -> None:
        bar = self.verticalScrollBar()
        following = self._follow or bar.value() >= bar.maximum()  # stay on the newest row unless the user scrolled up
        self._model.set_rows(rows)
        if following:
            self.doItemsLayout()  # the scroll range is only updated by a layout pass: without it the jump falls short
            self.scrollToBottom()
            bar.setValue(bar.maximum())
            self._follow = False
