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


@pytest.mark.unit
def test_memory_sustained_breach_and_recovery():
    """
    AC-10: Memory sustained breach triggers alert; condition clearing resets state,
    allowing subsequent breach to trigger anew.
    """
    detector = SustainedRiskDetector(
        memory_threshold=85.0,
        sustained_duration_seconds=20.0,
        cooldown_seconds=40.0,
    )
    t0 = 2000.0

    # Normal RAM
    assert detector.evaluate_snapshot(_make_snapshot(t0, ram=60.0)) == []

    # High RAM (88%) at t0 + 10s
    assert detector.evaluate_snapshot(_make_snapshot(t0 + 10.0, ram=88.0)) == []

    # After 25s sustained (t0 + 35s, duration 25s >= 20s threshold) -> triggers alert
    alerts = detector.evaluate_snapshot(_make_snapshot(t0 + 35.0, ram=88.0))
    assert len(alerts) == 1
    assert alerts[0].metric_name == "Memory"
    assert alerts[0].observed_value == 88.0
    assert alerts[0].severity == "warning"
    assert detector.is_active_risk("Memory")

    # Condition clears at t0 + 40s (drops to 50%) -> active state is cleared
    assert detector.evaluate_snapshot(_make_snapshot(t0 + 40.0, ram=50.0)) == []
    assert not detector.is_active_risk("Memory")

    # New high RAM condition sustained from t0 + 50s to t0 + 75s (duration 25s) -> triggers new alert
    assert detector.evaluate_snapshot(_make_snapshot(t0 + 50.0, ram=96.0)) == []
    new_alerts = detector.evaluate_snapshot(_make_snapshot(t0 + 75.0, ram=96.0))
    assert len(new_alerts) == 1
    assert new_alerts[0].metric_name == "Memory"
    assert new_alerts[0].severity == "critical"  # RAM >= 95% is critical


@pytest.mark.unit
def test_disk_free_gb_threshold_and_severities():
    """
    AC-10: Low disk space triggers warning (<5GB) or critical (<1GB) sustained alert.
    """
    detector = SustainedRiskDetector(
        disk_free_gb_threshold=5.0,
        sustained_duration_seconds=10.0,
        cooldown_seconds=30.0,
    )
    t0 = 3000.0

    def _disk_snap(ts, free_gb):
        return SystemSnapshot(
            timestamp=ts,
            cpu_percent=10.0,
            memory_percent=20.0,
            memory_available_bytes=4 * 1024**3,
            disk_free_bytes=int(free_gb * 1024**3),
        )

    # Normal disk (20 GB)
    assert detector.evaluate_snapshot(_disk_snap(t0, free_gb=20.0)) == []

    # Warning breach: 3.0 GB free (< 5 GB) sustained for 15s
    assert detector.evaluate_snapshot(_disk_snap(t0 + 5.0, free_gb=3.0)) == []
    alerts = detector.evaluate_snapshot(_disk_snap(t0 + 20.0, free_gb=3.0))
    assert len(alerts) == 1
    assert alerts[0].metric_name == "DiskFreeGB"
    assert alerts[0].severity == "warning"
    assert alerts[0].observed_value == 3.0

    # Reset metric
    detector.reset_metric("DiskFreeGB")

    # Critical breach: 0.5 GB free (< 1 GB) sustained for 15s
    t1 = 4000.0
    assert detector.evaluate_snapshot(_disk_snap(t1, free_gb=0.5)) == []
    crit_alerts = detector.evaluate_snapshot(_disk_snap(t1 + 15.0, free_gb=0.5))
    assert len(crit_alerts) == 1
    assert crit_alerts[0].metric_name == "DiskFreeGB"
    assert crit_alerts[0].severity == "critical"


@pytest.mark.unit
def test_multiple_simultaneous_breaches():
    """
    AC-10: Simultaneous sustained pressure across multiple metrics emits alerts for each.
    """
    detector = SustainedRiskDetector(
        cpu_threshold=80.0,
        memory_threshold=80.0,
        sustained_duration_seconds=10.0,
        cooldown_seconds=30.0,
    )
    t0 = 5000.0

    # Both CPU and RAM high
    snap_high = _make_snapshot(t0, cpu=90.0, ram=92.0)
    assert detector.evaluate_snapshot(snap_high) == []

    # Sustained past 10s
    snap_sustained = _make_snapshot(t0 + 15.0, cpu=90.0, ram=92.0)
    alerts = detector.evaluate_snapshot(snap_sustained)
    assert len(alerts) == 2
    metrics = {a.metric_name for a in alerts}
    assert metrics == {"CPU", "Memory"}

