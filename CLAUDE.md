# Live Bitcoin Tracker

Polymarket US (https://docs.polymarket.us) read-only tooling using the `polymarket-us` Python SDK, managed with uv.
Tracks Polymarket US's BTC Up/Down markets in three time frames (15 min, hourly, daily). Design notes: `docs/DESIGN.md`.

- The widget and `pm btc15` need **no keys** (public data): use `live_bitcoin_tracker.client.get_public_client()`. If the user has set up keys, the widget uses the faster authenticated WebSocket feed automatically (`feed: live (keyed)`); `--keyless` ignores them.
- Keys (`POLYMARKET_KEY_ID` / `POLYMARKET_SECRET_KEY`, from the environment, a `.env`, or the per-user config folder) are only for account commands and the keyed live feed: `get_client()`. Never print or cat them; the secret is base64 and ends in `=`.

## Live data (read-only)

Run from this directory. Add `--json` before the command for machine-readable output.

    uv run pm account              # balances + positions (with live bid/ask) + open orders
    uv run pm balances | positions | orders
    uv run pm search "yankees"     # find events and market slugs
    uv run pm price <market-slug>  # best bid/ask, last trade
    uv run pm book <market-slug> --depth 10
    uv run pm market <market-slug>
    uv run pm --json event <event-slug>
    uv run pm btc15 [--hours 6] [--volume]   # one-shot styled table (Chg $/% blue-orange gradient, Result green/red, volume)
    uv run bitcoin-tracker-tui [--snapshot] [--keyless]   # live terminal widget (15 minutes only): ticker, styled table, colour key, ASCII coin = analog countdown on wide terminals (also: uv run pm widget)
                                   # keys: q quit, v table/strip view, r refresh, arrows/PgUp/PgDn scroll
    uv run bitcoin-tracker [--timeframe 15m|1h|1d] [--keyless] [--snapshot out.png]   # desktop window (PySide6; needs `uv sync --extra gui`): tabs for 15 min, hourly (24 h) and daily (30 days): chart, odds, history table

Rapid-fire calls can trip a Cloudflare 1015 rate limit; wait a minute.

The CLI is read-only. Placing, modifying or cancelling orders spends real money; nothing in this project does that.

## Time frames

`live_bitcoin_tracker/timeframes.py` holds everything that differs between the three frames (window maths, slugs, row
labels, colour-band scale, chart candle size); the rest of the code asks a `Timeframe`. Slugs: `btc-updown-{15m|1h|1d}-YYYY-MM-DD-HHMMz`
(UTC start; markets prefix `cpc-`). The daily window is 5 PM ET to 5 PM ET, so its UTC start moves between 21:00 and 22:00
with daylight saving; the open/close come from each event's `assetPriceTerms` (`windowStart`, `windowEnd`, `priceToBeat`, `settlementPrice`).
Outcomes use the average of 60 BRTI prices before each boundary (see `docs/DESIGN.md`), not a single tick.
GUI tests: `QT_QPA_PLATFORM=offscreen uv run pytest`.

GitHub page picture: `docs/social-preview.png` (made by `packaging/make_social_preview.py`); GitHub only takes it by hand: repo Settings > General > Social preview.
