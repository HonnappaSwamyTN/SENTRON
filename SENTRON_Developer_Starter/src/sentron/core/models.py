"""Small shared contracts used by SENTRON modules.

Keep these models independent of UI, database, and Windows-specific code.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


def utc_now() -> datetime:
    """Return an aware UTC timestamp."""
    return datetime.now(timezone.utc)


class Decision(str, Enum):
    ALLOW = "ALLOW"
    ASK = "ASK"
    BLOCK = "BLOCK"


@dataclass(frozen=True, slots=True)
class ActionRequest:
    """A normalized request for an action an agent wants SENTRON to perform."""

    agent_id: str
    tool_name: str
    operation: str
    action_id: str = field(default_factory=lambda: str(uuid4()))
    task_id: str | None = None
    target: str | None = None
    destination: str | None = None
    recipient: str | None = None
    purpose: str | None = None
    data_classification: str | None = None
    risk_flags: tuple[str, ...] = ()
    untrusted_context_refs: tuple[str, ...] = ()
    session_id: str | None = None
    timestamp: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        for field_name in ("agent_id", "tool_name", "operation"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty string")
        if self.timestamp.tzinfo is None or self.timestamp.utcoffset() is None:
            raise ValueError("timestamp must be timezone-aware")
        object.__setattr__(self, "risk_flags", tuple(self.risk_flags))
        object.__setattr__(self, "untrusted_context_refs", tuple(self.untrusted_context_refs))


@dataclass(frozen=True, slots=True)
class PolicyResult:
    decision: Decision
    reason_code: str
    explanation: str
    required_approval_scope: tuple[str, ...] = ()
    event_id: str = field(default_factory=lambda: str(uuid4()))
    risk_flags: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class AuditEvent:
    """Privacy-conscious event record. Never store raw prompt/secret contents here."""

    event_type: str
    action_id: str
    agent_id: str
    timestamp: datetime = field(default_factory=utc_now)
    decision: Decision | None = None
    reason_code: str | None = None
    explanation: str | None = None
    execution_status: str | None = None
    approval_id: str | None = None


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    status: str
    decision: Decision
    reason_code: str
    explanation: str
    action_id: str
    approval_id: str | None = None
    output: Any = None


@dataclass(frozen=True, slots=True)
class RiskSignal:
    finding_type: str
    evidence_snippet: str
    risk_level: str  # low, medium, high, critical
    details: str


@dataclass(frozen=True, slots=True)
class SecretFinding:
    category: str  # e.g. "API_KEY", "PASSWORD", "BEARER_TOKEN", "EMAIL"
    start: int
    end: int
    length: int
    preview: str  # Masked preview only (e.g., "sk-****", "****"), NEVER the raw secret
    details: str

    @property
    def matched_snippet(self) -> str:
        return self.preview

    @property
    def redacted_replacement(self) -> str:
        return f"[REDACTED_{self.category}]"


@dataclass(frozen=True, slots=True)
class ProcessSummary:
    pid: int
    name: str
    cpu_percent: float
    memory_mb: float


@dataclass(frozen=True, slots=True)
class SystemSnapshot:
    timestamp: float
    cpu_percent: float
    memory_percent: float
    memory_available_bytes: int
    disk_free_bytes: int
    disk_busy_percent: float | None = None
    top_processes: tuple[ProcessSummary, ...] = ()
    unavailable_metrics: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "top_processes", tuple(self.top_processes))
        object.__setattr__(self, "unavailable_metrics", tuple(self.unavailable_metrics))


@dataclass(frozen=True, slots=True)
class RiskAlert:
    alert_id: str
    metric_name: str
    severity: str  # warning, critical
    observed_value: float
    threshold_value: float
    duration_seconds: float
    cooldown_until: float
    timestamp: float
    is_simulated: bool = False


@dataclass(frozen=True, slots=True)
class WindowsEvidence:
    event_id: int
    log_channel: str
    source: str
    event_time: str
    description: str
    raw_data: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class RecoveryRecommendation:
    recommendation_id: str
    severity: str
    title: str
    suggested_action: str
    confirmed_observations: tuple[str, ...] = ()
    suspected_causes: tuple[str, ...] = ()
    is_automated: bool = False  # Always False in V1

    def __post_init__(self) -> None:
        object.__setattr__(self, "confirmed_observations", tuple(self.confirmed_observations))
        object.__setattr__(self, "suspected_causes", tuple(self.suspected_causes))


@dataclass(frozen=True, slots=True)
class UnifiedEvent:
    event_id: str
    timestamp: float
    subsystem: str  # AgentGuard, CrashGuard, Core
    event_type: str
    severity: str  # info, warning, critical
    summary: str
    payload_json: str
    redacted: bool = False

