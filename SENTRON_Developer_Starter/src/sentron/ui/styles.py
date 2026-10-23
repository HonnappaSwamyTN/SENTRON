"""Security Console stylesheets and theme tokens for SENTRON (Requirement 2).

Provides two complete, accessible themes:
1. Light Mode (Warm Security Console):
   - Warm-white surfaces (#F5F2E9, #FFFFFF)
   - Dark readable text (#171717, #2B2B2B, #4A453A)
   - Black/charcoal elements (#171717, #262626)
   - Gold accents (#E2B83B, #C49B24, #F0C952)

2. Dark Mode (Dark Charcoal Console):
   - Dark charcoal surfaces (#141414, #1C1C1C, #212121)
   - Light readable text (#F5F2E9, #E6EDF3, #A09A8E)
   - Charcoal elements (#262626, #333333)
   - Gold accents (#E2B83B, #F0C952)

Both themes maintain accessible contrast ratios, clear hover, active,
disabled, and keyboard-focus states across all widgets.
"""
from __future__ import annotations

LIGHT_THEME_QSS = """
/* =========================================================================
   LIGHT THEME: Warm Security Console
   ========================================================================= */

QMainWindow, QDialog, QWidget {
    background-color: #F5F2E9;
    color: #171717;
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    font-size: 13px;
}

/* Scrollbars */
QScrollBar:vertical {
    border: none;
    background: #EAE6DB;
    width: 8px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background: #D9D4C8;
    min-height: 24px;
    border-radius: 4px;
}
QScrollBar::handle:vertical:hover {
    background: #E2B83B;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    border: none;
    background: #EAE6DB;
    height: 8px;
    margin: 0px;
}
QScrollBar::handle:horizontal {
    background: #D9D4C8;
    min-width: 24px;
    border-radius: 4px;
}
QScrollBar::handle:horizontal:hover {
    background: #E2B83B;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

/* Splitter */
QSplitter::handle {
    background-color: #D9D4C8;
}
QSplitter::handle:hover {
    background-color: #E2B83B;
}

/* Scroll Area */
QScrollArea {
    background: transparent;
    border: none;
}

/* GroupBox / Card Containers */
QGroupBox {
    background-color: #FFFFFF;
    border: 1px solid #D9D4C8;
    border-radius: 8px;
    margin-top: 24px;
    padding: 14px;
    font-weight: 700;
    font-size: 13px;
    color: #171717;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 4px 10px;
    background-color: #171717;
    border: 1px solid #171717;
    border-radius: 4px;
    color: #E2B83B;
    font-weight: 700;
}

/* Stat Cards */
QFrame#statCard {
    background-color: #FFFFFF;
    border: 1px solid #D9D4C8;
    border-radius: 8px;
    padding: 10px;
}

/* General Buttons */
QPushButton {
    background-color: #171717;
    color: #F5F2E9;
    border: 1px solid #333333;
    border-radius: 6px;
    padding: 7px 14px;
    font-weight: 600;
}
QPushButton:hover {
    background-color: #262626;
    border-color: #E2B83B;
    color: #E2B83B;
}
QPushButton:pressed {
    background-color: #0F0F0F;
}
QPushButton:focus {
    outline: none;
    border: 2px solid #E2B83B;
}
QPushButton:disabled {
    background-color: #E2DDD0;
    color: #8C8578;
    border-color: #D9D4C8;
}

/* Action-specific button classes */
QPushButton#btnAllow, QPushButton#btnApprove {
    background-color: #255931;
    color: #FFFFFF;
    border: 1px solid #1B4524;
}
QPushButton#btnAllow:hover, QPushButton#btnApprove:hover {
    background-color: #2F6F3D;
    color: #FFFFFF;
}

QPushButton#btnAsk, QPushButton#btnWarning {
    background-color: #E2B83B;
    color: #171717;
    border: 1px solid #C49B24;
    font-weight: 700;
}
QPushButton#btnAsk:hover, QPushButton#btnWarning:hover {
    background-color: #F0C952;
    color: #171717;
}

QPushButton#btnBlock, QPushButton#btnReject {
    background-color: #8C2424;
    color: #FFFFFF;
    border: 1px solid #6E1B1B;
}
QPushButton#btnBlock:hover, QPushButton#btnReject:hover {
    background-color: #A32D2D;
    color: #FFFFFF;
}

QPushButton#btnPrimary {
    background-color: #E2B83B;
    color: #171717;
    border: 1px solid #C49B24;
    font-weight: 700;
}
QPushButton#btnPrimary:hover {
    background-color: #F0C952;
}

/* Navigation Bar & Buttons */
QFrame#navContainer {
    background-color: #171717;
    border: 1px solid #2B2B2B;
    border-radius: 8px;
    padding: 4px;
}

QPushButton#navBtnActive {
    background-color: #E2B83B;
    color: #171717;
    border: 2px solid #C49B24;
    border-radius: 6px;
    padding: 8px 18px;
    font-weight: 800;
}
QPushButton#navBtnActive:hover {
    background-color: #F0C952;
    color: #171717;
    border: 2px solid #D4A728;
}
QPushButton#navBtnActive:focus {
    outline: none;
    border: 2px solid #FFFFFF;
}

QPushButton#navBtnInactive {
    background-color: #262626;
    color: #F5F2E9;
    border: 1px solid #383838;
    border-radius: 6px;
    padding: 8px 18px;
    font-weight: 600;
}
QPushButton#navBtnInactive:hover {
    background-color: #383838;
    color: #FFFFFF;
    border: 1px solid #E2B83B;
}
QPushButton#navBtnInactive:focus {
    outline: none;
    border: 2px solid #E2B83B;
}
QPushButton#navBtnInactive:disabled {
    background-color: #1C1C1C;
    color: #666666;
    border: 1px solid #282828;
}

/* Tooltips */
QToolTip {
    background-color: #171717;
    color: #F5F2E9;
    border: 1px solid #E2B83B;
    border-radius: 4px;
    padding: 5px 8px;
    font-size: 11px;
}

/* Input Fields */
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: #FFFFFF;
    color: #171717;
    border: 1px solid #D9D4C8;
    border-radius: 6px;
    padding: 6px 10px;
    selection-background-color: #E2B83B;
    selection-color: #171717;
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QComboBox:focus {
    outline: none;
    border: 2px solid #E2B83B;
}
QComboBox::drop-down {
    border: none;
    width: 20px;
}

/* Tables */
QTableWidget, QTableView {
    background-color: #FFFFFF;
    border: 1px solid #D9D4C8;
    border-radius: 6px;
    gridline-color: #EAE6DB;
    color: #171717;
    selection-background-color: #E2B83B33;
    selection-color: #171717;
}
QHeaderView::section {
    background-color: #171717;
    color: #E2B83B;
    padding: 6px 10px;
    border: 1px solid #262626;
    font-weight: 700;
}

/* Header & Brand Labels (High Contrast Dark on Light Background) */
QLabel#brandTitle {
    font-size: 20px;
    font-weight: 900;
    color: #171717;
    letter-spacing: 0.5px;
}
QLabel#brandTagline {
    font-size: 12px;
    font-weight: 500;
    color: #4A453A;
}
QLabel#headerTitle {
    font-size: 16px;
    font-weight: 800;
    color: #171717;
}
QLabel#secondaryText {
    font-size: 11px;
    color: #4A453A;
}
QLabel#statTitle {
    color: #4A453A;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.5px;
}
QLabel#subLabel {
    color: #4A453A;
    font-size: 11px;
}

/* Badges with High Accessible Contrast */
QLabel#badgeActive {
    background-color: #171717;
    color: #F5F2E9;
    border: 1px solid #E2B83B;
    border-radius: 10px;
    padding: 3px 10px;
    font-weight: 700;
    font-size: 11px;
}
QLabel#badgeSafe {
    background-color: #E6F4EA;
    color: #137333;
    border: 1px solid #137333;
    border-radius: 10px;
    padding: 3px 10px;
    font-weight: 700;
    font-size: 11px;
}
QLabel#badgeWarning {
    background-color: #FEF7E0;
    color: #8A4500;
    border: 1px solid #B06000;
    border-radius: 10px;
    padding: 3px 10px;
    font-weight: 700;
    font-size: 11px;
}
QLabel#badgeDanger {
    background-color: #FCE8E6;
    color: #A51B17;
    border: 1px solid #C5221F;
    border-radius: 10px;
    padding: 3px 10px;
    font-weight: 700;
    font-size: 11px;
}
"""

DARK_THEME_QSS = """
/* =========================================================================
   DARK THEME: Dark Charcoal Console
   ========================================================================= */

QMainWindow, QDialog, QWidget {
    background-color: #141414;
    color: #F5F2E9;
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    font-size: 13px;
}

/* Scrollbars */
QScrollBar:vertical {
    border: none;
    background: #1A1A1A;
    width: 8px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background: #333333;
    min-height: 24px;
    border-radius: 4px;
}
QScrollBar::handle:vertical:hover {
    background: #E2B83B;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    border: none;
    background: #1A1A1A;
    height: 8px;
    margin: 0px;
}
QScrollBar::handle:horizontal {
    background: #333333;
    min-width: 24px;
    border-radius: 4px;
}
QScrollBar::handle:horizontal:hover {
    background: #E2B83B;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

/* Splitter */
QSplitter::handle {
    background-color: #2E2E2E;
}
QSplitter::handle:hover {
    background-color: #E2B83B;
}

/* Scroll Area */
QScrollArea {
    background: transparent;
    border: none;
}

/* GroupBox / Card Containers */
QGroupBox {
    background-color: #1C1C1C;
    border: 1px solid #333333;
    border-radius: 8px;
    margin-top: 24px;
    padding: 14px;
    font-weight: 700;
    font-size: 13px;
    color: #F5F2E9;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 4px 10px;
    background-color: #262626;
    border: 1px solid #383838;
    border-radius: 4px;
    color: #E2B83B;
    font-weight: 700;
}

/* Stat Cards */
QFrame#statCard {
    background-color: #1C1C1C;
    border: 1px solid #333333;
    border-radius: 8px;
    padding: 10px;
}

/* General Buttons */
QPushButton {
    background-color: #262626;
    color: #F5F2E9;
    border: 1px solid #383838;
    border-radius: 6px;
    padding: 7px 14px;
    font-weight: 600;
}
QPushButton:hover {
    background-color: #333333;
    border-color: #E2B83B;
    color: #E2B83B;
}
QPushButton:pressed {
    background-color: #181818;
}
QPushButton:focus {
    outline: none;
    border: 2px solid #E2B83B;
}
QPushButton:disabled {
    background-color: #1A1A1A;
    color: #555555;
    border-color: #262626;
}

/* Action-specific button classes */
QPushButton#btnAllow, QPushButton#btnApprove {
    background-color: #184222;
    color: #FFFFFF;
    border: 1px solid #255931;
}
QPushButton#btnAllow:hover, QPushButton#btnApprove:hover {
    background-color: #255931;
    color: #FFFFFF;
}

QPushButton#btnAsk, QPushButton#btnWarning {
    background-color: #E2B83B;
    color: #141414;
    border: 1px solid #C49B24;
    font-weight: 700;
}
QPushButton#btnAsk:hover, QPushButton#btnWarning:hover {
    background-color: #F0C952;
    color: #141414;
}

QPushButton#btnBlock, QPushButton#btnReject {
    background-color: #6E1B1B;
    color: #FFFFFF;
    border: 1px solid #8C2424;
}
QPushButton#btnBlock:hover, QPushButton#btnReject:hover {
    background-color: #8C2424;
    color: #FFFFFF;
}

QPushButton#btnPrimary {
    background-color: #E2B83B;
    color: #141414;
    border: 1px solid #C49B24;
    font-weight: 700;
}
QPushButton#btnPrimary:hover {
    background-color: #F0C952;
}

/* Navigation Bar & Buttons */
QFrame#navContainer {
    background-color: #1C1C1C;
    border: 1px solid #2E2E2E;
    border-radius: 8px;
    padding: 4px;
}

QPushButton#navBtnActive {
    background-color: #E2B83B;
    color: #141414;
    border: 2px solid #C49B24;
    border-radius: 6px;
    padding: 8px 18px;
    font-weight: 800;
}
QPushButton#navBtnActive:hover {
    background-color: #F0C952;
    color: #141414;
    border: 2px solid #D4A728;
}
QPushButton#navBtnActive:focus {
    outline: none;
    border: 2px solid #FFFFFF;
}

QPushButton#navBtnInactive {
    background-color: #242424;
    color: #D9D4C8;
    border: 1px solid #333333;
    border-radius: 6px;
    padding: 8px 18px;
    font-weight: 600;
}
QPushButton#navBtnInactive:hover {
    background-color: #333333;
    color: #FFFFFF;
    border: 1px solid #E2B83B;
}
QPushButton#navBtnInactive:focus {
    outline: none;
    border: 2px solid #E2B83B;
}
QPushButton#navBtnInactive:disabled {
    background-color: #181818;
    color: #555555;
    border: 1px solid #222222;
}

/* Tooltips */
QToolTip {
    background-color: #212121;
    color: #F5F2E9;
    border: 1px solid #E2B83B;
    border-radius: 4px;
    padding: 5px 8px;
    font-size: 11px;
}

/* Input Fields */
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: #1E1E1E;
    color: #F5F2E9;
    border: 1px solid #383838;
    border-radius: 6px;
    padding: 6px 10px;
    selection-background-color: #E2B83B;
    selection-color: #141414;
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QComboBox:focus {
    outline: none;
    border: 2px solid #E2B83B;
}
QComboBox::drop-down {
    border: none;
    width: 20px;
}

/* Tables */
QTableWidget, QTableView {
    background-color: #1C1C1C;
    border: 1px solid #333333;
    border-radius: 6px;
    gridline-color: #282828;
    color: #F5F2E9;
    selection-background-color: #E2B83B33;
    selection-color: #F5F2E9;
}
QHeaderView::section {
    background-color: #242424;
    color: #E2B83B;
    padding: 6px 10px;
    border: 1px solid #303030;
    font-weight: 700;
}

/* Header & Brand Labels (High Contrast in Dark Mode) */
QLabel#brandTitle {
    font-size: 20px;
    font-weight: 900;
    color: #F5F2E9;
    letter-spacing: 0.5px;
}
QLabel#brandTagline {
    font-size: 12px;
    font-weight: 500;
    color: #A09A8E;
}
QLabel#headerTitle {
    font-size: 16px;
    font-weight: 800;
    color: #F5F2E9;
}
QLabel#secondaryText {
    font-size: 11px;
    color: #A09A8E;
}
QLabel#statTitle {
    color: #A09A8E;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.5px;
}
QLabel#subLabel {
    color: #8C8578;
    font-size: 11px;
}

/* Badges with High Accessible Contrast in Dark Mode */
QLabel#badgeActive {
    background-color: #262626;
    color: #E2B83B;
    border: 1px solid #E2B83B;
    border-radius: 10px;
    padding: 3px 10px;
    font-weight: 700;
    font-size: 11px;
}
QLabel#badgeSafe {
    background-color: #13381B;
    color: #4ADE80;
    border: 1px solid #22C55E;
    border-radius: 10px;
    padding: 3px 10px;
    font-weight: 700;
    font-size: 11px;
}
QLabel#badgeWarning {
    background-color: #3D2800;
    color: #FBBF24;
    border: 1px solid #F59E0B;
    border-radius: 10px;
    padding: 3px 10px;
    font-weight: 700;
    font-size: 11px;
}
QLabel#badgeDanger {
    background-color: #450A0A;
    color: #F87171;
    border: 1px solid #EF4444;
    border-radius: 10px;
    padding: 3px 10px;
    font-weight: 700;
    font-size: 11px;
}
"""

# Backward compatibility alias
WARM_CONSOLE_QSS = LIGHT_THEME_QSS


def get_theme_qss(theme_name: str) -> str:
    """Return the active stylesheet for the requested theme."""
    if (theme_name or "").lower() == "dark":
        return DARK_THEME_QSS
    return LIGHT_THEME_QSS
