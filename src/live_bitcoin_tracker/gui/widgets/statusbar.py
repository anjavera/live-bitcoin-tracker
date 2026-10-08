"""One muted line (or two, when there is an error) at the bottom of the window."""

from PySide6.QtWidgets import QLabel


class StatusBar(QLabel):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("muted")
        self.setWordWrap(True)

    def set_text(self, text: str) -> None:
        self.setText(text)
