"""Time-limited, scoped approvals for AgentGuard."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from threading import RLock
from uuid import uuid4

from sentron.core.models import ActionRequest, utc_now


@dataclass(frozen=True, slots=True)
class ApprovalScope:
    agent_id: str
    tool_name: str
    operation: str
    target: str | None
    destination: str | None
    recipient: str | None
    purpose: str | None
    task_id: str | None
    data_classification: str | None
    risk_flags: tuple[str, ...]
    untrusted_context_refs: tuple[str, ...]
    session_id: str | None

    @classmethod
    def from_request(cls, request: ActionRequest) -> "ApprovalScope":
        return cls(
            agent_id=request.agent_id,
            tool_name=request.tool_name,
            operation=request.operation,
            target=request.target,
            destination=request.destination,
            recipient=request.recipient,
            purpose=request.purpose,
            task_id=request.task_id,
            data_classification=request.data_classification,
            risk_flags=request.risk_flags,
            untrusted_context_refs=request.untrusted_context_refs,
            session_id=request.session_id,
        )

    def matches(self, request: ActionRequest) -> bool:
        return self == self.from_request(request)


@dataclass(slots=True)
class ApprovalRecord:
    approval_id: str
    scope: ApprovalScope
    expires_at: datetime
    session_id: str | None
    remaining_uses: int


class ApprovalManager:
    """In-memory approval registry; persistence can be added via shared storage later."""

    def __init__(self) -> None:
        self._records: dict[str, ApprovalRecord] = {}
        self._lock = RLock()

    def grant(
        self,
        request: ActionRequest,
        *,
        ttl_seconds: int = 300,
        session_id: str | None = None,
        max_uses: int = 1,
        now: datetime | None = None,
    ) -> ApprovalRecord:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        if max_uses <= 0:
            raise ValueError("max_uses must be positive")
        issued_at = now or utc_now()
        if session_id is not None and session_id != request.session_id:
            raise ValueError("session_id must match the action request session")
        effective_session_id = session_id if session_id is not None else request.session_id
        if issued_at.tzinfo is None or issued_at.utcoffset() is None:
            raise ValueError("now must be timezone-aware")
        record = ApprovalRecord(
            approval_id=str(uuid4()),
            scope=ApprovalScope.from_request(request),
            expires_at=issued_at + timedelta(seconds=ttl_seconds),
            session_id=effective_session_id,
            remaining_uses=max_uses,
        )
        with self._lock:
            self._records[record.approval_id] = record
        return record

    def validate_and_consume(
        self,
        approval_id: str,
        request: ActionRequest,
        *,
        session_id: str | None = None,
        now: datetime | None = None,
    ) -> tuple[bool, str]:
        current_time = now or utc_now()
        if session_id is not None and session_id != request.session_id:
            return False, "approval_session_mismatch"
        effective_session_id = session_id if session_id is not None else request.session_id
        if current_time.tzinfo is None or current_time.utcoffset() is None:
            raise ValueError("now must be timezone-aware")
        with self._lock:
            record = self._records.get(approval_id)
            if record is None:
                return False, "approval_not_found"
            if current_time >= record.expires_at:
                del self._records[approval_id]
                return False, "approval_expired"
            if record.session_id is not None and record.session_id != effective_session_id:
                return False, "approval_session_mismatch"
            if not record.scope.matches(request):
                return False, "approval_scope_mismatch"
            if record.remaining_uses <= 0:
                del self._records[approval_id]
                return False, "approval_already_consumed"
            record.remaining_uses -= 1
            if record.remaining_uses == 0:
                del self._records[approval_id]
            return True, "approval_valid"
