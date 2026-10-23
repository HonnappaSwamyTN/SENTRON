"""Unified SQLite storage for SENTRON events and audit logs.

Conforms to ARCHITECTURE.md and fulfills AC-08, AC-16, and AC-17.
Stores privacy-conscious, redacted event records for all subsystems.
"""
from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from threading import RLock
from uuid import uuid4

from sentron.agentguard.audit import StoredAuditEvent, redact_sensitive_text
from sentron.core.models import AuditEvent, UnifiedEvent, utc_now


class StorageError(RuntimeError):
    """Raised when storage operations fail."""


class EventStore:
    """Unified SQLite event storage for AgentGuard and CrashGuard."""

    SCHEMA = """
    CREATE TABLE IF NOT EXISTS events (
        event_id TEXT PRIMARY KEY,
        timestamp REAL NOT NULL,
        subsystem TEXT NOT NULL,
        event_type TEXT NOT NULL,
        severity TEXT NOT NULL,
        summary TEXT NOT NULL,
        payload_json TEXT NOT NULL,
        redacted INTEGER DEFAULT 0,
        is_simulated INTEGER NOT NULL DEFAULT 0
    );

    CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);
    CREATE INDEX IF NOT EXISTS idx_events_subsystem ON events(subsystem);
    CREATE INDEX IF NOT EXISTS idx_events_event_type ON events(event_type);
    """

    def __init__(
        self,
        db_path: str | Path = ":memory:",
        connection: sqlite3.Connection | None = None,
        lock: RLock | None = None,
    ) -> None:
        self._lock = lock if lock is not None else RLock()
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
                cursor = self._conn.execute("PRAGMA table_info(events)")
                existing_columns = {row[1] for row in cursor.fetchall()}
                if "is_simulated" not in existing_columns:
                    self._conn.execute(
                        "ALTER TABLE events ADD COLUMN is_simulated INTEGER NOT NULL DEFAULT 0"
                    )
                self._conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_events_is_simulated ON events(is_simulated)"
                )
                self._conn.commit()
            except sqlite3.Error as exc:
                raise StorageError(f"Failed to initialize storage schema: {exc}") from exc

    def has_event(self, event_id: str) -> bool:
        """Check if an event with the given event_id exists in storage."""
        with self._lock:
            try:
                cursor = self._conn.execute("SELECT 1 FROM events WHERE event_id = ? LIMIT 1", (event_id,))
                return cursor.fetchone() is not None
            except sqlite3.Error as exc:
                raise StorageError(f"Failed to query event existence: {exc}") from exc

    def record_unified_event(self, event: UnifiedEvent, ignore_duplicate: bool = False) -> StoredAuditEvent | None:
        """Record a UnifiedEvent into the events table with secret redaction.

        If ignore_duplicate is True and the event already exists, returns None without raising an error.
        """
        if ignore_duplicate and self.has_event(event.event_id):
            return None

        sanitized_summary, summary_redacted = redact_sensitive_text(event.summary)
        summary_final = sanitized_summary or event.summary

        is_redacted = event.redacted or summary_redacted
        sanitized_json, json_redacted = redact_sensitive_text(event.payload_json)
        payload_final = sanitized_json or event.payload_json
        if json_redacted:
            is_redacted = True

        with self._lock:
            try:
                is_sim = bool(getattr(event, "is_simulated", False))
                self._conn.execute(
                    """
                    INSERT INTO events (event_id, timestamp, subsystem, event_type, severity, summary, payload_json, redacted, is_simulated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event.event_id,
                        event.timestamp,
                        event.subsystem,
                        event.event_type,
                        event.severity,
                        summary_final,
                        payload_final,
                        1 if is_redacted else 0,
                        1 if is_sim else 0,
                    ),
                )
                self._conn.commit()
            except sqlite3.IntegrityError as exc:
                if ignore_duplicate:
                    return None
                raise StorageError(f"Failed to persist event '{event.event_id}': {exc}") from exc
            except sqlite3.Error as exc:
                raise StorageError(f"Failed to persist event '{event.event_id}': {exc}") from exc

        return StoredAuditEvent(
            event_id=event.event_id,
            timestamp=event.timestamp,
            subsystem=event.subsystem,
            event_type=event.event_type,
            severity=event.severity,
            summary=summary_final,
            payload_json=payload_final,
            redacted=is_redacted,
            is_simulated=is_sim,
        )

    def record_event(self, event: AuditEvent) -> StoredAuditEvent:
        """AuditSink compatibility for AgentGuard."""
        if not hasattr(self, "_cached_audit_log") or self._cached_audit_log is None:
            from sentron.agentguard.audit import SqliteAuditLog
            self._cached_audit_log = SqliteAuditLog(connection=self._conn)
        return self._cached_audit_log.record_event(event)

    def get_recent_events(
        self,
        limit: int = 5,
        subsystem: str | None = None,
        genuine_only: bool = False,
    ) -> list[StoredAuditEvent]:
        """Retrieve the most recent events ordered newest first."""
        if limit <= 0:
            return []

        conditions: list[str] = []
        params: list[object] = []
        if subsystem is not None:
            conditions.append("subsystem = ?")
            params.append(subsystem)

        if genuine_only:
            conditions.append("(is_simulated = 0 OR is_simulated IS NULL)")

        where_clause = f" WHERE {' AND '.join(conditions)}" if conditions else ""
        query = f"SELECT event_id, timestamp, subsystem, event_type, severity, summary, payload_json, redacted, is_simulated FROM events{where_clause} ORDER BY timestamp DESC, rowid DESC LIMIT ?"
        params.append(limit)

        with self._lock:
            try:
                cursor = self._conn.execute(query, params)
                rows = cursor.fetchall()
            except sqlite3.Error as exc:
                raise StorageError(f"Failed to fetch recent events: {exc}") from exc

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
                is_simulated=bool(row[8]) if len(row) > 8 and row[8] is not None else False,
            )
            for row in rows
        ]

    def get_unified_timeline(
        self,
        start_time: float | None = None,
        end_time: float | None = None,
        limit: int = 50,
        genuine_only: bool = False,
    ) -> list[StoredAuditEvent]:
        """Retrieve unified timeline interleaving AgentGuard and CrashGuard events (AC-16)."""
        conditions: list[str] = ["1=1"]
        params: list[object] = []

        if start_time is not None:
            conditions.append("timestamp >= ?")
            params.append(start_time)

        if end_time is not None:
            conditions.append("timestamp <= ?")
            params.append(end_time)

        if genuine_only:
            conditions.append("(is_simulated = 0 OR is_simulated IS NULL)")

        query = f"SELECT event_id, timestamp, subsystem, event_type, severity, summary, payload_json, redacted, is_simulated FROM events WHERE {' AND '.join(conditions)} ORDER BY timestamp DESC, rowid DESC LIMIT ?"
        params.append(limit)

        with self._lock:
            try:
                cursor = self._conn.execute(query, params)
                rows = cursor.fetchall()
            except sqlite3.Error as exc:
                raise StorageError(f"Failed to fetch unified timeline: {exc}") from exc

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
                is_simulated=bool(row[8]) if len(row) > 8 and row[8] is not None else False,
            )
            for row in rows
        ]

    def search_events(
        self,
        query: str = "",
        subsystem: str | None = None,
        severity: str | None = None,
        limit: int = 50,
        genuine_only: bool = False,
    ) -> list[StoredAuditEvent]:
        """Search historical events across all or specific subsystems (AC-08, AC-16)."""
        conditions: list[str] = ["1=1"]
        params: list[object] = []

        if subsystem is not None:
            conditions.append("subsystem = ?")
            params.append(subsystem)

        if genuine_only:
            conditions.append("(is_simulated = 0 OR is_simulated IS NULL)")

        if query:
            conditions.append("(summary LIKE ? OR event_type LIKE ? OR payload_json LIKE ?)")
            like_term = f"%{query}%"
            params.extend([like_term, like_term, like_term])

        if severity is not None:
            conditions.append("severity = ?")
            params.append(severity)

        sql = f"SELECT event_id, timestamp, subsystem, event_type, severity, summary, payload_json, redacted, is_simulated FROM events WHERE {' AND '.join(conditions)} ORDER BY timestamp DESC, rowid DESC LIMIT ?"
        params.append(limit)

        with self._lock:
            try:
                cursor = self._conn.execute(sql, params)
                rows = cursor.fetchall()
            except sqlite3.Error as exc:
                raise StorageError(f"Failed to search events: {exc}") from exc

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
                is_simulated=bool(row[8]) if len(row) > 8 and row[8] is not None else False,
            )
            for row in rows
        ]

    def purge_older_than(self, days: int) -> int:
        """Purge events older than configurable number of days (AC-17).

        Returns number of deleted records.
        """
        if days < 0:
            raise ValueError("days must be non-negative")

        cutoff_timestamp = time.time() - (days * 86400)
        with self._lock:
            try:
                cursor = self._conn.execute("DELETE FROM events WHERE timestamp < ?", (cutoff_timestamp,))
                deleted = cursor.rowcount
                self._conn.commit()
                return deleted
            except sqlite3.Error as exc:
                raise StorageError(f"Failed to purge events: {exc}") from exc

    def close(self) -> None:
        """Close database connection."""
        with self._lock:
            try:
                self._conn.close()
            except sqlite3.Error:
                pass
