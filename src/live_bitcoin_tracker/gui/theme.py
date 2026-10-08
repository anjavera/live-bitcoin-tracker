"""Look of the desktop window: palette, fonts and one Qt style sheet (modelled on Polymarket's event page)."""

from pathlib import Path

PAGE = "#0b0d12"
CARD = "#1c1f27"
UP = "#00AE4B"
DOWN = "#FE3D32"
BTC_ORANGE = "#F7931A"
MUTED = "#9aa3b2"
TEXT = "#ffffff"
RADIUS = 20

HEADLINE_FONT = "Instrument Sans Condensed"
BODY_FONT = "Inter"
FALLBACK_FONTS = ("Segoe UI", "Helvetica Neue", "DejaVu Sans")
FONT_DIR = Path(__file__).parent / "fonts"


def pick_fonts(available: list[str]) -> tuple[str, str]:
    """(headline family, body family): Polymarket's fonts when installed, else a plain system font, else ''."""
    fallback = next((f for f in FALLBACK_FONTS if f in available), "")
    return (HEADLINE_FONT if HEADLINE_FONT in available else fallback,
            BODY_FONT if BODY_FONT in available else fallback)


def load_bundled_fonts(directory: Path = FONT_DIR) -> list[str]:
    """Register the .ttf files shipped in `directory` with Qt; returns their family names ([] if there are none)."""
    if not directory.is_dir():
        return []
    from PySide6.QtGui import QFontDatabase

    families: list[str] = []
    for path in sorted(directory.glob("*.ttf")):
        font_id = QFontDatabase.addApplicationFont(str(path))
        if font_id >= 0:
            families.extend(QFontDatabase.applicationFontFamilies(font_id))
    return families


def stylesheet(headline: str = "", body: str = "") -> str:
    body_rule = f"font-family: '{body}';" if body else ""
    head_rule = f"font-family: '{headline}';" if headline else ""
    return f"""
QMainWindow, QWidget#page {{ background: {PAGE}; }}
QWidget {{ color: {TEXT}; {body_rule} font-size: 14px; }}
QFrame#card {{ background: {CARD}; border-radius: {RADIUS}px; }}
QLabel#muted {{ color: {MUTED}; }}
QLabel#big {{ {head_rule} font-size: 24px; font-weight: 700; }}
QLabel#title {{ {head_rule} font-size: 32px; font-weight: 700; }}
QPushButton#pill {{ background: {CARD}; border: none; border-radius: 999px; padding: 6px 16px; }}
QPushButton#pill:checked {{ background: {TEXT}; color: {PAGE}; }}
QPushButton#tab {{ background: transparent; color: {MUTED}; border: none; border-bottom: 2px solid transparent; padding: 6px 14px; font-weight: 600; }}
QPushButton#tab:hover {{ color: {TEXT}; }}
QPushButton#tab:checked {{ color: {TEXT}; border-bottom: 2px solid {BTC_ORANGE}; }}
QTableView {{ background: {CARD}; gridline-color: {PAGE}; border: none; }}
QHeaderView::section {{ background: {CARD}; color: {MUTED}; border: none; padding: 4px; }}
"""
