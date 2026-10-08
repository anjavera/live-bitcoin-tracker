"""Entry point for `btc15-gui`. Qt is imported lazily so `--version` and the CLI never need PySide6."""

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

        return version("btc15-widget")
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
    return ("btc15-gui needs one system library on this desktop (X11) to open its window.\n"
            "Install it with:  sudo apt install libxcb-cursor0   (Fedora: sudo dnf install xcb-util-cursor)")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="btc15-gui", description="Live BTC 15-minute Up/Down desktop window")
    parser.add_argument("--version", action="version", version=f"btc15-gui {_version()}")
    parser.add_argument("--keyless", action="store_true", help="ignore any API keys and use public data only")
    parser.add_argument("--snapshot", metavar="PNG", help="save one picture of the window to PNG and exit")
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


def run(args: argparse.Namespace) -> int:
    from PySide6.QtGui import QFontDatabase
    from PySide6.QtWidgets import QApplication

    from btc15_widget.gui import theme
    from btc15_widget.gui.controller import Controller, utcnow
    from btc15_widget.gui.window import MainWindow

    app = QApplication.instance() or QApplication(sys.argv[:1])
    theme.load_bundled_fonts()
    headline, body = theme.pick_fonts(QFontDatabase.families())
    app.setStyleSheet(theme.stylesheet(headline, body))
    clock = _clock_override or utcnow
    controller = Controller(_sources_override, clock, use_keys=not args.keyless)
    window = MainWindow(controller, clock)
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
    except ImportError:
        print("btc15-gui needs the GUI extra: install it with  uv sync --extra gui  (or pip install 'btc15-widget[gui]')",
              file=sys.stderr)
        return 1


def cli() -> None:
    sys.exit(main())


if __name__ == "__main__":
    cli()
