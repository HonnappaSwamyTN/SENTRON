"""Floating Shield Launcher and Compact Status Panel for SENTRON.

Replaces the floating hub with an unobtrusive, always-on-top golden shield icon.
First click expands a compact CrashGuard status panel showing live host telemetry,
active sustained-risk alerts, Windows crash/hang diagnostics, and last-update time.
Unambiguous click handling ensures stability and clear user control.
"""
from __future__ import annotations

import datetime
import weakref
from PySide6.QtCore import Qt, QPoint, QPointF, QRectF
from PySide6.QtGui import (
    QMouseEvent,
    QPainter,
    QPainterPath,
    QColor,
    QPen,
    QBrush,
    QFont,
    QCursor,
)
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QStackedLayout,
    QSizePolicy,
)


class CircularShieldView(QWidget):
    """Circular launcher icon view with precise centering and hover close control."""

    def __init__(self, hub: FloatingHubWidget) -> None:
        super().__init__()
        self._hub_ref = weakref.ref(hub)
        self._is_hovered = False
        self.setObjectName("shieldView")
        self.setAttribute(Qt.WA_Hover, True)
        self.setMouseTracking(True)

        # Small 'x' close control overlay near upper-right edge
        self.btn_exit = QPushButton("✕", self)
        self.btn_exit.setObjectName("btnShieldExit")
        self.btn_exit.setToolTip("Exit SENTRON")
        self.btn_exit.setFixedSize(16, 16)
        self.btn_exit.setStyleSheet("""
            QPushButton#btnShieldExit {
                background-color: #212121;
                color: #D9D4C8;
                border: 1px solid #E2B83B;
                border-radius: 8px;
                font-size: 10px;
                font-weight: 800;
                padding: 0px;
            }
            QPushButton#btnShieldExit:hover {
                background-color: #C42B1C;
                color: #FFFFFF;
                border: 1px solid #FF6B6B;
            }
        """)
        self.btn_exit.hide()
        self.btn_exit.clicked.connect(self._on_exit_clicked)
        self._update_exit_button_pos()

        # Backward compatibility dummy label
        self.lbl_shield_icon = QLabel(self)
        self.lbl_shield_icon.hide()

    def _update_exit_button_pos(self) -> None:
        w = self.width()
        btn_x = max(0, w - 18)
        self.btn_exit.move(btn_x, 2)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._update_exit_button_pos()

    def enterEvent(self, event) -> None:
        self._is_hovered = True
        self.btn_exit.show()
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        cur_pos = self.mapFromGlobal(QCursor.pos())
        if not self.rect().contains(cur_pos):
            self._is_hovered = False
            self.btn_exit.hide()
            self.update()
        super().leaveEvent(event)

    @property
    def hub(self) -> FloatingHubWidget | None:
        return self._hub_ref() if self._hub_ref else None

    def _on_exit_clicked(self) -> None:
        hub = self.hub
        if hub is not None:
            hub.hide()
            if hub.on_exit_app:
                hub.on_exit_app()
                return
        app = QApplication.instance()
        if app:
            app.quit()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        d = min(w, h)
        cx = w / 2.0
        cy = h / 2.0
        r = (d - 3.0) / 2.0

        # Circular background & border (strictly anti-aliased true circle)
        if self._is_hovered:
            pen = QPen(QColor("#F0C952"), 2.0)
            brush = QBrush(QColor("#212121"))
        else:
            pen = QPen(QColor("#E2B83B"), 1.5)
            brush = QBrush(QColor("#171717"))

        painter.setPen(pen)
        painter.setBrush(brush)
        painter.drawEllipse(QPointF(cx, cy), r, r)

        # Golden-yellow shield icon precisely centered
        sw = d * 0.44
        sh = d * 0.52
        top = cy - sh / 2.0
        bottom = cy + sh / 2.0
        left = cx - sw / 2.0
        right = cx + sw / 2.0

        path = QPainterPath()
        path.moveTo(cx, top)
        path.lineTo(right, top + sh * 0.08)
        path.lineTo(right, cy)
        path.cubicTo(right, cy + sh * 0.25, cx + sw * 0.2, bottom - sh * 0.08, cx, bottom)
        path.cubicTo(cx - sw * 0.2, bottom - sh * 0.08, left, cy + sh * 0.25, left, cy)
        path.lineTo(left, top + sh * 0.08)
        path.closeSubpath()

        shield_color = QColor("#F0C952") if self._is_hovered else QColor("#E2B83B")
        painter.setPen(QPen(shield_color, 1.2))
        painter.setBrush(QBrush(shield_color))
        painter.drawPath(path)

        # Subtle dark inner shield core for crisp security depth
        in_w = sw * 0.60
        in_h = sh * 0.60
        in_top = cy - in_h / 2.0 + 1.0
        in_bottom = cy + in_h / 2.0
        in_left = cx - in_w / 2.0
        in_right = cx + in_w / 2.0

        inner_path = QPainterPath()
        inner_path.moveTo(cx, in_top)
        inner_path.lineTo(in_right, in_top + in_h * 0.08)
        inner_path.lineTo(in_right, cy)
        inner_path.cubicTo(in_right, cy + in_h * 0.22, cx + in_w * 0.2, in_bottom - in_h * 0.08, cx, in_bottom)
        inner_path.cubicTo(cx - in_w * 0.2, in_bottom - in_h * 0.08, in_left, cy + in_h * 0.22, in_left, cy)
        inner_path.lineTo(in_left, in_top + in_h * 0.08)
        inner_path.closeSubpath()

        core_color = QColor("#212121") if self._is_hovered else QColor("#171717")
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(core_color))
        painter.drawPath(inner_path)


class FloatingHubWidget(QWidget):
    """Movable floating circular shield launcher with expandable compact status panel."""

    def __init__(
        self,
        on_toggle_dashboard: callable | None = None,
        on_exit_app: callable | None = None,
        shield_size: int = 48,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.on_toggle_dashboard = on_toggle_dashboard
        self.on_exit_app = on_exit_app
        self._shield_size = shield_size
        self._drag_pos = QPoint()
        self._press_pos = QPoint()
        self._is_dragging = False
        self._expanded = False

        self._latest_alert_text = "No active sustained risks."
        self._latest_evidence_text = "Windows Event Log: No recent crashes/hangs."
        self._last_cpu = 0.0
        self._last_ram = 0.0
        self._last_disk_gb: float | None = None
        self._is_active = True

        # Always-on-top, frameless utility window with translucent background
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        self._init_ui()
        self.collapse()

    def _init_ui(self) -> None:
        self.setObjectName("floatingHub")
        self.setStyleSheet("""
            QWidget#floatingHub {
                background: transparent;
                border: none;
            }
        """)

        # Root layout with stacked views: Collapsed Circular Shield vs Expanded Panel
        self.root_stack = QStackedLayout(self)
        self.root_stack.setContentsMargins(0, 0, 0, 0)

        # -------------------------------------------------------------
        # View 0: Collapsed Circular Shield Launcher (Default 48x48)
        # -------------------------------------------------------------
        self.shield_view = CircularShieldView(self)
        self.root_stack.addWidget(self.shield_view)

        # -------------------------------------------------------------
        # View 1: Expanded Compact CrashGuard Status Panel
        # -------------------------------------------------------------
        self.panel_view = QWidget()
        self.panel_view.setObjectName("panelView")
        self.panel_view.setStyleSheet("""
            QWidget#panelView {
                background-color: #171717;
                border: 1px solid #E2B83B;
                border-radius: 8px;
            }
        """)
        panel_layout = QVBoxLayout(self.panel_view)
        panel_layout.setContentsMargins(12, 10, 12, 10)
        panel_layout.setSpacing(8)

        # Header Row: Title, Overall Status, and Collapse Button
        header_row = QHBoxLayout()
        header_row.setSpacing(6)

        lbl_title = QLabel("🛡️ SENTRON SHIELD")
        lbl_title.setStyleSheet("font-weight: 800; color: #E2B83B; font-size: 12px; letter-spacing: 0.5px;")

        self.lbl_overall = QLabel("LOCAL ACTIVE")
        self.lbl_overall.setStyleSheet("color: #255931; background-color: #25593122; border: 1px solid #255931; border-radius: 4px; padding: 1px 6px; font-size: 9px; font-weight: 700;")

        header_row.addWidget(lbl_title)
        header_row.addWidget(self.lbl_overall)
        header_row.addStretch()

        self.btn_collapse = QPushButton("✕")
        self.btn_collapse.setToolTip("Collapse to Shield")
        self.btn_collapse.setFixedSize(22, 22)
        self.btn_collapse.setStyleSheet("""
            QPushButton {
                background-color: #212121;
                color: #D9D4C8;
                border: 1px solid #333333;
                border-radius: 11px;
                font-size: 11px;
                font-weight: 700;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: #333333;
                color: #E2B83B;
                border-color: #E2B83B;
            }
        """)
        self.btn_collapse.clicked.connect(self.collapse)
        header_row.addWidget(self.btn_collapse)
        panel_layout.addLayout(header_row)

        # Thin divider
        div = QFrame()
        div.setFrameShape(QFrame.HLine)
        div.setStyleSheet("color: #2B2B2B;")
        panel_layout.addWidget(div)

        # Module statuses (Preserved for backward-compatibility with tests)
        status_box = QVBoxLayout()
        status_box.setSpacing(3)

        self.lbl_crashguard = QLabel("CrashGuard: Active")
        self.lbl_crashguard.setStyleSheet("color: #F5F2E9; font-size: 11px; font-weight: 600;")
        status_box.addWidget(self.lbl_crashguard)

        self.lbl_agentguard = QLabel("AgentGuard: 0 Pending (Safe)")
        self.lbl_agentguard.setStyleSheet("color: #D9D4C8; font-size: 11px;")
        status_box.addWidget(self.lbl_agentguard)

        self.lbl_metrics_detail = QLabel("CPU: 0.0%  •  RAM: 0.0%  •  Disk: -- GB free")
        self.lbl_metrics_detail.setStyleSheet("color: #D9D4C8; font-size: 10px; font-family: Consolas, monospace;")
        status_box.addWidget(self.lbl_metrics_detail)
        panel_layout.addLayout(status_box)

        # Diagnostic Alerts & Evidence Container
        diag_box = QFrame()
        diag_box.setStyleSheet("background-color: #212121; border-radius: 6px; padding: 6px;")
        diag_layout = QVBoxLayout(diag_box)
        diag_layout.setContentsMargins(6, 6, 6, 6)
        diag_layout.setSpacing(4)

        self.lbl_latest_alert = QLabel("Alert: No active sustained risks.")
        self.lbl_latest_alert.setStyleSheet("color: #D9D4C8; font-size: 10px;")
        self.lbl_latest_alert.setWordWrap(True)
        diag_layout.addWidget(self.lbl_latest_alert)

        self.lbl_latest_evidence = QLabel("Windows Evidence: No recent crashes/hangs.")
        self.lbl_latest_evidence.setStyleSheet("color: #8C8578; font-size: 10px;")
        self.lbl_latest_evidence.setWordWrap(True)
        diag_layout.addWidget(self.lbl_latest_evidence)

        panel_layout.addWidget(diag_box)

        # Timestamp & Open Full Dashboard action
        action_row = QHBoxLayout()
        action_row.setSpacing(8)

        self.lbl_timestamp = QLabel("Updated: --:--:--")
        self.lbl_timestamp.setStyleSheet("color: #8C8578; font-size: 10px;")
        action_row.addWidget(self.lbl_timestamp)
        action_row.addStretch()

        self.btn_toggle = QPushButton("Open Dashboard")
        self.btn_toggle.setStyleSheet("""
            QPushButton {
                background-color: #E2B83B;
                color: #171717;
                border: 1px solid #C49B24;
                border-radius: 5px;
                padding: 5px 12px;
                font-weight: 700;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #F0C952;
            }
        """)
        if self.on_toggle_dashboard:
            self.btn_toggle.clicked.connect(self.on_toggle_dashboard)
        action_row.addWidget(self.btn_toggle)
        panel_layout.addLayout(action_row)

        self.root_stack.addWidget(self.panel_view)

    def is_expanded(self) -> bool:
        """Return True if compact status panel is currently expanded."""
        return self._expanded

    def expand(self) -> None:
        """Expand from compact shield icon to the full status panel."""
        self._expanded = True
        self.root_stack.setCurrentIndex(1)
        self.setFixedSize(360, 240)
        self.update()

    def collapse(self) -> None:
        """Collapse into the single compact circular shield launcher."""
        self._expanded = False
        self.root_stack.setCurrentIndex(0)
        self.setFixedSize(self._shield_size, self._shield_size)
        self.update()

    def set_shield_size(self, size: int) -> None:
        """Set the circular shield diameter, maintaining equal width and height."""
        self._shield_size = max(24, size)
        if not self._expanded:
            self.setFixedSize(self._shield_size, self._shield_size)
            self.update()

    def toggle_expanded(self) -> None:
        """Toggle between collapsed shield and expanded status panel."""
        if self._expanded:
            self.collapse()
        else:
            self.expand()

    def update_status(
        self,
        agent_pending_count: int = 0,
        crash_active: bool = True,
        cpu_pct: float = 0.0,
        ram_pct: float = 0.0,
        disk_free_gb: float | None = None,
        latest_alert: str | None = None,
        latest_evidence: str | None = None,
    ) -> None:
        """Update live status display across both collapsed and expanded states.

        Never displays PROTECTED or Active if background worker is stopped or degraded.
        """
        self._is_active = crash_active
        self._last_cpu = cpu_pct
        self._last_ram = ram_pct
        if disk_free_gb is not None:
            self._last_disk_gb = disk_free_gb

        # AgentGuard Status
        if agent_pending_count > 0:
            self.lbl_agentguard.setText(f"AgentGuard: {agent_pending_count} Awaiting Approval")
            self.lbl_agentguard.setStyleSheet("color: #E2B83B; font-weight: 700; font-size: 11px;")
        else:
            self.lbl_agentguard.setText("AgentGuard: 0 Pending (Safe)")
            self.lbl_agentguard.setStyleSheet("color: #D9D4C8; font-size: 11px;")

        # CrashGuard Status & Honesty
        disk_str = f"{self._last_disk_gb:.1f} GB free" if self._last_disk_gb is not None else "-- GB free"
        self.lbl_metrics_detail.setText(f"CPU: {cpu_pct:.1f}%  •  RAM: {ram_pct:.1f}%  •  Disk: {disk_str}")

        if crash_active:
            self.lbl_crashguard.setText(f"CrashGuard: CPU {cpu_pct:.0f}%, RAM {ram_pct:.0f}%")
            self.lbl_crashguard.setStyleSheet("color: #F5F2E9; font-weight: 600; font-size: 11px;")
            self.lbl_overall.setText("PROTECTED")
            self.lbl_overall.setStyleSheet(
                "color: #255931; background-color: #25593122; border: 1px solid #255931; border-radius: 4px; padding: 1px 6px; font-size: 9px; font-weight: 700;"
            )
        else:
            self.lbl_crashguard.setText("CrashGuard: Inactive / Stopped")
            self.lbl_crashguard.setStyleSheet("color: #8C2424; font-size: 11px;")
            self.lbl_overall.setText("DEGRADED")
            self.lbl_overall.setStyleSheet(
                "color: #8C2424; background-color: #8C242422; border: 1px solid #8C2424; border-radius: 4px; padding: 1px 6px; font-size: 9px; font-weight: 700;"
            )

        # Alerts and evidence snippets
        if latest_alert is not None:
            self._latest_alert_text = latest_alert
        self.lbl_latest_alert.setText(f"Alert: {self._latest_alert_text}")

        if latest_evidence is not None:
            self._latest_evidence_text = latest_evidence
        self.lbl_latest_evidence.setText(f"Windows Evidence: {self._latest_evidence_text}")

        now_str = datetime.datetime.now().strftime("%H:%M:%S")
        self.lbl_timestamp.setText(f"Updated: {now_str}")

    def set_alert(self, alert_text: str) -> None:
        """Update active sustained-risk alert snippet."""
        self._latest_alert_text = alert_text
        self.lbl_latest_alert.setText(f"Alert: {alert_text}")
        if "No active" not in alert_text:
            self.lbl_latest_alert.setStyleSheet("color: #E2B83B; font-size: 10px; font-weight: 600;")
        else:
            self.lbl_latest_alert.setStyleSheet("color: #D9D4C8; font-size: 10px;")

    def set_evidence(self, evidence_summary: str) -> None:
        """Update latest Windows crash/hang evidence diagnostic snippet."""
        self._latest_evidence_text = evidence_summary
        self.lbl_latest_evidence.setText(f"Windows Evidence: {evidence_summary}")

    # -------------------------------------------------------------
    # Mouse Drag and Unambiguous Click Handling
    # -------------------------------------------------------------
    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            if not self._expanded and self.shield_view.btn_exit.isVisible():
                btn_rect = self.shield_view.btn_exit.geometry()
                if btn_rect.contains(event.position().toPoint()):
                    event.accept()
                    return
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self._press_pos = event.globalPosition().toPoint()
            self._is_dragging = False
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if event.buttons() == Qt.LeftButton:
            move_delta = (event.globalPosition().toPoint() - self._press_pos).manhattanLength()
            if move_delta > 5:
                self._is_dragging = True
                self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            if not self._expanded and self.shield_view.btn_exit.isVisible():
                btn_rect = self.shield_view.btn_exit.geometry()
                if btn_rect.contains(event.position().toPoint()):
                    event.accept()
                    return
            # If user clicked collapsed shield without dragging, expand panel
            if not self._is_dragging and not self._expanded:
                self.expand()
            event.accept()

    @property
    def btn_exit(self) -> QPushButton:
        return self.shield_view.btn_exit

    @property
    def btn_close(self) -> QPushButton:
        return self.shield_view.btn_exit

    @property
    def lbl_shield_icon(self) -> QLabel:
        return self.shield_view.lbl_shield_icon

    def closeEvent(self, event) -> None:
        self.on_toggle_dashboard = None
        self.on_exit_app = None
        super().closeEvent(event)
