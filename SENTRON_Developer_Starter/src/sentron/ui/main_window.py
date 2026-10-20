"""Main Desktop Window for SENTRON."""
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
    QTabWidget,
    QSplitter,
    QScrollArea,
    QFrame,
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
from sentron.ui.hub_widget import FloatingHubWidget
from sentron.ui.styles import DARK_THEME_QSS
from sentron.ui.timeline_panel import UnifiedTimelinePanel


class SentronMainWindow(QMainWindow):
    """Main application window uniting AgentGuard, CrashGuard, and the Unified Timeline."""

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

        self.setWindowTitle("SENTRON — Local Security Guard for AI Actions & System Stability")
        # Sensible minimum and default dimensions that comfortably fit 1366x768 laptops
        self.setMinimumSize(880, 540)
        self.resize(1160, 680)
        self.setStyleSheet(DARK_THEME_QSS)

        # Create Floating Hub and position non-intrusively in the upper right
        self.floating_hub = FloatingHubWidget(on_toggle_dashboard=self.toggle_dashboard_visibility)
        screen = QApplication.primaryScreen()
        if screen:
            screen_geo = screen.availableGeometry()
            self.floating_hub.move(screen_geo.x() + screen_geo.width() - 360, screen_geo.y() + 40)
        else:
            self.floating_hub.move(80, 80)
        self.floating_hub.show()

        self._init_ui()
        self._wire_signals()

    def _init_ui(self) -> None:
        central = QWidget(self)
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(12, 10, 12, 12)
        root_layout.setSpacing(8)

        # Header bar
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

        self.btn_toggle_hub = QPushButton("Hide Floating Hub")
        self.btn_toggle_hub.setStyleSheet("padding: 5px 12px; font-size: 11px;")
        self.btn_toggle_hub.clicked.connect(self._toggle_hub)

        header_bar.addWidget(badge_offline)
        header_bar.addWidget(badge_api)
        header_bar.addWidget(self.btn_toggle_hub)
        root_layout.addLayout(header_bar)

        # Divider
        div = QFrame()
        div.setFrameShape(QFrame.HLine)
        div.setStyleSheet("color: #30363d;")
        root_layout.addWidget(div)

        # Main Tab Widget
        self.tabs = QTabWidget()

        # Tab 1: Live Security & Health Dashboard (Splitter: AgentGuard + CrashGuard)
        dashboard_tab = QWidget()
        dash_layout = QVBoxLayout(dashboard_tab)
        dash_layout.setContentsMargins(0, 4, 0, 0)
        dash_layout.setSpacing(0)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(6)
        splitter.setChildrenCollapsible(False)

        # Left: AgentGuard wrapped in clean scroll area for smaller windows
        self.agentguard_panel = AgentGuardPanel(
            executor=self.executor,
            policy_engine=self.policy,
            approval_manager=self.approvals,
            audit_log=self.audit_log,
        )
        self.agent_scroll = QScrollArea()
        self.agent_scroll.setWidgetResizable(True)
        self.agent_scroll.setFrameShape(QFrame.NoFrame)
        self.agent_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.agent_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.agent_scroll.setWidget(self.agentguard_panel)
        splitter.addWidget(self.agent_scroll)

        # Right: CrashGuard wrapped in clean scroll area
        self.crashguard_panel = CrashGuardPanel(worker=self.worker)
        self.crash_scroll = QScrollArea()
        self.crash_scroll.setWidgetResizable(True)
        self.crash_scroll.setFrameShape(QFrame.NoFrame)
        self.crash_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.crash_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.crash_scroll.setWidget(self.crashguard_panel)
        splitter.addWidget(self.crash_scroll)

        splitter.setSizes([580, 580])
        dash_layout.addWidget(splitter)
        self.tabs.addTab(dashboard_tab, "Live Security & Health Dashboard")

        # Tab 2: Unified Timeline & Correlation Search (AC-16)
        self.timeline_panel = UnifiedTimelinePanel(event_store=self.event_store)
        self.tabs.addTab(self.timeline_panel, "Unified Timeline & Temporal Search")

        root_layout.addWidget(self.tabs)

    def _wire_signals(self) -> None:
        # Route background worker updates to main Qt thread via signals
        self.snapshot_received.connect(self._on_snapshot_received)
        self.alert_received.connect(self._on_alert_received)
        self.evidence_received.connect(self._on_evidence_received)

        self.worker.on_snapshot = lambda snap: self.snapshot_received.emit(snap)
        self.worker.on_alert = lambda alert, recs: self.alert_received.emit(alert, recs)
        self.worker.on_evidence = lambda evs, warns: self.evidence_received.emit(evs, warns)

        # Connect AgentGuard audit events to refresh timeline
        self.agentguard_panel.event_recorded.connect(self._on_agentguard_event)

    @Slot(list, list)
    def _on_evidence_received(self, evidence_list: list, warnings: list) -> None:
        self.crashguard_panel.update_evidence(evidence_list, warnings)

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

        # Update Floating Hub
        pending_count = 1 if self.agentguard_panel.approval_box.isVisible() else 0
        self.floating_hub.update_status(
            agent_pending_count=pending_count,
            crash_active=self.worker.is_active,
            cpu_pct=snapshot.cpu_percent,
            ram_pct=snapshot.memory_percent,
        )

    @Slot(object, list)
    def _on_alert_received(self, alert: RiskAlert, recs: list) -> None:
        self.crashguard_panel.handle_alert(alert, recs)

        # Also persist alert into unified SQLite event store (AC-16)
        try:
            unit_str = "GB free" if alert.metric_name == "DiskFreeGB" else "%"
            sim_prefix = "[SIMULATED DEMO ALERT] " if alert.is_simulated else ""
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
        """Switch to dashboard tab, bring window forward, and close popup."""
        self.tabs.setCurrentIndex(0)
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
            self.btn_toggle_hub.setText("Show Floating Hub")
        else:
            self.floating_hub.show()
            self.btn_toggle_hub.setText("Hide Floating Hub")

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
