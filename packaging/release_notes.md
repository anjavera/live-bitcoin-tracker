## Live Bitcoin Tracker v0.1.0: first public release

An unofficial, read-only tracker for Polymarket US's **Bitcoin Up or Down** markets: **15 minute**, **hourly** (last 24 hours) and **daily** (last 30 days, closing 5 PM ET) in one window, with the live price, the odds, a countdown and a colour-coded history table. It places no orders and is not financial advice.

### What has been tested
- **Linux: tested.**
- **Windows: tested.** Built, ran 423 tests and ran with live data on a Windows Server 2022 machine. A desktop Windows 10 or 11 has not been tried.
- **macOS: visually untested.** The Mac build is built and checked by automated tests, but nobody has looked at it on a real Mac yet. Please [open an issue](../../issues) if something looks wrong.

### Install
- **Easiest, no security warnings:** install [uv](https://docs.astral.sh/uv/), then `uv tool install "live-bitcoin-tracker[gui] @ git+https://github.com/anjavera/live-bitcoin-tracker"` and run `bitcoin-tracker`.
- **Or download a file below** and run it. These builds are **not code-signed yet**, so Windows ("More info", then "Run anyway") and macOS (right-click, then "Open") warn the first time. Linux: run `sh install-gui.sh`.

Daily markets only began on 2026-10-04, so the first rows of the 30-day table show "none" for now. Not affiliated with Polymarket or CF Benchmarks.
