from datetime import datetime, timezone

import pytest

pytest.importorskip("PySide6")

from PySide6.QtGui import QColor  # noqa: E402

from live_bitcoin_tracker.gui import theme  # noqa: E402
from live_bitcoin_tracker.gui.series import ChartPoint  # noqa: E402
from live_bitcoin_tracker.gui.viewmodel import HeaderVM, OddsVM  # noqa: E402
from live_bitcoin_tracker.gui.widgets.chart import PriceChart, map_point, time_labels  # noqa: E402
from live_bitcoin_tracker.gui.widgets.coin import CoinWidget, arc_spans  # noqa: E402
from live_bitcoin_tracker.gui.widgets.header import HeaderCard  # noqa: E402
from live_bitcoin_tracker.gui.widgets.odds import OddsCard  # noqa: E402

START = datetime(2026, 10, 2, 21, 0, tzinfo=timezone.utc)
T0 = int(START.timestamp())


def texts(widget):
    from PySide6.QtWidgets import QLabel

    return [label.text() for label in widget.findChildren(QLabel)]


def not_blank(pixmap) -> bool:
    image = pixmap.toImage()
    first = image.pixel(0, 0)
    return any(image.pixel(x, y) != first for x in range(0, image.width(), 7) for y in range(0, image.height(), 7))


# ---- chart geometry (pure) --------------------------------------------------------------------
def test_map_point_corners():
    assert map_point(ChartPoint(T0, 110.0), START, 800, 200, 100.0, 110.0) == (0.0, 0.0)
    assert map_point(ChartPoint(T0 + 900, 100.0), START, 800, 200, 100.0, 110.0) == (800.0, 200.0)
    x, y = map_point(ChartPoint(T0 + 450, 105.0), START, 800, 200, 100.0, 110.0)
    assert (x, y) == (400.0, 100.0)


def test_map_point_degenerate_range_does_not_divide_by_zero():
    assert map_point(ChartPoint(T0, 5.0), START, 100, 50, 5.0, 5.0)[1] == 25.0


def test_time_labels_every_two_minutes_in_the_chosen_zone():
    labels = time_labels(START, local_time=False)
    assert [offset for offset, _ in labels] == [0, 120, 240, 360, 480, 600, 720, 840]
    assert labels[0][1] == "5:00pm" and labels[1][1] == "5:02pm"  # 21:00Z is 17:00 EDT


# ---- chart widget -----------------------------------------------------------------------------
def test_chart_empty_state_renders(qapp):
    chart = PriceChart()
    chart.resize(600, 250)
    chart.set_data([], START, None, "")
    assert not chart.grab().isNull() and chart.empty is True


def test_chart_renders_with_points_and_beat(qapp):
    chart = PriceChart()
    chart.resize(600, 250)
    points = [ChartPoint(T0 + i, 84400.0 + i) for i in range(0, 300, 5)]
    chart.set_data(points, START, 84445.85, "Polymarket index")
    assert chart.empty is False and not_blank(chart.grab())


def test_chart_beat_outside_range_still_in_view(qapp):
    chart = PriceChart()
    chart.resize(600, 250)
    chart.set_data([ChartPoint(T0, 100.0), ChartPoint(T0 + 10, 101.0)], START, 500.0, "")
    lo, hi = chart.y_bounds
    assert lo < 100.0 and hi > 500.0
    assert not chart.grab().isNull()


def test_chart_caption_is_kept_for_the_approx_notice(qapp):
    chart = PriceChart()
    chart.set_data([ChartPoint(T0, 1.0)], START, None, "approx. (exchange composite)")
    assert chart.caption == "approx. (exchange composite)"


# ---- coin -------------------------------------------------------------------------------------
def test_arc_spans_split_the_ring_at_the_elapsed_fraction():
    assert arc_spans(0.0)[0][1] == 0 and arc_spans(1.0)[1][1] == 0
    used, left = arc_spans(0.5)
    assert used[1] == -180 * 16 and left[1] == -180 * 16
    assert used[0] == 90 * 16 and left[0] == 90 * 16 - 180 * 16  # clockwise from 12 o'clock


def test_coin_progress_clamped(qapp):
    coin = CoinWidget()
    coin.resize(120, 120)
    for fraction in (-0.2, 0.0, 0.5, 1.0, 1.5):
        coin.set_progress(fraction, None)
        assert not coin.grab().isNull()
    assert coin.fraction == 1.0


def test_coin_used_arc_colour_follows_the_lean(qapp):
    coin = CoinWidget()
    coin.set_progress(0.4, "UP")
    assert coin.used_color == QColor(theme.UP)
    coin.set_progress(0.4, "DOWN")
    assert coin.used_color == QColor(theme.DOWN)
    coin.set_progress(0.4, None)
    assert coin.used_color != QColor(theme.UP) and coin.used_color != QColor(theme.DOWN)


# ---- header card ------------------------------------------------------------------------------
def header_vm(**over):
    base = dict(price_text="$84,489.89", approx=False, beat_text="$84,445.85", gap_text="+$44.04", gap_sign=1,
                countdown="04:12", elapsed_fraction=0.72, lean="UP", source="index", caption="Polymarket index")
    base.update(over)
    return HeaderVM(**base)


def test_header_card_shows_texts(qapp):
    card = HeaderCard()
    card.set_vm(header_vm())
    shown = texts(card)
    for expected in ("$84,489.89", "$84,445.85", "+$44.04", "04:12", "Polymarket index", "BTC UP OR DOWN · 15 MIN"):
        assert expected in shown


def test_header_card_marks_estimates_and_colours_the_gap(qapp):
    card = HeaderCard()
    card.set_vm(header_vm(approx=True, source="proxy", caption="approx. (exchange composite)"))
    assert "≈ $84,489.89" in texts(card)
    card.set_vm(header_vm(gap_sign=-1, gap_text="-$3.00"))
    assert theme.DOWN in card.gap_label.styleSheet()
    card.set_vm(header_vm(gap_sign=1))
    assert theme.UP in card.gap_label.styleSheet()


def test_header_card_without_data_shows_dashes(qapp):
    card = HeaderCard()
    card.set_vm(header_vm(price_text="—", beat_text="—", gap_text="—", gap_sign=0, lean=None, source=None, caption=""))
    assert texts(card).count("—") >= 3


# ---- odds card --------------------------------------------------------------------------------
def odds_vm(**over):
    base = dict(up_pct=92, down_pct=8, up_cents=92, down_cents=8, spread_text="0.02", state_label=None, stale=False)
    base.update(over)
    return OddsVM(**base)


def test_odds_card_shows_percent_and_cents(qapp):
    card = OddsCard()
    card.set_vm(odds_vm())
    shown = " | ".join(texts(card))
    assert "92%" in shown and "92¢" in shown and "8%" in shown and "8¢" in shown and "0.02" in shown
    assert card.bar_fraction == pytest.approx(0.92)


def test_odds_card_missing_shows_dashes(qapp):
    card = OddsCard()
    card.set_vm(odds_vm(up_pct=None, down_pct=None, up_cents=None, down_cents=None, spread_text="—"))
    shown = texts(card)
    assert "—" in shown and card.bar_fraction is None


def test_odds_card_stale_and_market_state_pill(qapp):
    card = OddsCard()
    card.set_vm(odds_vm(up_pct=None, down_pct=None, up_cents=None, down_cents=None, stale=True, state_label="halted"))
    shown = texts(card)
    assert "stale" in shown and "halted" in shown
    card.set_vm(odds_vm())
    assert card.state_pill.isHidden()


def test_chart_time_labels_follow_the_window_length():
    from datetime import datetime, timezone

    from live_bitcoin_tracker.gui.widgets.chart import time_labels, map_point
    from live_bitcoin_tracker.gui.series import ChartPoint

    start = datetime(2026, 10, 8, 5, 0, tzinfo=timezone.utc)  # 1:00 AM ET
    assert time_labels(start, False)[:2] == [(0, "1:00am"), (120, "1:02am")]
    hourly = time_labels(start, False, 3600, 600)
    assert len(hourly) == 6 and hourly[1] == (600, "1:10am")
    day = datetime(2026, 10, 7, 21, 0, tzinfo=timezone.utc)  # 5 PM ET
    daily = time_labels(day, False, 86400, 4 * 3600)
    assert [label for _, label in daily] == ["5pm", "9pm", "1am", "5am", "9am", "1pm"]
    p = ChartPoint(int(start.timestamp()) + 1800, 100.0)
    assert map_point(p, start, 100, 50, 90, 110, seconds=3600)[0] == 50
