from datetime import datetime, timedelta, timezone

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QModelIndex, Qt  # noqa: E402
from PySide6.QtGui import QColor  # noqa: E402

from live_bitcoin_tracker import colors  # noqa: E402
from live_bitcoin_tracker.gui import theme  # noqa: E402
from live_bitcoin_tracker.gui.viewmodel import RowVM, table_rows  # noqa: E402
from live_bitcoin_tracker.gui.widgets.history_table import COLUMNS, HistoryModel, HistoryTable  # noqa: E402
from live_bitcoin_tracker.gui.widgets.legend import LegendBar  # noqa: E402
from live_bitcoin_tracker.gui.widgets.statusbar import StatusBar  # noqa: E402
from live_bitcoin_tracker.gui.widgets.strip import StripWidget  # noqa: E402
from live_bitcoin_tracker.model import Window  # noqa: E402
from live_bitcoin_tracker.state import WidgetState  # noqa: E402
from live_bitcoin_tracker.windows import floor_window  # noqa: E402

UTC = timezone.utc
STEP = timedelta(minutes=15)
NOW = datetime(2026, 10, 2, 21, 5, 30, tzinfo=UTC)


def state(index=None):
    live = floor_window(NOW)
    windows = [Window(live - i * STEP, open=84000.0, close=None if i == 0 else 84000.0 + (30 if i % 2 else -120))
               for i in range(96, -1, -1)]
    s = WidgetState()
    s.set_history(windows, NOW)
    if index is not None:
        s.apply_index(index, NOW)
    return s


def rows(index=84044.04):
    return table_rows(state(index), NOW)


def cell(model, row, col, role):
    return model.data(model.index(row, col), role)


# ---- model ------------------------------------------------------------------------------------
def test_model_shape_and_headers(qapp):
    model = HistoryModel()
    model.set_rows(rows())
    assert model.rowCount() == 97 and model.columnCount() == len(COLUMNS) == 6
    assert [model.headerData(i, Qt.Orientation.Horizontal) for i in range(6)] == \
        ["Window (ET)", "Open", "Close", "Chg $", "Chg %", "Result"]


def test_model_header_follows_the_time_zone_toggle(qapp):
    model = HistoryModel()
    model.set_local_time(True)
    assert model.headerData(0, Qt.Orientation.Horizontal) == "Window (local)"


def test_model_cell_colors_match_row_fills(qapp):
    model = HistoryModel()
    data = rows()
    model.set_rows(data)
    settled = next(i for i, r in enumerate(data) if r.result_fill)
    r = data[settled]
    assert cell(model, settled, 3, Qt.ItemDataRole.BackgroundRole) == QColor(r.chg_fill)
    assert cell(model, settled, 4, Qt.ItemDataRole.BackgroundRole) == QColor(r.chg_fill)
    assert cell(model, settled, 5, Qt.ItemDataRole.BackgroundRole) == QColor(r.result_fill)
    assert cell(model, settled, 3, Qt.ItemDataRole.ForegroundRole) == QColor(colors.text_on(r.chg_fill))
    assert cell(model, settled, 5, Qt.ItemDataRole.ForegroundRole) == QColor(colors.text_on(r.result_fill))
    assert cell(model, settled, 0, Qt.ItemDataRole.BackgroundRole) is None


def test_model_text_and_alignment(qapp):
    model = HistoryModel()
    data = rows()
    model.set_rows(data)
    assert cell(model, 3, 0, Qt.ItemDataRole.DisplayRole) == data[3].label
    assert cell(model, 3, 3, Qt.ItemDataRole.DisplayRole) == data[3].chg_text
    assert cell(model, 3, 5, Qt.ItemDataRole.DisplayRole) == data[3].result_text
    assert cell(model, 3, 3, Qt.ItemDataRole.TextAlignmentRole) == Qt.AlignmentFlag.AlignCenter
    assert cell(model, 3, 1, Qt.ItemDataRole.TextAlignmentRole) == (Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)


def test_model_live_row_has_no_result_fill_but_a_change_fill(qapp):
    model = HistoryModel()
    model.set_rows(rows())
    last = 96
    assert cell(model, last, 5, Qt.ItemDataRole.DisplayRole) == "UP?"
    assert cell(model, last, 5, Qt.ItemDataRole.BackgroundRole) is None
    assert cell(model, last, 5, Qt.ItemDataRole.ForegroundRole) == QColor(theme.UP)
    assert cell(model, last, 3, Qt.ItemDataRole.BackgroundRole) == QColor(colors.net_color(44.04, "dark"))
    assert cell(model, last, 0, Qt.ItemDataRole.FontRole).bold() is True


def test_model_not_editable_and_out_of_range_safe(qapp):
    model = HistoryModel()
    model.set_rows(rows())
    assert not (model.flags(model.index(0, 0)) & Qt.ItemFlag.ItemIsEditable)
    assert model.data(QModelIndex(), Qt.ItemDataRole.DisplayRole) is None
    assert model.data(model.index(500, 0), Qt.ItemDataRole.DisplayRole) is None


def test_model_missing_market_row_text(qapp):
    model = HistoryModel()
    model.set_rows([RowVM("x", "-", "-", "-", "-", "none", None, None, False, "no market")])
    assert cell(model, 0, 5, Qt.ItemDataRole.DisplayRole) == "none"


# ---- table view -------------------------------------------------------------------------------
def test_table_scrolls_to_newest_row_on_first_fill(qapp):
    table = HistoryTable()
    table.resize(640, 300)
    table.show()
    table.set_rows(rows())
    qapp.processEvents()
    bar = table.verticalScrollBar()
    assert bar.value() == bar.maximum() > 0


def test_table_follows_newest_row_until_user_scrolls(qapp):
    table = HistoryTable()
    table.resize(640, 300)
    table.show()
    table.set_rows(rows())
    qapp.processEvents()
    bar = table.verticalScrollBar()
    bar.setValue(bar.minimum())  # the user scrolls to the top
    table.set_rows(rows(84050.0))
    qapp.processEvents()
    assert bar.value() == bar.minimum()  # still where the user left it
    bar.setValue(bar.maximum())
    table.set_rows(rows(84051.0))
    qapp.processEvents()
    assert bar.value() == bar.maximum()


def test_table_is_read_only_and_selectionless(qapp):
    table = HistoryTable()
    assert table.editTriggers() == table.EditTrigger.NoEditTriggers
    assert table.selectionMode() == table.SelectionMode.NoSelection


# ---- strip ------------------------------------------------------------------------------------
def test_strip_has_96_cells_and_tooltips(qapp):
    strip = StripWidget()
    strip.resize(720, 200)
    strip.set_rows(rows())
    assert len(strip.cells) == 96  # the live row is not part of the strip
    assert strip.tooltip_at(strip.cell_rect(0).center()) == rows()[0].label + "  " + rows()[0].chg_text
    assert not strip.grab().isNull()


def test_strip_cell_colours_follow_the_rows(qapp):
    strip = StripWidget()
    data = rows()
    strip.set_rows(data)
    i = next(i for i, r in enumerate(data[:96]) if r.result_fill)
    assert strip.cells[i].result == QColor(data[i].result_fill)
    assert strip.cells[i].change == QColor(data[i].chg_fill)


def test_strip_gap_cells_are_neutral(qapp):
    strip = StripWidget()
    strip.set_rows([RowVM("x", "-", "-", "-", "-", "gap", None, None, False, "boom")] * 96 + [])
    assert strip.cells[0].result is None and strip.cells[0].change is None
    assert not strip.grab().isNull()


# ---- legend / status --------------------------------------------------------------------------
def test_legend_lists_nine_bands_each_sign(qapp):
    from PySide6.QtWidgets import QLabel

    legend = LegendBar()
    swatches = legend.swatches
    assert len(swatches["blue"]) == 9 and len(swatches["orange"]) == 9
    assert swatches["blue"][0] == QColor(colors.net_color(5, "dark"))
    assert swatches["orange"][-1] == QColor(colors.net_color(-1500, "dark"))
    shown = " ".join(label.text() for label in legend.findChildren(QLabel))
    assert "1000+" in shown and "UP" in shown and "DOWN" in shown


def test_statusbar_text(qapp):
    bar = StatusBar()
    bar.set_text("feed: live (keyless)")
    assert bar.text() == "feed: live (keyless)"
    bar.set_text("feed: live\nError: boom")
    assert "Error: boom" in bar.text()


def test_model_identical_rows_do_not_reset_the_view(qapp):
    model = HistoryModel()
    resets = []
    model.modelReset.connect(lambda: resets.append(1))
    model.set_rows(rows())
    model.set_rows(rows())  # the window repaints once a second; unchanged data must not disturb scrolling
    assert len(resets) == 1
    model.set_rows(rows(84099.0))
    assert len(resets) == 2
