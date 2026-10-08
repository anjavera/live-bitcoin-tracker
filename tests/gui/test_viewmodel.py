from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from live_bitcoin_tracker import colors
from live_bitcoin_tracker.gui import theme
from live_bitcoin_tracker.gui.viewmodel import (LEGEND_BANDS, header_vm, odds_vm, status_text, table_rows,
                                        window_column_title)
from live_bitcoin_tracker.history import NO_MARKET
from live_bitcoin_tracker.model import LiveTick, Window
from live_bitcoin_tracker.state import WidgetState
from live_bitcoin_tracker.windows import MARKET_SLUG, floor_window

UTC = timezone.utc
STEP = timedelta(minutes=15)
NOW = datetime(2026, 10, 2, 21, 5, 30, tzinfo=UTC)  # 5m30s into the 21:00 window


def history(now=NOW):
    live = floor_window(now)
    return [Window(live - i * STEP, open=84000.0 + i, close=None if i == 0 else 84001.0 + i) for i in range(96, -1, -1)]


def state_with(index=None, now=NOW, windows=None):
    state = WidgetState()
    state.set_history(history(now) if windows is None else windows, now)
    if index is not None:
        state.apply_index(index, now)
    return state


def tick(up=0.92, now=NOW, state=None):
    return LiveTick(slug=MARKET_SLUG.format(floor_window(now)), up_price=up, best_bid=up - 0.01, best_ask=up + 0.01,
                    last_trade=up, shares_traded=1.0, state=state)


# ---- header ---------------------------------------------------------------------------------
def test_header_index_price_exact_no_approx():
    vm = header_vm(state_with(index=84489.89), NOW)
    assert vm.price_text == "$84,489.89" and vm.approx is False
    assert vm.source == "index" and vm.caption == "Polymarket index"
    assert vm.beat_text == "$84,000.00"


def test_header_proxy_marks_approx_and_caption():
    state = state_with()
    state.apply_quotes({"coinbase": 84100.0, "kraken": 84100.0}, NOW)
    vm = header_vm(state, NOW)
    assert vm.price_text == "$84,100.00" and vm.approx is True
    assert vm.source == "proxy" and vm.caption.startswith("approx.")


def test_header_no_data_dashes():
    vm = header_vm(WidgetState(), NOW)
    assert vm.price_text == "—" and vm.beat_text == "—" and vm.gap_text == "—"
    assert vm.gap_sign == 0 and vm.lean is None and vm.source is None and vm.caption == ""


def test_header_stale_quotes_say_stale():
    state = state_with()
    state.apply_quotes({"coinbase": 84100.0}, NOW - timedelta(seconds=60))
    assert header_vm(state, NOW).price_text == "stale"


def test_gap_sign_and_text():
    up = header_vm(state_with(index=84044.04), NOW)
    assert up.gap_text == "+$44.04" and up.gap_sign == 1 and up.lean == "UP"
    down = header_vm(state_with(index=83990.0), NOW)
    assert down.gap_text == "-$10.00" and down.gap_sign == -1 and down.lean == "DOWN"
    flat = header_vm(state_with(index=84000.0), NOW)
    assert flat.gap_text == "+$0.00" and flat.gap_sign == 0 and flat.lean == "UP"  # >= is Up


def test_countdown_and_elapsed_fraction_at_start_mid_end():
    start = header_vm(state_with(now=datetime(2026, 10, 2, 21, 0, 0, tzinfo=UTC)), datetime(2026, 10, 2, 21, 0, 0, tzinfo=UTC))
    assert start.countdown == "15:00" and start.elapsed_fraction == 0.0
    mid = header_vm(state_with(), NOW)
    assert mid.countdown == "09:30" and abs(mid.elapsed_fraction - 330 / 900) < 1e-9
    end = datetime(2026, 10, 2, 21, 14, 59, 500000, tzinfo=UTC)
    last = header_vm(state_with(now=end), end)
    assert last.countdown == "00:01" and last.elapsed_fraction > 0.99


# ---- odds -----------------------------------------------------------------------------------
def test_odds_percent_cents_from_up_price():
    state = state_with()
    state.apply_tick(tick(0.92), NOW)
    vm = odds_vm(state, NOW)
    assert (vm.up_pct, vm.down_pct, vm.up_cents, vm.down_cents) == (92, 8, 92, 8)
    assert vm.spread_text == "0.02" and vm.stale is False and vm.state_label is None


def test_odds_stale_and_missing():
    state = state_with()
    assert odds_vm(state, NOW).up_pct is None and odds_vm(state, NOW).spread_text == "—"
    state.apply_tick(tick(0.6), NOW)
    stale = odds_vm(state, NOW + timedelta(seconds=30))
    assert stale.stale is True and stale.up_pct is None


def test_odds_state_label_halted():
    state = state_with()
    state.apply_tick(tick(0.5, state="MARKET_STATE_HALTED"), NOW)
    assert odds_vm(state, NOW).state_label == "halted"


def test_odds_tick_without_price_is_dashes():
    state = state_with()
    bad = tick(0.5)
    bad.up_price = None
    state.apply_tick(bad, NOW)
    vm = odds_vm(state, NOW)
    assert vm.up_pct is None and vm.down_cents is None


# ---- table ----------------------------------------------------------------------------------
def test_table_rows_count_97_and_order():
    rows = table_rows(state_with(), NOW)
    assert len(rows) == 97
    assert rows[-1].live is True and sum(r.live for r in rows) == 1
    assert rows[0].label == "10-01 17:00-17:15"   # 96 windows (24 h) before the live 17:00 ET one
    assert rows[-2].label == "10-02 16:45-17:00" and rows[-1].label == "10-02 17:00-17:15"
    assert len({r.label for r in rows}) == 97


def test_table_settled_row_fills_match_colors_module():
    live = floor_window(NOW)
    windows = history()
    windows[-2] = Window(live - STEP, open=84000.0, close=84030.0)  # +30 -> UP, band 3
    windows[-3] = Window(live - 2 * STEP, open=84000.0, close=83900.0)  # -100 -> DOWN
    rows = table_rows(state_with(windows=windows), NOW)
    up, down = rows[-2], rows[-3]
    assert up.result_text == "UP" and up.result_fill == theme.UP
    assert up.chg_fill == colors.net_color(30.0, "dark")
    assert up.chg_text == "+30.00" and up.pct_text == "+0.036%"
    assert up.open_text == "84,000.00" and up.close_text == "84,030.00"
    assert down.result_text == "DOWN" and down.result_fill == theme.DOWN
    assert down.chg_fill == colors.net_color(-100.0, "dark") and down.chg_text == "-100.00"


def test_table_live_row_provisional():
    rows = table_rows(state_with(index=84044.04), NOW)
    live = rows[-1]
    assert live.live and live.close_text == "≈ 84,044.04"
    assert live.result_text == "UP?" and live.result_fill is None
    assert live.chg_fill == colors.net_color(44.04, "dark") and live.chg_text == "+44.04"


def test_table_live_row_without_price_shows_live():
    live = table_rows(state_with(), NOW)[-1]
    assert live.result_text == "LIVE"  # status "" counts as open, no price yet
    assert live.chg_fill is None and live.chg_text == "-"


def test_table_live_row_open_status_shows_live():
    windows = history()
    windows[-1] = Window(floor_window(NOW), open=84000.0, close=None, status="OPEN")
    assert table_rows(state_with(windows=windows), NOW)[-1].result_text == "LIVE"


def test_table_missing_market_row_shows_none():
    windows = history()
    windows[-1] = Window(floor_window(NOW), open=None, close=None, error=NO_MARKET)
    windows[-2] = Window(floor_window(NOW) - STEP, open=None, close=None, error="HTTP 500")
    rows = table_rows(state_with(windows=windows), NOW)
    assert rows[-1].result_text == "none" and rows[-1].error == NO_MARKET and rows[-1].chg_fill is None
    assert rows[-2].result_text == "gap" and rows[-2].open_text == "-"


def test_table_empty_state_has_97_placeholder_rows():
    rows = table_rows(WidgetState(), NOW)
    assert len(rows) == 97 and all(r.chg_fill is None and r.result_fill is None for r in rows)


def test_table_local_time_toggle_changes_label():
    state = state_with()
    et = table_rows(state, NOW)[-1].label
    tokyo = table_rows(state, NOW, local_time=True, local_tz=ZoneInfo("Asia/Tokyo"))[-1].label
    assert et == "10-02 17:00-17:15"  # 21:00Z is 17:00 EDT
    assert tokyo == "10-03 06:00-06:15"
    assert window_column_title(False) == "Window (ET)" and window_column_title(True) == "Window (local)"


# ---- status / legend ------------------------------------------------------------------------
def test_status_text_includes_error_and_source():
    state = state_with(index=84000.0)
    state.feed_mode = "keyless"
    state.error = "history unavailable: 60 of 97 windows failed (boom)"
    text = status_text(state, NOW + timedelta(seconds=3), "live")
    assert "live" in text and "keyless" in text and "Polymarket index" in text
    assert "history unavailable" in text


def test_status_text_market_state_and_loading():
    state = WidgetState()
    state.loading = True
    assert "loading" in status_text(state, NOW, "connecting").lower()
    state = state_with()
    state.apply_tick(tick(0.5, state="MARKET_STATE_SUSPENDED"), NOW)
    assert "suspended" in status_text(state, NOW, "live")


def test_legend_bands_match_colors_edges():
    assert LEGEND_BANDS == ["10", "25", "50", "100", "200", "300", "400", "500", "1000+"]
