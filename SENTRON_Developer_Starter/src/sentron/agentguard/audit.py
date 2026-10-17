"""Persistent SQLite security audit logging for AgentGuard (AC-08).

Stores privacy-conscious, redacted audit events in a local SQLite database
conforming to the frozen architecture schema.
"""
from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from threading import RLock
from uuid import uuid4

from sentron.core.models import AuditEvent, Decision


class AuditStorageError(RuntimeError):
    """Raised when an audit event cannot be persisted or retrieved."""


@dataclass(frozen=True, slots=True)
class StoredAuditEvent:
    """A persisted audit record retrieved from the SQLite event store."""

    event_id: str
    timestamp: float
    subsystem: str
    event_type: str
    severity: str
    summary: str
    payload_json: str
    redacted: bool = False

    @property
    def payload(self) -> dict:
        try:
            return json.loads(self.payload_json)
        except json.JSONDecodeError:
            return {}


# Regex patterns for detecting and sanitizing common secret tokens in audit text
_SECRET_PATTERNS = (
    # OpenAI / generic LLM API keys
    (re.compile(r"\bsk-[a-zA-Z0-9_\-]{16,}\b"), "[REDACTED_API_KEY]"),
    # GitHub personal access tokens
    (re.compile(r"\bghp_[a-zA-Z0-9]{20,}\b"), "[REDACTED_TOKEN]"),
    # AWS access key IDs
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "[REDACTED_AWS_KEY]"),
    # Authorization Bearer tokens
    (re.compile(r"(?i)\b(bearer\s+)[a-zA-Z0-9_\-\.]{16,}\b"), r"\1[REDACTED_TOKEN]"),
    # Password/token key-value assignments
    (re.compile(r"(?i)\b(password|passwd|secret|token|api_key)\s*([:=])\s*([^\s,;\"']+)"), r"\1\2[REDACTED_SECRET]"),
    # Quoted JSON password/token assignments
    (re.compile(r"(?i)([\"'](?:password|passwd|secret|token|api_key)[\"']\s*:\s*[\"'])([^\"']+)([\"'])"), r"\1[REDACTED_SECRET]\3"),
)


def redact_sensitive_text(text: str | None) -> tuple[str | None, bool]:
    """Redact recognized secret patterns from text.

    Returns:
        (sanitized_text, was_redacted)
    """
    if text is None:
        return None, False

    sanitized = text
    redacted = False
    for pattern, replacement in _SECRET_PATTERNS:
        new_text, count = pattern.subn(replacement, sanitized)
        if count > 0:
            sanitized = new_text
            redacted = True

    return sanitized, redacted


def _determine_severity(event: AuditEvent) -> str:
    """Map an audit event to a standard severity level ('info', 'warning', 'critical')."""
    if event.decision == Decision.BLOCK:
        return "critical"
    if event.event_type == "execution_failed":
        return "critical"
    if event.event_type in ("approval_rejected", "approval_required"):
        return "warning"
    return "info"


class SqliteAuditLog:
    """Local SQLite-backed persistent audit logger for AgentGuard.

    Implements the AuditSink protocol required by ControlledExecutor.
    """

    SCHEMA = """
    CREATE TABLE IF NOT EXISTS events (
        event_id TEXT PRIMARY KEY,
        timestamp REAL NOT NULL,
        subsystem TEXT NOT NULL,
        event_type TEXT NOT NULL,
        severity TEXT NOT NULL,
        summary TEXT NOT NULL,
        payload_json TEXT NOT NULL,
        redacted INTEGER DEFAULT 0
    );

    CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);
    CREATE INDEX IF NOT EXISTS idx_events_subsystem ON events(subsystem);
    CREATE INDEX IF NOT EXISTS idx_events_event_type ON events(event_type);
    """

    def __init__(self, db_path: str | Path = ":memory:", connection: sqlite3.Connection | None = None) -> None:
        self._lock = RLock()
        self._db_path = str(db_path) if isinstance(db_path, Path) else db_path
        if connection is not None:
            self._conn = connection
        else:
            self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._init_schema()

    def _init_schema(self) -> None:
        with self._lock:
            try:
                self._conn.executescript(self.SCHEMA)
                self._conn.commit()
            except sqlite3.Error as exc:
                raise AuditStorageError(f"Failed to initialize SQLite audit schema: {exc}") from exc

    def record_event(self, event: AuditEvent) -> StoredAuditEvent:
        """Persist an AuditEvent conforming to the AuditSink protocol."""
        event_id = str(uuid4())
        timestamp = event.timestamp.timestamp()
        subsystem = "AgentGuard"
        severity = _determine_severity(event)

        # Build raw summary and payload
        raw_summary = (
            f"Agent '{event.agent_id}' {event.event_type}: "
            f"{event.reason_code or event.execution_status or (event.decision.value if event.decision else 'recorded')}"
        )
        if event.explanation:
            raw_summary += f" - {event.explanation}"

        raw_payload = {
            "action_id": event.action_id,
            "agent_id": event.agent_id,
            "decision": event.decision.value if event.decision else None,
            "reason_code": event.reason_code,
            "explanation": event.explanation,
            "execution_status": event.execution_status,
            "approval_id": event.approval_id,
        }

        # Redact secrets from summary and payload
        sanitized_summary, summary_redacted = redact_sensitive_text(raw_summary)
        summary_final = sanitized_summary or raw_summary

        is_redacted = summary_redacted
        sanitized_payload = {}
        for key, value in raw_payload.items():
            if isinstance(value, str):
                s_val, r_flag = redact_sensitive_text(value)
                sanitized_payload[key] = s_val
                if r_flag:
                    is_redacted = True
            else:
                sanitized_payload[key] = value

        payload_json = json.dumps(sanitized_payload, sort_keys=True)
        sanitized_json, json_redacted = redact_sensitive_text(payload_json)
        if json_redacted:
            payload_json = sanitized_json or payload_json
            is_redacted = True

        with self._lock:
            try:
                self._conn.execute(
                    """
                    INSERT INTO events (event_id, timestamp, subsystem, event_type, severity, summary, payload_json, redacted)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event_id,
                        timestamp,
                        subsystem,
                        event.event_type,
                        severity,
                        summary_final,
                        payload_json,
                        1 if is_redacted else 0,
                    ),
                )
                self._conn.commit()
            except sqlite3.Error as exc:
                raise AuditStorageError(f"Failed to persist audit event '{event_id}': {exc}") from exc

        return StoredAuditEvent(
            event_id=event_id,
            timestamp=timestamp,
            subsystem=subsystem,
            event_type=event.event_type,
            severity=severity,
            summary=summary_final,
            payload_json=payload_json,
            redacted=is_redacted,
        )

    def get_recent_events(
        self,
        limit: int = 5,
        subsystem: str | None = "AgentGuard",
    ) -> list[StoredAuditEvent]:
        """Retrieve the most recent audit events ordered newest first.

        Governing Criteria: AC-08 (defaults to limit=5, subsystem='AgentGuard').
        """
        if limit <= 0:
            return []

        query = "SELECT event_id, timestamp, subsystem, event_type, severity, summary, payload_json, redacted FROM events"
        params: list[object] = []
        if subsystem is not None:
            query += " WHERE subsystem = ?"
            params.append(subsystem)

        query += " ORDER BY timestamp DESC, rowid DESC LIMIT ?"
        params.append(limit)

        with self._lock:
            try:
                cursor = self._conn.execute(query, params)
                rows = cursor.fetchall()
            except sqlite3.Error as exc:
                raise AuditStorageError(f"Failed to fetch recent audit events: {exc}") from exc

        return [
            StoredAuditEvent(
                event_id=row[0],
                timestamp=row[1],
                subsystem=row[2],
                event_type=row[3],
                severity=row[4],
                summary=row[5],
                payload_json=row[6],
                redacted=bool(row[7]),
            )
            for row in rows
        ]

    def search_events(
        self,
        query: str = "",
        subsystem: str | None = "AgentGuard",
        agent_id: str | None = None,
        severity: str | None = None,
        limit: int = 50,
    ) -> list[StoredAuditEvent]:
        """Search historical audit events by keyword, agent ID, and severity.

        Governing Criteria: AC-08.
        """
        sql = "SELECT event_id, timestamp, subsystem, event_type, severity, summary, payload_json, redacted FROM events WHERE 1=1"
        params: list[object] = []

        if subsystem is not None:
            sql += " AND subsystem = ?"
            params.append(subsystem)

        if query:
            sql += " AND (summary LIKE ? OR event_type LIKE ? OR payload_json LIKE ?)"
            like_term = f"%{query}%"
            params.extend([like_term, like_term, like_term])

        if severity is not None:
            sql += " AND severity = ?"
            params.append(severity)

        sql += " ORDER BY timestamp DESC, rowid DESC LIMIT ?"
        params.append(limit)

        with self._lock:
            try:
                cursor = self._conn.execute(sql, params)
                rows = cursor.fetchall()
            except sqlite3.Error as exc:
                raise AuditStorageError(f"Failed to search audit events: {exc}") from exc

        results = [
            StoredAuditEvent(
                event_id=row[0],
                timestamp=row[1],
                subsystem=row[2],
                event_type=row[3],
                severity=row[4],
                summary=row[5],
                payload_json=row[6],
                redacted=bool(row[7]),
            )
            for row in rows
        ]

        if agent_id is not None:
            results = [r for r in results if r.payload.get("agent_id") == agent_id]

        return results

    def close(self) -> None:
        """Close the database connection."""
        with self._lock:
            try:
                self._conn.close()
            except sqlite3.Error:
                pass
