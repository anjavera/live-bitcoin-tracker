import subprocess
import sys

from live_bitcoin_tracker.gui.main import main


def test_version_prints_and_exits_zero(capsys):
    assert main(["--version"]) == 0
    assert capsys.readouterr().out.startswith("bitcoin-tracker ")


def test_main_module_imports_without_pyside():
    code = ("import sys; sys.modules['PySide6'] = None; "
            "import live_bitcoin_tracker.gui.main; print('ok')")
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "ok"


def _no_lib(name):
    raise OSError(name)


def test_linux_x11_without_xcb_cursor_gets_a_plain_hint():
    from live_bitcoin_tracker.gui.main import display_problem

    msg = display_problem("linux", {"DISPLAY": ":0"}, find_library=lambda name: None, load=_no_lib)
    assert msg and "libxcb-cursor0" in msg and "apt install" in msg


def test_library_found_by_loading_it_is_fine_even_if_find_library_cannot_see_it():
    from live_bitcoin_tracker.gui.main import display_problem

    assert display_problem("linux", {"DISPLAY": ":0"}, find_library=lambda n: None, load=lambda n: object()) is None


def test_no_display_variable_means_no_check():
    from live_bitcoin_tracker.gui.main import display_problem

    assert display_problem("linux", {}, find_library=lambda n: None, load=_no_lib) is None


def test_linux_with_the_library_or_wayland_or_forced_platform_is_fine():
    from live_bitcoin_tracker.gui.main import display_problem

    assert display_problem("linux", {"DISPLAY": ":0"}, find_library=lambda n: "libxcb-cursor.so.0", load=_no_lib) is None
    assert display_problem("linux", {"DISPLAY": ":0", "WAYLAND_DISPLAY": "wayland-0"}, find_library=lambda n: None, load=_no_lib) is None
    assert display_problem("linux", {"DISPLAY": ":0", "QT_QPA_PLATFORM": "offscreen"}, find_library=lambda n: None, load=_no_lib) is None


def test_other_systems_are_never_checked():
    from live_bitcoin_tracker.gui.main import display_problem

    assert display_problem("win32", {"DISPLAY": ":0"}, find_library=lambda n: None, load=_no_lib) is None
    assert display_problem("darwin", {"DISPLAY": ":0"}, find_library=lambda n: None, load=_no_lib) is None


# ---- app icon and desktop identity --------------------------------------------------------------------
def test_the_icon_is_bundled_valid_and_matches_the_installer_copy(qapp):
    from pathlib import Path

    from PySide6.QtGui import QImage

    from live_bitcoin_tracker.gui import main

    bundled = Path(main.__file__).parent / "assets" / "icon.png"
    installer = Path(main.__file__).parents[3] / "packaging" / "linux" / "icon.png"
    image = QImage(str(bundled))
    assert not image.isNull() and image.width() >= 256 and image.width() == image.height()
    assert bundled.read_bytes() == installer.read_bytes()  # one picture everywhere


def test_the_app_names_itself_and_sets_the_icon_so_desktops_do_not_show_a_gear(qapp):
    from PySide6.QtGui import QGuiApplication

    from live_bitcoin_tracker.gui import main

    main.apply_app_identity(qapp)
    assert qapp.applicationName() == "Live Bitcoin Tracker"
    assert QGuiApplication.desktopFileName() == main.DESKTOP_FILE == "live-bitcoin-tracker"
    assert not qapp.windowIcon().isNull()


def test_the_linux_desktop_entry_matches_the_app_and_the_installer():
    from pathlib import Path

    root = Path(__file__).parents[2] / "packaging" / "linux"
    entry = (root / "live-bitcoin-tracker.desktop").read_text()
    assert "Icon=live-bitcoin-tracker" in entry and "StartupWMClass=live-bitcoin-tracker" in entry
    installer = (root / "install-gui.sh").read_text()
    assert "live-bitcoin-tracker.png" in installer and "live-bitcoin-tracker.desktop" in installer


def test_a_qt_library_that_will_not_load_is_reported_as_such_not_as_a_missing_extra(monkeypatch, capsys):
    from live_bitcoin_tracker.gui import main

    def boom(_args):
        raise ImportError("libEGL.so.1: cannot open shared object file: No such file or directory", name="PySide6.QtGui")

    monkeypatch.setattr(main, "run", boom)
    monkeypatch.setattr(main, "display_problem", lambda *a, **k: None)
    assert main.main([]) == 1
    err = capsys.readouterr().err
    assert "libEGL.so.1" in err and "needs the GUI extra" not in err


def test_a_missing_pyside_is_still_reported_as_a_missing_extra(monkeypatch, capsys):
    from live_bitcoin_tracker.gui import main

    def boom(_args):
        raise ImportError("No module named 'PySide6'", name="PySide6")

    monkeypatch.setattr(main, "run", boom)
    monkeypatch.setattr(main, "display_problem", lambda *a, **k: None)
    assert main.main([]) == 1
    assert "needs the GUI extra" in capsys.readouterr().err
