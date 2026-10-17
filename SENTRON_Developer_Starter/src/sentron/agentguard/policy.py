"""Deterministic, fail-closed policy evaluation for supported agent actions."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from sentron.core.models import ActionRequest, Decision, PolicyResult


@dataclass(frozen=True, slots=True)
class PolicyRule:
    """A rule matches every non-None selector; None means any value.

    ALLOW rules must be narrowly scoped to an agent, tool, operation, and an
    action target or destination. This prevents accidental wildcard grants.
    """

    decision: Decision
    agent_id: str | None = None
    operation: str | None = None
    tool_name: str | None = None
    target: str | None = None
    destination: str | None = None
    reason_code: str = "configured_rule"
    explanation: str = "Matched a configured policy rule."

    TARGET_REQUIRED_OPERATIONS = frozenset({
        "read_file", "write_file", "create_file", "modify_file", "delete_file", "open_file",
    })
    DESTINATION_REQUIRED_OPERATIONS = frozenset({
        "send_message", "send_email", "upload_file", "share_file", "post_message",
    })

    def __post_init__(self) -> None:
        if self.decision is not Decision.ALLOW:
            return

        required_selectors = ("agent_id", "tool_name", "operation")
        missing = [
            name for name in required_selectors
            if not isinstance(getattr(self, name), str) or not getattr(self, name).strip()
        ]
        if missing:
            raise ValueError(
                "ALLOW rules must explicitly specify agent_id, tool_name, and operation; "
                f"missing: {', '.join(missing)}"
            )

        operation = self.operation.strip().lower()
        if operation in self.TARGET_REQUIRED_OPERATIONS and not self.target:
            raise ValueError(f"ALLOW rules for {operation} must specify a target")
        if operation in self.DESTINATION_REQUIRED_OPERATIONS and not self.destination:
            raise ValueError(f"ALLOW rules for {operation} must specify a destination")
        if operation not in self.TARGET_REQUIRED_OPERATIONS | self.DESTINATION_REQUIRED_OPERATIONS:
            if not self.target and not self.destination:
                raise ValueError("ALLOW rules must specify a target or destination")

    def matches(self, request: ActionRequest) -> bool:
        selectors = ("agent_id", "operation", "tool_name", "target", "destination")
        return all(
            getattr(self, name) is None or getattr(self, name) == getattr(request, name)
            for name in selectors
        )


class PolicyEngine:
    """Evaluate requests without relying on an LLM or probabilistic model.

    Default behavior is ASK. Only an explicit matching ALLOW rule can allow an
    action, and risk flags or sensitive data classifications override that allow.
    """

    SENSITIVE_CLASSIFICATIONS = {
        "personal", "pii", "confidential", "secret", "credential", "restricted"
    }
    ALWAYS_BLOCK_OPERATIONS = {
        "disable_security", "steal_credentials", "exfiltrate_data", "format_disk"
    }
    APPROVAL_SCOPE_FIELDS = (
        "agent_id", "tool_name", "operation", "target", "destination",
        "recipient", "purpose", "task_id", "data_classification",
        "risk_flags", "untrusted_context_refs", "session_id",
    )

    def __init__(self, rules: Iterable[PolicyRule] = ()) -> None:
        self._rules = tuple(rules)

    def evaluate(self, request: ActionRequest) -> PolicyResult:
        operation = request.operation.strip().lower()
        if operation in self.ALWAYS_BLOCK_OPERATIONS:
            return PolicyResult(
                decision=Decision.BLOCK,
                reason_code="prohibited_operation",
                explanation="This operation is prohibited by the V1 safety policy.",
                risk_flags=request.risk_flags,
            )

        matching = [rule for rule in self._rules if rule.matches(request)]
        # Most restrictive matching rule wins: BLOCK > ASK > ALLOW.
        for decision in (Decision.BLOCK, Decision.ASK):
            for rule in matching:
                if rule.decision == decision:
                    return PolicyResult(
                        decision=decision,
                        reason_code=rule.reason_code,
                        explanation=rule.explanation,
                        required_approval_scope=self.APPROVAL_SCOPE_FIELDS if decision == Decision.ASK else (),
                        risk_flags=request.risk_flags,
                    )

        if request.risk_flags:
            return PolicyResult(
                decision=Decision.ASK,
                reason_code="risk_flags_present",
                explanation="The request has suspicious-input risk flags and needs user review.",
                required_approval_scope=self.APPROVAL_SCOPE_FIELDS,
                risk_flags=request.risk_flags,
            )

        classification = (request.data_classification or "").strip().lower()
        if classification in self.SENSITIVE_CLASSIFICATIONS:
            return PolicyResult(
                decision=Decision.ASK,
                reason_code="sensitive_data_requires_review",
                explanation="The request involves sensitive data and needs explicit review.",
                required_approval_scope=self.APPROVAL_SCOPE_FIELDS,
            )

        for rule in matching:
            if rule.decision == Decision.ALLOW:
                return PolicyResult(
                    decision=Decision.ALLOW,
                    reason_code=rule.reason_code,
                    explanation=rule.explanation,
                )

        return PolicyResult(
            decision=Decision.ASK,
            reason_code="no_matching_allow_rule",
            explanation="No explicit allow rule matched this request; user approval is required.",
            required_approval_scope=self.APPROVAL_SCOPE_FIELDS,
            risk_flags=request.risk_flags,
        )
