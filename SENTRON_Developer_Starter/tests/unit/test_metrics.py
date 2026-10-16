"""
Unit tests for Metrics Collector (CrashGuard A - Dev3).
Governing Criteria: AC-09
"""
import pytest

@pytest.mark.unit
@pytest.mark.skip(reason="Pending implementation by Dev3 in crashguard.metrics (AC-09)")
def test_genuine_system_measurements_collected():
    """
    AC-09: Telemetry reflects genuine system measurements via psutil; no hardcoded demo values.
    """
    raise NotImplementedError("Dev3 must implement crashguard.metrics and this test")
