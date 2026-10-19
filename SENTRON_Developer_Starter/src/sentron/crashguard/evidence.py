"""Windows Evidence Collector for CrashGuard (AC-11, AC-14).

Collects Windows diagnostic records (Application Error, Application Hang,
unexpected shutdown) and separates confirmed observations from inferred hypotheses.
Handles permission denials gracefully without failing.
"""
from __future__ import annotations

from sentron.core.models import WindowsEvidence
from sentron.platform.windows.event_log import WindowsEventLogAdapter


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
        inferred = (
            f"Suspected: The process associated with '{evidence.source}' may have experienced "
            "an unhandled exception, resource deadlock, or sudden termination."
        )
        return confirmed, inferred
