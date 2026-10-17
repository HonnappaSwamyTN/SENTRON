from datetime import datetime, timezone, timedelta
import pytest

from sentron.agentguard.approval import ApprovalManager
from sentron.agentguard.audit import SqliteAuditLog, AuditStorageError
from sentron.agentguard.executor import ControlledExecutor
from sentron.agentguard.policy import PolicyEngine, PolicyRule
from sentron.core.models import ActionRequest, AuditEvent, Decision


def test_event_persistence_and_retrieval():
    audit = SqliteAuditLog(":memory:")
    now = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    event = AuditEvent(
        event_type="policy_decision",
        action_id="act-1",
        agent_id="agent-alpha",
        timestamp=now,
        decision=Decision.ALLOW,
        reason_code="safe_mock_read",
        explanation="Read allowed by policy.",
    )
    stored = audit.record_event(event)
    assert stored.subsystem == "AgentGuard"
    assert stored.event_type == "policy_decision"
    assert stored.severity == "info"
    assert not stored.redacted

    recent = audit.get_recent_events(limit=5)
    assert len(recent) == 1
    assert recent[0].event_id == stored.event_id
    assert recent[0].timestamp == now.timestamp()
    assert recent[0].payload["action_id"] == "act-1"
    assert recent[0].payload["agent_id"] == "agent-alpha"
    assert recent[0].payload["decision"] == "ALLOW"
    assert recent[0].payload["reason_code"] == "safe_mock_read"


def test_recent_event_ordering_and_limit_to_five():
    audit = SqliteAuditLog(":memory:")
    base = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    for i in range(10):
        audit.record_event(
            AuditEvent(
                event_type="policy_decision",
                action_id=f"act-{i}",
                agent_id="agent-alpha",
                timestamp=base + timedelta(seconds=i),
                decision=Decision.ALLOW,
                reason_code=f"rule_{i}",
            )
        )

    recent = audit.get_recent_events(limit=5, subsystem="AgentGuard")
    assert len(recent) == 5
    action_ids = [e.payload["action_id"] for e in recent]
    assert action_ids == ["act-9", "act-8", "act-7", "act-6", "act-5"]
    timestamps = [e.timestamp for e in recent]
    assert timestamps == sorted(timestamps, reverse=True)


def test_keyword_search_across_fields():
    audit = SqliteAuditLog(":memory:")
    audit.record_event(
        AuditEvent(
            event_type="policy_decision",
            action_id="act-blocked",
            agent_id="agent-bad",
            decision=Decision.BLOCK,
            reason_code="blocked_prohibited_operation",
            explanation="Prohibited operation disable_security.",
        )
    )
    audit.record_event(
        AuditEvent(
            event_type="policy_decision",
            action_id="act-allowed",
            agent_id="agent-good",
            decision=Decision.ALLOW,
            reason_code="safe_read",
            explanation="Safe read permitted.",
        )
    )
    audit.record_event(
        AuditEvent(
            event_type="approval_rejected",
            action_id="act-rejected",
            agent_id="agent-bad",
            decision=Decision.ASK,
            reason_code="approval_scope_mismatch",
            explanation="Supplied approval did not match target.",
        )
    )

    # Search for "blocked"
    blocked_results = audit.search_events(query="blocked")
    assert len(blocked_results) == 1
    assert blocked_results[0].payload["action_id"] == "act-blocked"
    assert blocked_results[0].severity == "critical"

    # Search by agent_id
    agent_bad_results = audit.search_events(agent_id="agent-bad")
    assert len(agent_bad_results) == 2
    assert {r.payload["action_id"] for r in agent_bad_results} == {"act-blocked", "act-rejected"}

    # Search by severity
    critical_results = audit.search_events(severity="critical")
    assert len(critical_results) == 1
    assert critical_results[0].payload["action_id"] == "act-blocked"


def test_sensitive_data_redaction():
    audit = SqliteAuditLog(":memory:")
    event = AuditEvent(
        event_type="policy_decision",
        action_id="act-secret",
        agent_id="agent-1",
        decision=Decision.ASK,
        reason_code="secret_detected",
        explanation="Attempted to use key sk-1234567890abcdef1234567890 with password: MySecretPassword123!",
    )
    stored = audit.record_event(event)
    assert stored.redacted is True

    recent = audit.get_recent_events(limit=1)
    assert len(recent) == 1
    record = recent[0]
    assert record.redacted is True
    assert "sk-1234567890abcdef1234567890" not in record.summary
    assert "sk-1234567890abcdef1234567890" not in record.payload_json
    assert "MySecretPassword123!" not in record.summary
    assert "MySecretPassword123!" not in record.payload_json
    assert "[REDACTED_API_KEY]" in record.payload_json
    assert "[REDACTED_SECRET]" in record.payload_json


def test_storage_failure_behavior():
    audit = SqliteAuditLog(":memory:")
    audit.close()
    event = AuditEvent(
        event_type="policy_decision",
        action_id="act-fail",
        agent_id="agent-1",
        decision=Decision.ALLOW,
    )
    with pytest.raises(AuditStorageError, match="Failed to persist audit event"):
        audit.record_event(event)

    with pytest.raises(AuditStorageError, match="Failed to fetch recent audit events"):
        audit.get_recent_events()


def test_compatibility_with_controlled_executor():
    audit = SqliteAuditLog(":memory:")
    rule = PolicyRule(
        decision=Decision.ALLOW,
        agent_id="agent-a",
        tool_name="mock_tool",
        operation="read_file",
        target="demo.txt",
    )
    policy = PolicyEngine([rule])
    approvals = ApprovalManager()
    calls = []
    executor = ControlledExecutor(
        policy_engine=policy,
        approval_manager=approvals,
        action_handler=lambda action: calls.append(action.action_id) or {"data": "mock_content"},
        audit_sink=audit,
    )

    request = ActionRequest(
        agent_id="agent-a",
        tool_name="mock_tool",
        operation="read_file",
        target="demo.txt",
    )
    result = executor.execute(request)
    assert result.status == "executed"
    assert calls == [request.action_id]

    events = audit.get_recent_events(limit=5)
    assert len(events) == 2
    event_types = [e.event_type for e in events]
    assert event_types == ["execution_succeeded", "policy_decision"]
    assert all(e.subsystem == "AgentGuard" for e in events)
    assert all(e.payload["action_id"] == request.action_id for e in events)
