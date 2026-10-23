"""Unit and Integration Tests for AgentGuard Alert Popups.

Verifies:
1. Scenario B opens an approval popup with Approve Once & Reject.
2. Scenario C opens a blocked-action popup without an approval button.
3. Scenario D opens a prompt-injection warning popup.
4. Scenario A (safe ALLOW action) does not open a disruptive popup.
5. Approve/reject actions correctly update pending simulated request without affecting real permissions.
6. Dismissing a popup fails closed without approving or executing.
7. Real (non-simulated) AgentGuard decisions can trigger notifications with authentic labeling.
8. Popups work while dashboard is hidden, and View Details unhides the dashboard.
9. Duplicate alerts are safely deduplicated to prevent alert spam.
10. Dark and light themes apply correctly.
"""
import time
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from sentron.core.models import ActionRequest, Decision
from sentron.main import create_application
from sentron.ui.agent_alert_popup import AgentAlertDeduplicator, AgentGuardAlert, AgentGuardAlertPopup


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(["-platform", "offscreen"])
    return app


@pytest.fixture
def app_window(qapp, tmp_path):
    db_file = tmp_path / f"test_agent_popup_{time.time_ns()}.db"
    app, window = create_application(db_path=db_file, start_worker=False)
    window.show()
    qapp.processEvents()
    yield window
    window.exit_application()
    qapp.processEvents()


# =========================================================================
# 1. SCENARIO POPUP BEHAVIOR TESTS
# =========================================================================

@pytest.mark.unit
def test_scenario_b_opens_approval_popup(qapp, app_window):
    """Scenario B (sensitive action / ASK HUMAN) opens an approval popup with Approve Once and Reject."""
    demo = app_window.test_panel
    demo.btn_agent_sensitive.click()
    qapp.processEvents()

    popup = app_window._agent_alert_popup
    assert popup is not None
    assert popup.isVisible()
    assert "Approval Required" in popup.lbl_title.text() or "Sensitive Data" in popup.lbl_title.text()
    assert popup.is_simulated() is True
    assert popup.lbl_sim_badge.isVisible() is True
    assert popup.btn_approve.isVisible() is True
    assert popup.btn_reject.isVisible() is True
    assert popup.btn_view_details.isVisible() is True
    assert popup.btn_dismiss.isVisible() is True

    # Details check
    assert "demo-finance-agent" in popup.lbl_agent.text()
    assert "confidential_q4_results.xlsx" in popup.lbl_target.text()
    assert "ASK HUMAN" in popup.lbl_decision.text()


@pytest.mark.unit
def test_scenario_c_opens_blocked_action_popup_without_approval_button(qapp, app_window):
    """Scenario C (prohibited action / BLOCK) opens a warning popup with NO approval option."""
    demo = app_window.test_panel
    demo.btn_agent_blocked.click()
    qapp.processEvents()

    popup = app_window._agent_alert_popup
    assert popup is not None
    assert popup.isVisible()
    assert "Prohibited Action Blocked" in popup.lbl_title.text()
    assert popup.current_alert.decision == Decision.BLOCK

    # CRITICAL SECURITY REQUIREMENT: Never show an Approve button for blocked prohibited action
    assert popup.btn_approve.isVisible() is False
    assert popup.btn_reject.isVisible() is False
    assert popup.btn_view_details.isVisible() is True
    assert popup.btn_dismiss.isVisible() is True
    assert "BLOCK" in popup.lbl_decision.text()

    # Attempting to programmatically trigger approve on BLOCK must be a no-op
    popup._handle_approve()
    assert app_window.agentguard_panel._current_pending_request is None


@pytest.mark.unit
def test_scenario_d_opens_prompt_injection_warning_popup(qapp, app_window):
    """Scenario D (prompt injection / redaction) opens a security warning popup."""
    demo = app_window.test_panel
    demo.btn_agent_injection.click()
    qapp.processEvents()

    popup = app_window._agent_alert_popup
    assert popup is not None
    assert popup.isVisible()
    assert "Prompt Injection Detected" in popup.lbl_title.text()
    assert popup.current_alert.alert_type == "prompt_injection"

    # Security warning: no approval button
    assert popup.btn_approve.isVisible() is False
    assert popup.lbl_risk_signals.isVisible() is True
    assert "PROMPT_INJECTION_OVERRIDE" in popup.lbl_risk_signals.text()
    assert popup.lbl_redaction.isVisible() is True


@pytest.mark.unit
def test_scenario_a_does_not_open_disruptive_popup(qapp, app_window):
    """Scenario A (safe action / ALLOW) shows results in panel without opening a disruptive popup."""
    # Ensure popup is not currently visible
    if app_window._agent_alert_popup:
        app_window._agent_alert_popup.close()

    demo = app_window.test_panel
    demo.btn_agent_safe.click()
    qapp.processEvents()

    # Popup must NOT be visible
    assert app_window._agent_alert_popup is None or not app_window._agent_alert_popup.isVisible()

    # Output appears in panel
    assert "[SIMULATED DEMO: SCENARIO A]" in demo.agent_demo_output.toPlainText()
    assert "ALLOW" in demo.agent_demo_output.toPlainText()


# =========================================================================
# 2. APPROVE / REJECT ENFORCEMENT & SIMULATION BOUNDARY TESTS
# =========================================================================

@pytest.mark.unit
def test_approve_action_updates_pending_request_and_audit(qapp, app_window):
    """Approving via popup updates the pending request, executes mock handler, and logs to audit."""
    demo = app_window.test_panel
    demo.btn_agent_sensitive.click()
    qapp.processEvents()

    popup = app_window._agent_alert_popup
    assert popup.isVisible()
    assert app_window.agentguard_panel._current_pending_request is not None

    # Click Approve Once
    popup.btn_approve.click()
    qapp.processEvents()

    # Popup closes
    assert not popup.isVisible()

    # Pending request cleared from panel
    assert app_window.agentguard_panel._current_pending_request is None
    assert app_window.agentguard_panel.approval_box.isVisible() is False
    assert "ALLOW" in app_window.agentguard_panel.lbl_decision.text()

    # Test panel updated
    assert "APPROVED ONCE" in demo.agent_demo_output.toPlainText()

    # Audit log confirms approval_accepted event
    recent = app_window.audit_log.get_recent_events(limit=5)
    accepted_events = [e for e in recent if e.event_type == "approval_accepted"]
    assert len(accepted_events) >= 1


@pytest.mark.unit
def test_reject_action_halts_execution_fail_closed(qapp, app_window):
    """Rejecting via popup halts execution fail-closed and logs user denial in audit."""
    demo = app_window.test_panel
    demo.btn_agent_sensitive.click()
    qapp.processEvents()

    popup = app_window._agent_alert_popup
    assert popup.isVisible()

    # Click Reject
    popup.btn_reject.click()
    qapp.processEvents()

    # Popup closes
    assert not popup.isVisible()

    # Pending request cleared and marked rejected
    assert app_window.agentguard_panel._current_pending_request is None
    assert "REJECTED BY USER" in app_window.agentguard_panel.lbl_decision.text()
    assert "HALTED" in app_window.agentguard_panel.lbl_execution_status.text()
    assert "REJECTED BY OPERATOR" in demo.agent_demo_output.toPlainText()

    # Audit log confirms approval_rejected event
    recent = app_window.audit_log.get_recent_events(limit=5)
    rejected_events = [e for e in recent if e.event_type == "approval_rejected"]
    assert len(rejected_events) >= 1


@pytest.mark.unit
def test_dismissing_popup_fails_closed_without_approving(qapp, app_window):
    """Dismissing the popup must NOT silently approve or resume pending request."""
    demo = app_window.test_panel
    demo.btn_agent_sensitive.click()
    qapp.processEvents()

    popup = app_window._agent_alert_popup
    assert popup.isVisible()
    pending_req = app_window.agentguard_panel._current_pending_request
    assert pending_req is not None

    # Click Dismiss
    popup.btn_dismiss.click()
    qapp.processEvents()

    # Popup closed
    assert not popup.isVisible()

    # Action remains unapproved (fail-closed)
    assert app_window.agentguard_panel._current_pending_request is not None
    recent = app_window.audit_log.get_recent_events(limit=3)
    # Ensure no approval_accepted was written
    for ev in recent:
        assert ev.event_type != "approval_accepted"


# =========================================================================
# 3. REAL AGENT DECISIONS & BACKGROUND NOTIFICATIONS
# =========================================================================

@pytest.mark.unit
def test_real_agent_decisions_trigger_notifications(qapp, app_window):
    """Real (non-simulated) sensitive action requests trigger authentic AgentGuard notifications."""
    real_request = ActionRequest(
        agent_id="real-prod-agent",
        tool_name="database_tool",
        operation="read_file",
        target="customer_pii_records.db",
        data_classification="confidential",
        purpose="Monthly regulatory compliance report.",
        session_id="prod-session-100",
    )

    app_window.process_agent_request(real_request, is_simulated=False)
    qapp.processEvents()

    popup = app_window._agent_alert_popup
    assert popup is not None
    assert popup.isVisible()

    # Must be labeled as authentic (NOT simulated)
    assert popup.is_simulated() is False
    assert popup.lbl_sim_badge.isVisible() is False
    assert popup.lbl_sim_disclaimer.isVisible() is False
    assert "real-prod-agent" in popup.lbl_agent.text()
    assert popup.btn_approve.isVisible() is True


@pytest.mark.unit
def test_popups_work_while_dashboard_is_hidden(qapp, app_window):
    """Popups appear in the foreground even when the main dashboard is hidden."""
    app_window.hide()
    qapp.processEvents()
    assert app_window.isHidden() is True

    # Trigger sensitive alert while hidden
    app_window.test_panel.btn_agent_sensitive.click()
    qapp.processEvents()

    popup = app_window._agent_alert_popup
    assert popup is not None
    assert popup.isVisible() is True
    assert popup.windowFlags() & Qt.WindowStaysOnTopHint

    # Clicking View Details brings dashboard back forward
    popup.btn_view_details.click()
    qapp.processEvents()

    assert app_window.isVisible() is True
    assert app_window.get_active_section_index() == 1


# =========================================================================
# 4. DEDUPLICATION & THEME STYLING TESTS
# =========================================================================

@pytest.mark.unit
def test_duplicate_alerts_handled_safely(qapp):
    """Deduplicator suppresses rapid identical alerts within cooldown window."""
    dedup = AgentAlertDeduplicator(cooldown_seconds=2.0)
    alert1 = AgentGuardAlert(
        alert_type="approval_required",
        decision=Decision.ASK,
        title="AgentGuard — Approval Required",
        agent_id="agent-01",
        tool_name="tool-01",
        operation="read_file",
        target="file.txt",
    )
    # First occurrence -> not a duplicate
    assert dedup.is_duplicate(alert1) is False

    # Immediate second occurrence with same fingerprint -> duplicate!
    assert dedup.is_duplicate(alert1) is True

    # Alert with different operation -> not a duplicate
    alert2 = AgentGuardAlert(
        alert_type="approval_required",
        decision=Decision.ASK,
        title="AgentGuard — Approval Required",
        agent_id="agent-01",
        tool_name="tool-01",
        operation="write_file",
        target="file.txt",
    )
    assert dedup.is_duplicate(alert2) is False


@pytest.mark.unit
def test_dark_and_light_theme_support(qapp):
    """Popup renders cleanly and updates styling when switching between dark and light themes."""
    popup = AgentGuardAlertPopup(theme="light")
    alert = AgentGuardAlert(
        alert_type="approval_required",
        decision=Decision.ASK,
        title="AgentGuard — Approval Required",
        agent_id="test-agent",
        tool_name="file_tool",
        operation="read_file",
        target="test.csv",
        is_simulated=True,
    )
    popup.display_alert(alert)

    # Test Light mode
    popup.set_theme("light")
    assert popup.theme == "light"
    assert "#FFFFFF" in popup.card.styleSheet()

    # Test Dark mode
    popup.set_theme("dark")
    assert popup.theme == "dark"
    assert "#161b22" in popup.card.styleSheet()
    popup.close()


@pytest.mark.unit
def test_unclassified_request_with_secret_triggers_sensitive_data_popup(qapp, app_window):
    """An unclassified request containing secrets is detected, classified as confidential, and triggers popup with redaction."""
    panel = app_window.agentguard_panel
    req = ActionRequest(
        agent_id="test-agent",
        tool_name="api_tool",
        operation="call_endpoint",
        target="https://api.example.com",
        purpose="Use secret token sk-1234567890abcdef1234567890abcdef to sync data",
    )
    result = panel.process_agent_request(req, is_simulated=False)

    assert result.decision == Decision.ASK
    popup = app_window._agent_alert_popup
    assert popup is not None
    assert popup.isVisible()
    assert popup.current_alert is not None
    assert popup.current_alert.alert_type == "sensitive_data"
    assert "sk-****" in popup.lbl_redaction.text()
    assert popup.btn_approve.isVisible() is True
    assert popup.btn_reject.isVisible() is True


@pytest.mark.unit
def test_cpu_temperature_alert_logging(qapp, app_window):
    """CrashGuard CPUTemperature alert logs with °C units and preserves is_simulated."""
    from sentron.core.models import RiskAlert
    alert = RiskAlert(
        alert_id="temp-alert-1",
        metric_name="CPUTemperature",
        severity="warning",
        observed_value=88.5,
        threshold_value=85.0,
        duration_seconds=10.0,
        cooldown_until=time.time() + 30.0,
        timestamp=time.time(),
        is_simulated=True,
    )
    app_window._on_alert_received(alert, [])
    qapp.processEvents()

    assert "88.5°C" in app_window.floating_hub.lbl_latest_alert.text()
    events = app_window.event_store.get_recent_events(limit=5)
    matching = [e for e in events if e.event_id == "temp-alert-1"]
    assert len(matching) == 1
    assert matching[0].is_simulated is True
    assert "88.5°C" in matching[0].summary

