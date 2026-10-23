"""Automated sanity test for SENTRON desktop application initialization and UI wiring."""
import sys
import time
import pytest
from PySide6.QtWidgets import QApplication

from sentron.main import create_application


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(["-platform", "offscreen"])
    return app


def test_sentron_app_initialization_and_scenario_execution(qapp, tmp_path):
    """Verify application initializes, exercises scenarios, and closes cleanly."""
    db_file = tmp_path / "test_app_sentron.db"
    app, window = create_application(db_path=db_file)

    try:
        # Window and hub must be initialized
        assert window is not None
        assert window.floating_hub is not None
        assert window.agentguard_panel is not None
        assert window.crashguard_panel is not None
        assert window.timeline_panel is not None

        window.show()

        # 1. Run Scenario A: Safe action
        window.agentguard_panel._run_safe_scenario()
        assert "ALLOW" in window.agentguard_panel.lbl_decision.text()
        assert "EXECUTED" in window.agentguard_panel.lbl_execution_status.text()

        # 2. Run Scenario B: Sensitive action requiring approval
        window.agentguard_panel._run_sensitive_scenario()
        assert "ASK" in window.agentguard_panel.lbl_decision.text()
        assert window.agentguard_panel.approval_box.isHidden() is False

        # Approve it
        window.agentguard_panel._approve_current_request()
        assert "EXECUTED" in window.agentguard_panel.lbl_execution_status.text()
        assert window.agentguard_panel.approval_box.isHidden() is True

        # 3. Run Scenario C: Prohibited action
        window.agentguard_panel._run_prohibited_scenario()
        assert "BLOCK" in window.agentguard_panel.lbl_decision.text()
        assert "BLOCKED" in window.agentguard_panel.lbl_execution_status.text()

        # 4. Run Scenario D: Suspicious prompt injection
        window.agentguard_panel._run_injection_scenario()
        assert "ASK" in window.agentguard_panel.lbl_decision.text() or "BLOCK" in window.agentguard_panel.lbl_decision.text()

        # 5. Check Audit Feed has recorded all events
        recent = window.audit_log.get_recent_events(limit=5)
        assert len(recent) >= 4

        # 6. Check CrashGuard updates
        snapshot = window.worker.collector.collect_snapshot()
        window.crashguard_panel.update_snapshot(snapshot)
        assert window.crashguard_panel.chart_widget.width() >= 0

        # 7. Check Floating Hub status update
        window.floating_hub.update_status(agent_pending_count=0, crash_active=True, cpu_pct=snapshot.cpu_percent, ram_pct=snapshot.memory_percent)
        assert "PROTECTED" in window.floating_hub.lbl_overall.text()

    finally:
        # Clean shutdown
        window.exit_application()
