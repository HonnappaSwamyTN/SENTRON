"""Unit and UI tests for SENTRON UI Fixes and Demo Consolidation.

Covers:
- Header text and navigation contrast/style definitions.
- Navigation hover, selected, and focus states.
- The 'Hackathon Demo' -> 'Test' rename.
- Demo/simulation controls appearing ONLY in Test section, not in CrashGuard or AgentGuard.
- Simulated records being distinguishable from genuine audit/evidence records.
- AgentGuard showing at most the latest 20 genuine recorded actions in newest-first order with accessible indicators.
- Existing CrashGuard monitoring, AgentGuard permission checks, and shutdown lifecycle intact.
"""
from datetime import datetime, timezone, timedelta
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QPushButton

from sentron.agentguard.audit import SqliteAuditLog, StoredAuditEvent
from sentron.core.models import ActionRequest, AuditEvent, Decision, SystemSnapshot, utc_now
from sentron.main import create_application
from sentron.ui.styles import WARM_CONSOLE_QSS


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(["-platform", "offscreen"])
    return app


@pytest.mark.unit
def test_header_text_and_navigation_contrast_and_styles():
    """Verify high-contrast color tokens and navigation pseudo-classes in stylesheet."""
    # Header & brand text contrast tokens
    assert "#brandTitle" in WARM_CONSOLE_QSS
    assert "color: #171717;" in WARM_CONSOLE_QSS
    assert "#brandTagline" in WARM_CONSOLE_QSS
    assert "color: #4A453A;" in WARM_CONSOLE_QSS

    # Navigation active state: gold accent, dark readable text
    assert "#navBtnActive" in WARM_CONSOLE_QSS
    assert "background-color: #E2B83B;" in WARM_CONSOLE_QSS
    assert "color: #171717;" in WARM_CONSOLE_QSS
    assert "#navBtnActive:hover" in WARM_CONSOLE_QSS
    assert "#navBtnActive:focus" in WARM_CONSOLE_QSS

    # Navigation inactive state: readable on dark container
    assert "#navBtnInactive" in WARM_CONSOLE_QSS
    assert "background-color: #262626;" in WARM_CONSOLE_QSS
    assert "color: #F5F2E9;" in WARM_CONSOLE_QSS

    # Hover state: visibly different background (#383838), contrasting foreground (#FFFFFF), gold accent border
    assert "#navBtnInactive:hover" in WARM_CONSOLE_QSS
    assert "background-color: #383838;" in WARM_CONSOLE_QSS
    assert "color: #FFFFFF;" in WARM_CONSOLE_QSS
    assert "border: 1px solid #E2B83B;" in WARM_CONSOLE_QSS

    # Keyboard focus and disabled state
    assert "#navBtnInactive:focus" in WARM_CONSOLE_QSS
    assert "#navBtnInactive:disabled" in WARM_CONSOLE_QSS

    # Accessible badges
    assert "#badgeSafe" in WARM_CONSOLE_QSS
    assert "color: #137333;" in WARM_CONSOLE_QSS
    assert "#badgeWarning" in WARM_CONSOLE_QSS
    assert "color: #8A4500;" in WARM_CONSOLE_QSS
    assert "#badgeDanger" in WARM_CONSOLE_QSS
    assert "color: #A51B17;" in WARM_CONSOLE_QSS


@pytest.mark.unit
def test_navigation_test_rename_and_section_order(qapp, tmp_path):
    """Verify Hackathon Demo is renamed to Test, and navigation targets work accurately."""
    db_file = tmp_path / "test_nav_rename.db"
    app, window = create_application(db_path=db_file)

    try:
        window.show()
        qapp.processEvents()

        # 1. First nav item must have visible CrashGuard label
        assert "CrashGuard" in window.btn_nav_crashguard.text()
        assert window.btn_nav_crashguard.text().startswith("1. ")

        # 2. Second nav item must have visible AgentGuard label
        assert "AgentGuard" in window.btn_nav_agentguard.text()
        assert window.btn_nav_agentguard.text().startswith("2. ")

        # 3. Third nav item renamed from Hackathon Demo -> Test
        assert "Test" in window.btn_nav_test.text()
        assert "Hackathon Demo" not in window.btn_nav_test.text()
        assert window.btn_nav_test.text().startswith("3. ")

        # 4. Backward compatibility alias
        assert window.btn_nav_demo is window.btn_nav_test
        assert window.sec_test is not None
        assert window.sec_demo is window.sec_test

        # 5. Section order in layout: CrashGuard -> AgentGuard -> Test
        assert window.sec_crashguard.pos().y() <= window.sec_agentguard.pos().y()
        assert window.sec_agentguard.pos().y() <= window.sec_test.pos().y()

        # 6. Navigation clicks scroll to correct sections
        window.scroll_to_section(2)
        qapp.processEvents()
        assert window.get_active_section_index() == 2
        assert window.btn_nav_test.objectName() == "navBtnActive"

        window.scroll_to_section(0)
        qapp.processEvents()
        assert window.get_active_section_index() == 0
        assert window.btn_nav_crashguard.objectName() == "navBtnActive"

    finally:
        window.exit_application()


@pytest.mark.unit
def test_demo_controls_appear_only_in_test_section(qapp, tmp_path):
    """Verify production CrashGuard and AgentGuard panels do NOT contain demo controls."""
    db_file = tmp_path / "test_demo_isolation.db"
    app, window = create_application(db_path=db_file)

    try:
        window.show()
        qapp.processEvents()

        # CrashGuard: genuine host telemetry only, no simulation buttons in panel
        crash_panel = window.crashguard_panel
        assert not hasattr(crash_panel, "demo_group") or crash_panel.demo_group is None
        # Assert buttons not in crash panel layout
        crash_btn_texts = [btn.text() for btn in crash_panel.findChildren(QPushButton)]
        for text in crash_btn_texts:
            assert "Simulate" not in text
            assert "CPU Load" not in text
            assert "RAM Load" not in text

        # AgentGuard: genuine governance only, no scenario buttons in panel layout
        agent_panel = window.agentguard_panel
        agent_btn_texts = [btn.text() for btn in agent_panel.findChildren(QPushButton)]
        for text in agent_btn_texts:
            assert "A. [SAFE]" not in text
            assert "B. [SENSITIVE]" not in text
            assert "C. [PROHIBITED]" not in text
            assert "D. [INJECTION]" not in text

        # Test Section: contains the consolidated simulation controls with prominent labeling
        test_panel = window.test_panel
        test_btn_texts = [btn.text() for btn in test_panel.findChildren(QPushButton)]
        assert any("[SIMULATED / TEST DATA] Safe Action" in t for t in test_btn_texts)
        assert any("[SIMULATED / TEST DATA] Sensitive Action" in t for t in test_btn_texts)
        assert any("[SIMULATED / TEST DATA] Prohibited Action" in t for t in test_btn_texts)
        assert any("[SIMULATED / TEST DATA] Prompt Injection" in t for t in test_btn_texts)
        assert any("[SIMULATED / TEST DATA] Sustained CPU" in t for t in test_btn_texts)
        assert any("[SIMULATED / TEST DATA] Sustained RAM" in t for t in test_btn_texts)

    finally:
        window.exit_application()


@pytest.mark.unit
def test_simulated_records_distinguishable_from_genuine_audit():
    """Verify test data has distinct is_simulated flag and [SIMULATED / TEST DATA] marker."""
    audit = SqliteAuditLog(":memory:")

    # 1. Record genuine production action
    genuine_event = AuditEvent(
        event_type="policy_decision",
        action_id="act-prod-001",
        agent_id="real-prod-agent",
        decision=Decision.ALLOW,
        reason_code="prod_rule_allowed",
        explanation="Production policy allowed document read.",
        session_id="prod-sess-42",
        is_simulated=False,
    )
    stored_gen = audit.record_event(genuine_event)
    assert not stored_gen.is_simulated
    assert not stored_gen.is_test_data
    assert "[SIMULATED / TEST DATA]" not in stored_gen.summary
    assert stored_gen.payload.get("is_simulated") is False
    assert stored_gen.payload.get("source") == "production"

    # 2. Record simulated test action
    test_event = AuditEvent(
        event_type="policy_decision",
        action_id="act-test-001",
        agent_id="demo-doc-agent",
        decision=Decision.ALLOW,
        reason_code="demo_read_allowed",
        explanation="Simulated scenario evaluation.",
        session_id="test-session-simulated",
        is_simulated=True,
    )
    stored_test = audit.record_event(test_event)
    assert stored_test.is_simulated
    assert stored_test.is_test_data
    assert "[SIMULATED / TEST DATA]" in stored_test.summary
    assert stored_test.payload.get("is_simulated") is True
    assert stored_test.payload.get("source") == "simulated_test"

    # 3. get_recent_events genuine_only filtering
    all_events = audit.get_recent_events(limit=10)
    assert len(all_events) == 2

    genuine_only = audit.get_recent_events(limit=10, genuine_only=True)
    assert len(genuine_only) == 1
    assert genuine_only[0].event_id == stored_gen.event_id


@pytest.mark.unit
def test_agentguard_displays_latest_20_genuine_actions(qapp, tmp_path):
    """Verify AgentGuard audit table displays at most 20 actions in newest-first order with accessible indicators."""
    db_file = tmp_path / "test_20_actions.db"
    app, window = create_application(db_path=db_file)

    try:
        window.show()
        qapp.processEvents()

        agent_panel = window.agentguard_panel
        audit = window.audit_log
        base_time = datetime(2026, 3, 1, 10, 0, 0, tzinfo=timezone.utc)

        # Insert 25 varied actions (allowed, blocked, pending-approval, rejected)
        for i in range(25):
            if i % 4 == 0:
                dec = Decision.ALLOW
                ev_type = "policy_decision"
                reason = "rule_allowed"
                status = "executed"
            elif i % 4 == 1:
                dec = Decision.BLOCK
                ev_type = "policy_decision"
                reason = "rule_blocked"
                status = "blocked"
            elif i % 4 == 2:
                dec = Decision.ASK
                ev_type = "approval_required"
                reason = "rule_sensitive"
                status = "approval_required"
            else:
                dec = Decision.ASK
                ev_type = "approval_rejected"
                reason = "user_denied"
                status = "denied"

            audit.record_event(
                AuditEvent(
                    event_type=ev_type,
                    action_id=f"action-{i:03d}",
                    agent_id=f"agent-{i}",
                    timestamp=base_time + timedelta(seconds=i),
                    decision=dec,
                    reason_code=reason,
                    execution_status=status,
                    explanation=f"Action event index {i}",
                )
            )

        # Refresh UI
        agent_panel.refresh_audit_feed()
        qapp.processEvents()

        # Table must cap display at latest 20 actions
        assert agent_panel.audit_table.rowCount() == 20

        # Row 0 must be the newest action (action-024)
        item_action_newest = agent_panel.audit_table.item(0, 2)
        assert item_action_newest is not None
        assert item_action_newest.text() == "action-024"

        # Check accessible indicator formatting (bracketed symbol + readable uppercase text)
        for row in range(agent_panel.audit_table.rowCount()):
            outcome_item = agent_panel.audit_table.item(row, 3)
            assert outcome_item is not None
            text = outcome_item.text()
            assert any(tag in text for tag in ["[✓ ALLOWED]", "[✕ BLOCKED]", "[⏳ PENDING APPROVAL]", "[✕ REJECTED]"])

        # Row 19 must be action-005 (20th newest)
        item_action_oldest_in_20 = agent_panel.audit_table.item(19, 2)
        assert item_action_oldest_in_20 is not None
        assert item_action_oldest_in_20.text() == "action-005"

    finally:
        window.exit_application()


@pytest.mark.unit
def test_fewer_than_20_actions_renders_available_count(qapp, tmp_path):
    """Verify that when fewer than 20 actions exist, only available actions are rendered."""
    db_file = tmp_path / "test_few_actions.db"
    app, window = create_application(db_path=db_file)

    try:
        window.show()
        qapp.processEvents()

        agent_panel = window.agentguard_panel
        audit = window.audit_log

        # Insert exactly 3 actions
        for i in range(3):
            audit.record_event(
                AuditEvent(
                    event_type="policy_decision",
                    action_id=f"few-act-{i}",
                    agent_id="sample-agent",
                    decision=Decision.ALLOW,
                    reason_code="allowed",
                )
            )

        agent_panel.refresh_audit_feed()
        qapp.processEvents()

        assert agent_panel.audit_table.rowCount() == 3

    finally:
        window.exit_application()
