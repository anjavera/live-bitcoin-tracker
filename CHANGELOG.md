# Changelog

All notable changes to this project. Format follows [Keep a Changelog](https://keepachangelog.com/);
the project uses [semantic versioning](https://semver.org/).

## [Unreleased] - first public release (0.1.0)

### Added
- **One window, three time frames.** The desktop window has tabs for the 15-minute, hourly and daily BTC Up/Down
  markets, with the same design on each: price chart, odds, countdown and colour-coded history. Hourly shows the last
  24 hours and daily the last 30 days. The daily window runs 5 PM ET to 5 PM ET and its close and countdown follow
  Polymarket's daily market, including daylight-saving changes (23 and 25 hour days). Switch with the buttons or keys 1, 2, 3;
  the window remembers the last tab, and `--timeframe` picks one at start.
- Colour bands scale with the time frame; the colour key is one compact row that fits the smallest window.
- The history table follows the newest row until you scroll away.
- Live terminal widget (`bitcoin-tracker-tui`): ticker with price, price to beat, gap, countdown and Up/Down odds;
  24-hour colour-coded history table; strip view; colour key; ASCII coin whose ring is the analog countdown.
- Desktop window (`bitcoin-tracker`, PySide6): live price chart for the current window, odds, 24-hour history table,
  local-time and always-on-top options, `--snapshot` image export.
- `pm` command line: `btc15`, `search`, `price`, `book`, `market`, `event`, and (with keys) `account`,
  `balances`, `positions`, `orders`. `--json` output.
- Keyless mode: no API keys needed. Optional keys switch the widget to Polymarket's faster live feed;
  `--keyless` ignores them.
- Live price from Polymarket's own BTC index, with an exchange-average fallback marked as approximate.
- Odds fallback chain (order book, then best bid/offer, then the event's quotes) so odds show right after a rollover.
- Clear messages when Polymarket has no live market or is in maintenance; market state (halted, suspended) in the status line.
- Standalone apps for Windows, macOS (Apple Silicon) and Linux, a Linux installer with menu entry and icon,
  and a release workflow. CI runs on Linux, macOS and Windows.
- MIT licence.

### Known limitations
- Polymarket US's daily markets began on 2026-10-04, so the 30-day table shows "none" for earlier days for now.
- The daily market slug carries the UTC start (21:00 in summer, 22:00 in winter). The app also tries the neighbouring hour,
  but this has not been observed live across a daylight-saving change yet (next one: 2026-11-01).
- The terminal widget and `pm btc15` cover the 15-minute market only.
- The Windows build was tested on Windows Server 2022 (build, 423 tests, live screenshots of all three tabs); it has not been tried on a desktop Windows 10/11, and the macOS build has not been tried by hand.
- The apps are not code-signed, so Windows and macOS show a one-time warning.
- Read-only: nothing in this project places, changes or cancels orders.
