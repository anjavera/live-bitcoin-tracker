# Changelog

All notable changes to this project. Format follows [Keep a Changelog](https://keepachangelog.com/);
the project uses [semantic versioning](https://semver.org/).

## [Unreleased] - first public release (0.1.0)

### Added
- Live terminal widget (`btc15-widget`): ticker with price, price to beat, gap, countdown and Up/Down odds;
  24-hour colour-coded history table; strip view; colour key; ASCII coin whose ring is the analog countdown.
- Desktop window (`btc15-gui`, PySide6): live price chart for the current window, odds, 24-hour history table,
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
- Windows and macOS builds are produced by automated checks and have not been tried by hand yet.
- The apps are not code-signed, so Windows and macOS show a one-time warning.
- Read-only: nothing in this project places, changes or cancels orders.
