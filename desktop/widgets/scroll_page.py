"""Scrollable page helper."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QScrollArea, QSizePolicy, QVBoxLayout, QWidget


def wrap_scrollable(inner: QWidget, *, min_content_width: int = 640) -> QScrollArea:
    """Put a page body into a vertical QScrollArea with expanding width."""
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    inner.setMinimumWidth(min_content_width)
    inner.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    scroll.setWidget(inner)
    return scroll


def make_page_with_scroll(*, min_content_width: int = 640) -> tuple[QWidget, QVBoxLayout, QScrollArea]:
    """Create page root + inner scroll layout for long forms."""
    page = QWidget()
    outer = QVBoxLayout(page)
    outer.setContentsMargins(0, 0, 0, 0)
    inner = QWidget()
    layout = QVBoxLayout(inner)
    layout.setContentsMargins(8, 8, 16, 16)
    layout.setSpacing(14)
    scroll = wrap_scrollable(inner, min_content_width=min_content_width)
    outer.addWidget(scroll)
    return page, layout, scroll
