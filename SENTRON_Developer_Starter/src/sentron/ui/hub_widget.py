"""Movable Floating Desktop Hub for SENTRON (AC-15).

Compact, movable, always-on-top desktop status widget.
Accurately reflects active subsystem health without falsely claiming protection.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
)


class FloatingHubWidget(QWidget):
    """Movable floating desktop widget exposing module statuses."""

    def __init__(
        self,
        on_toggle_dashboard: callable | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.on_toggle_dashboard = on_toggle_dashboard
        self._drag_pos = QPoint()

        # Window flags for floating hub
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, False)

        self._init_ui()

    def _init_ui(self) -> None:
        self.setObjectName("floatingHub")
        self.setStyleSheet("""
            QWidget#floatingHub {
                background-color: #161b22;
                border: 2px solid #58a6ff;
                border-radius: 10px;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)

        # Brand icon & title
        brand_layout = QVBoxLayout()
        brand_layout.setSpacing(1)
        lbl_brand = QLabel("🛡️ SENTRON")
        lbl_brand.setStyleSheet("font-weight: 800; color: #58a6ff; font-size: 13px;")
        self.lbl_overall = QLabel("LOCAL ACTIVE")
        self.lbl_overall.setStyleSheet("color: #3fb950; font-size: 10px; font-weight: 700;")
        brand_layout.addWidget(lbl_brand)
        brand_layout.addWidget(self.lbl_overall)
        layout.addLayout(brand_layout)

        # Divider line
        div = QFrame()
        div.setFrameShape(QFrame.VLine)
        div.setStyleSheet("color: #30363d;")
        layout.addWidget(div)

        # Module statuses
        status_layout = QVBoxLayout()
        status_layout.setSpacing(2)

        self.lbl_agentguard = QLabel("AgentGuard: 0 Pending")
        self.lbl_agentguard.setStyleSheet("color: #c9d1d9; font-size: 11px;")

        self.lbl_crashguard = QLabel("CrashGuard: Active")
        self.lbl_crashguard.setStyleSheet("color: #c9d1d9; font-size: 11px;")

        status_layout.addWidget(self.lbl_agentguard)
        status_layout.addWidget(self.lbl_crashguard)
        layout.addLayout(status_layout)

        # Toggle Dashboard button
        self.btn_toggle = QPushButton("Dashboard")
        self.btn_toggle.setStyleSheet("""
            QPushButton {
                background-color: #1f6feb;
                color: #ffffff;
                border-radius: 5px;
                padding: 5px 12px;
                font-weight: 600;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #388bfd;
            }
        """)
        if self.on_toggle_dashboard:
            self.btn_toggle.clicked.connect(self.on_toggle_dashboard)
        layout.addWidget(self.btn_toggle)

    def update_status(
        self,
        agent_pending_count: int = 0,
        crash_active: bool = True,
        cpu_pct: float = 0.0,
        ram_pct: float = 0.0,
    ) -> None:
        """Update live status display (AC-15).

        Never displays Active if worker is stopped.
        """
        if agent_pending_count > 0:
            self.lbl_agentguard.setText(f"AgentGuard: {agent_pending_count} Awaiting Approval")
            self.lbl_agentguard.setStyleSheet("color: #d29922; font-weight: 700; font-size: 11px;")
        else:
            self.lbl_agentguard.setText("AgentGuard: 0 Pending (Safe)")
            self.lbl_agentguard.setStyleSheet("color: #3fb950; font-size: 11px;")

        if crash_active:
            self.lbl_crashguard.setText(f"CrashGuard: CPU {cpu_pct:.0f}%, RAM {ram_pct:.0f}%")
            self.lbl_crashguard.setStyleSheet("color: #58a6ff; font-size: 11px;")
            self.lbl_overall.setText("PROTECTED")
            self.lbl_overall.setStyleSheet("color: #3fb950; font-size: 10px; font-weight: 700;")
        else:
            self.lbl_crashguard.setText("CrashGuard: Inactive / Stopped")
            self.lbl_crashguard.setStyleSheet("color: #f85149; font-size: 11px;")
            self.lbl_overall.setText("DEGRADED")
            self.lbl_overall.setStyleSheet("color: #d29922; font-size: 10px; font-weight: 700;")

    # Make the entire widget draggable across the screen
    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if event.buttons() == Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
