import subprocess
import sys

from btc15_widget.gui.main import main


def test_version_prints_and_exits_zero(capsys):
    assert main(["--version"]) == 0
    assert capsys.readouterr().out.startswith("btc15-gui ")


def test_main_module_imports_without_pyside():
    code = ("import sys; sys.modules['PySide6'] = None; "
            "import btc15_widget.gui.main; print('ok')")
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "ok"


def _no_lib(name):
    raise OSError(name)


def test_linux_x11_without_xcb_cursor_gets_a_plain_hint():
    from btc15_widget.gui.main import display_problem

    msg = display_problem("linux", {"DISPLAY": ":0"}, find_library=lambda name: None, load=_no_lib)
    assert msg and "libxcb-cursor0" in msg and "apt install" in msg


def test_library_found_by_loading_it_is_fine_even_if_find_library_cannot_see_it():
    from btc15_widget.gui.main import display_problem

    assert display_problem("linux", {"DISPLAY": ":0"}, find_library=lambda n: None, load=lambda n: object()) is None


def test_no_display_variable_means_no_check():
    from btc15_widget.gui.main import display_problem

    assert display_problem("linux", {}, find_library=lambda n: None, load=_no_lib) is None


def test_linux_with_the_library_or_wayland_or_forced_platform_is_fine():
    from btc15_widget.gui.main import display_problem

    assert display_problem("linux", {"DISPLAY": ":0"}, find_library=lambda n: "libxcb-cursor.so.0", load=_no_lib) is None
    assert display_problem("linux", {"DISPLAY": ":0", "WAYLAND_DISPLAY": "wayland-0"}, find_library=lambda n: None, load=_no_lib) is None
    assert display_problem("linux", {"DISPLAY": ":0", "QT_QPA_PLATFORM": "offscreen"}, find_library=lambda n: None, load=_no_lib) is None


def test_other_systems_are_never_checked():
    from btc15_widget.gui.main import display_problem

    assert display_problem("win32", {"DISPLAY": ":0"}, find_library=lambda n: None, load=_no_lib) is None
    assert display_problem("darwin", {"DISPLAY": ":0"}, find_library=lambda n: None, load=_no_lib) is None
