# Design notes

How the BTC 15-minute Up/Down tracker gets its data and how it is put together. Read-only: nothing here
places, changes or cancels orders.

## What it shows

The last 24 hours (96 windows) of Polymarket US "BTC Up or Down: 15 min" markets, plus the live window with
Up/Down odds, a live BTC price, the price to beat and a countdown.

## Price source

Polymarket settles each window on **CF Benchmarks' Bitcoin Real-Time Index (BRTI)**: the average of 60 BRTI
prices in the last minute before each boundary, rounded to 2 decimals. The result is Up if close >= open.
Polymarket's API exposes the open (`assetPriceTerms.priceToBeat`) and, once settled, the close
(`settlementPrice`). CF Benchmarks' own live feed is licensed data, so it is not used.

The live price therefore comes from Polymarket's own BTC index. If that is unavailable, the app falls back to the
mean of public Coinbase, Kraken, Bitstamp and Gemini prices and marks it as approximate (shown with "≈"). In a
calibration over 17 settled windows the exchange mean was within about $4.65 of the BRTI open on average (max $9.12,
bias about -$4). The app re-measures this periodically and shows the error in the UI.

Approximate values never enter history: a settled window is coloured from the real result, and the live window is
marked provisional.

## Data

- **No API keys are needed** for the widget or `pm btc15`. Keys are optional: with them the widget uses the
  authenticated WebSocket feed (`feed: live (keyed)`); `--keyless` forces the public path.
- **History:** settled windows addressed by slug `btc-updown-15m-YYYY-MM-DD-HHMMz`, fetched in one
  `events.list` request (up to 100 windows) and cached locally; only new windows are fetched afterwards.
  Volume needs one extra request per window, so it is opt-in (`--volume`).
- **Live window (keyless):** the public order book is polled every 2 seconds. Up price is the midpoint of best
  bid/ask (last trade if one side is empty). Odds fall back to best bid/offer and then the event's quotes right
  after a rollover.
- **Rate limits:** Polymarket's REST API can trip a Cloudflare 1015 limit, so requests use retry with backoff, and
  history is cached.

## Display

- Header: live price, price to beat, gap, countdown to the end of the window.
- Odds: Up/Down price and spread; market state (halted, suspended) when not open.
- History: result **green = Up, red = Down**; fill is a net-change gradient, **blue = positive, orange =
  negative**, in 9 steps by absolute change: 0-10, 10-25, 25-50, 50-100, 100-200, 200-300, 300-400, 400-500,
  500+ (dollars). The smallest step is a pale tint so it reads on dark backgrounds.
- Dark theme only. Palettes sit behind a `theme` argument so another theme could be added.

## Architecture

One data layer, two front ends.

- **Core (no UI imports):** `windows`, `model`, `history`, `feed`, `index`, `proxy`, `calibration`, `state`,
  `colors`, `sources`, `paths`, `client`.
- **Terminal widget** (`btc15-widget`, Textual): `app.py`, `render.py`, `panel.py`.
- **Desktop window** (`btc15-gui`, PySide6, optional `gui` extra): `src/btc15_widget/gui/`.
  - `controller.py` owns the state and data sources and emits Qt signals; it has no widgets and is testable
    headless.
  - `series.py` turns index ticks into chart points (pure functions, no Qt).
  - `theme.py`, `window.py` and `widgets/` (header, chart, odds, history table, strip, legend, status bar, coin).
  - The chart is drawn with QPainter, because QtCharts is not part of PySide6-Essentials.
- **Command line** (`pm`): `btc15`, `search`, `price`, `book`, `market`, `event`, and with keys `account`,
  `balances`, `positions`, `orders`. `--json` gives machine-readable output.

### Threading

The data layer uses blocking-I/O threads plus an asyncio feed. In the GUI the controller runs the feed on its own
thread and hands results to the UI through queued Qt signals. The UI thread only reads state and paints. Closing
the window stops all threads.

## Desktop window

The look follows Polymarket's public event page (dark background, green Up and red Down, rounded cards) but adds
the 24-hour history and has no trading. It copies only the general style and colours, not the logo, name or
artwork.

- **Chart:** the live 15-minute window on the X axis, price line, dashed price-to-beat line, orange dot for the
  latest price, and a faint blue (above) or orange (below) fill. Index history for the elapsed part of the window
  is fetched once at start (1-second candles), then extended from the live poll.
- **Countdown:** large `mm:ss` with a ring coin whose arc shows elapsed time and the current lean.
- **Odds:** Up/Down as percent and cents, a split probability bar, and the spread.
- **Keys:** `Ctrl+Q` quit, `v` table/strip, `r` refresh. The View menu has a local-time option and always-on-top.

## Packaging

- The `gui` extra (`PySide6-Essentials`) keeps the command-line install small.
- `release.yml` builds standalone apps with PyInstaller for Linux, macOS (Apple Silicon) and Windows, runs a
  `--version` smoke test, and attaches the files to a GitHub Release. CI runs the tests on all three systems with
  Qt in offscreen mode.
- The apps are not code-signed, so Windows and macOS show a one-time warning (documented in the README).
- PySide6 is LGPL; see `THIRD_PARTY_NOTICES.md`.

## Testing

Plain pytest covers colour-band boundaries, slug and window generation across hour and day boundaries, the proxy
composite, the Up/Down rule, the controller, chart series and the table view-model with fake data sources and an
injected clock. Widget tests run with `QT_QPA_PLATFORM=offscreen`.

## Non-goals

Order placement or any trading panel, account views in the GUI, light theme, mobile.
