"""Windows Evidence Collector for CrashGuard (AC-11, AC-14).

Collects Windows diagnostic records (Application Error, Application Hang,
unexpected shutdown) and separates confirmed observations from inferred hypotheses.
Handles permission denials gracefully without failing.
Provides deterministic deduplication and EventStore persistence.
"""
from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime
from typing import TYPE_CHECKING

from sentron.core.models import UnifiedEvent, WindowsEvidence
from sentron.platform.windows.event_log import WindowsEventLogAdapter

if TYPE_CHECKING:
    from sentron.core.storage import EventStore


class WindowsEvidenceCollector:
    """Collects operating system diagnostic records."""

    def __init__(self, adapter: WindowsEventLogAdapter | None = None) -> None:
        self._adapter = adapter or WindowsEventLogAdapter()

    def collect_evidence(self, limit: int = 5) -> tuple[list[WindowsEvidence], list[str]]:
        """Collect recent event records.

        Returns:
            (evidence_records, unavailable_warnings)
        """
        try:
            return self._adapter.query_recent_diagnostic_events(limit=limit)
        except Exception:
            return [], ["windows_event_log_access_denied"]

    def format_diagnostic_statement(self, evidence: WindowsEvidence) -> tuple[str, str]:
        """Separates confirmed observation from inferred hypothesis (AC-11).

        Returns:
            (confirmed_observation, inferred_hypothesis)
        """
        event_names = {
            1000: "Application Error (Crash)",
            1002: "Application Hang (Frozen UI)",
            6008: "Unexpected System Shutdown",
        }
        event_desc = event_names.get(evidence.event_id, f"Event ID {evidence.event_id}")
        confirmed = (
            f"Confirmed: {event_desc} recorded in {evidence.log_channel} log by source "
            f"'{evidence.source}' at {evidence.event_time}."
        )
        if evidence.event_id == 6008:
            inferred = (
                "Suspected: The system rebooted or shut down abruptly without completing standard "
                "shutdown sequences (e.g., power loss, kernel panic, or forced hard reset)."
            )
        elif evidence.event_id == 1002:
            inferred = (
                f"Suspected: The process associated with '{evidence.source}' stopped interacting "
                "with Windows (window message pump unresponsive or thread deadlock)."
            )
        else:
            inferred = (
                f"Suspected: The process associated with '{evidence.source}' may have experienced "
                "an unhandled exception, resource deadlock, or sudden termination."
            )
        return confirmed, inferred


def generate_evidence_event_id(evidence: WindowsEvidence) -> str:
    """Generate a deterministic, collision-resistant event ID for a WindowsEvidence record."""
    raw_key = f"{evidence.log_channel}:{evidence.event_id}:{evidence.event_time}:{evidence.source}"
    digest = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()[:16]
    return f"winevt-{digest}"


def make_evidence_unified_event(
    evidence: WindowsEvidence,
    collector: WindowsEvidenceCollector | None = None,
) -> UnifiedEvent:
    """Transform a WindowsEvidence record into a UnifiedEvent for timeline persistence."""
    collector = collector or WindowsEvidenceCollector()
    confirmed, inferred = collector.format_diagnostic_statement(evidence)

    try:
        ts = datetime.fromisoformat(evidence.event_time).timestamp()
    except Exception:
        ts = time.time()

    if evidence.event_id == 6008:
        severity = "critical"
    elif evidence.event_id == 1000:
        severity = "critical"
    elif evidence.event_id == 1002:
        severity = "warning"
    else:
        severity = "warning"

    payload = {
        "event_id": evidence.event_id,
        "log_channel": evidence.log_channel,
        "source": evidence.source,
        "event_time": evidence.event_time,
        "description": evidence.description,
        "confirmed_observation": confirmed,
        "inferred_hypothesis": inferred,
        "is_confirmed_os_evidence": True,
    }

    return UnifiedEvent(
        event_id=generate_evidence_event_id(evidence),
        timestamp=ts,
        subsystem="CrashGuard",
        event_type="HOST_CRASH_EVIDENCE",
        severity=severity,
        summary=confirmed,
        payload_json=json.dumps(payload),
        redacted=False,
    )


def persist_windows_evidence(
    store: EventStore,
    evidence_list: list[WindowsEvidence],
    collector: WindowsEvidenceCollector | None = None,
    seen_ids: set[str] | None = None,
) -> list[UnifiedEvent]:
    """Persist Windows crash/hang evidence into EventStore with deterministic deduplication."""
    persisted: list[UnifiedEvent] = []
    for ev in evidence_list:
        unified_ev = make_evidence_unified_event(ev, collector=collector)
        if seen_ids is not None and unified_ev.event_id in seen_ids:
            continue
        if store.has_event(unified_ev.event_id):
            if seen_ids is not None:
                seen_ids.add(unified_ev.event_id)
            continue

        result = store.record_unified_event(unified_ev, ignore_duplicate=True)
        if result is not None:
            if seen_ids is not None:
                seen_ids.add(unified_ev.event_id)
            persisted.append(unified_ev)
    return persisted
