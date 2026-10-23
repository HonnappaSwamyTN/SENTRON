"""CrashGuard Threshold-Crossing Alert Popup (AC-10 / Hackathon MVP / Requirement 3).

Redesigned alert popup that immediately communicates:
1. What happened (e.g. sustained high CPU/memory use or elevated CPU temperature)
2. Current reading (measured value and unit)
3. Threshold (e.g. 93% resource risk or configured threshold)
4. Duration sustained
5. Main suspected contributors (e.g. Chrome with PID and measured usage)
6. Recommended next step

Actions:
- View Details (switches to CrashGuard panel)
- Review Processes (opens ProcessReviewDialog)
- Remind Me Later / Dismiss (snoozes alert)

Non-modal, top-level, non-focus-stealing dialog that displays even when
the main dashboard window is hidden.
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
    QVBoxLayout,
    QWidget,
)

from sentron.core.models import RecoveryRecommendation, RiskAlert
from sentron.ui.agent_alert_popup import AgentGuardAlert, AgentGuardAlertPopup

__all__ = ["CrashGuardAlertPopup", "AgentGuardAlertPopup", "AgentGuardAlert"]


class CrashGuardAlertPopup(QDialog):
    """On-screen threshold-crossing alert popup for SENTRON CrashGuard."""

    def __init__(
        self,
        parent: QWidget | None = None,
        on_view_details: Callable[[], None] | None = None,
        on_review_processes: Callable[[], None] | None = None,
        on_dismiss: Callable[[], None] | None = None,
        theme: str = "light",
    ) -> None:
        super().__init__(parent)
        self.on_view_details = on_view_details
        self.on_review_processes = on_review_processes
        self.on_dismiss = on_dismiss
        self.theme = (theme or "light").lower()

        # Key-value store of active alerts by metric_name to combine simultaneous breaches
        self._alerts: dict[str, tuple[RiskAlert, list[RecoveryRecommendation]]] = {}

        # Set up non-modal, top-level, non-focus-stealing window flags
        self.setWindowFlags(
            Qt.Tool
            | Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setMinimumWidth(480)
        self.setMaximumWidth(540)

        # Optional auto-dismiss timer (60s) so it doesn't linger indefinitely if unattended
        self._auto_dismiss_timer = QTimer(self)
        self._auto_dismiss_timer.setSingleShot(True)
        self._auto_dismiss_timer.timeout.connect(self._handle_dismiss)

        self._init_ui()

    def set_theme(self, theme_name: str) -> None:
        """Update active theme styling."""
        self.theme = (theme_name or "light").lower()
        self._apply_card_style(is_simulated=self.is_simulated())
        if self.isVisible():
            self.update()

    def _init_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Outer card container
        self.card = QFrame()
        self.card.setObjectName("alertCard")
        self._apply_card_style(is_simulated=False)

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(16, 14, 16, 14)
        card_layout.setSpacing(10)

        # --- Top Header Bar ---
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)

        # Shield/Warning Icon & Title (supports both exact phrases for test compatibility)
        self.lbl_title = QLabel("🛡️ SENTRON CrashGuard Alert — High System Resource Risk")
        self.lbl_title.setObjectName("alertTitle")
        self.lbl_title.setStyleSheet("font-size: 13px; font-weight: 800;")
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
            "background: transparent; border: none; font-size: 13px; font-weight: bold; padding: 2px 5px;"
        )
        btn_close_x.clicked.connect(self._handle_dismiss)
        header_layout.addWidget(btn_close_x)

        card_layout.addLayout(header_layout)

        # --- Structured Summary Block (Requirement 3 concise structure) ---
        self.structured_box = QFrame()
        self.structured_box.setStyleSheet(
            "background-color: rgba(0, 0, 0, 0.08); border-radius: 6px; padding: 8px;"
        )
        struct_layout = QVBoxLayout(self.structured_box)
        struct_layout.setContentsMargins(8, 8, 8, 8)
        struct_layout.setSpacing(4)

        self.lbl_risk_level = QLabel("• <b>Risk level:</b> Critical")
        self.lbl_risk_level.setStyleSheet("font-size: 12px;")
        struct_layout.addWidget(self.lbl_risk_level)

        self.lbl_reading = QLabel("• <b>Current reading:</b> 0.0%")
        self.lbl_reading.setStyleSheet("font-size: 12px;")
        struct_layout.addWidget(self.lbl_reading)

        self.lbl_threshold = QLabel("• <b>Threshold:</b> 93% sustained risk limit")
        self.lbl_threshold.setStyleSheet("font-size: 12px;")
        struct_layout.addWidget(self.lbl_threshold)

        self.lbl_duration = QLabel("• <b>Duration:</b> 0s sustained")
        self.lbl_duration.setStyleSheet("font-size: 12px;")
        struct_layout.addWidget(self.lbl_duration)

        self.lbl_contributor = QLabel("• <b>Main contributor:</b> None confirmed")
        self.lbl_contributor.setStyleSheet("font-size: 12px;")
        self.lbl_contributor.setWordWrap(True)
        struct_layout.addWidget(self.lbl_contributor)

        card_layout.addWidget(self.structured_box)

        # --- Brief Trigger Reason ---
        self.lbl_trigger_reason = QLabel("Sustained resource utilization has crossed configured risk thresholds.")
        self.lbl_trigger_reason.setStyleSheet("font-size: 11px;")
        self.lbl_trigger_reason.setWordWrap(True)
        card_layout.addWidget(self.lbl_trigger_reason)

        # --- Resources Summary Box (combined resources) ---
        self.resources_frame = QFrame()
        self.resources_frame.setStyleSheet(
            "background-color: rgba(0, 0, 0, 0.12); border-radius: 6px; padding: 6px;"
        )
        self.resources_layout = QVBoxLayout(self.resources_frame)
        self.resources_layout.setContentsMargins(6, 6, 6, 6)
        self.resources_layout.setSpacing(6)
        card_layout.addWidget(self.resources_frame)

        # --- Recommended Action Callout ---
        self.lbl_recovery_notice = QLabel(
            "<b>Recommended action:</b> Save active work immediately, then consider closing unused tabs or pausing a selected noncritical process."
        )
        self.lbl_recovery_notice.setStyleSheet(
            "color: #2ea043; font-size: 11px; font-weight: 600;"
        )
        self.lbl_recovery_notice.setWordWrap(True)
        card_layout.addWidget(self.lbl_recovery_notice)

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

        # --- Action Buttons ---
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(8)

        self.btn_view_details = QPushButton("View Details")
        self.btn_view_details.setObjectName("btnViewDetails")
        self.btn_view_details.setStyleSheet("font-weight: 700; font-size: 11px; padding: 6px 12px;")
        self.btn_view_details.clicked.connect(self._handle_view_details)
        actions_layout.addWidget(self.btn_view_details)

        self.btn_review_processes = QPushButton("Review Processes")
        self.btn_review_processes.setObjectName("btnReviewProcesses")
        self.btn_review_processes.setStyleSheet("font-weight: 700; font-size: 11px; padding: 6px 12px;")
        self.btn_review_processes.clicked.connect(self._handle_review_processes)
        actions_layout.addWidget(self.btn_review_processes)

        actions_layout.addStretch()

        self.btn_dismiss = QPushButton("Dismiss")
        self.btn_dismiss.setObjectName("btnDismiss")
        self.btn_dismiss.setStyleSheet("font-weight: 600; font-size: 11px; padding: 6px 12px;")
        self.btn_dismiss.clicked.connect(self._handle_dismiss)
        actions_layout.addWidget(self.btn_dismiss)

        card_layout.addLayout(actions_layout)

        root_layout.addWidget(self.card)

    def _apply_card_style(self, is_simulated: bool) -> None:
        border_color = "#f59e0b" if is_simulated else "#da3633"
        is_dark = self.theme == "dark"
        bg_color = "#161b22" if is_dark else "#FFFFFF"
        text_color = "#F5F2E9" if is_dark else "#171717"
        self.card.setStyleSheet(
            f"QFrame#alertCard {{"
            f"  background-color: {bg_color};"
            f"  color: {text_color};"
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
        """Return True if any active alert is marked as simulated."""
        return any(alert.is_simulated for alert, _ in self._alerts.values())

    def _refresh_content(self) -> None:
        if not self._alerts:
            return

        has_simulated = self.is_simulated()
        self._apply_card_style(is_simulated=has_simulated)
        self.lbl_sim_badge.setVisible(has_simulated)
        self.lbl_sim_disclaimer.setVisible(has_simulated)

        # Get latest alert
        latest_metric = max(self._alerts.keys(), key=lambda k: self._alerts[k][0].timestamp)
        primary_alert, primary_recs = self._alerts[latest_metric]

        latest_ts = primary_alert.timestamp
        time_str = datetime.datetime.fromtimestamp(latest_ts).strftime("%H:%M:%S")
        self.lbl_timestamp.setText(time_str)

        # Structured items
        unit = "%" if primary_alert.metric_name in ("CPU", "Memory") else ("°C" if primary_alert.metric_name == "CPUTemperature" else "GB")
        sev_color = "#f85149" if primary_alert.severity == "critical" else "#d29922"
        self.lbl_risk_level.setText(
            f"• <b>Risk level:</b> <span style='color: {sev_color}; font-weight: bold;'>{primary_alert.severity.upper()}</span>"
        )
        self.lbl_reading.setText(f"• <b>Current reading:</b> {primary_alert.observed_value:.1f}{unit}")
        self.lbl_threshold.setText(f"• <b>Threshold:</b> {primary_alert.threshold_value:.1f}{unit}")
        self.lbl_duration.setText(f"• <b>Duration:</b> {primary_alert.duration_seconds:.0f}s sustained")

        # Contributor info (Never claim confirmed unless supported by measured evidence)
        if primary_alert.contributor_details:
            self.lbl_contributor.setText(f"• <b>Main contributor:</b> {primary_alert.contributor_details}")
        elif primary_alert.contributor_process:
            self.lbl_contributor.setText(
                f"• <b>Main contributor:</b> '{primary_alert.contributor_process}' (PID {primary_alert.contributor_pid})"
            )
        else:
            self.lbl_contributor.setText("• <b>Main contributor:</b> Multiple concurrent processes (no single dominant contributor)")

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
            f"CrashGuard detected sustained pressure on {resource_names} exceeding risk limits for >{primary_alert.duration_seconds:.0f}s."
        )

        # Recommendation
        if primary_alert.metric_name == "CPUTemperature":
            self.lbl_recovery_notice.setText(
                "<b>Safe Recovery — Advisory:</b> Verify cooling airflow and vents. Consider pausing intensive background render/compile tasks."
            )
        elif primary_alert.contributor_process and "chrome" in primary_alert.contributor_process.lower():
            self.lbl_recovery_notice.setText(
                "<b>Safe Recovery — Recommended action:</b> Save your work, then consider closing unused Chrome tabs or pausing a selected noncritical process."
            )
        else:
            self.lbl_recovery_notice.setText(
                "<b>Safe Recovery — Recommended action:</b> Save active work. SENTRON will not terminate, suspend, or kill any running processes automatically."
            )

    def _create_resource_row(self, alert: RiskAlert) -> QWidget:
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(4, 3, 4, 3)
        row_layout.setSpacing(8)

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
        elif alert.metric_name == "CPUTemperature":
            icon_str = "🌡️"
            display_name = "CPU Temp"
            unit = "°C"
        else:
            icon_str = "📊"
            display_name = alert.metric_name
            unit = ""

        lbl_metric = QLabel(f"{icon_str} {display_name}")
        lbl_metric.setStyleSheet("font-weight: 700; font-size: 11px;")

        measured_str = f"{alert.observed_value:.1f}{unit}"
        threshold_str = f"{alert.threshold_value:.1f}{unit}"

        lbl_values = QLabel(f"Measured: <b>{measured_str}</b> | Threshold: {threshold_str}")
        lbl_values.setStyleSheet("font-size: 11px;")

        sev_color = "#f85149" if alert.severity == "critical" else "#d29922"
        lbl_sev = QLabel(alert.severity.upper())
        lbl_sev.setStyleSheet(
            f"color: {sev_color}; font-size: 9px; font-weight: 800; border: 1px solid {sev_color}; "
            f"border-radius: 3px; padding: 1px 4px;"
        )

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
        self._auto_dismiss_timer.start(60000)

    def reposition(self) -> None:
        """Position at bottom-right corner of screen or parent."""
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
        self._auto_dismiss_timer.stop()
        self.close()
        if self.on_view_details:
            try:
                self.on_view_details()
            except Exception:
                pass

    def _handle_review_processes(self) -> None:
        self._auto_dismiss_timer.stop()
        self.close()
        if self.on_review_processes:
            try:
                self.on_review_processes()
            except Exception:
                pass

    def _handle_dismiss(self) -> None:
        self._auto_dismiss_timer.stop()
        self.close()
        if self.on_dismiss:
            try:
                self.on_dismiss()
            except Exception:
                pass
