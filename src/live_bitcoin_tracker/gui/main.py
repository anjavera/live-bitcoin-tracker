"""Entry point for `bitcoin-tracker`. Qt is imported lazily so `--version` and the CLI never need PySide6."""

import argparse
import os
import sys
import time

SNAPSHOT_WAIT_SECONDS = 8.0  # how long --snapshot waits for the first price and live odds
SNAPSHOT_SIZE = (900, 1000)

# Test hooks: when set, used instead of the real Polymarket sources / the system clock.
_sources_override = None
_clock_override = None


def _version() -> str:
    try:
        from importlib.metadata import version

        return version("live-bitcoin-tracker")
    except Exception:  # not installed as a package (e.g. some frozen builds)
        return "unknown"


def display_problem(platform: str, env, find_library=None, load=None) -> str | None:
    """A plain-English hint when Qt cannot open a window on this Linux desktop; None when all looks fine.

    Qt 6.5+ needs libxcb-cursor0 on X11 sessions and aborts before our code can say anything. Only X11 sessions
    (DISPLAY set, no Wayland, no forced QT_QPA_PLATFORM) are checked. Loading the library is the real test;
    find_library needs ldconfig/gcc, which some systems lack, so it is only a second opinion.
    """
    if (not platform.startswith("linux") or not env.get("DISPLAY") or env.get("QT_QPA_PLATFORM")
            or env.get("WAYLAND_DISPLAY")):
        return None
    if load is None:
        import ctypes

        load = ctypes.CDLL
    try:
        load("libxcb-cursor.so.0")
        return None
    except OSError:
        pass
    if find_library is None:
        from ctypes.util import find_library
    if find_library("xcb-cursor"):
        return None
    return ("bitcoin-tracker needs one system library on this desktop (X11) to open its window.\n"
            "Install it with:  sudo apt install libxcb-cursor0   (Fedora: sudo dnf install xcb-util-cursor)")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bitcoin-tracker", description="Live Bitcoin Tracker: BTC Up/Down 15-minute, hourly and daily markets")
    parser.add_argument("--version", action="version", version=f"bitcoin-tracker {_version()}")
    parser.add_argument("--keyless", action="store_true", help="ignore any API keys and use public data only")
    parser.add_argument("--snapshot", metavar="PNG", help="save one picture of the window to PNG and exit")
    parser.add_argument("--timeframe", choices=["15m", "1h", "1d"], help="start on this time frame (default: the one used last time)")
    return parser


def _snapshot(app, window, controller, clock, path: str) -> int:
    window.resize(*SNAPSHOT_SIZE)
    window.show()
    controller.start()
    deadline = time.monotonic() + SNAPSHOT_WAIT_SECONDS

    def ready() -> bool:
        state, now = controller.state, clock()
        return bool(state.windows) and state.live_price(now) is not None and (
            state.live_tick(now) is not None or state.live_market_missing(now))

    while time.monotonic() < deadline and not ready():
        app.processEvents()
        time.sleep(0.02)
    for _ in range(5):
        app.processEvents()
    window.refresh_view()
    saved = window.grab().save(path)
    window.close()
    if not saved:
        print(f"Error: could not save the picture to {path}", file=sys.stderr)
        return 1
    return 0


SETTINGS_ORG = SETTINGS_APP = "LiveBitcoinTracker"
APP_NAME = "Live Bitcoin Tracker"
DESKTOP_FILE = "live-bitcoin-tracker"  # the .desktop file's name: how Linux desktops match a window to its menu entry and icon


def apply_app_identity(app) -> None:
    """Name and icon for the window, the task bar and the dock (otherwise desktops show a generic gear)."""
    from pathlib import Path

    from PySide6.QtGui import QGuiApplication, QIcon

    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    QGuiApplication.setDesktopFileName(DESKTOP_FILE)
    icon = Path(__file__).parent / "assets" / "icon.png"
    if icon.is_file():
        app.setWindowIcon(QIcon(str(icon)))


def _saved_timeframe() -> str:
    """The time frame used last time; '15m' when nothing is saved or the settings cannot be read."""
    try:
        from PySide6.QtCore import QSettings

        return str(QSettings(SETTINGS_ORG, SETTINGS_APP).value("timeframe", "15m"))
    except Exception:
        return "15m"


def _remember_timeframe(timeframe) -> None:
    try:
        from PySide6.QtCore import QSettings

        QSettings(SETTINGS_ORG, SETTINGS_APP).setValue("timeframe", timeframe.key)
    except Exception:
        pass  # a convenience only: never let it break the window


def run(args: argparse.Namespace) -> int:
    from PySide6.QtGui import QFontDatabase
    from PySide6.QtWidgets import QApplication

    from live_bitcoin_tracker.gui import theme
    from live_bitcoin_tracker.gui.controller import Controller, utcnow
    from live_bitcoin_tracker.gui.window import MainWindow

    app = QApplication.instance() or QApplication(sys.argv[:1])
    apply_app_identity(app)
    theme.load_bundled_fonts()
    headline, body = theme.pick_fonts(QFontDatabase.families())
    app.setStyleSheet(theme.stylesheet(headline, body))
    clock = _clock_override or utcnow
    from live_bitcoin_tracker.timeframes import by_key

    explicit = args.timeframe is not None
    timeframe = by_key(args.timeframe if explicit else _saved_timeframe())
    controller = Controller(_sources_override, clock, use_keys=not args.keyless, timeframe=timeframe)
    window = MainWindow(controller, clock, on_timeframe=None if args.snapshot else _remember_timeframe)
    if args.snapshot:
        return _snapshot(app, window, controller, clock, args.snapshot)
    window.show()
    controller.start()
    code = app.exec()
    controller.stop()
    return code


def main(argv: list[str] | None = None) -> int:
    try:
        args = build_parser().parse_args(argv)
    except SystemExit as e:  # argparse exits for --version/--help; hand the code back to the caller
        return e.code if isinstance(e.code, int) else 0
    problem = display_problem(sys.platform, os.environ)
    if problem:
        print(problem, file=sys.stderr)
        return 1
    try:
        return run(args)
    except ImportError as e:
        missing = getattr(e, "name", "") or ""
        if missing.startswith("PySide6") and not str(e).startswith("lib"):
            print("bitcoin-tracker needs the GUI extra: install it with  uv sync --extra gui  (or pip install 'live-bitcoin-tracker[gui]')",
                  file=sys.stderr)
        else:  # Qt is there but cannot load: usually a system library, so say what the loader said
            print(f"bitcoin-tracker could not start its window library: {e}\n"
                  "On Linux this usually means a system package is missing, for example: sudo apt install libgl1 libegl1 libxkbcommon0",
                  file=sys.stderr)
        return 1


def cli() -> None:
    sys.exit(main())


if __name__ == "__main__":
    cli()
