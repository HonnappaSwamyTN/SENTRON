"""
Unit tests for Sustained-Risk Detector (CrashGuard A - Dev3).
Governing Criteria: AC-10
"""
import pytest

@pytest.mark.unit
@pytest.mark.skip(reason="Pending implementation by Dev3 in crashguard.risk (AC-10)")
def test_transient_spike_does_not_trigger_alert():
    """
    AC-10: A short transient spike does not trigger a sustained-risk alert.
    """
    raise NotImplementedError("Dev3 must implement crashguard.risk and this test")


@pytest.mark.unit
@pytest.mark.skip(reason="Pending implementation by Dev3 in crashguard.risk (AC-10)")
def test_sustained_threshold_breach_generates_alert_with_cooldown():
    """
    AC-10: Sustained pressure beyond duration window generates an alert; subsequent pressure observes cooldown.
    """
    raise NotImplementedError("Dev3 must implement crashguard.risk and this test")
