"""
Unit tests for Sustained-Risk Detector (CrashGuard A - Dev3).
Governing Criteria: AC-10
"""
import pytest
from sentron.core.models import SystemSnapshot
from sentron.crashguard.risk import SustainedRiskDetector


def _make_snapshot(ts: float, cpu: float = 20.0, ram: float = 30.0) -> SystemSnapshot:
    return SystemSnapshot(
        timestamp=ts,
        cpu_percent=cpu,
        memory_percent=ram,
        memory_available_bytes=4 * 1024**3,
        disk_free_bytes=50 * 1024**3,
    )


@pytest.mark.unit
def test_transient_spike_does_not_trigger_alert():
    """
    AC-10: A short transient spike does not trigger a sustained-risk alert.
    """
    detector = SustainedRiskDetector(
        cpu_threshold=85.0,
        sustained_duration_seconds=30.0,
        cooldown_seconds=60.0,
    )

    t0 = 1000.0
    # Normal reading
    assert detector.evaluate_snapshot(_make_snapshot(t0, cpu=20.0)) == []

    # Spike at t0 + 5s (only 5s duration < 30s threshold)
    assert detector.evaluate_snapshot(_make_snapshot(t0 + 5.0, cpu=95.0)) == []

    # Drop back down at t0 + 10s
    assert detector.evaluate_snapshot(_make_snapshot(t0 + 10.0, cpu=25.0)) == []


@pytest.mark.unit
def test_sustained_threshold_breach_generates_alert_with_cooldown():
    """
    AC-10: Sustained pressure beyond duration window generates an alert; subsequent pressure observes cooldown.
    """
    detector = SustainedRiskDetector(
        cpu_threshold=85.0,
        sustained_duration_seconds=30.0,
        cooldown_seconds=60.0,
    )

    t0 = 1000.0
    # Start high CPU
    assert detector.evaluate_snapshot(_make_snapshot(t0, cpu=92.0)) == []

    # After 15s (still under 30s) -> no alert
    assert detector.evaluate_snapshot(_make_snapshot(t0 + 15.0, cpu=92.0)) == []

    # After 35s (> 30s threshold) -> triggers exactly ONE alert
    alerts = detector.evaluate_snapshot(_make_snapshot(t0 + 35.0, cpu=92.0))
    assert len(alerts) == 1
    assert alerts[0].metric_name == "CPU"
    assert alerts[0].observed_value == 92.0
    assert alerts[0].duration_seconds >= 30.0

    # Continued high CPU during cooldown window (e.g. at t0 + 50s, cooldown is 60s) -> suppressed
    assert detector.evaluate_snapshot(_make_snapshot(t0 + 50.0, cpu=92.0)) == []
