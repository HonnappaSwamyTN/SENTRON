"""Controlled execution boundary and privacy-conscious audit logging."""
from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, Any

from sentron.agentguard.approval import ApprovalManager
from sentron.agentguard.policy import PolicyEngine
from sentron.core.models import ActionRequest, AuditEvent, Decision, ExecutionResult, utc_now


class AuditSink(Protocol):
    def record_event(self, event: AuditEvent) -> None: ...


class InMemoryAuditLog:
    """Simple audit sink for development and tests; not persistent storage."""

    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    def record_event(self, event: AuditEvent) -> None:
        self.events.append(event)


class ControlledExecutor:
    """Execute only after policy ALLOW or a matching, valid approval.

    The injected handler defines the actual action. V1 should use a safe mock
    handler; this class does not execute shell commands or perform OS actions.
    """

    def __init__(
        self,
        policy_engine: PolicyEngine,
        approval_manager: ApprovalManager,
        action_handler: Callable[[ActionRequest], Any],
        audit_sink: AuditSink,
    ) -> None:
        self._policy = policy_engine
        self._approvals = approval_manager
        self._handler = action_handler
        self._audit = audit_sink

    def execute(
        self,
        request: ActionRequest,
        *,
        approval_id: str | None = None,
        session_id: str | None = None,
    ) -> ExecutionResult:
        req_session_id = getattr(request, "session_id", None) if request is not None else None
        req_action_id = getattr(request, "action_id", "unknown_action") if request is not None else "unknown_action"
        req_agent_id = getattr(request, "agent_id", "unknown_agent") if request is not None else "unknown_agent"

        policy_result = self._policy.evaluate(request)
        if policy_result is None or policy_result.decision not in (Decision.ALLOW, Decision.ASK, Decision.BLOCK):
            unknown_dec = getattr(policy_result, "decision", None)
            self._audit.record_event(AuditEvent(
                event_type="policy_decision",
                action_id=req_action_id,
                agent_id=req_agent_id,
                timestamp=utc_now(),
                decision=Decision.BLOCK,
                reason_code="unknown_policy_decision",
                explanation=f"Execution blocked: unrecognized policy decision {unknown_dec!r}.",
                session_id=req_session_id,
            ))
            return ExecutionResult(
                status="blocked",
                decision=Decision.BLOCK,
                reason_code="unknown_policy_decision",
                explanation=f"Execution blocked: unrecognized policy decision {unknown_dec!r}.",
                action_id=req_action_id,
            )

        self._audit.record_event(AuditEvent(
            event_type="policy_decision",
            action_id=req_action_id,
            agent_id=req_agent_id,
            timestamp=utc_now(),
            decision=policy_result.decision,
            reason_code=policy_result.reason_code,
            explanation=policy_result.explanation,
            session_id=req_session_id,
        ))

        if policy_result.decision == Decision.BLOCK:
            return ExecutionResult(
                status="blocked",
                decision=Decision.BLOCK,
                reason_code=policy_result.reason_code,
                explanation=policy_result.explanation,
                action_id=req_action_id,
            )

        used_approval_id: str | None = None
        if policy_result.decision == Decision.ASK:
            if approval_id is None:
                self._audit.record_event(AuditEvent(
                    event_type="approval_required",
                    action_id=req_action_id,
                    agent_id=req_agent_id,
                    decision=Decision.ASK,
                    reason_code=policy_result.reason_code,
                    explanation="Execution withheld until the user approves this scoped action.",
                    session_id=req_session_id,
                ))
                return ExecutionResult(
                    status="approval_required",
                    decision=Decision.ASK,
                    reason_code=policy_result.reason_code,
                    explanation="Execution withheld until the user approves this scoped action.",
                    action_id=req_action_id,
                )

            effective_session_id = session_id if session_id is not None else req_session_id
            if session_id is not None and session_id != req_session_id:
                valid, approval_reason = False, "approval_session_mismatch"
            else:
                valid, approval_reason = self._approvals.validate_and_consume(
                    approval_id, request, session_id=effective_session_id
                )
            if not valid:
                self._audit.record_event(AuditEvent(
                    event_type="approval_rejected",
                    action_id=req_action_id,
                    agent_id=req_agent_id,
                    decision=Decision.ASK,
                    reason_code=approval_reason,
                    explanation="The supplied approval is invalid, expired, consumed, or outside its scope.",
                    approval_id=approval_id,
                    session_id=req_session_id,
                ))
                return ExecutionResult(
                    status="approval_required",
                    decision=Decision.ASK,
                    reason_code=approval_reason,
                    explanation="Approval did not authorize this exact action; obtain fresh approval.",
                    action_id=req_action_id,
                    approval_id=approval_id,
                )
            used_approval_id = approval_id
            self._audit.record_event(AuditEvent(
                event_type="approval_accepted",
                action_id=req_action_id,
                agent_id=req_agent_id,
                decision=Decision.ASK,
                reason_code="approval_valid",
                explanation="A matching scoped approval was accepted.",
                approval_id=approval_id,
                session_id=req_session_id,
            ))

        # Absolute fail-closed boundary: only ALLOW or validly approved ASK may reach handler
        if policy_result.decision != Decision.ALLOW and used_approval_id is None:
            return ExecutionResult(
                status="blocked",
                decision=Decision.BLOCK,
                reason_code="unauthorized_execution",
                explanation="Execution blocked: action has not received authorized approval.",
                action_id=req_action_id,
            )

        try:
            output = self._handler(request)
        except Exception as exc:  # Avoid logging exception messages that may contain secrets.
            reason_code = f"execution_error_{type(exc).__name__}"
            self._audit.record_event(AuditEvent(
                event_type="execution_failed",
                action_id=req_action_id,
                agent_id=req_agent_id,
                decision=policy_result.decision,
                reason_code=reason_code,
                execution_status="failed",
                approval_id=used_approval_id,
                session_id=req_session_id,
            ))
            return ExecutionResult(
                status="failed",
                decision=policy_result.decision,
                reason_code="execution_failed",
                explanation="The action handler failed; details were not written to the audit log.",
                action_id=req_action_id,
                approval_id=used_approval_id,
            )

        self._audit.record_event(AuditEvent(
            event_type="execution_succeeded",
            action_id=req_action_id,
            agent_id=req_agent_id,
            decision=policy_result.decision,
            reason_code="execution_succeeded",
            execution_status="succeeded",
            approval_id=used_approval_id,
            session_id=req_session_id,
        ))
        return ExecutionResult(
            status="executed",
            decision=policy_result.decision,
            reason_code="execution_succeeded",
            explanation="The action handler completed after authorization.",
            action_id=req_action_id,
            approval_id=used_approval_id,
            output=output,
        )
