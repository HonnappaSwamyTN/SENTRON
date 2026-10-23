"""Unit tests for the 93% CrashGuard resource-risk threshold and sustained-risk behavior.

Tests cover:
- Single source of truth: DEFAULT_RESOURCE_RISK_THRESHOLD = 93.0
- Values below threshold (e.g. 90.0%, 92.5%): no alert triggered even if sustained
- Values at boundary (93.0%) and above threshold (e.g. 93.1%, 95.0%): alert triggered only after sustained duration (>10s)
- Transient spikes above 93% do not trigger alerts (requires sustained duration)
- Cooldown suppression after alert generation
- Strict distinction between 93% resource risk threshold and CPU temperature threshold
"""

import time
import pytest

from sentron.crashguard.risk import (
    SustainedRiskDetector,
    DEFAULT_RESOURCE_RISK_THRESHOLD,
    DEFAULT_TEMPERATURE_ADVISORY_THRESHOLD,
)
from sentron.core.models import SystemSnapshot, RiskAlert
from sentron.core.settings import AppSettings


def _make_snapshot(ts: float, cpu: float = 10.0, mem: float = 10.0, temp: float = None) -> SystemSnapshot:
    return SystemSnapshot(
        timestamp=ts,
        cpu_percent=cpu,
        memory_percent=mem,
        memory_available_bytes=8 * 1024**3,
        disk_free_bytes=100 * 1024**3,
        disk_busy_percent=5.0,
        top_processes=[],
        unavailable_metrics=(),
        cpu_temperature_c=temp,
        cpu_temperature_status="available" if temp is not None else "unavailable",
    )


@pytest.mark.unit
def test_single_source_of_truth_is_93_percent():
    """Verify that default threshold constant is exactly 93.0% and matches AppSettings."""
    assert DEFAULT_RESOURCE_RISK_THRESHOLD == 93.0
    settings = AppSettings()
    assert settings.resource_risk_threshold == 93.0
    
    # SustainedRiskDetector default constructor must use 93.0
    detector = SustainedRiskDetector()
    assert detector.cpu_threshold == 93.0
    assert detector.memory_threshold == 93.0


@pytest.mark.unit
def test_values_below_93_do_not_trigger_alert():
    """Values below 93% (e.g. 90.0%, 92.5%, 92.9%) never trigger alerts even when sustained for a long duration."""
    detector = SustainedRiskDetector(
        sustained_duration_seconds=10.0,
        cooldown_seconds=30.0,
    )
    t0 = 1000.0
    
    # 90.0% sustained for 20 seconds
    assert detector.evaluate_snapshot(_make_snapshot(t0, cpu=90.0)) == []
    assert detector.evaluate_snapshot(_make_snapshot(t0 + 5.0, cpu=90.0)) == []
    assert detector.evaluate_snapshot(_make_snapshot(t0 + 12.0, cpu=90.0)) == []
    assert detector.evaluate_snapshot(_make_snapshot(t0 + 20.0, cpu=90.0)) == []
    assert not detector.is_active_risk("CPU")
    
    # 92.9% (just below 93.0%) sustained for 15 seconds
    t1 = 2000.0
    assert detector.evaluate_snapshot(_make_snapshot(t1, cpu=92.9)) == []
    assert detector.evaluate_snapshot(_make_snapshot(t1 + 15.0, cpu=92.9)) == []
    assert not detector.is_active_risk("CPU")


@pytest.mark.unit
def test_transient_spike_above_93_does_not_trigger_alert():
    """A transient spike above 93% that recovers before 10s does not trigger an alert."""
    detector = SustainedRiskDetector(
        sustained_duration_seconds=10.0,
        cooldown_seconds=30.0,
    )
    t0 = 1000.0
    
    # Spike starts at 96.0%
    assert detector.evaluate_snapshot(_make_snapshot(t0, cpu=96.0)) == []
    # 4 seconds later, still 96.0% (not yet sustained for 10s)
    assert detector.evaluate_snapshot(_make_snapshot(t0 + 4.0, cpu=96.0)) == []
    # Recovers back to 50.0% at 7s
    assert detector.evaluate_snapshot(_make_snapshot(t0 + 7.0, cpu=50.0)) == []
    # Later at 15s (after original 10s mark), but recovery already cleared first breach
    assert detector.evaluate_snapshot(_make_snapshot(t0 + 15.0, cpu=50.0)) == []
    assert not detector.is_active_risk("CPU")


@pytest.mark.unit
def test_sustained_pressure_above_93_triggers_alert_and_observes_cooldown():
    """Pressure sustained >= 93.0% for >10s triggers exactly one alert and respects cooldown."""
    detector = SustainedRiskDetector(
        sustained_duration_seconds=10.0,
        cooldown_seconds=30.0,
    )
    t0 = 1000.0
    
    # Start breach at 94.5%
    assert detector.evaluate_snapshot(_make_snapshot(t0, cpu=94.5)) == []
    # Mid-window (5s) -> no alert
    assert detector.evaluate_snapshot(_make_snapshot(t0 + 5.0, cpu=94.5)) == []
    # Sustained past 10s (11s) -> triggers alert
    alerts = detector.evaluate_snapshot(_make_snapshot(t0 + 11.0, cpu=94.5))
    assert len(alerts) == 1
    assert alerts[0].metric_name == "CPU"
    assert alerts[0].observed_value == 94.5
    assert alerts[0].threshold_value == 93.0
    assert alerts[0].duration_seconds >= 10.0
    assert detector.is_active_risk("CPU")
    
    # Still at 95.0% during cooldown window (e.g. t0 + 20s, cooldown is 30s) -> suppressed
    assert detector.evaluate_snapshot(_make_snapshot(t0 + 20.0, cpu=95.0)) == []


@pytest.mark.unit
def test_resource_threshold_distinct_from_temperature_threshold():
    """93% resource threshold is clearly distinguished from CPU temperature advisory limit."""
    assert DEFAULT_RESOURCE_RISK_THRESHOLD == 93.0
    assert DEFAULT_TEMPERATURE_ADVISORY_THRESHOLD == 80.0
    assert DEFAULT_RESOURCE_RISK_THRESHOLD != DEFAULT_TEMPERATURE_ADVISORY_THRESHOLD
    
    detector = SustainedRiskDetector(
        cpu_threshold=93.0,
        temperature_threshold=80.0,
        sustained_duration_seconds=5.0,
    )
    
    t0 = 1000.0
    detector._first_breach_time["CPUTemperature"] = t0 - 6.0
    # CPU is normal (35%), but Temperature is 85°C
    snap = _make_snapshot(t0, cpu=35.0, temp=85.0)
    alerts = detector.evaluate_snapshot(snap)
    
    assert len(alerts) == 1
    assert alerts[0].metric_name == "CPUTemperature"
    assert alerts[0].threshold_value == 80.0
    assert alerts[0].observed_value == 85.0
    # CPU alert was not triggered
    assert not detector.is_active_risk("CPU")
    assert detector.is_active_risk("CPUTemperature")
