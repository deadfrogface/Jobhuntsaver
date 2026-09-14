"""Theme detection and light/dark stylesheets (Stellenanker design system)."""

from __future__ import annotations

import sys

from desktop.branding import (
    COLOR_ACCENT,
    COLOR_DARK_BG,
    COLOR_LIGHT_BG,
    COLOR_PRIMARY,
    COLOR_PRIMARY_HOVER,
    COLOR_SIDEBAR_BOTTOM,
    COLOR_SIDEBAR_TOP,
)


def detect_system_dark() -> bool:
    """Return True if Windows prefers dark mode. Failures fall back to light."""
    if sys.platform != "win32":
        return False
    try:
        import winreg

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        )
        value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        winreg.CloseKey(key)
        return int(value) == 0
    except Exception:
        return False


def resolve_theme(preference: str) -> str:
    pref = (preference or "system").lower()
    if pref == "dark":
        return "dark"
    if pref == "light":
        return "light"
    return "dark" if detect_system_dark() else "light"


LIGHT_STYLESHEET = f"""
QWidget {{
    font-family: "Segoe UI", "Calibri", sans-serif;
    font-size: 13px;
    color: #1c2430;
}}
QMainWindow, QDialog, QWizard {{
    background: {COLOR_LIGHT_BG};
}}
QScrollArea {{
    border: none;
    background: transparent;
}}
QFrame#Sidebar {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 {COLOR_SIDEBAR_TOP}, stop:1 {COLOR_SIDEBAR_BOTTOM});
    border: none;
    min-width: 168px;
    max-width: 240px;
}}
QLabel#Brand {{
    color: #f4f7fa;
    font-size: 17px;
    font-weight: 700;
    letter-spacing: 0.2px;
}}
QLabel#BrandTagline {{
    color: rgba(244,247,250,0.72);
    font-size: 11px;
}}
QLabel#PageTitle {{
    font-size: 20px;
    font-weight: 700;
    color: #143447;
}}
QLabel#PageSubtitle {{
    color: #5a6b7a;
    font-size: 13px;
}}
QLabel#EmptyState {{
    color: #5a6b7a;
    font-size: 14px;
    padding: 24px;
}}
QLabel#NextActionTitle {{
    font-size: 16px;
    font-weight: 700;
    color: #143447;
}}
QLabel#BadgeOk, QLabel#BadgeWarn, QLabel#BadgeDanger, QLabel#BadgeMuted, QLabel#BadgeInfo {{
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 600;
}}
QLabel#BadgeOk {{ background: #d8efe8; color: #18574b; }}
QLabel#BadgeWarn {{ background: #fce8d5; color: #8a3d12; }}
QLabel#BadgeDanger {{ background: #f5d6d6; color: #8a1f1f; }}
QLabel#BadgeMuted {{ background: #e6edf3; color: #5a6b7a; }}
QLabel#BadgeInfo {{ background: #dce8f2; color: #1a3a4a; }}
QPushButton#NavButton {{
    text-align: left;
    padding: 10px 14px;
    border: none;
    border-radius: 6px;
    color: #d7e4ec;
    background: transparent;
}}
QPushButton#NavButton:hover {{
    background: rgba(255,255,255,0.08);
}}
QPushButton#NavButton:checked {{
    background: rgba(31, 107, 92, 0.45);
    color: #ffffff;
    font-weight: 600;
}}
QFrame#Card, QFrame#HeroCard, QFrame#DetailPanel {{
    background: #ffffff;
    border: 1px solid #d5dee8;
    border-radius: 10px;
}}
QFrame#HeroCard {{
    padding: 4px;
}}
QLabel#CardValue {{
    font-size: 22px;
    font-weight: 700;
    color: #143447;
}}
QLabel#CardTitle {{
    color: #5a6b7a;
    font-size: 12px;
}}
QPushButton#PrimaryButton {{
    background: {COLOR_PRIMARY};
    color: white;
    border: none;
    border-radius: 6px;
    padding: 9px 16px;
    font-weight: 600;
}}
QPushButton#PrimaryButton:hover {{ background: {COLOR_PRIMARY_HOVER}; }}
QPushButton#PrimaryButton:disabled {{ background: #9bb5ad; color: #f2f2f2; }}
QPushButton#SecondaryButton {{
    background: #ffffff;
    color: #1c2430;
    border: 1px solid #b7c4d1;
    border-radius: 6px;
    padding: 8px 14px;
}}
QPushButton#SecondaryButton:hover {{ background: #f3f7fa; }}
QPushButton#GhostButton {{
    background: transparent;
    color: {COLOR_PRIMARY};
    border: none;
    padding: 6px 10px;
    font-weight: 600;
}}
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QTextEdit, QPlainTextEdit, QListWidget {{
    background: #ffffff;
    color: #1c2430;
    border: 1px solid #c5d0db;
    border-radius: 5px;
    padding: 6px 8px;
    selection-background-color: {COLOR_PRIMARY};
    selection-color: #ffffff;
}}
QTableWidget {{
    background: #ffffff;
    color: #1c2430;
    border: 1px solid #d5dee8;
    border-radius: 8px;
    gridline-color: #e6edf3;
}}
QHeaderView::section {{
    background: #f4f7fa;
    color: #1c2430;
    padding: 6px;
    border: none;
    border-bottom: 1px solid #d5dee8;
    font-weight: 600;
}}
QGroupBox {{
    font-weight: 600;
    border: 1px solid #d5dee8;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 12px;
    background: #ffffff;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
    color: #143447;
}}
QTabWidget::pane {{
    border: 1px solid #d5dee8;
    border-radius: 6px;
    background: #ffffff;
}}
QTabBar::tab {{
    background: #e4ebf2;
    color: #1c2430;
    padding: 8px 14px;
    margin-right: 2px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
}}
QTabBar::tab:selected {{
    background: #ffffff;
    font-weight: 600;
}}
QStatusBar {{ background: #e4ebf2; color: #1c2430; }}
QScrollBar:vertical {{
    background: {COLOR_LIGHT_BG};
    width: 12px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: #b7c4d1;
    border-radius: 5px;
    min-height: 24px;
}}
QToolTip {{
    background: #1c2430;
    color: #ffffff;
    border: none;
    padding: 4px 8px;
}}
QCheckBox, QRadioButton {{ color: #1c2430; spacing: 8px; }}
QMenu {{
    background: #ffffff;
    color: #1c2430;
    border: 1px solid #d5dee8;
}}
QMenu::item:selected {{ background: {COLOR_PRIMARY}; color: #ffffff; }}
QLabel#WarningLabel {{ color: {COLOR_ACCENT}; font-weight: 600; }}
QPlainTextEdit#LogPlain {{
    font-family: "Cascadia Mono", "Consolas", monospace;
    font-size: 12px;
}}
QListWidget#EventList {{
    border: 1px solid #d5dee8;
    border-radius: 8px;
    padding: 4px;
}}
"""

DARK_STYLESHEET = f"""
QWidget {{
    font-family: "Segoe UI", "Calibri", sans-serif;
    font-size: 13px;
    color: #e8eef4;
}}
QMainWindow, QDialog, QWizard {{
    background: {COLOR_DARK_BG};
}}
QScrollArea {{
    border: none;
    background: transparent;
}}
QFrame#Sidebar {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #0d1b24, stop:1 #071018);
    border: none;
    min-width: 168px;
    max-width: 240px;
}}
QLabel#Brand {{
    color: #f4f7fa;
    font-size: 17px;
    font-weight: 700;
}}
QLabel#BrandTagline {{
    color: rgba(244,247,250,0.65);
    font-size: 11px;
}}
QLabel#PageTitle {{
    font-size: 20px;
    font-weight: 700;
    color: #f2f7fb;
}}
QLabel#PageSubtitle {{
    color: #9ab5b6;
    font-size: 13px;
}}
QLabel#EmptyState {{
    color: #9ab5b6;
    font-size: 14px;
    padding: 24px;
}}
QLabel#NextActionTitle {{
    font-size: 16px;
    font-weight: 700;
    color: #f2f7fb;
}}
QLabel#BadgeOk {{ background: #1f3d36; color: #9fd5c4; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }}
QLabel#BadgeWarn {{ background: #3d2a18; color: #f0c090; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }}
QLabel#BadgeDanger {{ background: #3d1a1a; color: #f0a0a0; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }}
QLabel#BadgeMuted {{ background: #243343; color: #9ab5b6; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }}
QLabel#BadgeInfo {{ background: #1a3040; color: #a8c8dc; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }}
QPushButton#NavButton {{
    text-align: left;
    padding: 10px 14px;
    border: none;
    border-radius: 6px;
    color: #c9d7e2;
    background: transparent;
}}
QPushButton#NavButton:hover {{
    background: rgba(255,255,255,0.08);
}}
QPushButton#NavButton:checked {{
    background: rgba(31, 107, 92, 0.55);
    color: #ffffff;
    font-weight: 600;
}}
QFrame#Card, QFrame#HeroCard, QFrame#DetailPanel {{
    background: #1a2430;
    border: 1px solid #2b3a4a;
    border-radius: 10px;
}}
QLabel#CardValue {{
    font-size: 22px;
    font-weight: 700;
    color: #f2f7fb;
}}
QLabel#CardTitle {{
    color: #9ab5b6;
    font-size: 12px;
}}
QPushButton#PrimaryButton {{
    background: #3d8b78;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 9px 16px;
    font-weight: 600;
}}
QPushButton#PrimaryButton:hover {{ background: #347867; }}
QPushButton#PrimaryButton:disabled {{ background: #3a4a55; color: #9aa8b4; }}
QPushButton#SecondaryButton {{
    background: #1a2430;
    color: #e8eef4;
    border: 1px solid #3a4d60;
    border-radius: 6px;
    padding: 8px 14px;
}}
QPushButton#SecondaryButton:hover {{ background: #223142; }}
QPushButton#GhostButton {{
    background: transparent;
    color: #9fd5c4;
    border: none;
    padding: 6px 10px;
    font-weight: 600;
}}
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QTextEdit, QPlainTextEdit, QListWidget {{
    background: #0f161e;
    color: #e8eef4;
    border: 1px solid #3a4d60;
    border-radius: 5px;
    padding: 6px 8px;
    selection-background-color: #3d8b78;
    selection-color: #ffffff;
}}
QComboBox QAbstractItemView {{
    background: #1a2430;
    color: #e8eef4;
    selection-background-color: #3d8b78;
}}
QTableWidget {{
    background: #0f161e;
    color: #e8eef4;
    border: 1px solid #2b3a4a;
    border-radius: 8px;
    gridline-color: #243343;
    alternate-background-color: #15202b;
}}
QHeaderView::section {{
    background: #1a2430;
    color: #e8eef4;
    padding: 6px;
    border: none;
    border-bottom: 1px solid #2b3a4a;
    font-weight: 600;
}}
QGroupBox {{
    font-weight: 600;
    border: 1px solid #2b3a4a;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 12px;
    background: #1a2430;
    color: #e8eef4;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
    color: #d7e6f0;
}}
QTabWidget::pane {{
    border: 1px solid #2b3a4a;
    border-radius: 6px;
    background: #1a2430;
}}
QTabBar::tab {{
    background: #121820;
    color: #c9d7e2;
    padding: 8px 14px;
    margin-right: 2px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
}}
QTabBar::tab:selected {{
    background: #1a2430;
    color: #ffffff;
    font-weight: 600;
}}
QStatusBar {{ background: #0f161e; color: #c9d7e2; }}
QScrollBar:vertical {{
    background: #121820;
    width: 12px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: #3a4d60;
    border-radius: 5px;
    min-height: 24px;
}}
QToolTip {{
    background: #e8eef4;
    color: #121820;
    border: none;
    padding: 4px 8px;
}}
QCheckBox, QRadioButton {{ color: #e8eef4; spacing: 8px; }}
QMenu {{
    background: #1a2430;
    color: #e8eef4;
    border: 1px solid #2b3a4a;
}}
QMenu::item:selected {{ background: #3d8b78; color: #ffffff; }}
QMessageBox {{ background: #1a2430; }}
QMessageBox QLabel {{ color: #e8eef4; }}
QLabel#WarningLabel {{ color: #f0c090; font-weight: 600; }}
QPlainTextEdit#LogPlain {{
    font-family: "Cascadia Mono", "Consolas", monospace;
    font-size: 12px;
}}
QListWidget#EventList {{
    border: 1px solid #2b3a4a;
    border-radius: 8px;
    padding: 4px;
}}
"""


def stylesheet_for(preference: str) -> str:
    theme = resolve_theme(preference)
    return DARK_STYLESHEET if theme == "dark" else LIGHT_STYLESHEET
