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
                raise StorageError(f"Failed to initialize storage schema: {exc}") from exc

    def record_unified_event(self, event: UnifiedEvent) -> StoredAuditEvent:
        """Record a UnifiedEvent into the events table with secret redaction."""
        sanitized_summary, summary_redacted = redact_sensitive_text(event.summary)
        summary_final = sanitized_summary or event.summary

        is_redacted = event.redacted or summary_redacted
        sanitized_json, json_redacted = redact_sensitive_text(event.payload_json)
        payload_final = sanitized_json or event.payload_json
        if json_redacted:
            is_redacted = True

        with self._lock:
            try:
                self._conn.execute(
                    """
                    INSERT INTO events (event_id, timestamp, subsystem, event_type, severity, summary, payload_json, redacted)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
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
                    ),
                )
                self._conn.commit()
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
        )

    def record_event(self, event: AuditEvent) -> StoredAuditEvent:
        """AuditSink compatibility for AgentGuard."""
        from sentron.agentguard.audit import SqliteAuditLog
        logger = SqliteAuditLog(connection=self._conn)
        return logger.record_event(event)

    def get_recent_events(
        self,
        limit: int = 5,
        subsystem: str | None = None,
    ) -> list[StoredAuditEvent]:
        """Retrieve the most recent events ordered newest first."""
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
            )
            for row in rows
        ]

    def get_unified_timeline(
        self,
        start_time: float | None = None,
        end_time: float | None = None,
        limit: int = 50,
    ) -> list[StoredAuditEvent]:
        """Retrieve unified timeline interleaving AgentGuard and CrashGuard events (AC-16)."""
        query = "SELECT event_id, timestamp, subsystem, event_type, severity, summary, payload_json, redacted FROM events WHERE 1=1"
        params: list[object] = []

        if start_time is not None:
            query += " AND timestamp >= ?"
            params.append(start_time)

        if end_time is not None:
            query += " AND timestamp <= ?"
            params.append(end_time)

        query += " ORDER BY timestamp DESC, rowid DESC LIMIT ?"
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
            )
            for row in rows
        ]

    def search_events(
        self,
        query: str = "",
        subsystem: str | None = None,
        severity: str | None = None,
        limit: int = 50,
    ) -> list[StoredAuditEvent]:
        """Search historical events across all or specific subsystems (AC-08, AC-16)."""
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
