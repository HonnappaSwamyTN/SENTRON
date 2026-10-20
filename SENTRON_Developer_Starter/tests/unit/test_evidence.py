"""
Unit tests for Windows Evidence Collector (CrashGuard B - Dev4).
Governing Criteria: AC-11, AC-14, AC-16, AC-17
"""
import pytest
from sentron.core.models import WindowsEvidence
from sentron.core.storage import EventStore
from sentron.crashguard.evidence import (
    WindowsEvidenceCollector,
    generate_evidence_event_id,
    make_evidence_unified_event,
    persist_windows_evidence,
)


@pytest.mark.unit
def test_evidence_separates_confirmed_observations_from_inferred_hypotheses():
    """
    AC-11: Formats diagnostic statements explicitly distinguishing confirmed facts from inferred causes.
    """
    collector = WindowsEvidenceCollector()

    # 1. Event 1000: Application Error (Crash)
    crash_ev = WindowsEvidence(
        event_id=1000,
        log_channel="Application",
        source="faulty_service.exe",
        event_time="2026-10-19T10:15:30Z",
        description="Faulting application name: faulty_service.exe, version: 1.0.0.0",
    )
    confirmed, inferred = collector.format_diagnostic_statement(crash_ev)
    assert "Confirmed:" in confirmed
    assert "Application Error" in confirmed
    assert "faulty_service.exe" in confirmed
    assert "Suspected:" in inferred

    # 2. Event 1002: Application Hang
    hang_ev = WindowsEvidence(
        event_id=1002,
        log_channel="Application",
        source="frozen_app.exe",
        event_time="2026-10-19T11:20:00Z",
        description="The program frozen_app.exe stopped interacting with Windows",
    )
    confirmed_hang, inferred_hang = collector.format_diagnostic_statement(hang_ev)
    assert "Confirmed:" in confirmed_hang
    assert "Application Hang" in confirmed_hang
    assert "frozen_app.exe" in confirmed_hang
    assert "Suspected:" in inferred_hang

    # 3. Event 6008: Unexpected System Shutdown
    shutdown_ev = WindowsEvidence(
        event_id=6008,
        log_channel="System",
        source="EventLog",
        event_time="2026-10-19T08:00:00Z",
        description="The previous system shutdown at 07:58:12 was unexpected.",
    )
    confirmed_shut, inferred_shut = collector.format_diagnostic_statement(shutdown_ev)
    assert "Confirmed:" in confirmed_shut
    assert "Unexpected System Shutdown" in confirmed_shut
    assert "System" in confirmed_shut
    assert "Suspected:" in inferred_shut


@pytest.mark.unit
def test_evidence_deterministic_id_and_unified_event():
    """Deterministic event_id enables idempotent deduplication across polls."""
    ev = WindowsEvidence(
        event_id=1000,
        log_channel="Application",
        source="calc.exe",
        event_time="2026-10-20T12:00:00Z",
        description="Faulting module: ntdll.dll",
    )
    id1 = generate_evidence_event_id(ev)
    id2 = generate_evidence_event_id(ev)
    assert id1 == id2
    assert id1.startswith("winevt-")

    unified = make_evidence_unified_event(ev)
    assert unified.event_id == id1
    assert unified.subsystem == "CrashGuard"
    assert unified.event_type == "HOST_CRASH_EVIDENCE"
    assert unified.severity == "critical"
    assert "Confirmed:" in unified.summary
    assert "is_confirmed_os_evidence" in unified.payload_json


@pytest.mark.unit
def test_persist_windows_evidence_and_deduplication():
    """Repeated persistence polling must deduplicate and not create duplicate rows."""
    store = EventStore(db_path=":memory:")

    ev1 = WindowsEvidence(
        event_id=1000,
        log_channel="Application",
        source="agent_tool.exe",
        event_time="2026-10-20T12:00:00Z",
        description="Crash in agent_tool.exe",
    )
    ev2 = WindowsEvidence(
        event_id=1002,
        log_channel="Application",
        source="browser.exe",
        event_time="2026-10-20T12:05:00Z",
        description="Hang in browser.exe",
    )

    seen: set[str] = set()

    # Poll 1: 2 new events
    persisted1 = persist_windows_evidence(store, [ev1, ev2], seen_ids=seen)
    assert len(persisted1) == 2
    assert len(seen) == 2
    assert len(store.get_recent_events(limit=10)) == 2

    # Poll 2: identical 2 events -> 0 new rows
    persisted2 = persist_windows_evidence(store, [ev1, ev2], seen_ids=seen)
    assert len(persisted2) == 0
    assert len(store.get_recent_events(limit=10)) == 2

    # Poll 3: new 3rd event
    ev3 = WindowsEvidence(
        event_id=6008,
        log_channel="System",
        source="EventLog",
        event_time="2026-10-20T12:10:00Z",
        description="Unexpected shutdown",
    )
    persisted3 = persist_windows_evidence(store, [ev1, ev2, ev3], seen_ids=seen)
    assert len(persisted3) == 1
    assert persisted3[0].event_id == generate_evidence_event_id(ev3)
    assert len(store.get_recent_events(limit=10)) == 3

    # Clean up
    store.close()
