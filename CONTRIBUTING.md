# Contributing to Live Bitcoin Tracker

Thanks for helping. This is a small, read-only project, so the rules are short.

## What fits this project
- **In scope:** showing Polymarket US's Bitcoin Up or Down markets (15 minute, hourly, daily) clearly and accurately; fixing bugs; making the apps
  work well on Linux, Windows and macOS; accessibility; documentation; tests.
- **Out of scope:** anything that places, changes or cancels orders, handles money, or gives trading advice or signals. The project is
  deliberately read-only. Proposals for that will be declined, however good the idea.
- **Not affiliated with Polymarket or CF Benchmarks.** Please keep names, logos and wording from implying otherwise.

## Reporting a problem
Open an [issue](../../issues/new/choose). The most useful reports say: which system (Windows 10/11, macOS, Linux and desktop), how you
installed it (`uv` or a download), the version (`bitcoin-tracker --version`), which tab you were on, and a screenshot. **macOS reports are
especially welcome: the Mac build has not been looked at on a real Mac yet.**

To report a **security problem**, do not open a public issue: see [SECURITY.md](SECURITY.md).

## Changing the code
1. Fork the repository and create a branch.
2. Install: `uv sync --extra gui`
3. Run the tests: `QT_QPA_PLATFORM=offscreen uv run pytest` (on Windows set the variable in PowerShell with `$env:QT_QPA_PLATFORM="offscreen"`).
   A few tests skip themselves on platforms where Qt's offscreen mode has no fonts; that is expected.
4. Try the app against live data: `uv run bitcoin-tracker --keyless` (public data only, no keys needed).
5. Add or update tests for what you change: new behaviour comes with a test that fails without it.
6. Keep the change focused, and explain **why** in the pull request, not only what.

Design notes and the reasoning behind choices are in [`docs/DESIGN.md`](docs/DESIGN.md); the three time frames live in
`src/live_bitcoin_tracker/timeframes.py`. Never commit API keys, `.env` files, or anything personal.

## Pull request checklist
- [ ] Tests pass locally and the new behaviour is covered.
- [ ] No keys, personal paths or data were added.
- [ ] Anything a user would notice is in `CHANGELOG.md`.
- [ ] For a visible change, a screenshot is attached.

By contributing you agree your work is released under the project's [MIT licence](LICENSE).
Please follow the [Code of Conduct](CODE_OF_CONDUCT.md).
