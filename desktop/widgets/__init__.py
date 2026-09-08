"""Reusable list editor widget (add/remove string items)."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLineEdit,
    QListWidget,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class ListEditor(QWidget):
    def __init__(self, placeholder: str = "Eintrag hinzufügen…", parent=None) -> None:
        super().__init__(parent)
        self.list = QListWidget()
        self.input = QLineEdit()
        self.input.setPlaceholderText(placeholder)
        add_btn = QPushButton("Hinzufügen")
        add_btn.setObjectName("SecondaryButton")
        remove_btn = QPushButton("Entfernen")
        remove_btn.setObjectName("SecondaryButton")
        add_btn.clicked.connect(self._add)
        remove_btn.clicked.connect(self._remove)
        self.input.returnPressed.connect(self._add)

        row = QHBoxLayout()
        row.addWidget(self.input, 1)
        row.addWidget(add_btn)
        row.addWidget(remove_btn)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.list)
        layout.addLayout(row)

    def _add(self) -> None:
        text = self.input.text().strip()
        if not text:
            return
        self.list.addItem(text)
        self.input.clear()

    def _remove(self) -> None:
        for item in self.list.selectedItems():
            self.list.takeItem(self.list.row(item))

    def get_items(self) -> list[str]:
        return [self.list.item(i).text() for i in range(self.list.count())]

    def set_items(self, items: list[str] | None) -> None:
        self.list.clear()
        for item in items or []:
            if item:
                self.list.addItem(str(item))
