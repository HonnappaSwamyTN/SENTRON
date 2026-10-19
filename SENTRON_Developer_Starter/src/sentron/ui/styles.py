"""Dark security dashboard stylesheet and UI tokens for SENTRON."""

DARK_THEME_QSS = """
/* Global Window & Fonts */
QMainWindow, QDialog, QWidget {
    background-color: #0d1117;
    color: #e6edf3;
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    font-size: 13px;
}

/* Scrollbars */
QScrollBar:vertical {
    border: none;
    background: #161b22;
    width: 8px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background: #30363d;
    min-height: 20px;
    border-radius: 4px;
}
QScrollBar::handle:vertical:hover {
    background: #58a6ff;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    border: none;
    background: #161b22;
    height: 8px;
    margin: 0px;
}
QScrollBar::handle:horizontal {
    background: #30363d;
    min-width: 20px;
    border-radius: 4px;
}
QScrollBar::handle:horizontal:hover {
    background: #58a6ff;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

/* Splitter */
QSplitter::handle {
    background-color: #21262d;
}
QSplitter::handle:hover {
    background-color: #58a6ff;
}

/* Scroll Area */
QScrollArea {
    background: transparent;
    border: none;
}

/* Tabs */
QTabWidget::pane {
    border: 1px solid #30363d;
    background: #161b22;
    border-radius: 8px;
}
QTabBar::tab {
    background: #161b22;
    color: #8b949e;
    padding: 10px 20px;
    border: 1px solid #30363d;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 4px;
    font-weight: 600;
}
QTabBar::tab:selected {
    background: #21262d;
    color: #58a6ff;
    border-bottom: 2px solid #58a6ff;
}
QTabBar::tab:hover {
    background: #1f242c;
    color: #f0f6fc;
}

/* GroupBox / Cards */
QGroupBox {
    background-color: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
    margin-top: 24px;
    padding: 16px;
    font-weight: 700;
    font-size: 13px;
    color: #f0f6fc;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 4px 10px;
    background-color: #21262d;
    border: 1px solid #30363d;
    border-radius: 4px;
    color: #58a6ff;
}

/* Buttons */
QPushButton {
    background-color: #21262d;
    color: #c9d1d9;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 600;
}
QPushButton:hover {
    background-color: #30363d;
    border-color: #8b949e;
    color: #ffffff;
}
QPushButton:pressed {
    background-color: #161b22;
}
QPushButton:disabled {
    background-color: #161b22;
    color: #484f58;
    border-color: #21262d;
}

/* Action-specific button classes */
QPushButton#btnAllow, QPushButton#btnApprove {
    background-color: #238636;
    color: #ffffff;
    border: 1px solid #2ea043;
}
QPushButton#btnAllow:hover, QPushButton#btnApprove:hover {
    background-color: #2ea043;
}

QPushButton#btnAsk, QPushButton#btnWarning {
    background-color: #9e6a03;
    color: #ffffff;
    border: 1px solid #bb8009;
}
QPushButton#btnAsk:hover, QPushButton#btnWarning:hover {
    background-color: #bb8009;
}

QPushButton#btnBlock, QPushButton#btnReject {
    background-color: #b62324;
    color: #ffffff;
    border: 1px solid #da3633;
}
QPushButton#btnBlock:hover, QPushButton#btnReject:hover {
    background-color: #da3633;
}

QPushButton#btnPrimary {
    background-color: #1f6feb;
    color: #ffffff;
    border: 1px solid #388bfd;
}
QPushButton#btnPrimary:hover {
    background-color: #388bfd;
}

/* Input Fields */
QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: #0d1117;
    color: #f0f6fc;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 6px 10px;
    selection-background-color: #1f6feb;
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border-color: #58a6ff;
}

/* Tables */
QTableWidget, QTableView {
    background-color: #0d1117;
    border: 1px solid #30363d;
    border-radius: 6px;
    gridline-color: #21262d;
    color: #c9d1d9;
    selection-background-color: #1f6feb;
    selection-color: #ffffff;
}
QHeaderView::section {
    background-color: #161b22;
    color: #8b949e;
    padding: 6px 10px;
    border: 1px solid #21262d;
    font-weight: 600;
}

/* Badges / Labels */
QLabel#brandTitle {
    font-size: 20px;
    font-weight: 800;
    color: #58a6ff;
    letter-spacing: 1px;
}
QLabel#brandTagline {
    font-size: 12px;
    color: #8b949e;
}
QLabel#badgeActive {
    background-color: #1f6feb22;
    color: #58a6ff;
    border: 1px solid #388bfd;
    border-radius: 12px;
    padding: 3px 10px;
    font-weight: 600;
    font-size: 11px;
}
QLabel#badgeSafe {
    background-color: #23863622;
    color: #3fb950;
    border: 1px solid #2ea043;
    border-radius: 12px;
    padding: 3px 10px;
    font-weight: 700;
    font-size: 11px;
}
QLabel#badgeWarning {
    background-color: #9e6a0322;
    color: #d29922;
    border: 1px solid #bb8009;
    border-radius: 12px;
    padding: 3px 10px;
    font-weight: 700;
    font-size: 11px;
}
QLabel#badgeDanger {
    background-color: #b6232422;
    color: #f85149;
    border: 1px solid #da3633;
    border-radius: 12px;
    padding: 3px 10px;
    font-weight: 700;
    font-size: 11px;
}
"""
