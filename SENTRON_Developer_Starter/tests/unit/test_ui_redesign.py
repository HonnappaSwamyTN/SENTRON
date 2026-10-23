"""Tests for SENTRON UI Redesign: Floating Shield Launcher, Three-Section Dashboard & Demo.

Verifies:
- Hub click-state transitions (collapsed 50x50 shield vs expanded compact status panel)
- Compact status rendering and operational honesty (never claims PROTECTED if degraded)
- Vertical section ordering (Section 1: CrashGuard -> Section 2: AgentGuard -> Section 3: Demo)
- Navigation and continuous scroll synchronization (active indicators, non-exclusive tabs)
- Hackathon Demo simulation labeling, harmless synthetic scenarios, secret redaction, and restore controls
"""
import pytest
from PySide6.QtCore import Qt, QPoint
from PySide6.QtWidgets import QApplication

from sentron.main import create_application
from sentron.ui.hub_widget import FloatingHubWidget


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(["-platform", "offscreen"])
    return app


@pytest.mark.unit
def test_shield_launcher_click_state_transitions(qapp):
    """Shield launcher collapses to 50x50 shield icon and expands unambiguously to status panel."""
    open_called = []
    hub = FloatingHubWidget(on_toggle_dashboard=lambda: open_called.append(True))

    try:
        hub.show()
        qapp.processEvents()

        # 1. Starts in collapsed shield state
        assert not hub.is_expanded()
        assert hub.width() <= 55
        assert hub.height() <= 55

        # 2. Expand to compact status panel
        hub.expand()
        qapp.processEvents()
        assert hub.is_expanded()
        assert hub.width() >= 340
        assert hub.height() >= 220

        # 3. Collapse via collapse button
        hub.btn_collapse.click()
        qapp.processEvents()
        assert not hub.is_expanded()
        assert hub.width() <= 55

        # 4. Toggle expands again
        hub.toggle_expanded()
        qapp.processEvents()
        assert hub.is_expanded()

        # 5. Open dashboard button invokes callback
        hub.btn_toggle.click()
        assert len(open_called) == 1

        # 6. Unambiguous click: clicking inside expanded body does NOT collapse panel
        assert hub.is_expanded()
        hub.panel_view.setEnabled(True)
        assert hub.is_expanded()

    finally:
        hub.close()


@pytest.mark.unit
def test_compact_crashguard_status_rendering_and_honesty(qapp):
    """Compact status panel accurately reflects host telemetry and never claims PROTECTED when inactive."""
    hub = FloatingHubWidget()

    try:
        # Inactive state: must display DEGRADED and Inactive/Stopped, never PROTECTED
        hub.update_status(
            agent_pending_count=0,
            crash_active=False,
            cpu_pct=0.0,
            ram_pct=0.0,
            disk_free_gb=50.0,
        )
        assert "DEGRADED" in hub.lbl_overall.text()
        assert "Inactive" in hub.lbl_crashguard.text() or "Stopped" in hub.lbl_crashguard.text()
        assert "PROTECTED" not in hub.lbl_overall.text()

        # Active healthy state: displays PROTECTED, CPU, RAM, and Disk
        hub.update_status(
            agent_pending_count=0,
            crash_active=True,
            cpu_pct=24.5,
            ram_pct=52.0,
            disk_free_gb=128.4,
        )
        assert "PROTECTED" in hub.lbl_overall.text()
        assert "25%" in hub.lbl_crashguard.text() or "24" in hub.lbl_crashguard.text()
        assert "24.5%" in hub.lbl_metrics_detail.text()
        assert "52.0%" in hub.lbl_metrics_detail.text()
        assert "128.4 GB free" in hub.lbl_metrics_detail.text()
        assert "Updated:" in hub.lbl_timestamp.text()

        # Alerts and evidence updates
        hub.set_alert("⚠️ Sustained CPU at 92.0% (11s)")
        assert "Sustained CPU at 92.0%" in hub.lbl_latest_alert.text()

        hub.set_evidence("Event 1000 (Application Error)")
        assert "Event 1000" in hub.lbl_latest_evidence.text()

        # Pending approvals count
        hub.update_status(
            agent_pending_count=3,
            crash_active=True,
            cpu_pct=20.0,
            ram_pct=40.0,
        )
        assert "3 Awaiting Approval" in hub.lbl_agentguard.text()

    finally:
        hub.close()


@pytest.mark.unit
def test_main_window_three_section_ordering_and_continuous_scroll(qapp, tmp_path):
    """Main window hosts Section 1 (CrashGuard), Section 2 (AgentGuard), Section 3 (Demo) in exact order."""
    db_file = tmp_path / "test_ui_ordering.db"
    app, window = create_application(db_path=db_file)

    try:
        window.show()
        qapp.processEvents()

        # Verify scroll area hosts all three sections continuously
        assert window.main_scroll is not None
        assert window.sec_crashguard is not None
        assert window.sec_agentguard is not None
        assert window.sec_demo is not None

        # Verify all sections exist simultaneously in the content layout
        assert window.sec_crashguard.isVisible()
        assert window.sec_agentguard.isVisible()
        assert window.sec_demo.isVisible()

        # Verify vertical hierarchy order: CrashGuard -> AgentGuard -> Demo
        assert window.sec_crashguard.pos().y() <= window.sec_agentguard.pos().y()
        assert window.sec_agentguard.pos().y() <= window.sec_demo.pos().y()

        # Verify sub-panels are properly parented
        assert window.crashguard_panel.parent() is not None
        assert window.agentguard_panel.parent() is not None
        assert window.demo_panel.parent() is not None
        assert window.timeline_panel.parent() is not None

    finally:
        window.exit_application()


@pytest.mark.unit
def test_navigation_bar_scroll_destinations_and_indicator(qapp, tmp_path):
    """Navigation bar provides 3 visible destinations, updates active indicator, and scrolls to sections."""
    db_file = tmp_path / "test_ui_nav.db"
    app, window = create_application(db_path=db_file)

    try:
        window.show()
        qapp.processEvents()

        # Check navigation buttons
        assert len(window._nav_buttons) == 3
        assert window.btn_nav_crashguard.objectName() == "navBtnActive"
        assert window.btn_nav_agentguard.objectName() == "navBtnInactive"
        assert window.btn_nav_demo.objectName() == "navBtnInactive"
        assert window.get_active_section_index() == 0

        # Scroll to Section 1 (AgentGuard)
        window.scroll_to_section(1)
        qapp.processEvents()
        assert window.get_active_section_index() == 1
        assert window.btn_nav_agentguard.objectName() == "navBtnActive"
        assert window.btn_nav_crashguard.objectName() == "navBtnInactive"

        # Scroll to Section 2 (Demo)
        window.scroll_to_section(2)
        qapp.processEvents()
        assert window.get_active_section_index() == 2
        assert window.btn_nav_demo.objectName() == "navBtnActive"

        # Backward compatibility proxy: window.tabs
        assert window.tabs.count() == 3
        assert window.tabs.currentIndex() == 2
        window.tabs.setCurrentIndex(0)
        qapp.processEvents()
        assert window.tabs.currentIndex() == 0
        assert window.btn_nav_crashguard.objectName() == "navBtnActive"

    finally:
        window.exit_application()


@pytest.mark.unit
def test_demo_panel_simulation_labeling_and_safety_controls(qapp, tmp_path):
    """Section 3 Demo Console features guided scenarios, clear simulation labeling, and secret redaction."""
    db_file = tmp_path / "test_ui_demo.db"
    app, window = create_application(db_path=db_file)

    try:
        window.show()
        qapp.processEvents()

        demo = window.demo_panel
        assert demo is not None

        # 1. Run Safe Demo
        demo.btn_agent_safe.click()
        qapp.processEvents()
        assert "[SIMULATED DEMO: SCENARIO A]" in demo.agent_demo_output.toPlainText()
        assert "ALLOW" in demo.agent_demo_output.toPlainText()

        # 2. Run Sensitive Demo (triggers human approval)
        demo.btn_agent_sensitive.click()
        qapp.processEvents()
        assert "[SIMULATED DEMO: SCENARIO B]" in demo.agent_demo_output.toPlainText()
        assert "ASK" in demo.agent_demo_output.toPlainText()
        assert window.agentguard_panel.approval_box.isVisible()

        # 3. Run Blocked Demo
        demo.btn_agent_blocked.click()
        qapp.processEvents()
        assert "[SIMULATED DEMO: SCENARIO C]" in demo.agent_demo_output.toPlainText()
        assert "BLOCK" in demo.agent_demo_output.toPlainText()

        # 4. Run Injection + Redaction Demo
        demo.btn_agent_injection.click()
        qapp.processEvents()
        assert "[SIMULATED DEMO: SCENARIO D]" in demo.agent_demo_output.toPlainText()
        # Raw secret must NOT be exposed unredacted in the preview
        assert "sk-test-demo-key-12345" not in demo.agent_demo_output.toPlainText()
        assert "[REDACTED_API_KEY]" in demo.agent_demo_output.toPlainText()

        # 5. Trigger Simulated Host CPU stress
        demo.btn_crash_cpu.click()
        qapp.processEvents()
        assert "[SIMULATED DEMO: CPU STRESS]" in demo.crash_demo_output.toPlainText()
        assert window.worker._synthetic_override is not None
        assert window.worker._synthetic_override.cpu_percent == 95.0

        # 6. Restore to Authentic Live
        demo.btn_crash_restore.click()
        qapp.processEvents()
        assert "[SIMULATION RESTORED]" in demo.crash_demo_output.toPlainText()
        assert window.worker._synthetic_override is None

    finally:
        window.exit_application()
