"""Warm Security Console stylesheet and UI tokens for SENTRON.

Color Palette:
- Charcoal black: #171717
- Warm white: #F5F2E9
- Golden yellow: #E2B83B
- Muted warm grey: #D9D4C8
"""

WARM_CONSOLE_QSS = """
/* Global Window & Fonts */
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
}

QPushButton#btnAsk, QPushButton#btnWarning {
    background-color: #E2B83B;
    color: #171717;
    border: 1px solid #C49B24;
    font-weight: 700;
}
QPushButton#btnAsk:hover, QPushButton#btnWarning:hover {
    background-color: #F0C952;
}

QPushButton#btnBlock, QPushButton#btnReject {
    background-color: #8C2424;
    color: #FFFFFF;
    border: 1px solid #6E1B1B;
}
QPushButton#btnBlock:hover, QPushButton#btnReject:hover {
    background-color: #A32D2D;
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

/* Navigation Buttons */
QPushButton#navBtnActive {
    background-color: #E2B83B;
    color: #171717;
    border: 1px solid #E2B83B;
    border-radius: 6px;
    padding: 8px 18px;
    font-weight: 800;
}
QPushButton#navBtnInactive {
    background-color: #212121;
    color: #D9D4C8;
    border: 1px solid #333333;
    border-radius: 6px;
    padding: 8px 18px;
    font-weight: 600;
}
QPushButton#navBtnInactive:hover {
    background-color: #2A2A2A;
    color: #E2B83B;
    border-color: #E2B83B;
}

/* Input Fields */
QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: #FFFFFF;
    color: #171717;
    border: 1px solid #D9D4C8;
    border-radius: 6px;
    padding: 6px 10px;
    selection-background-color: #E2B83B;
    selection-color: #171717;
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border-color: #E2B83B;
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

/* Badges / Labels */
QLabel#brandTitle {
    font-size: 19px;
    font-weight: 900;
    color: #E2B83B;
    letter-spacing: 0.5px;
}
QLabel#brandTagline {
    font-size: 12px;
    color: #D9D4C8;
}
QLabel#badgeActive {
    background-color: #171717;
    color: #E2B83B;
    border: 1px solid #E2B83B;
    border-radius: 10px;
    padding: 3px 10px;
    font-weight: 700;
    font-size: 11px;
}
QLabel#badgeSafe {
    background-color: #25593122;
    color: #255931;
    border: 1px solid #255931;
    border-radius: 10px;
    padding: 3px 10px;
    font-weight: 700;
    font-size: 11px;
}
QLabel#badgeWarning {
    background-color: #E2B83B22;
    color: #8A6200;
    border: 1px solid #E2B83B;
    border-radius: 10px;
    padding: 3px 10px;
    font-weight: 700;
    font-size: 11px;
}
QLabel#badgeDanger {
    background-color: #8C242422;
    color: #8C2424;
    border: 1px solid #8C2424;
    border-radius: 10px;
    padding: 3px 10px;
    font-weight: 700;
    font-size: 11px;
}
"""

# Maintain backward compatibility for any existing imports
DARK_THEME_QSS = WARM_CONSOLE_QSS
