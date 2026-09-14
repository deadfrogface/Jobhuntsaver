"""About dialog — Karrierekrake brand artwork + technical identity note."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QVBoxLayout,
)

from desktop import __version__
from desktop.branding import (
    DATA_DIR_NAME,
    DISPLAY_NAME,
    EXE_BASENAME,
    SHORT_DESCRIPTION_DE,
    SHORT_DESCRIPTION_EN,
    TAGLINE_DE,
    TAGLINE_EN,
    TECHNICAL_NAME,
    logo_path,
)
from desktop.i18n import i18n, tr
from desktop.tray import app_icon


class AboutDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("about.title"))
        self.setWindowIcon(app_icon())
        self.setMinimumWidth(480)
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        self.art = QLabel()
        self.art.setAlignment(Qt.AlignmentFlag.AlignCenter)
        path = logo_path(master=True) or logo_path()
        if path is not None:
            pix = QPixmap(str(path))
            if not pix.isNull():
                self.art.setPixmap(
                    pix.scaledToWidth(420, Qt.TransformationMode.SmoothTransformation)
                )
        layout.addWidget(self.art)

        self.title = QLabel()
        self.title.setObjectName("PageTitle")
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title)

        self.tagline = QLabel()
        self.tagline.setObjectName("PageSubtitle")
        self.tagline.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.tagline.setWordWrap(True)
        layout.addWidget(self.tagline)

        self.body = QLabel()
        self.body.setWordWrap(True)
        self.body.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.body)

        self.tech = QLabel()
        self.tech.setObjectName("PageSubtitle")
        self.tech.setWordWrap(True)
        self.tech.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.tech)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)
        self.retranslate_ui()

    def retranslate_ui(self) -> None:
        lang = (i18n.language or "de").lower()
        self.setWindowTitle(tr("about.title"))
        self.title.setText(f"{DISPLAY_NAME}  ·  v{__version__}")
        self.tagline.setText(TAGLINE_EN if lang.startswith("en") else TAGLINE_DE)
        self.body.setText(
            SHORT_DESCRIPTION_EN if lang.startswith("en") else SHORT_DESCRIPTION_DE
        )
        self.tech.setText(
            tr("about.tech").format(
                display=DISPLAY_NAME,
                technical=TECHNICAL_NAME,
                exe=f"{EXE_BASENAME}.exe",
                data=DATA_DIR_NAME,
            )
        )
