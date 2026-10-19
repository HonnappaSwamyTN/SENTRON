"""
Integration tests for Security Audit History & Search (AgentGuard / Core).
Governing Criteria: AC-08
"""
import time
import pytest
from sentron.agentguard.audit import SqliteAuditLog
from sentron.core.models import AuditEvent, Decision, utc_now


@pytest.mark.integration
def test_recent_security_events_displayed_and_searchable():
    """
    AC-08: Recent security events are displayed (latest 5) and older events can be searched.
    """
    audit = SqliteAuditLog(db_path=":memory:")

    # Insert 10 audit records with incremental timestamps
    for i in range(10):
        decision = Decision.BLOCK if i == 7 else Decision.ALLOW
        reason = "prohibited_action" if i == 7 else "normal_allow"
        audit.record_event(
            AuditEvent(
                event_type="policy_decision",
                action_id=f"action-{i}",
                agent_id=f"agent-{i % 3}",
                decision=decision,
                reason_code=reason,
                explanation=f"Evaluation record {i}",
            )
        )
        time.sleep(0.005)

    # 1. get_recent_events returns latest 5
    recent = audit.get_recent_events(limit=5, subsystem="AgentGuard")
    assert len(recent) == 5
    # Newest record should be action-9
    assert "action-9" in recent[0].summary or recent[0].payload.get("action_id") == "action-9"

    # 2. search_events retrieves matching historical events
    blocked_events = audit.search_events(query="prohibited_action", subsystem="AgentGuard")
    assert len(blocked_events) == 1
    assert blocked_events[0].payload.get("action_id") == "action-7"
