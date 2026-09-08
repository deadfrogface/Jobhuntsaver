"""Shared desktop styles – calm professional look (no purple/glow)."""

APP_STYLESHEET = """
QWidget {
    font-family: "Segoe UI", "Calibri", sans-serif;
    font-size: 13px;
    color: #1c2430;
}
QMainWindow, QDialog {
    background: #eef2f6;
}
QFrame#Sidebar {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #1a3a4a, stop:1 #0f2733);
    border: none;
}
QLabel#Brand {
    color: #f4f7fa;
    font-size: 18px;
    font-weight: 700;
    letter-spacing: 0.5px;
}
QPushButton.NavButton {
    text-align: left;
    padding: 10px 14px;
    border: none;
    border-radius: 6px;
    color: #d7e4ec;
    background: transparent;
}
QPushButton.NavButton:hover {
    background: rgba(255,255,255,0.08);
}
QPushButton.NavButton[active="true"] {
    background: rgba(61, 139, 120, 0.35);
    color: #ffffff;
    font-weight: 600;
}
QFrame#Card {
    background: #ffffff;
    border: 1px solid #d5dee8;
    border-radius: 10px;
}
QLabel#CardValue {
    font-size: 22px;
    font-weight: 700;
    color: #143447;
}
QLabel#CardTitle {
    color: #5a6b7a;
    font-size: 12px;
}
QPushButton#PrimaryButton {
    background: #2f7a68;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 9px 16px;
    font-weight: 600;
}
QPushButton#PrimaryButton:hover {
    background: #266456;
}
QPushButton#PrimaryButton:disabled {
    background: #9bb5ad;
}
QPushButton#SecondaryButton {
    background: #ffffff;
    border: 1px solid #b7c4d1;
    border-radius: 6px;
    padding: 8px 14px;
}
QPushButton#SecondaryButton:hover {
    background: #f3f7fa;
}
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QTextEdit, QPlainTextEdit {
    background: #ffffff;
    border: 1px solid #c5d0db;
    border-radius: 5px;
    padding: 6px 8px;
}
QTableWidget {
    background: #ffffff;
    border: 1px solid #d5dee8;
    border-radius: 8px;
    gridline-color: #e6edf3;
}
QHeaderView::section {
    background: #f4f7fa;
    padding: 6px;
    border: none;
    border-bottom: 1px solid #d5dee8;
    font-weight: 600;
}
QStatusBar {
    background: #e4ebf2;
}
QProgressBar {
    border: 1px solid #c5d0db;
    border-radius: 5px;
    text-align: center;
    background: #ffffff;
}
QProgressBar::chunk {
    background: #3d8b78;
    border-radius: 4px;
}
"""
