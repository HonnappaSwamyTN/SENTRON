"""
Unit tests for Platform Fallback & Degradation (CrashGuard A/B - Dev3/Dev4).
Governing Criteria: AC-14
"""
import pytest

@pytest.mark.unit
@pytest.mark.skip(reason="Pending implementation by Dev3/Dev4 in platform fallback adapters (AC-14)")
def test_missing_metrics_and_permissions_handled_gracefully():
    """
    AC-14: Missing metrics, unavailable permissions, and unsupported Windows events are handled gracefully.
    """
    raise NotImplementedError("Dev3/Dev4 must implement graceful degradation and this test")
