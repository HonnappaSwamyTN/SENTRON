"""
Unit tests for Core Storage & Retention (Core / Integration Owner).
Governing Criteria: AC-17
"""
import time
import pytest
from sentron.core.models import UnifiedEvent
from sentron.core.storage import EventStore


@pytest.mark.unit
def test_sensitive_values_redacted_and_retention_configurable():
    """
    AC-17: Sensitive values are redacted where detected, and event retention is configurable.
    """
    store = EventStore(db_path=":memory:")

    # 1. Test Redaction on store
    secret_payload = '{"api_key": "sk-1234567890abcdef1234567890abcdef", "note": "classified"}'
    event = UnifiedEvent(
        event_id="test-ev-1",
        timestamp=time.time(),
        subsystem="Core",
        event_type="CONFIG_UPDATE",
        severity="info",
        summary="Updated API key sk-1234567890abcdef1234567890abcdef",
        payload_json=secret_payload,
    )
    stored = store.record_unified_event(event)
    assert stored.redacted is True
    assert "sk-1234567890abcdef1234567890abcdef" not in stored.summary
    assert "sk-1234567890abcdef1234567890abcdef" not in stored.payload_json
    assert "[REDACTED_" in stored.summary or "[REDACTED_" in stored.payload_json

    # 2. Test Retention Purge
    old_timestamp = time.time() - (40 * 86400)  # 40 days ago
    old_event = UnifiedEvent(
        event_id="old-ev-2",
        timestamp=old_timestamp,
        subsystem="Core",
        event_type="OLD_RECORD",
        severity="info",
        summary="Old system record",
        payload_json="{}",
    )
    store.record_unified_event(old_event)

    # Purge older than 30 days
    deleted_count = store.purge_older_than(days=30)
    assert deleted_count == 1

    # Verify only recent record remains
    recent = store.get_recent_events(limit=10)
    assert len(recent) == 1
    assert recent[0].event_id == "test-ev-1"


@pytest.mark.unit
def test_storage_is_simulated_and_genuine_filtering():
    """Verify that is_simulated events are persisted and genuine_only filters properly."""
    store = EventStore(db_path=":memory:")
    now = time.time()

    ev_real = UnifiedEvent(
        event_id="real-1",
        timestamp=now,
        subsystem="CrashGuard",
        event_type="SYSTEM_ALERT",
        severity="warning",
        summary="Sustained CPU pressure at 94.0% for 10s",
        payload_json='{"is_simulated": false}',
        is_simulated=False,
    )
    ev_sim = UnifiedEvent(
        event_id="sim-1",
        timestamp=now + 1.0,
        subsystem="CrashGuard",
        event_type="SYSTEM_ALERT",
        severity="warning",
        summary="[SIMULATED DEMO ALERT] Sustained CPU pressure at 94.0% for 10s",
        payload_json='{"is_simulated": true}',
        is_simulated=True,
    )

    stored_real = store.record_unified_event(ev_real)
    stored_sim = store.record_unified_event(ev_sim)

    assert stored_real.is_simulated is False
    assert stored_sim.is_simulated is True
    assert stored_sim.is_test_data is True

    # Check get_recent_events
    all_recent = store.get_recent_events(limit=10, genuine_only=False)
    assert len(all_recent) == 2

    genuine_recent = store.get_recent_events(limit=10, genuine_only=True)
    assert len(genuine_recent) == 1
    assert genuine_recent[0].event_id == "real-1"
    assert genuine_recent[0].is_simulated is False

    # Check get_unified_timeline
    timeline_all = store.get_unified_timeline(genuine_only=False)
    assert len(timeline_all) == 2

    timeline_genuine = store.get_unified_timeline(genuine_only=True)
    assert len(timeline_genuine) == 1
    assert timeline_genuine[0].event_id == "real-1"

    # Check search_events
    search_all = store.search_events(query="Sustained", genuine_only=False)
    assert len(search_all) == 2

    search_genuine = store.search_events(query="Sustained", genuine_only=True)
    assert len(search_genuine) == 1
    assert search_genuine[0].event_id == "real-1"

