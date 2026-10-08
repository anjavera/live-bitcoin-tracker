"""View-models: widget state in, plain display data out. No Qt here, so everything is testable without a display."""

from dataclasses import dataclass
from datetime import datetime, timedelta, tzinfo

from btc15_widget import colors
from btc15_widget.gui import theme
from btc15_widget.history import NO_MARKET
from btc15_widget.render import ET, _countdown, _signed_money
from btc15_widget.state import WidgetState
from btc15_widget.windows import floor_window, seconds_remaining

WINDOW_SECONDS = 900
DASH = "—"
LEGEND_BANDS = [str(edge) for edge in colors.BAND_EDGES[:-1]] + [f"{colors.BAND_EDGES[-1]}+"]


@dataclass(frozen=True)
class HeaderVM:
    price_text: str
    approx: bool
    beat_text: str
    gap_text: str
    gap_sign: int  # +1 above the price to beat, -1 below, 0 unknown
    countdown: str
    elapsed_fraction: float  # 0.0 at the window start, 1.0 at its end
    lean: str | None  # "UP" / "DOWN" / None
    source: str | None  # "index" / "proxy" / None
    caption: str


@dataclass(frozen=True)
class OddsVM:
    up_pct: int | None
    down_pct: int | None
    up_cents: int | None
    down_cents: int | None
    spread_text: str
    state_label: str | None  # "halted", "suspended"...; None when open or unknown
    stale: bool


@dataclass(frozen=True)
class RowVM:
    label: str
    open_text: str
    close_text: str
    chg_text: str
    pct_text: str
    result_text: str
    chg_fill: str | None
    result_fill: str | None
    live: bool
    error: str | None


def header_vm(state: WidgetState, now: datetime) -> HeaderVM:
    live = state.live_window(now)
    price, gap, source = state.live_price(now), state.gap(now), state.price_source(now)
    if price is not None:
        price_text = f"${price:,.2f}"
    else:
        price_text = "stale" if state.quotes_at is not None and state.is_stale("quotes", now) else DASH
    if source == "index":  # the official index is exact: no estimate marker
        caption = "Polymarket index"
    elif source == "proxy":
        margin = f", ±${state.calibration.mean_abs_error:.1f}" if state.calibration else ""
        caption = f"approx. (exchange composite{margin})"
    else:
        caption = ""
    remaining = seconds_remaining(now, live.start)
    return HeaderVM(
        price_text=price_text,
        approx=source == "proxy",
        beat_text=f"${live.open:,.2f}" if live.open is not None else DASH,
        gap_text=DASH if gap is None else _signed_money(gap),
        gap_sign=0 if gap is None else (1 if gap > 0 else -1 if gap < 0 else 0),
        countdown=_countdown(now, live.start),
        elapsed_fraction=min(1.0, max(0.0, 1 - remaining / WINDOW_SECONDS)),
        lean=None if gap is None else ("UP" if gap >= 0 else "DOWN"),
        source=source,
        caption=caption,
    )


def odds_vm(state: WidgetState, now: datetime) -> OddsVM:
    tick = state.live_tick(now)
    label = state.market_state_label(now)
    if tick is None:
        return OddsVM(None, None, None, None, DASH, label, False)
    if state.is_stale("tick", now):
        return OddsVM(None, None, None, None, DASH, label, True)
    spread = DASH if tick.spread is None else f"{tick.spread:.2f}"
    if tick.up_price is None:
        return OddsVM(None, None, None, None, spread, label, False)
    up = round(tick.up_price * 100)
    return OddsVM(up, 100 - up, up, 100 - up, spread, label, False)


def window_column_title(local_time: bool) -> str:
    return "Window (local)" if local_time else "Window (ET)"


def _money(value: float | None) -> str:
    return f"{value:,.2f}" if value is not None else "-"


def table_rows(state: WidgetState, now: datetime, local_time: bool = False, local_tz: tzinfo | None = None) -> list[RowVM]:
    """The 96 past windows then the live one, oldest first, with fills already decided."""
    live_start, live_price = floor_window(now), state.live_price(now)
    rows: list[RowVM] = []
    for w in state.table_windows(now):
        t = w.start.astimezone(local_tz) if local_time and local_tz else w.start.astimezone() if local_time else w.start.astimezone(ET)
        label = f"{t:%m-%d %H:%M}-{(t + timedelta(minutes=15)):%H:%M}"
        is_live_row = w.start == live_start
        provisional_ok = is_live_row and not w.settled and not w.error and live_price is not None and w.open is not None
        chg_fill = result_fill = None
        close_text = _money(w.close)
        chg_text = pct_text = "-"
        if w.error:
            result_text = "none" if w.error == NO_MARKET else "gap"
        elif w.net is not None or provisional_ok:
            provisional = w.net is None
            net = live_price - w.open if provisional else w.net
            chg_fill = colors.net_color(net, "dark")
            chg_text, pct_text = f"{net:+,.2f}", f"{net / w.open * 100:+.3f}%"
            outcome = "UP" if net >= 0 else "DOWN"
            if provisional:
                close_text, result_text = f"≈ {live_price:,.2f}", f"{outcome}?"
            else:
                result_text, result_fill = outcome, theme.UP if outcome == "UP" else theme.DOWN
        else:
            result_text = "LIVE" if w.status in ("OPEN", "ACTIVE", "") else "-"
        rows.append(RowVM(label=label, open_text=_money(w.open), close_text=close_text, chg_text=chg_text,
                          pct_text=pct_text, result_text=result_text, chg_fill=chg_fill, result_fill=result_fill,
                          live=is_live_row, error=w.error))
    return rows


def status_text(state: WidgetState, now: datetime, feed_status: str) -> str:
    mode = f" ({state.feed_mode})" if state.feed_mode else ""
    market = state.market_state_label(now)
    market = f" · market {market}" if market else ""
    if state.price_source(now) == "index":
        age = f"price: Polymarket index {max(0, int((now - state.index_at).total_seconds()))}s ago"
    elif state.quotes_at is not None:
        age = f"price: exchange quotes {max(0, int((now - state.quotes_at).total_seconds()))}s ago"
    else:
        age = "price: waiting"
    text = f"feed: {feed_status}{mode}{market} · {age}"
    if state.loading and not state.windows:
        text += "\nloading 24h history… (first run takes a few minutes; later runs are cached)"
    if state.error:
        text += f"\nError: {state.error}"
    return text
