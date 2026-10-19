"""
Unit tests for Platform Fallback Adapters (CrashGuard - Dev3 / Dev4).
Governing Criteria: AC-14
"""
from unittest.mock import MagicMock
import pytest
from sentron.crashguard.evidence import WindowsEvidenceCollector
from sentron.platform.windows.event_log import WindowsEventLogAdapter


@pytest.mark.unit
def test_missing_permissions_degrades_gracefully_without_crash():
    """
    AC-14: Access denied or platform error degrades gracefully and records unavailable metrics.
    """
    mock_adapter = MagicMock(spec=WindowsEventLogAdapter)
    mock_adapter.query_recent_diagnostic_events.side_effect = PermissionError("Access is denied")

    collector = WindowsEvidenceCollector(adapter=mock_adapter)
    evidence, warnings = collector.collect_evidence()

    assert evidence == []
    assert len(warnings) > 0
    assert "access_denied" in warnings[0].lower()
