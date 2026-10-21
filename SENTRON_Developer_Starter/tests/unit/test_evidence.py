"""
Unit tests for Windows Evidence Collector (CrashGuard B - Dev4).
Governing Criteria: AC-11, AC-14, AC-16, AC-17
"""
from unittest.mock import patch
import pytest
from sentron.core.models import WindowsEvidence
from sentron.core.storage import EventStore
from sentron.crashguard.evidence import (
    WindowsEvidenceCollector,
    generate_evidence_event_id,
    load_seen_ids_from_json,
    make_evidence_unified_event,
    persist_windows_evidence,
    save_seen_ids_to_json,
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


@pytest.mark.unit
def test_seen_ids_json_state_persistence_and_reload(tmp_path):
    """AC-11: State Persistence - persist seen_ids to a JSON file across application restarts."""
    json_path = tmp_path / "seen_events.json"
    store = EventStore(db_path=":memory:")

    ev1 = WindowsEvidence(
        event_id=1000,
        log_channel="Application",
        source="app_a.exe",
        event_time="2026-10-21T01:00:00Z",
        description="Crash A",
    )
    ev2 = WindowsEvidence(
        event_id=1002,
        log_channel="Application",
        source="app_b.exe",
        event_time="2026-10-21T01:05:00Z",
        description="Hang B",
    )

    # 1. Initial persistence with state_file_path
    seen_ids = set()
    persisted = persist_windows_evidence(
        store, [ev1, ev2], seen_ids=seen_ids, state_file_path=json_path
    )
    assert len(persisted) == 2
    assert json_path.is_file()

    # 2. Verify JSON file contents directly
    loaded_ids = load_seen_ids_from_json(json_path)
    assert len(loaded_ids) == 2
    assert generate_evidence_event_id(ev1) in loaded_ids
    assert generate_evidence_event_id(ev2) in loaded_ids

    # 3. Simulate new application process session loading from JSON file
    new_seen_ids = load_seen_ids_from_json(json_path)
    assert len(new_seen_ids) == 2

    ev3 = WindowsEvidence(
        event_id=41,
        log_channel="System",
        source="Kernel-Power",
        event_time="2026-10-21T01:10:00Z",
        description="Power reset",
    )
    # Subsequent poll with old events and new event
    persisted_new = persist_windows_evidence(
        store, [ev1, ev2, ev3], seen_ids=new_seen_ids, state_file_path=json_path
    )
    # ev1 and ev2 must be deduplicated via loaded JSON seen_ids
    assert len(persisted_new) == 1
    assert persisted_new[0].event_id == generate_evidence_event_id(ev3)

    # File updated with 3 seen IDs
    reloaded_ids = load_seen_ids_from_json(json_path)
    assert len(reloaded_ids) == 3
    assert generate_evidence_event_id(ev3) in reloaded_ids

    store.close()


@pytest.mark.unit
def test_seen_ids_json_permission_error_handling(tmp_path):
    """AC-14: Gracefully handles PermissionError when accessing seen_ids JSON file."""
    json_path = tmp_path / "protected_seen_events.json"
    store = EventStore(db_path=":memory:")

    ev = WindowsEvidence(
        event_id=1000,
        log_channel="Application",
        source="test.exe",
        event_time="2026-10-21T02:00:00Z",
        description="Test",
    )

    # 1. Permission error when writing JSON
    with patch("builtins.open", side_effect=PermissionError("WinError 5: Access is denied")):
        success = save_seen_ids_to_json({"winevt-test1"}, file_path=json_path)
        assert success is False

        # persist_windows_evidence does not crash when file cannot be saved
        persisted = persist_windows_evidence(
            store, [ev], seen_ids=set(), state_file_path=json_path
        )
        assert len(persisted) == 1

    # 2. Permission error when reading JSON
    with patch("builtins.open", side_effect=PermissionError("WinError 5: Access is denied")):
        loaded = load_seen_ids_from_json(json_path)
        assert loaded == set()

    store.close()


@pytest.mark.unit
def test_extended_event_coverage_and_hypotheses():
    """AC-11: Formats extended event IDs (1001, 41, 1074, 219) with confirmed/inferred separation."""
    collector = WindowsEvidenceCollector()

    # Event 1001: WER Report
    ev_1001 = WindowsEvidence(
        event_id=1001,
        log_channel="Application",
        source="Windows Error Reporting",
        event_time="2026-10-21T03:00:00Z",
        description="Fault bucket 123456",
    )
    conf_1001, inf_1001 = collector.format_diagnostic_statement(ev_1001)
    assert "Confirmed:" in conf_1001
    assert "Windows Error Reporting" in conf_1001
    assert "Suspected:" in inf_1001
    assert "WER" in conf_1001 or "Error Reporting" in conf_1001
    ue_1001 = make_evidence_unified_event(ev_1001, collector=collector)
    assert ue_1001.severity == "warning"

    # Event 41: Kernel-Power
    ev_41 = WindowsEvidence(
        event_id=41,
        log_channel="System",
        source="Microsoft-Windows-Kernel-Power",
        event_time="2026-10-21T03:05:00Z",
        description="The system has rebooted without cleanly shutting down first.",
    )
    conf_41, inf_41 = collector.format_diagnostic_statement(ev_41)
    assert "Confirmed:" in conf_41
    assert "Kernel-Power" in conf_41
    assert "Suspected:" in inf_41
    ue_41 = make_evidence_unified_event(ev_41, collector=collector)
    assert ue_41.severity == "critical"

    # Event 1074: User32 / System Restart
    ev_1074 = WindowsEvidence(
        event_id=1074,
        log_channel="System",
        source="USER32",
        event_time="2026-10-21T03:10:00Z",
        description="The process C:\\Windows\\System32\\svchost.exe has initiated restart.",
    )
    conf_1074, inf_1074 = collector.format_diagnostic_statement(ev_1074)
    assert "Confirmed:" in conf_1074
    assert "Shutdown / Restart" in conf_1074
    assert "Suspected:" in inf_1074
    ue_1074 = make_evidence_unified_event(ev_1074, collector=collector)
    assert ue_1074.severity == "info"

    # Event 219: Kernel-PnP Driver Load Failure
    ev_219 = WindowsEvidence(
        event_id=219,
        log_channel="System",
        source="Microsoft-Windows-Kernel-PnP",
        event_time="2026-10-21T03:15:00Z",
        description="The driver \\Driver\\WudfRd failed to load for the device.",
    )
    conf_219, inf_219 = collector.format_diagnostic_statement(ev_219)
    assert "Confirmed:" in conf_219
    assert "Kernel-PnP" in conf_219
    assert "Suspected:" in inf_219
    assert "driver" in inf_219.lower()
    ue_219 = make_evidence_unified_event(ev_219, collector=collector)
    assert ue_219.severity == "warning"

