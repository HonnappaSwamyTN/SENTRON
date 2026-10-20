"""Main Desktop Dashboard Window for SENTRON.

Three-Section Vertically Scrollable Security Console:
Section 1: CrashGuard (System Health, Rolling Telemetry, Evidence, Recovery)
Section 2: AgentGuard (Deterministic Gatekeeping, Input Risk, Secrets Redaction, Audit)
Section 3: Demo (Guided, Reproducible Hackathon Scenarios & Reset Controls)

Includes persistent top navigation with active-section tracking and smooth scrolling.
"""
from __future__ import annotations

import json
from uuid import uuid4
from PySide6.QtCore import Qt, QTimer, Signal, Slot
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QFrame,
    QGroupBox,
    QSizePolicy,
)

from sentron.agentguard.approval import ApprovalManager
from sentron.agentguard.audit import SqliteAuditLog
from sentron.agentguard.executor import ControlledExecutor
from sentron.agentguard.policy import PolicyEngine
from sentron.core.models import RiskAlert, SystemSnapshot, UnifiedEvent
from sentron.core.storage import EventStore
from sentron.crashguard.evidence import persist_windows_evidence
from sentron.crashguard.worker import MonitoringWorker
from sentron.ui.agentguard_panel import AgentGuardPanel
from sentron.ui.alert_popup import CrashGuardAlertPopup
from sentron.ui.crashguard_panel import CrashGuardPanel
from sentron.ui.demo_panel import DemoPanel
from sentron.ui.hub_widget import FloatingHubWidget
from sentron.ui.styles import WARM_CONSOLE_QSS, DARK_THEME_QSS
from sentron.ui.timeline_panel import UnifiedTimelinePanel


class NavigationTabsProxy:
    """Proxy providing backward-compatible tab-index interface to the scrollable dashboard."""

    def __init__(self, main_window: SentronMainWindow) -> None:
        self._window = main_window

    def setCurrentIndex(self, index: int) -> None:
        self._window.scroll_to_section(index)

    def currentIndex(self) -> int:
        return self._window.get_active_section_index()

    def count(self) -> int:
        return 3


class SentronMainWindow(QMainWindow):
    """Main application window uniting CrashGuard, AgentGuard, and Hackathon Demo Console."""

    snapshot_received = Signal(object)
    alert_received = Signal(object, list)
    evidence_received = Signal(list, list)

    def __init__(
        self,
        executor: ControlledExecutor,
        policy_engine: PolicyEngine,
        approval_manager: ApprovalManager,
        audit_log: SqliteAuditLog,
        event_store: EventStore,
        worker: MonitoringWorker,
    ) -> None:
        super().__init__()
        self.executor = executor
        self.policy = policy_engine
        self.approvals = approval_manager
        self.audit_log = audit_log
        self.event_store = event_store
        self.worker = worker
        self._alert_popup: CrashGuardAlertPopup | None = None
        self._active_nav_index = 0

        self.setWindowTitle("SENTRON — Local Security Guard for AI Actions & System Stability")
        # Sensible minimum and default dimensions that comfortably fit 1366x768 laptops
        self.setMinimumSize(880, 540)
        self.resize(1160, 720)
        self.setStyleSheet(WARM_CONSOLE_QSS)

        # Create Floating Shield Launcher and position non-intrusively in the upper right
        self.floating_hub = FloatingHubWidget(on_toggle_dashboard=self.toggle_dashboard_visibility)
        screen = QApplication.primaryScreen()
        if screen:
            screen_geo = screen.availableGeometry()
            self.floating_hub.move(screen_geo.x() + screen_geo.width() - 80, screen_geo.y() + 40)
        else:
            self.floating_hub.move(80, 80)
        self.floating_hub.show()

        self._init_ui()
        self.tabs = NavigationTabsProxy(self)
        self._wire_signals()

    def _init_ui(self) -> None:
        central = QWidget(self)
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(12, 10, 12, 10)
        root_layout.setSpacing(8)

        # -------------------------------------------------------------
        # Sticky Top Bar: Brand, Badges & Hub Toggle
        # -------------------------------------------------------------
        header_bar = QHBoxLayout()
        header_bar.setSpacing(10)

        title_vbox = QVBoxLayout()
        title_vbox.setSpacing(1)
        brand_label = QLabel("🛡️ SENTRON")
        brand_label.setObjectName("brandTitle")
        tagline_label = QLabel("Local Security Guard for AI Actions and System Stability")
        tagline_label.setObjectName("brandTagline")
        title_vbox.addWidget(brand_label)
        title_vbox.addWidget(tagline_label)
        header_bar.addLayout(title_vbox)

        header_bar.addStretch()

        # Badges & Launcher Toggle
        badge_offline = QLabel("OFFLINE ONLY")
        badge_offline.setObjectName("badgeSafe")

        badge_api = QLabel("0 EXTERNAL APIS • ZERO KEYS")
        badge_api.setObjectName("badgeActive")

        self.btn_toggle_hub = QPushButton("Hide Shield Launcher")
        self.btn_toggle_hub.setStyleSheet("padding: 5px 12px; font-size: 11px;")
        self.btn_toggle_hub.clicked.connect(self._toggle_hub)

        header_bar.addWidget(badge_offline)
        header_bar.addWidget(badge_api)
        header_bar.addWidget(self.btn_toggle_hub)
        root_layout.addLayout(header_bar)

        # -------------------------------------------------------------
        # Sticky Top Navigation Bar (CrashGuard -> AgentGuard -> Demo)
        # -------------------------------------------------------------
        nav_container = QFrame()
        nav_container.setStyleSheet("background-color: #171717; border-radius: 6px; padding: 4px;")
        nav_layout = QHBoxLayout(nav_container)
        nav_layout.setContentsMargins(6, 4, 6, 4)
        nav_layout.setSpacing(8)

        self.btn_nav_crashguard = QPushButton("1. ⚡ CrashGuard")
        self.btn_nav_crashguard.setObjectName("navBtnActive")
        self.btn_nav_crashguard.clicked.connect(lambda: self.scroll_to_section(0))

        self.btn_nav_agentguard = QPushButton("2. 🛡️ AgentGuard")
        self.btn_nav_agentguard.setObjectName("navBtnInactive")
        self.btn_nav_agentguard.clicked.connect(lambda: self.scroll_to_section(1))

        self.btn_nav_demo = QPushButton("3. 🧪 Hackathon Demo")
        self.btn_nav_demo.setObjectName("navBtnInactive")
        self.btn_nav_demo.clicked.connect(lambda: self.scroll_to_section(2))

        self._nav_buttons = [
            self.btn_nav_crashguard,
            self.btn_nav_agentguard,
            self.btn_nav_demo,
        ]

        nav_layout.addWidget(self.btn_nav_crashguard)
        nav_layout.addWidget(self.btn_nav_agentguard)
        nav_layout.addWidget(self.btn_nav_demo)
        nav_layout.addStretch()

        root_layout.addWidget(nav_container)

        # -------------------------------------------------------------
        # Vertically Scrollable Continuous Dashboard
        # Order: Section 1 (CrashGuard) -> Section 2 (AgentGuard) -> Section 3 (Demo)
        # -------------------------------------------------------------
        self.main_scroll = QScrollArea()
        self.main_scroll.setWidgetResizable(True)
        self.main_scroll.setFrameShape(QFrame.NoFrame)
        self.main_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.main_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(4, 8, 4, 16)
        self.content_layout.setSpacing(20)

        # -------------------------------------------------------------
        # Section 1: CrashGuard
        # -------------------------------------------------------------
        self.sec_crashguard = QWidget()
        sec1_layout = QVBoxLayout(self.sec_crashguard)
        sec1_layout.setContentsMargins(0, 0, 0, 0)
        sec1_layout.setSpacing(8)

        self.crashguard_panel = CrashGuardPanel(worker=self.worker)
        sec1_layout.addWidget(self.crashguard_panel)
        self.content_layout.addWidget(self.sec_crashguard)

        # Section Divider
        div1 = QFrame()
        div1.setFrameShape(QFrame.HLine)
        div1.setStyleSheet("color: #D9D4C8; margin: 10px 0;")
        self.content_layout.addWidget(div1)

        # -------------------------------------------------------------
        # Section 2: AgentGuard & Temporal Audit Log
        # -------------------------------------------------------------
        self.sec_agentguard = QWidget()
        sec2_layout = QVBoxLayout(self.sec_agentguard)
        sec2_layout.setContentsMargins(0, 0, 0, 0)
        sec2_layout.setSpacing(10)

        self.agentguard_panel = AgentGuardPanel(
            executor=self.executor,
            policy_engine=self.policy,
            approval_manager=self.approvals,
            audit_log=self.audit_log,
        )
        sec2_layout.addWidget(self.agentguard_panel)

        # Unified Timeline & Correlation Search (AC-16) inside Section 2
        timeline_group = QGroupBox("Unified Timeline & Correlation Search (Temporal Audit)")
        timeline_group_layout = QVBoxLayout(timeline_group)
        timeline_group_layout.setContentsMargins(8, 12, 8, 8)
        self.timeline_panel = UnifiedTimelinePanel(event_store=self.event_store)
        timeline_group_layout.addWidget(self.timeline_panel)
        sec2_layout.addWidget(timeline_group)

        self.content_layout.addWidget(self.sec_agentguard)

        # Section Divider
        div2 = QFrame()
        div2.setFrameShape(QFrame.HLine)
        div2.setStyleSheet("color: #D9D4C8; margin: 10px 0;")
        self.content_layout.addWidget(div2)

        # -------------------------------------------------------------
        # Section 3: Demo (Hackathon Verification Console)
        # -------------------------------------------------------------
        self.sec_demo = QWidget()
        sec3_layout = QVBoxLayout(self.sec_demo)
        sec3_layout.setContentsMargins(0, 0, 0, 0)
        sec3_layout.setSpacing(8)

        self.demo_panel = DemoPanel(
            worker=self.worker,
            on_run_agent_safe=self.agentguard_panel._run_safe_scenario,
            on_run_agent_sensitive=self.agentguard_panel._run_sensitive_scenario,
            on_run_agent_blocked=self.agentguard_panel._run_prohibited_scenario,
            on_run_agent_injection=self.agentguard_panel._run_injection_scenario,
            on_reset_live=self._on_demo_reset_live,
        )
        self.demo_panel.demo_reset_requested.connect(self._on_demo_reset_live)
        sec3_layout.addWidget(self.demo_panel)
        self.content_layout.addWidget(self.sec_demo)

        self.main_scroll.setWidget(self.content_widget)
        root_layout.addWidget(self.main_scroll)

        # Sync vertical scroll position with navigation highlight
        self.main_scroll.verticalScrollBar().valueChanged.connect(self._on_scroll_position_changed)

    def _wire_signals(self) -> None:
        self.snapshot_received.connect(self._on_snapshot_received)
        self.alert_received.connect(self._on_alert_received)
        self.evidence_received.connect(self._on_evidence_received)

        self.worker.on_snapshot = lambda snap: self.snapshot_received.emit(snap)
        self.worker.on_alert = lambda alert, recs: self.alert_received.emit(alert, recs)
        self.worker.on_evidence = lambda evs, warns: self.evidence_received.emit(evs, warns)

        self.agentguard_panel.event_recorded.connect(self._on_agentguard_event)

    # -------------------------------------------------------------
    # Navigation & Continuous Scrolling
    # -------------------------------------------------------------
    def scroll_to_section(self, index: int) -> None:
        """Scroll smoothly to the specified section without hiding other sections."""
        target_widget = self.sec_crashguard
        if index == 1:
            target_widget = self.sec_agentguard
        elif index == 2:
            target_widget = self.sec_demo

        self.set_active_navigation(index)
        # Scroll precisely to target widget's top offset
        target_y = target_widget.pos().y()
        self.main_scroll.verticalScrollBar().setValue(max(0, target_y - 10))

    def get_active_section_index(self) -> int:
        return self._active_nav_index

    def set_active_navigation(self, index: int) -> None:
        self._active_nav_index = index
        for i, btn in enumerate(self._nav_buttons):
            if i == index:
                btn.setObjectName("navBtnActive")
            else:
                btn.setObjectName("navBtnInactive")
            btn.setStyle(btn.style())

    def _on_scroll_position_changed(self, scroll_y: int) -> None:
        """Dynamically update active navigation indicator based on current viewport offset."""
        try:
            y_agent = self.sec_agentguard.pos().y() - 100
            y_demo = self.sec_demo.pos().y() - 100

            if scroll_y >= y_demo:
                self.set_active_navigation(2)
            elif scroll_y >= y_agent:
                self.set_active_navigation(1)
            else:
                self.set_active_navigation(0)
        except Exception:
            pass

    # -------------------------------------------------------------
    # Signal Handlers & Live Sync
    # -------------------------------------------------------------
    @Slot(list, list)
    def _on_evidence_received(self, evidence_list: list, warnings: list) -> None:
        self.crashguard_panel.update_evidence(evidence_list, warnings)

        # Update floating shield launcher compact diagnostic
        if evidence_list:
            latest = evidence_list[-1]
            self.floating_hub.set_evidence(f"Event {latest.event_id} ({latest.source})")

        # Persist newly captured evidence into unified SQLite event store (AC-16)
        try:
            newly_stored = persist_windows_evidence(
                store=self.event_store,
                evidence_list=evidence_list,
                collector=self.worker.evidence_collector,
                seen_ids=self.worker._seen_evidence_ids,
            )
            if newly_stored:
                self.timeline_panel.refresh_timeline()
        except Exception:
            pass

    @Slot(object)
    def _on_snapshot_received(self, snapshot: SystemSnapshot) -> None:
        self.crashguard_panel.update_snapshot(snapshot)

        # Update Floating Shield Launcher with live host metrics
        pending_count = 1 if self.agentguard_panel.approval_box.isVisible() else 0
        disk_free_gb = snapshot.disk_free_bytes / (1024**3)
        self.floating_hub.update_status(
            agent_pending_count=pending_count,
            crash_active=self.worker.is_active,
            cpu_pct=snapshot.cpu_percent,
            ram_pct=snapshot.memory_percent,
            disk_free_gb=disk_free_gb,
        )

    @Slot(object, list)
    def _on_alert_received(self, alert: RiskAlert, recs: list) -> None:
        self.crashguard_panel.handle_alert(alert, recs)

        # Update Floating Shield Launcher
        sim_prefix = "[SIMULATED DEMO ALERT] " if alert.is_simulated else ""
        alert_desc = f"{sim_prefix}Sustained {alert.metric_name} ({alert.observed_value:.1f}%)"
        self.floating_hub.set_alert(alert_desc)

        # Persist alert into unified SQLite event store (AC-16)
        try:
            unit_str = "GB free" if alert.metric_name == "DiskFreeGB" else "%"
            unified_ev = UnifiedEvent(
                event_id=alert.alert_id,
                timestamp=alert.timestamp,
                subsystem="CrashGuard",
                event_type="SYSTEM_ALERT",
                severity=alert.severity,
                summary=f"{sim_prefix}Sustained {alert.metric_name} pressure at {alert.observed_value:.1f}{unit_str} for {alert.duration_seconds:.0f}s",
                payload_json=json.dumps({
                    "metric_name": alert.metric_name,
                    "observed_value": alert.observed_value,
                    "threshold_value": alert.threshold_value,
                    "duration_seconds": alert.duration_seconds,
                    "is_simulated": alert.is_simulated,
                }),
                redacted=False,
            )
            self.event_store.record_unified_event(unified_ev)
            self.timeline_panel.refresh_timeline()
        except Exception:
            pass

        # Trigger or update on-screen threshold-crossing popup
        self._show_alert_popup(alert, recs)

    def _show_alert_popup(self, alert: RiskAlert, recs: list) -> None:
        """Display or update the non-blocking CrashGuard alert popup."""
        if self._alert_popup is None:
            self._alert_popup = CrashGuardAlertPopup(
                parent=self,
                on_view_details=self.show_crashguard_details,
            )
        self._alert_popup.add_alert(alert, recs)
        self._alert_popup.display_alert()

    def show_crashguard_details(self) -> None:
        """Scroll to CrashGuard section, bring window forward, and close popup."""
        self.scroll_to_section(0)
        self.showNormal()
        self.raise_()
        self.activateWindow()
        if self._alert_popup and self._alert_popup.isVisible():
            self._alert_popup.close()

    def dismiss_simulated_alerts(self) -> None:
        """Dismiss alert popup if it is currently displaying a simulated alert."""
        if self._alert_popup and self._alert_popup.isVisible() and self._alert_popup.is_simulated():
            self._alert_popup.close()
            self._alert_popup.clear_alerts()

    def _on_demo_reset_live(self) -> None:
        """Clear synthetic demo loads and dismiss demo alerts."""
        self.crashguard_panel._reset_to_authentic()
        self.dismiss_simulated_alerts()

    @Slot()
    def _on_agentguard_event(self) -> None:
        self.timeline_panel.refresh_timeline()

    def toggle_dashboard_visibility(self) -> None:
        if self.isVisible():
            self.hide()
        else:
            self.showNormal()
            self.activateWindow()

    def _toggle_hub(self) -> None:
        if self.floating_hub.isVisible():
            self.floating_hub.hide()
            self.btn_toggle_hub.setText("Show Shield Launcher")
        else:
            self.floating_hub.show()
            self.btn_toggle_hub.setText("Hide Shield Launcher")

    def closeEvent(self, event) -> None:
        """Clean shutdown of monitoring worker, popups, and databases."""
        if hasattr(self, "_alert_popup") and self._alert_popup:
            self._alert_popup.close()
        if hasattr(self, "worker") and self.worker:
            self.worker.stop(timeout=2.0)
        if hasattr(self, "floating_hub") and self.floating_hub:
            self.floating_hub.close()
        if hasattr(self, "audit_log") and self.audit_log:
            self.audit_log.close()
        if hasattr(self, "event_store") and self.event_store:
            self.event_store.close()
        event.accept()
