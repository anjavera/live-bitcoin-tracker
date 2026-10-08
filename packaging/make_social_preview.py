"""Draws docs/social-preview.png (1280x640), the picture GitHub shows when the repo is shared.

Run:  QT_QPA_PLATFORM=offscreen uv run --extra gui python packaging/make_social_preview.py
GitHub only accepts it by hand: repo Settings > General > Social preview > Upload an image.
"""

import sys
from pathlib import Path

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QGuiApplication, QImage, QPainter, QPen

ROOT = Path(__file__).resolve().parents[1]
W, H = 1280, 640
PAGE, CARD, TEXT, MUTED, ORANGE = "#0e1117", "#1b1f2a", "#ffffff", "#9aa3b2", "#f7931a"


def draw(out: Path) -> None:
    image = QImage(W, H, QImage.Format.Format_ARGB32)
    image.fill(QColor(PAGE))
    p = QPainter(image)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    icon = QImage(str(ROOT / "packaging" / "linux" / "icon.png"))
    p.drawImage(QRectF(150, 192, 256, 256), icon)  # drawn at its own size: no blur

    def text(x, y, w, h, s, px, color, bold=False, align=Qt.AlignmentFlag.AlignLeft):
        font = QFont("DejaVu Sans")
        font.setPixelSize(px)
        font.setBold(bold)
        p.setFont(font)
        p.setPen(QColor(color))
        p.drawText(QRectF(x, y, w, h), int(align | Qt.AlignmentFlag.AlignVCenter), s)

    text(520, 150, 740, 90, "Live Bitcoin Tracker", 62, TEXT, bold=True)
    text(520, 245, 700, 50, "Polymarket US: Bitcoin Up or Down", 34, MUTED)
    x = 520
    for label in ("15 min", "Hourly", "Daily"):  # the three tabs
        w = 40 + len(label) * 22
        p.setBrush(QColor(CARD))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(QRectF(x, 335, w, 64), 32, 32)
        text(x, 335, w, 64, label, 28, TEXT, bold=True, align=Qt.AlignmentFlag.AlignHCenter)
        x += w + 18
    p.setPen(QPen(QColor(ORANGE), 4))
    p.drawLine(520, 438, 1120, 438)
    text(520, 455, 700, 90, "Live price, odds, countdown and colour-coded history\nfor the last 24 hours and the last 30 days", 26, MUTED)
    p.end()
    image.save(str(out))


if __name__ == "__main__":
    app = QGuiApplication.instance() or QGuiApplication(sys.argv[:1])
    target = ROOT / "docs" / "social-preview.png"
    draw(target)
    print(target)
