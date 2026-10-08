# Third-party notices

The desktop window (`bitcoin-tracker`) uses **Qt for Python (PySide6)**, which is licensed under the GNU LGPL v3
(<https://doc.qt.io/qtforpython-6/licenses.html>). The standalone GUI builds package the unmodified Qt libraries
inside a single PyInstaller file (they are unpacked to a temporary folder when the app starts). Whether that
packaging fully satisfies the LGPL's "replace the library" terms has not been reviewed by a lawyer; the source of this
project and the exact PySide6 version (see `uv.lock`) are public, so you can run it against your own Qt with
`uv sync --extra gui`. Qt is a trademark of The Qt Company Ltd. The terminal widget does not use Qt.

Bundled fonts: none. The window uses Inter and Instrument Sans Condensed if they are installed on your computer
(both published under the SIL Open Font License 1.1 as far as we know) and your system font otherwise.

This project is not affiliated with Polymarket or CF Benchmarks; the look of the window is inspired by the public
Polymarket website, and no Polymarket logo, name artwork or code is used.
