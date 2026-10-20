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
        if not isinstance(self.decision, Decision):
            try:
                object.__setattr__(self, "decision", Decision(self.decision))
            except Exception:
                raise ValueError(f"Invalid policy rule decision: {self.decision!r}")

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

        # Forbid wildcards or overly broad catch-all values in ALLOW rules
        broad_terms = {"*", "?", "all", "any"}
        for name in ("agent_id", "tool_name", "operation", "target", "destination"):
            val = getattr(self, name)
            if val is not None and isinstance(val, str):
                cleaned = val.strip().lower()
                if cleaned in broad_terms or "*" in cleaned or "?" in cleaned:
                    raise ValueError(
                        f"ALLOW rules cannot contain wildcards or overly broad selector for '{name}': {val!r}"
                    )

        operation = self.operation.strip().lower()
        if operation in self.TARGET_REQUIRED_OPERATIONS and (not self.target or not self.target.strip()):
            raise ValueError(f"ALLOW rules for {operation} must specify a target")
        if operation in self.DESTINATION_REQUIRED_OPERATIONS and (not self.destination or not self.destination.strip()):
            raise ValueError(f"ALLOW rules for {operation} must specify a destination")
        if operation not in self.TARGET_REQUIRED_OPERATIONS | self.DESTINATION_REQUIRED_OPERATIONS:
            if (not self.target or not self.target.strip()) and (not self.destination or not self.destination.strip()):
                raise ValueError("ALLOW rules must specify a target or destination")

    def matches(self, request: ActionRequest) -> bool:
        req_agent = getattr(request, "agent_id", None)
        req_op = getattr(request, "operation", None)
        req_tool = getattr(request, "tool_name", None)
        req_target = getattr(request, "target", None)
        req_dest = getattr(request, "destination", None)

        if self.decision is Decision.ALLOW:
            # ALLOW rules are strictly agent-scoped and require exact agent_id match
            if not self.agent_id or self.agent_id != req_agent:
                return False
            if (
                self.operation is not None
                and (not isinstance(req_op, str) or self.operation.strip().lower() != req_op.strip().lower())
            ):
                return False
            if (
                self.tool_name is not None
                and (not isinstance(req_tool, str) or self.tool_name.strip().lower() != req_tool.strip().lower())
            ):
                return False
            if self.target is not None and self.target != req_target:
                return False
            if self.destination is not None and self.destination != req_dest:
                return False
            return True

        # Non-ALLOW rules (BLOCK / ASK)
        if self.agent_id is not None and self.agent_id != req_agent:
            return False
        if self.operation is not None:
            if not isinstance(req_op, str) or self.operation.strip().lower() != req_op.strip().lower():
                return False
        if self.tool_name is not None:
            if not isinstance(req_tool, str) or self.tool_name.strip().lower() != req_tool.strip().lower():
                return False
        if self.target is not None and self.target != req_target:
            return False
        if self.destination is not None and self.destination != req_dest:
            return False
        return True


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
        if request is None:
            return PolicyResult(
                decision=Decision.BLOCK,
                reason_code="malformed_request",
                explanation="Action request is missing or null.",
            )

        agent_id = getattr(request, "agent_id", None)
        if (
            not isinstance(agent_id, str)
            or not agent_id.strip()
            or agent_id in {"*", "?", "all", "any", "unknown", "none"}
            or "*" in agent_id
            or "?" in agent_id
        ):
            return PolicyResult(
                decision=Decision.BLOCK,
                reason_code="invalid_agent_identity",
                explanation="Action request lacks a valid, explicit agent identity.",
                risk_flags=getattr(request, "risk_flags", ()) or (),
            )

        tool_name = getattr(request, "tool_name", None)
        operation = getattr(request, "operation", None)
        if (
            not isinstance(tool_name, str)
            or not tool_name.strip()
            or not isinstance(operation, str)
            or not operation.strip()
            or "*" in tool_name
            or "?" in tool_name
            or "*" in operation
            or "?" in operation
        ):
            return PolicyResult(
                decision=Decision.BLOCK,
                reason_code="malformed_request",
                explanation="Action request lacks valid tool or operation name.",
                risk_flags=getattr(request, "risk_flags", ()) or (),
            )

        operation_clean = operation.strip().lower()
        if operation_clean in self.ALWAYS_BLOCK_OPERATIONS:
            return PolicyResult(
                decision=Decision.BLOCK,
                reason_code="prohibited_operation",
                explanation="This operation is prohibited by the V1 safety policy.",
                risk_flags=getattr(request, "risk_flags", ()),
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
                        risk_flags=getattr(request, "risk_flags", ()),
                    )

        if getattr(request, "risk_flags", ()):
            return PolicyResult(
                decision=Decision.ASK,
                reason_code="risk_flags_present",
                explanation="The request has suspicious-input risk flags and needs user review.",
                required_approval_scope=self.APPROVAL_SCOPE_FIELDS,
                risk_flags=request.risk_flags,
            )

        classification = (getattr(request, "data_classification", None) or "").strip().lower()
        if classification in self.SENSITIVE_CLASSIFICATIONS:
            return PolicyResult(
                decision=Decision.ASK,
                reason_code="sensitive_data_requires_review",
                explanation="The request involves sensitive data and needs explicit review.",
                required_approval_scope=self.APPROVAL_SCOPE_FIELDS,
            )

        for rule in matching:
            if rule.decision == Decision.ALLOW and rule.agent_id == request.agent_id:
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
            risk_flags=getattr(request, "risk_flags", ()),
        )
