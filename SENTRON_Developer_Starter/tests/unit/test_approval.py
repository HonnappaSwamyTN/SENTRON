from datetime import datetime, timedelta, timezone

import pytest

from sentron.agentguard.approval import ApprovalManager
from sentron.core.models import ActionRequest


def request(**overrides):
    values = dict(
        agent_id="agent-a", tool_name="mock_mail_tool", operation="send_message",
        target="draft-1", recipient="alice@example.test", destination="mock://mailbox",
        purpose="send requested test message", task_id="task-7", session_id="session-1",
    )
    values.update(overrides)
    return ActionRequest(**values)


def test_approval_matches_exact_scope_and_is_single_use_by_default():
    manager = ApprovalManager()
    action = request()
    approval = manager.grant(action, session_id="session-1")
    assert manager.validate_and_consume(approval.approval_id, action, session_id="session-1")[0]
    valid, reason = manager.validate_and_consume(approval.approval_id, action, session_id="session-1")
    assert not valid
    assert reason == "approval_not_found"


def test_changed_destination_requires_new_approval():
    manager = ApprovalManager()
    action = request()
    approval = manager.grant(action, session_id="session-1")
    changed = request(destination="mock://different-mailbox")
    valid, reason = manager.validate_and_consume(approval.approval_id, changed, session_id="session-1")
    assert not valid
    assert reason == "approval_scope_mismatch"


def test_approval_is_bound_to_session_when_requested():
    manager = ApprovalManager()
    action = request()
    approval = manager.grant(action, session_id="session-1")
    valid, reason = manager.validate_and_consume(approval.approval_id, action, session_id="session-2")
    assert not valid
    assert reason == "approval_session_mismatch"


def test_expired_approval_is_rejected():
    manager = ApprovalManager()
    action = request()
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    approval = manager.grant(action, ttl_seconds=5, now=now)
    valid, reason = manager.validate_and_consume(
        approval.approval_id, action, session_id="session-1", now=now + timedelta(seconds=6)
    )
    assert not valid
    assert reason == "approval_expired"


def test_changed_untrusted_context_requires_new_approval():
    manager = ApprovalManager()
    action = request(untrusted_context_refs=("context-a",))
    approval = manager.grant(action)
    changed = request(untrusted_context_refs=("context-b",))
    valid, reason = manager.validate_and_consume(approval.approval_id, changed)
    assert not valid
    assert reason == "approval_scope_mismatch"


def test_request_session_is_used_when_granting_and_validating():
    manager = ApprovalManager()
    action = request(session_id="session-1")
    approval = manager.grant(action)
    assert manager.validate_and_consume(approval.approval_id, action, session_id="session-1")[0]


def test_supplied_session_mismatch_rejected_when_request_session_is_none():
    manager = ApprovalManager()
    action = request(session_id=None)
    approval = manager.grant(action)
    valid, reason = manager.validate_and_consume(approval.approval_id, action, session_id="session-1")
    assert not valid
    assert reason == "approval_session_mismatch"


def test_grant_rejects_session_mismatch_when_request_session_is_none():
    manager = ApprovalManager()
    action = request(session_id=None)
    with pytest.raises(ValueError, match="session_id must match the action request session"):
        manager.grant(action, session_id="session-1")


