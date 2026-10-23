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
from PySide6.QtGui import QBrush, QColor, QIcon, QPainter, QPen, QPixmap
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
    QSystemTrayIcon,
    QMenu,
)

from sentron.agentguard.approval import ApprovalManager
from sentron.agentguard.audit import SqliteAuditLog
from sentron.agentguard.executor import ControlledExecutor
from sentron.agentguard.policy import PolicyEngine
from sentron.core.models import Decision, RiskAlert, SystemSnapshot, UnifiedEvent
from sentron.core.settings import SettingsManager
from sentron.core.storage import EventStore
from sentron.crashguard.evidence import persist_windows_evidence
from sentron.crashguard.worker import MonitoringWorker
from sentron.ui.agent_alert_popup import AgentGuardAlert, AgentGuardAlertPopup
from sentron.ui.agentguard_panel import AgentGuardPanel
from sentron.ui.alert_popup import CrashGuardAlertPopup
from sentron.ui.crashguard_panel import CrashGuardPanel
from sentron.ui.demo_panel import DemoPanel
from sentron.ui.hub_widget import FloatingHubWidget
from sentron.ui.styles import DARK_THEME_QSS, LIGHT_THEME_QSS, WARM_CONSOLE_QSS, get_theme_qss
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
        self._agent_alert_popup: AgentGuardAlertPopup | None = None
        self._active_nav_index = 0
        self.settings_manager = SettingsManager.get_instance()
        self.current_theme = self.settings_manager.get_theme()

        self.setWindowTitle("SENTRON — Local Security Guard for AI Actions & System Stability")
        # Sensible minimum and default dimensions that comfortably fit 1366x768 laptops
        self.setMinimumSize(880, 540)
        self.resize(1160, 720)

        self._is_exiting = False
        app = QApplication.instance()
        if app:
            app.setQuitOnLastWindowClosed(False)

        # Create Floating Shield Launcher and position non-intrusively in the upper right
        self.floating_hub = FloatingHubWidget(
            on_toggle_dashboard=self.toggle_dashboard_visibility,
            on_exit_app=self.exit_application,
        )
        screen = QApplication.primaryScreen()
        if screen:
            screen_geo = screen.availableGeometry()
            self.floating_hub.move(screen_geo.x() + screen_geo.width() - 80, screen_geo.y() + 40)
        else:
            self.floating_hub.move(80, 80)
        self.floating_hub.show()

        self._init_ui()
        self._init_tray_icon()
        self.apply_theme(self.current_theme)
        self.tabs = NavigationTabsProxy(self)
        self._wire_signals()

    def _init_ui(self) -> None:
        central = QWidget(self)
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(12, 10, 12, 10)
        root_layout.setSpacing(8)

        # -------------------------------------------------------------
        # Sticky Top Bar: Brand, Badges, Theme Selector & Actions
        # -------------------------------------------------------------
        header_bar = QHBoxLayout()
        header_bar.setSpacing(8)

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

        # Badges
        badge_offline = QLabel("OFFLINE ONLY")
        badge_offline.setObjectName("badgeSafe")

        badge_api = QLabel("0 EXTERNAL APIS • ZERO KEYS")
        badge_api.setObjectName("badgeActive")

        # Theme Selector Toggle
        self.btn_theme_toggle = QPushButton("☀️ Light" if self.current_theme == "light" else "🌙 Dark")
        self.btn_theme_toggle.setObjectName("btnThemeToggle")
        self.btn_theme_toggle.setToolTip("Switch between Light Mode and Dark Mode")
        self.btn_theme_toggle.setStyleSheet("padding: 5px 12px; font-size: 11px; font-weight: 700;")
        self.btn_theme_toggle.clicked.connect(self._toggle_theme)

        # Launcher Toggle
        self.btn_toggle_hub = QPushButton("Hide Shield Launcher")
        self.btn_toggle_hub.setStyleSheet("padding: 5px 12px; font-size: 11px;")
        self.btn_toggle_hub.clicked.connect(self._toggle_hub)

        # Explicit Exit SENTRON button
        self.btn_header_exit = QPushButton("Exit SENTRON")
        self.btn_header_exit.setToolTip("Cleanly terminate SENTRON and stop monitoring")
        self.btn_header_exit.setStyleSheet("padding: 5px 10px; font-size: 11px;")
        self.btn_header_exit.clicked.connect(self.exit_application)

        header_bar.addWidget(badge_offline)
        header_bar.addWidget(badge_api)
        header_bar.addWidget(self.btn_theme_toggle)
        header_bar.addWidget(self.btn_toggle_hub)
        header_bar.addWidget(self.btn_header_exit)
        root_layout.addLayout(header_bar)

        # -------------------------------------------------------------
        # Sticky Top Navigation Bar (CrashGuard -> AgentGuard -> Demo)
        # -------------------------------------------------------------
        nav_container = QFrame()
        nav_container.setObjectName("navContainer")
        nav_layout = QHBoxLayout(nav_container)
        nav_layout.setContentsMargins(6, 4, 6, 4)
        nav_layout.setSpacing(8)

        self.btn_nav_crashguard = QPushButton("1. ⚡ CrashGuard")
        self.btn_nav_crashguard.setObjectName("navBtnActive")
        self.btn_nav_crashguard.clicked.connect(lambda: self.scroll_to_section(0))

        self.btn_nav_agentguard = QPushButton("2. 🛡️ AgentGuard")
        self.btn_nav_agentguard.setObjectName("navBtnInactive")
        self.btn_nav_agentguard.clicked.connect(lambda: self.scroll_to_section(1))

        self.btn_nav_test = QPushButton("3. 🧪 Test")
        self.btn_nav_test.setObjectName("navBtnInactive")
        self.btn_nav_test.clicked.connect(lambda: self.scroll_to_section(2))
        self.btn_nav_demo = self.btn_nav_test  # Backward compatibility alias

        self._nav_buttons = [
            self.btn_nav_crashguard,
            self.btn_nav_agentguard,
            self.btn_nav_test,
        ]

        nav_layout.addWidget(self.btn_nav_crashguard)
        nav_layout.addWidget(self.btn_nav_agentguard)
        nav_layout.addWidget(self.btn_nav_test)
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
        # Section 3: Test (Simulated Scenarios & Verification Console)
        # -------------------------------------------------------------
        self.sec_test = QWidget()
        self.sec_demo = self.sec_test  # Backward compatibility alias
        sec3_layout = QVBoxLayout(self.sec_test)
        sec3_layout.setContentsMargins(0, 0, 0, 0)
        sec3_layout.setSpacing(8)

        self.test_panel = DemoPanel(
            worker=self.worker,
            on_run_agent_safe=self.agentguard_panel._run_safe_scenario,
            on_run_agent_sensitive=self.agentguard_panel._run_sensitive_scenario,
            on_run_agent_blocked=self.agentguard_panel._run_prohibited_scenario,
            on_run_agent_injection=self.agentguard_panel._run_injection_scenario,
            on_reset_live=self._on_demo_reset_live,
        )
        self.demo_panel = self.test_panel  # Backward compatibility alias
        self.test_panel.demo_reset_requested.connect(self._on_demo_reset_live)
        sec3_layout.addWidget(self.test_panel)
        self.content_layout.addWidget(self.sec_test)

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
        self.agentguard_panel.agent_alert_triggered.connect(self._show_agent_alert_popup)

    # -------------------------------------------------------------
    # Navigation & Continuous Scrolling
    # -------------------------------------------------------------
    def scroll_to_section(self, index: int) -> None:
        """Scroll smoothly to the specified section without hiding other sections."""
        target_widget = self.sec_crashguard
        if index == 1:
            target_widget = self.sec_agentguard
        elif index == 2:
            target_widget = self.sec_test

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
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _on_scroll_position_changed(self, scroll_y: int) -> None:
        """Dynamically update active navigation indicator based on current viewport offset."""
        try:
            y_agent = self.sec_agentguard.pos().y() - 100
            y_test = self.sec_test.pos().y() - 100

            if scroll_y >= y_test:
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
        if evidence_list and hasattr(self, "floating_hub") and self.floating_hub:
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
        if self.isVisible():
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
        unit_str = "GB free" if alert.metric_name == "DiskFreeGB" else ("°C" if alert.metric_name == "CPUTemperature" else "%")
        alert_desc = f"{sim_prefix}Sustained {alert.metric_name} ({alert.observed_value:.1f}{unit_str})"
        self.floating_hub.set_alert(alert_desc)

        # Persist alert into unified SQLite event store (AC-16)
        try:
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
                is_simulated=alert.is_simulated,
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
                parent=None,
                on_view_details=self.show_crashguard_details,
                on_review_processes=self.show_process_review,
                theme=self.current_theme,
            )
        self._alert_popup.set_theme(self.current_theme)
        self._alert_popup.add_alert(alert, recs)
        self._alert_popup.display_alert()

        # If dashboard window is currently hidden, also post a Windows notification via system tray
        if hasattr(self, "tray_icon") and self.tray_icon and self.isHidden():
            try:
                title = "SENTRON — High System Resource Risk" if alert.severity == "critical" else "SENTRON — Health Advisory"
                msg = f"Sustained {alert.metric_name} pressure at {alert.observed_value:.1f}%. Click to view details."
                self.tray_icon.showMessage(title, msg, QSystemTrayIcon.Warning, 6000)
            except Exception:
                pass

    def show_crashguard_details(self) -> None:
        """Scroll to CrashGuard section, bring window forward, and close popup."""
        self.scroll_to_section(0)
        self.showNormal()
        self.raise_()
        self.activateWindow()
        if self._alert_popup and self._alert_popup.isVisible():
            self._alert_popup.close()

    def show_process_review(self) -> None:
        """Open the controlled high-resource process response dialog."""
        self.crashguard_panel.open_process_review_dialog()

    def _show_agent_alert_popup(self, alert: AgentGuardAlert) -> None:
        """Display or update the non-blocking AgentGuard alert popup."""
        if self._agent_alert_popup is None:
            self._agent_alert_popup = AgentGuardAlertPopup(
                parent=None,
                on_approve=self._on_agent_popup_approve,
                on_reject=self._on_agent_popup_reject,
                on_view_details=self.show_agentguard_details,
                on_dismiss=self._on_agent_popup_dismiss,
                theme=self.current_theme,
            )

        # Check deduplication to prevent popup loops/spam
        if self._agent_alert_popup.should_suppress(alert):
            if self._agent_alert_popup.isVisible():
                self._agent_alert_popup.raise_()
            return

        self._agent_alert_popup.set_theme(self.current_theme)
        self._agent_alert_popup.display_alert(alert)

        # Post a Windows system tray notification if dashboard is currently hidden
        if hasattr(self, "tray_icon") and self.tray_icon and self.isHidden():
            try:
                title = alert.title
                sim_tag = "[SIMULATED] " if alert.is_simulated else ""
                target_str = alert.target or alert.destination or "resource"
                msg = f"{sim_tag}{alert.agent_id}: {alert.operation} on {target_str}. Decision: {alert.decision.value}."
                icon = QSystemTrayIcon.Critical if alert.decision == Decision.BLOCK else QSystemTrayIcon.Warning
                self.tray_icon.showMessage(title, msg, icon, 6000)
            except Exception:
                pass

    def _on_agent_popup_approve(self, alert: AgentGuardAlert) -> None:
        """Callback when user approves an action from the AgentGuard alert popup."""
        result = self.agentguard_panel.approve_action(alert.action_request)
        if hasattr(self, "test_panel") and self.test_panel and alert.action_request and result:
            self.test_panel.notify_agent_approved(alert.action_request, result)

    def _on_agent_popup_reject(self, alert: AgentGuardAlert) -> None:
        """Callback when user rejects an action from the AgentGuard alert popup."""
        self.agentguard_panel.reject_action(alert.action_request)
        if hasattr(self, "test_panel") and self.test_panel and alert.action_request:
            self.test_panel.notify_agent_rejected(alert.action_request)

    def _on_agent_popup_dismiss(self, alert: AgentGuardAlert | None = None) -> None:
        """Callback when popup is dismissed fail-closed."""
        pass

    def show_agentguard_details(self, alert: AgentGuardAlert | None = None) -> None:
        """Scroll to AgentGuard section, bring dashboard forward, and close popup."""
        self.scroll_to_section(1)
        self.showNormal()
        self.raise_()
        self.activateWindow()
        if self._agent_alert_popup and self._agent_alert_popup.isVisible():
            self._agent_alert_popup.close()

    def process_agent_request(self, request: ActionRequest, is_simulated: bool = False) -> ExecutionResult:
        """Public application interface for dispatching agent requests with full governance & popups."""
        return self.agentguard_panel.process_agent_request(request, is_simulated=is_simulated)

    def _toggle_theme(self) -> None:
        """Toggle between Light and Dark themes and persist the preference."""
        new_theme = "dark" if self.current_theme == "light" else "light"
        self.apply_theme(new_theme)

    def toggle_theme(self) -> None:
        """Public alias for toggling application theme."""
        self._toggle_theme()

    def apply_theme(self, theme_name: str) -> None:
        """Apply stylesheet across the application and update child components."""
        self.current_theme = (theme_name or "light").lower()
        self.settings_manager.set_theme(self.current_theme)
        qss = get_theme_qss(self.current_theme)
        app = QApplication.instance()
        if app:
            app.setStyleSheet(qss)
        self.setStyleSheet(qss)
        if hasattr(self, "crashguard_panel") and self.crashguard_panel:
            self.crashguard_panel.set_theme(self.current_theme)
        if hasattr(self, "agentguard_panel") and self.agentguard_panel:
            self.agentguard_panel.set_theme(self.current_theme)
        if hasattr(self, "timeline_panel") and self.timeline_panel:
            self.timeline_panel.set_theme(self.current_theme)
        if hasattr(self, "test_panel") and self.test_panel:
            self.test_panel.set_theme(self.current_theme)
        if hasattr(self, "_alert_popup") and self._alert_popup:
            self._alert_popup.set_theme(self.current_theme)
        if hasattr(self, "_agent_alert_popup") and self._agent_alert_popup:
            self._agent_alert_popup.set_theme(self.current_theme)
        if hasattr(self, "btn_theme_toggle") and self.btn_theme_toggle:
            self.btn_theme_toggle.setText("☀️ Light" if self.current_theme == "light" else "🌙 Dark")

    def _init_tray_icon(self) -> None:
        """Initialize Windows system tray icon and background notification support."""
        self.tray_icon: QSystemTrayIcon | None = None
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return

        self.tray_icon = QSystemTrayIcon(self)

        # Draw a sharp golden shield pixmap for the tray
        pixmap = QPixmap(24, 24)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QBrush(QColor("#E2B83B")))
        painter.setPen(QPen(QColor("#C49B24"), 1))
        painter.drawEllipse(2, 2, 20, 20)
        painter.end()
        self.tray_icon.setIcon(QIcon(pixmap))
        self.tray_icon.setToolTip("SENTRON — Local Security Guard & System Stability")

        tray_menu = QMenu(self)
        act_dash = tray_menu.addAction("Open Dashboard")
        act_dash.triggered.connect(self._show_from_tray)

        act_proc = tray_menu.addAction("Review High-Impact Processes")
        act_proc.triggered.connect(self.show_process_review)

        act_theme = tray_menu.addAction("Toggle Dark/Light Theme")
        act_theme.triggered.connect(self._toggle_theme)

        tray_menu.addSeparator()

        act_exit = tray_menu.addAction("Exit SENTRON")
        act_exit.triggered.connect(self.exit_application)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _show_from_tray(self) -> None:
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self.toggle_dashboard_visibility()

    def dismiss_simulated_alerts(self) -> None:
        """Dismiss alert popups if currently displaying a simulated alert."""
        if self._alert_popup and self._alert_popup.isVisible() and self._alert_popup.is_simulated():
            self._alert_popup.close()
            self._alert_popup.clear_alerts()
        if self._agent_alert_popup and self._agent_alert_popup.isVisible() and self._agent_alert_popup.is_simulated():
            self._agent_alert_popup.close()

    def _on_demo_reset_live(self) -> None:
        """Clear synthetic demo loads and dismiss demo alerts."""
        self.crashguard_panel._reset_to_authentic()
        self.dismiss_simulated_alerts()

    @Slot()
    def _on_agentguard_event(self) -> None:
        self.timeline_panel.refresh_timeline()
        if (
            hasattr(self, "_agent_alert_popup")
            and self._agent_alert_popup
            and self._agent_alert_popup.isVisible()
            and self._agent_alert_popup.current_alert
            and self._agent_alert_popup.current_alert.decision == Decision.ASK
            and self._agent_alert_popup.current_alert.alert_type != "prompt_injection"
            and self.agentguard_panel._current_pending_request is None
        ):
            self._agent_alert_popup.close()

    def showEvent(self, event) -> None:
        """Refresh panels on demand when dashboard becomes visible."""
        super().showEvent(event)
        latest = self.worker.get_latest_snapshot()
        if latest:
            self.crashguard_panel.update_snapshot(latest)

    def toggle_dashboard_visibility(self) -> None:
        if self.isVisible():
            self.hide()
        else:
            self.showNormal()
            self.activateWindow()
            latest = self.worker.get_latest_snapshot()
            if latest:
                self.crashguard_panel.update_snapshot(latest)

    def _toggle_hub(self) -> None:
        if self.floating_hub.isVisible():
            self.floating_hub.hide()
            self.btn_toggle_hub.setText("Show Shield Launcher")
        else:
            self.floating_hub.show()
            self.btn_toggle_hub.setText("Hide Shield Launcher")

    def close(self) -> bool:
        """Dashboard close: hide window while keeping shield and monitoring active unless exiting."""
        if not getattr(self, "_is_exiting", False):
            self.hide()
            if hasattr(self, "floating_hub") and self.floating_hub:
                self.floating_hub.show()
            return True
        return super().close()

    def closeEvent(self, event) -> None:
        """Dashboard window close handler: hides dashboard instead of terminating SENTRON process."""
        if not getattr(self, "_is_exiting", False):
            event.ignore()
            self.hide()
            if hasattr(self, "floating_hub") and self.floating_hub:
                self.floating_hub.show()
            return

        self._cleanup_resources()
        event.accept()

    def exit_application(self) -> None:
        """Clean shutdown of SENTRON: stop workers, release resources, and exit cleanly."""
        self._is_exiting = True
        self._cleanup_resources()
        if hasattr(self, "floating_hub") and self.floating_hub:
            self.floating_hub.hide()
            self.floating_hub.close()
        self.close()
        app = QApplication.instance()
        if app:
            app.quit()

    def _cleanup_resources(self) -> None:
        """Clean shutdown of monitoring worker, popups, and databases."""
        if getattr(self, "_cleaned_up", False):
            return
        self._cleaned_up = True
        if hasattr(self, "tray_icon") and self.tray_icon:
            try:
                self.tray_icon.hide()
            except Exception:
                pass
        if hasattr(self, "_alert_popup") and self._alert_popup:
            self._alert_popup.close()
        if hasattr(self, "_agent_alert_popup") and self._agent_alert_popup:
            self._agent_alert_popup.close()
        if hasattr(self, "floating_hub") and self.floating_hub:
            self.floating_hub.close()
        if hasattr(self, "worker") and self.worker:
            self.worker.stop(timeout=2.0)
        if hasattr(self, "audit_log") and self.audit_log:
            self.audit_log.close()
        if hasattr(self, "event_store") and self.event_store:
            self.event_store.close()
