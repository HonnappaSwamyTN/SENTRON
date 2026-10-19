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
