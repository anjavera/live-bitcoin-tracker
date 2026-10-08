"""View-models: widget state in, plain display data out. No Qt here, so everything is testable without a display."""

import math
from dataclasses import dataclass
from datetime import datetime, timedelta, tzinfo

from live_bitcoin_tracker import colors
from live_bitcoin_tracker.gui import theme
from live_bitcoin_tracker.history import NO_MARKET
from live_bitcoin_tracker.render import _signed_money
from live_bitcoin_tracker.state import WidgetState
from live_bitcoin_tracker.timeframes import DAILY, ET, FIFTEEN_MIN, Timeframe

WINDOW_SECONDS = 900
DASH = "—"
LEGEND_BANDS = [str(edge) for edge in colors.BAND_EDGES[:-1]] + [f"{colors.BAND_EDGES[-1]}+"]


def legend_bands(timeframe: Timeframe) -> list[str]:
    """Colour-band labels in dollars: the 15-minute bands times the frame's scale (an hour moves more than a quarter hour)."""
    edges = [round(edge * timeframe.band_scale) for edge in colors.BAND_EDGES]
    return [str(edge) for edge in edges[:-1]] + [f"{edges[-1]}+"]


def countdown_text(seconds: float, hours: bool = False) -> str:
    """Whole seconds rounded up as mm:ss, or h:mm:ss for the daily frame."""
    total = math.ceil(seconds)
    if hours:
        return f"{total // 3600}:{total % 3600 // 60:02d}:{total % 60:02d}"
    return f"{total // 60:02d}:{total % 60:02d}"


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
    title: str = "BTC UP OR DOWN · 15 MIN"


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
    tf = state.timeframe
    remaining, length = tf.seconds_remaining(now, live.start), tf.length(live.start).total_seconds()
    return HeaderVM(
        title=f"BTC UP OR DOWN · {tf.label.upper()}",
        price_text=price_text,
        approx=source == "proxy",
        beat_text=f"${live.open:,.2f}" if live.open is not None else DASH,
        gap_text=DASH if gap is None else _signed_money(gap),
        gap_sign=0 if gap is None else (1 if gap > 0 else -1 if gap < 0 else 0),
        countdown=countdown_text(remaining, tf.countdown_hours),
        elapsed_fraction=min(1.0, max(0.0, 1 - remaining / length)),
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
    """The past windows then the live one, oldest first, with fills already decided."""
    tf = state.timeframe
    live_start, live_price = tf.floor(now), state.live_price(now)
    tz = (local_tz if local_tz else None) if local_time else ET  # None means the computer's own zone
    rows: list[RowVM] = []
    for w in state.table_windows(now):
        label = tf.row_label(w.start, tz)
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
            chg_fill = colors.net_color(net / tf.band_scale, "dark")  # bands are the 15-minute ones, scaled by the frame
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
        text += f"\nloading {state.timeframe.heading.lower().removeprefix('past ')} of history… (first run takes a few minutes; later runs are cached)"
    elif state.timeframe is DAILY:
        none = [w for w in state.windows if w.error == NO_MARKET and w.start < now]
        real = [w for w in state.windows if not w.error and w.start < now]
        if none and real:
            first = min(w.start for w in real).astimezone(ET)
            text += f"\nPolymarket's daily markets start {first:%b} {first.day}: earlier days show none"
    if state.error:
        text += f"\nError: {state.error}"
    return text
