"""CrashGuard Threshold-Crossing Alert Popup (AC-10 / Hackathon MVP).

A non-blocking, non-modal, polished PySide6 popup notification dialog that:
- Prominently displays "SENTRON CrashGuard Alert"
- Clearly identifies affected resources (CPU, RAM, Disk) with measured values & thresholds with units
- Combines multiple simultaneous threshold breaches into one alert dialog
- Explains why the alert triggered and provides safe, non-destructive recovery guidance
- Clearly badges synthetic demonstration alerts as [SIMULATED DEMO ALERT]
- Provides "View Details" to switch to the CrashGuard panel and "Dismiss" to close without stopping monitoring
- Does not steal keyboard focus (WA_ShowWithoutActivating)
"""
from __future__ import annotations

import datetime
from typing import Callable
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from sentron.core.models import RecoveryRecommendation, RiskAlert


class CrashGuardAlertPopup(QDialog):
    """On-screen threshold-crossing alert popup for SENTRON CrashGuard."""

    def __init__(
        self,
        parent: QWidget | None = None,
        on_view_details: Callable[[], None] | None = None,
        on_dismiss: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self.on_view_details = on_view_details
        self.on_dismiss = on_dismiss

        # Key-value store of active alerts by metric_name to combine simultaneous breaches
        self._alerts: dict[str, tuple[RiskAlert, list[RecoveryRecommendation]]] = {}

        # Set up non-modal, top-level, non-focus-stealing window flags
        self.setWindowFlags(
            Qt.Tool
            | Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setMinimumWidth(440)
        self.setMaximumWidth(520)

        # Optional auto-dismiss timer (60s) so it doesn't linger indefinitely if unattended
        self._auto_dismiss_timer = QTimer(self)
        self._auto_dismiss_timer.setSingleShot(True)
        self._auto_dismiss_timer.timeout.connect(self._handle_dismiss)

        self._init_ui()

    def _init_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Outer card container
        self.card = QFrame()
        self.card.setObjectName("alertCard")
        self._apply_card_style(is_simulated=False)

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(14, 12, 14, 12)
        card_layout.setSpacing(10)

        # --- Top Header Bar ---
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)

        # Shield/Warning Icon & Title
        self.lbl_title = QLabel("🛡️ SENTRON CrashGuard Alert")
        self.lbl_title.setObjectName("alertTitle")
        self.lbl_title.setStyleSheet("font-size: 14px; font-weight: 800; color: #f0f6fc;")
        header_layout.addWidget(self.lbl_title)

        # Simulated Demo Badge (shown only for simulated alerts)
        self.lbl_sim_badge = QLabel("SIMULATED DEMO ALERT")
        self.lbl_sim_badge.setObjectName("simulatedBadge")
        self.lbl_sim_badge.setStyleSheet(
            "background-color: #451a03; color: #fbbf24; border: 1px solid #d97706; "
            "font-size: 10px; font-weight: 800; border-radius: 4px; padding: 2px 7px;"
        )
        self.lbl_sim_badge.setVisible(False)
        header_layout.addWidget(self.lbl_sim_badge)

        header_layout.addStretch()

        # Timestamp
        self.lbl_timestamp = QLabel("--:--:--")
        self.lbl_timestamp.setStyleSheet("color: #8b949e; font-size: 11px;")
        header_layout.addWidget(self.lbl_timestamp)

        # Top-right quick close button
        btn_close_x = QPushButton("✕")
        btn_close_x.setToolTip("Dismiss alert")
        btn_close_x.setStyleSheet(
            "background: transparent; color: #8b949e; border: none; font-size: 13px; font-weight: bold; padding: 2px 5px;"
        )
        btn_close_x.clicked.connect(self._handle_dismiss)
        header_layout.addWidget(btn_close_x)

        card_layout.addLayout(header_layout)

        # --- Brief Trigger Reason ---
        self.lbl_trigger_reason = QLabel("Sustained resource utilization has crossed configured risk thresholds.")
        self.lbl_trigger_reason.setStyleSheet("color: #c9d1d9; font-size: 11px; margin-top: 1px;")
        self.lbl_trigger_reason.setWordWrap(True)
        card_layout.addWidget(self.lbl_trigger_reason)

        # --- Resources Summary Box (combined resources) ---
        self.resources_frame = QFrame()
        self.resources_frame.setStyleSheet(
            "background-color: #0d1117; border: 1px solid #30363d; border-radius: 6px; padding: 6px;"
        )
        self.resources_layout = QVBoxLayout(self.resources_frame)
        self.resources_layout.setContentsMargins(6, 6, 6, 6)
        self.resources_layout.setSpacing(6)
        card_layout.addWidget(self.resources_frame)

        # --- Simulated Disclaimer (visible only during synthetic simulation) ---
        self.lbl_sim_disclaimer = QLabel(
            "⚠️ DEMO MODE: This alert is a synthetic demonstration and does not reflect actual hardware failure. Real system telemetry is unaffected."
        )
        self.lbl_sim_disclaimer.setStyleSheet(
            "color: #d29922; font-size: 11px; font-style: italic; background-color: #1c1503; border-left: 3px solid #d29922; padding: 4px 6px;"
        )
        self.lbl_sim_disclaimer.setWordWrap(True)
        self.lbl_sim_disclaimer.setVisible(False)
        card_layout.addWidget(self.lbl_sim_disclaimer)

        # --- Safe Recovery Guidance Notice ---
        self.lbl_recovery_notice = QLabel(
            "Safe Recovery: Save active work. SENTRON will not terminate, suspend, or kill any running processes."
        )
        self.lbl_recovery_notice.setStyleSheet(
            "color: #3fb950; font-size: 11px; font-weight: 600;"
        )
        self.lbl_recovery_notice.setWordWrap(True)
        card_layout.addWidget(self.lbl_recovery_notice)

        # --- Action Buttons ---
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(10)

        self.btn_view_details = QPushButton("View Details")
        self.btn_view_details.setObjectName("btnViewDetails")
        self.btn_view_details.setStyleSheet(
            "QPushButton#btnViewDetails {"
            "  background-color: #1f6feb; color: #ffffff; font-weight: 700; font-size: 11px;"
            "  border: 1px solid #388bfd; border-radius: 6px; padding: 6px 14px;"
            "}"
            "QPushButton#btnViewDetails:hover { background-color: #388bfd; }"
        )
        self.btn_view_details.clicked.connect(self._handle_view_details)

        self.btn_dismiss = QPushButton("Dismiss")
        self.btn_dismiss.setObjectName("btnDismiss")
        self.btn_dismiss.setStyleSheet(
            "QPushButton#btnDismiss {"
            "  background-color: #21262d; color: #c9d1d9; font-weight: 600; font-size: 11px;"
            "  border: 1px solid #30363d; border-radius: 6px; padding: 6px 14px;"
            "}"
            "QPushButton#btnDismiss:hover { background-color: #30363d; color: #f0f6fc; }"
        )
        self.btn_dismiss.clicked.connect(self._handle_dismiss)

        actions_layout.addStretch()
        actions_layout.addWidget(self.btn_view_details)
        actions_layout.addWidget(self.btn_dismiss)
        card_layout.addLayout(actions_layout)

        root_layout.addWidget(self.card)

    def _apply_card_style(self, is_simulated: bool) -> None:
        border_color = "#f59e0b" if is_simulated else "#da3633"
        self.card.setStyleSheet(
            f"QFrame#alertCard {{"
            f"  background-color: #161b22;"
            f"  border: 2px solid {border_color};"
            f"  border-radius: 10px;"
            f"}}"
        )

    def add_alert(self, alert: RiskAlert, recommendations: list[RecoveryRecommendation] | None = None) -> None:
        """Add or update an alert for a specific resource metric."""
        self._alerts[alert.metric_name] = (alert, recommendations or [])
        self._refresh_content()

    def clear_alerts(self) -> None:
        """Clear all registered alerts."""
        self._alerts.clear()
        self._refresh_content()

    def is_simulated(self) -> bool:
        """Return True if any of the active alerts are marked as simulated."""
        return any(alert.is_simulated for alert, _ in self._alerts.values())

    def _refresh_content(self) -> None:
        if not self._alerts:
            return

        has_simulated = self.is_simulated()
        self._apply_card_style(is_simulated=has_simulated)
        self.lbl_sim_badge.setVisible(has_simulated)
        self.lbl_sim_disclaimer.setVisible(has_simulated)

        # Format latest timestamp from alerts
        latest_ts = max(alert.timestamp for alert, _ in self._alerts.values())
        time_str = datetime.datetime.fromtimestamp(latest_ts).strftime("%H:%M:%S")
        self.lbl_timestamp.setText(time_str)

        # Clear existing resource item rows
        while self.resources_layout.count() > 0:
            child = self.resources_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Build row for each affected resource
        for metric_name, (alert, _) in self._alerts.items():
            row = self._create_resource_row(alert)
            self.resources_layout.addWidget(row)

        resource_names = ", ".join(self._alerts.keys())
        self.lbl_trigger_reason.setText(
            f"CrashGuard detected sustained pressure on {resource_names} exceeding safety thresholds for >10s."
        )

    def _create_resource_row(self, alert: RiskAlert) -> QWidget:
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(4, 3, 4, 3)
        row_layout.setSpacing(8)

        # Metric icon and label
        if alert.metric_name == "CPU":
            icon_str = "⚡"
            display_name = "CPU"
            unit = "%"
        elif alert.metric_name == "Memory":
            icon_str = "🧠"
            display_name = "RAM"
            unit = "%"
        elif alert.metric_name == "DiskFreeGB":
            icon_str = "💾"
            display_name = "Disk Free"
            unit = "GB"
        else:
            icon_str = "📊"
            display_name = alert.metric_name
            unit = ""

        lbl_metric = QLabel(f"{icon_str} {display_name}")
        lbl_metric.setStyleSheet("font-weight: 700; color: #f0f6fc; font-size: 11px;")

        # Values with units
        measured_str = f"{alert.observed_value:.1f}{unit}"
        threshold_str = f"{alert.threshold_value:.1f}{unit}"

        lbl_values = QLabel(f"Measured: <b>{measured_str}</b> | Threshold: {threshold_str}")
        lbl_values.setStyleSheet("color: #e6edf3; font-size: 11px;")

        # Severity badge
        sev_color = "#f85149" if alert.severity == "critical" else "#d29922"
        lbl_sev = QLabel(alert.severity.upper())
        lbl_sev.setStyleSheet(
            f"color: {sev_color}; font-size: 9px; font-weight: 800; border: 1px solid {sev_color}; "
            f"border-radius: 3px; padding: 1px 4px;"
        )

        # Duration
        lbl_duration = QLabel(f"({alert.duration_seconds:.0f}s sustained)")
        lbl_duration.setStyleSheet("color: #8b949e; font-size: 10px;")

        row_layout.addWidget(lbl_metric)
        row_layout.addWidget(lbl_values)
        row_layout.addWidget(lbl_duration)
        row_layout.addStretch()
        row_layout.addWidget(lbl_sev)

        return row_widget

    def display_alert(self) -> None:
        """Position popup and display it without stealing keyboard focus."""
        self._refresh_content()
        self.reposition()
        self.show()
        self.raise_()
        # Reset and start the 60s auto-dismiss timer
        self._auto_dismiss_timer.start(60000)

    def reposition(self) -> None:
        """Position at the bottom-right corner of the parent or primary screen."""
        self.adjustSize()
        parent_widget = self.parentWidget()

        margin = 24
        if parent_widget and parent_widget.isVisible() and not parent_widget.isMinimized():
            parent_geo = parent_widget.geometry()
            x = parent_geo.x() + parent_geo.width() - self.width() - margin
            y = parent_geo.y() + parent_geo.height() - self.height() - margin
        else:
            screen = QApplication.primaryScreen()
            if screen:
                screen_geo = screen.availableGeometry()
                x = screen_geo.x() + screen_geo.width() - self.width() - margin
                y = screen_geo.y() + screen_geo.height() - self.height() - margin
            else:
                x = 100
                y = 100

        self.move(max(0, x), max(0, y))

    def _handle_view_details(self) -> None:
        """Trigger callback to switch to CrashGuard panel, then close popup."""
        self._auto_dismiss_timer.stop()
        self.close()
        if self.on_view_details:
            try:
                self.on_view_details()
            except Exception:
                pass

    def _handle_dismiss(self) -> None:
        """Dismiss the popup without disabling or stopping monitoring."""
        self._auto_dismiss_timer.stop()
        self.close()
        if self.on_dismiss:
            try:
                self.on_dismiss()
            except Exception:
                pass
