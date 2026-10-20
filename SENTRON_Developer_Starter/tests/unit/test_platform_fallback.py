"""
Unit tests for Platform Fallback Adapters (CrashGuard - Dev3 / Dev4).
Governing Criteria: AC-14
"""
import subprocess
from unittest.mock import MagicMock, patch
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


@pytest.mark.unit
def test_unsupported_platform_fallback():
    """Non-Windows systems return unsupported_platform warning without failing."""
    adapter = WindowsEventLogAdapter()
    adapter.is_windows = False

    evidence, warnings = adapter.query_recent_diagnostic_events()
    assert evidence == []
    assert len(warnings) == 1
    assert "unsupported_platform" in warnings[0]


@pytest.mark.unit
def test_timeout_fallback():
    """Timeout during event log query degrades gracefully without crashing."""
    adapter = WindowsEventLogAdapter()
    adapter.is_windows = True

    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="powershell", timeout=3)):
        evidence, warnings = adapter.query_recent_diagnostic_events()
        assert evidence == []
        assert "windows_event_log_timeout" in warnings
