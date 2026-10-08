# Unofficial Bitcoin Up or Down 15 Minute Widget Tracker

A live widget for Polymarket US's **"BTC Up or Down: 15 min"** markets: the last 24 hours of
15-minute windows, colour-coded by result and net change, plus the live window with odds,
a live BTC price and a countdown.

> **Unofficial.** Not affiliated with, endorsed by, or connected to Polymarket or CF Benchmarks.
> Read-only market data. Nothing here places orders, and nothing here is financial advice.

**Status:** works today as a terminal app on Linux (tested); Windows and macOS builds are produced by
automated checks and have not been tried by hand yet. See
[`docs/DESIGN.md`](docs/DESIGN.md).

## Install (no Python needed)

Download the file for your computer from the [Releases page](../../releases/latest) and run it. It opens a
window with the live widget; press **q** to quit. The window needs to be at least 80 columns by 16 rows.

| Your computer | Download | How to start it |
|---|---|---|
| **Windows** | `btc15-widget-windows-x86_64.exe` | Double-click it. Windows may say it "protected your PC" because the app is not code-signed: click **More info**, then **Run anyway**. |
| **Mac** (Apple Silicon) | `btc15-widget-macos-arm64` | Open Terminal, then run `chmod +x ~/Downloads/btc15-widget-macos-arm64 && ~/Downloads/btc15-widget-macos-arm64`. If macOS blocks it, open **System Settings > Privacy & Security** and choose **Open Anyway**. |
| **Linux** | `btc15-widget-linux-x86_64` + `install.sh` | In the download folder run `sh install.sh`. This adds **BTC 15m Widget** to your app menu (it opens in a terminal window). |

The apps are not code-signed (that needs paid developer accounts), which is why Windows and macOS warn once.
If something does not work on your system, please [open an issue](../../issues) with what you saw.

**Already use Python?** `uv tool install git+https://github.com/anjavera/unofficial-bitcoin-up-or-down-15-minute-widget-tracker`
then run `btc15-widget`.

## Desktop window

Prefer a normal window to a terminal? There is also a desktop app with the same data: a live price chart for the
current 15 minutes, the Up/Down odds, and the 24-hour history table. It is read-only, like the terminal widget.

| Your computer | Download | How to start it |
|---|---|---|
| **Windows** | `btc15-gui-windows-x86_64.exe` | Double-click it (same one-time \"protected your PC\" warning as above: **More info**, then **Run anyway**). |
| **Mac** (Apple Silicon) | `btc15-gui-macos-arm64.zip` | Unzip it, then right-click **btc15-gui** and choose **Open** the first time (the app is not code-signed). |
| **Linux** | `btc15-gui-linux-x86_64` + `install-gui.sh` | In the download folder run `sh install-gui.sh`. This adds **BTC 15m Tracker** to your app menu. On an X11 desktop you may also need `sudo apt install libxcb-cursor0`; the app tells you if so. |

Keys: **v** switches table/strip, **r** reloads, **Ctrl+Q** quits. The **View** menu has a local-time option and
always-on-top. **Already use Python?** `uv tool install "btc15-widget[gui] @ git+https://github.com/anjavera/unofficial-bitcoin-up-or-down-15-minute-widget-tracker"`
then run `btc15-gui` (`--keyless` ignores any API keys).

The look is modelled on Polymarket's own market page (dark theme, green Up / red Down). The live price comes from
Polymarket's own BTC index, the one the markets settle on; if that is unavailable the window falls back to an
exchange average and marks it \"approx.\".

## No API keys needed

The live widget and `pm btc15` read only **public** Polymarket US data and public exchange prices, so there is
nothing to sign up for or configure. Just run it.

## Optional: use your own Polymarket US API keys

Keys are optional. With keys the widget switches automatically to Polymarket's faster live feed (updates are
pushed to you instead of polled every 2 seconds), and you can use the account commands (`pm account`,
`balances`, `positions`, `orders`). **Everyone needs their own keys: never share or reuse
anyone else's.**

How to get your own keys (from Polymarket US's official docs,
<https://docs.polymarket.us/api-reference/authentication>):

1. Download the **Polymarket US app** and create an account.
2. Complete **identity verification** in the app.
3. Go to <https://polymarket.us/developer> and sign in **the same way you sign in to the app** (Apple, Google or
   email). Switching sign-in methods can break your key.
4. Create a new key. You get a **Key ID** and a **Secret Key**. The secret key is shown **only once**: copy it
   somewhere safe before closing the dialog.
5. Put them in a file named `.env` in this project's folder (or set them as environment variables):

   ```
   POLYMARKET_KEY_ID=your-key-id
   POLYMARKET_SECRET_KEY=your-secret-key
   ```

The widget finds the keys by itself; the status line then shows `feed: live (keyed)`. To ignore your keys and use
public data only, run `btc15-widget --keyless` (the status line shows `feed: live (keyless)`).

**Keep your keys safe.** Polymarket's keys can be used to place orders including other functions involving your money. Treat the keys as if they were the full details to your credit/debit cards. `.env` is git-ignored here; never commit it or paste it anywhere. If a key is ever
exposed, revoke it at <https://polymarket.us/developer>. This project only reads data and never places orders.

## Usage

```
uv sync
uv run btc15-widget           # live terminal widget (add --keyless to ignore any API keys)
uv run btc15-widget --snapshot  # print one plain-text frame and exit
uv run btc15-gui              # desktop window (needs: uv sync --extra gui)
uv run pm btc15 --hours 6     # one-shot styled table, last 6 hours (add --volume for volumes; slower)
uv run pytest                 # tests
```

Terminal widget keys: **q** quit, **v** table/strip view, **r** refresh, arrows/PgUp/PgDn scroll. On terminals of at
least 116 columns by 28 rows an ASCII coin appears whose ring is the analog countdown (orange = time left,
green/red = time used, by the current lean).

Other read-only commands: `uv run pm search "<text>"`, `pm price <market-slug>`, `pm book <market-slug>`,
`pm market <market-slug>`, `pm event <event-slug>`, and (keys needed) `pm account`, `pm balances`, `pm positions`,
`pm orders`. Add `--json` before the command for machine-readable output. Rapid repeated calls can trip a
Cloudflare rate limit; wait a minute.

History for the last 24 hours loads in about a second with one request, and settled windows are cached locally.
The live price comes from Polymarket's own BTC index (the one the markets settle on). If it is unavailable the app
falls back to an average of Coinbase, Kraken, Bitstamp and Gemini and marks the price as approximate (&asymp;).
Windows are coloured from the real settled result; the live window is provisional.

## License

[MIT](LICENSE). This project is unofficial and comes with no warranty; see the notice at the top.
