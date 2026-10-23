"""Unit tests for non-elevated CPU temperature monitoring in CrashGuard.

Tests cover:
- Best-effort temperature detection under normal user permissions
- Handling of Access Denied without crashing or requesting elevation
- Rejection of invalid, corrupted, or out-of-range sensor readings
- Guarantee that temperature monitoring never requests UAC elevation or relaunches
- Guarantee that stale readings are never reused after cache expiration
- UI reporting of 'Unavailable' with the required informational notice
- Independence of CPU temperature from the 93% resource-risk threshold
"""

import os
import sys
import time
import pytest
from unittest.mock import MagicMock, patch
from PySide6.QtWidgets import QApplication, QLabel

from sentron.crashguard.temperature import (
    CpuTemperatureCollector,
    convert_raw_temperature_to_celsius,
    UNAVAILABLE_EXPLANATION,
)
from sentron.crashguard.risk import (
    SustainedRiskDetector,
    DEFAULT_RESOURCE_RISK_THRESHOLD,
    DEFAULT_TEMPERATURE_ADVISORY_THRESHOLD,
)
from sentron.core.models import SystemSnapshot, RiskAlert
from sentron.main import create_application


@pytest.fixture
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.mark.unit
def test_valid_temperature_readings_and_conversions():
    """Valid temperature readings in Kelvin, tenths of Kelvin, or Celsius are accepted."""
    # Direct Celsius
    assert convert_raw_temperature_to_celsius(55.0) == 55.0
    # Kelvin (328K ~ 54.9°C)
    assert convert_raw_temperature_to_celsius(328) == 54.9
    # Tenths of Kelvin (3282 ~ 55.0°C)
    assert convert_raw_temperature_to_celsius(3282) == 55.0
    # Boundary tests
    assert convert_raw_temperature_to_celsius(10.0) == 10.0
    assert convert_raw_temperature_to_celsius(125.0) == 125.0


@pytest.mark.unit
def test_invalid_temperature_values_rejected():
    """Unrealistic, negative, or corrupted sensor readings are safely rejected without fabricating."""
    # Negative / Zero
    assert convert_raw_temperature_to_celsius(-10.0) is None
    assert convert_raw_temperature_to_celsius(0.0) is None
    # Out of physical CPU bounds
    assert convert_raw_temperature_to_celsius(135.0) is None
    assert convert_raw_temperature_to_celsius(15000.0) is None
    # Invalid types
    assert convert_raw_temperature_to_celsius("corrupt") is None
    assert convert_raw_temperature_to_celsius(None) is None


@pytest.mark.unit
def test_successful_reading_via_performance_counters():
    """Successful reading from WMI performance counters reports status 'available'."""
    collector = CpuTemperatureCollector(cache_ttl_seconds=4.0)

    with patch.object(
        collector,
        "_query_perf_counters",
        return_value=(54.9, "available", "Thermal Zone Performance Counter (1 zone(s))"),
    ):
        temp, status, explanation = collector.get_temperature(force_refresh=True)
        assert temp == 54.9
        assert status == "available"
        assert "Performance Counter" in explanation


@pytest.mark.unit
def test_access_denied_safely_advances_to_next_source():
    """If ACPI or a source returns Access Denied, it safely continues to the next source without raising errors."""
    collector = CpuTemperatureCollector(cache_ttl_seconds=4.0)

    # Simulate: Perf counters return unavailable, ACPI raises Access Denied, but Hardware Monitor succeeds
    with patch.object(collector, "_query_perf_counters", return_value=(None, "unavailable", "")), \
         patch.object(collector, "_query_hardware_monitors", return_value=(52.0, "available", "LibreHardwareMonitor Sensor")), \
         patch.object(collector, "_query_acpi", side_effect=Exception("0x80041003 Access Denied")):
        
        temp, status, explanation = collector.get_temperature(force_refresh=True)
        assert temp == 52.0
        assert status == "available"
        assert "LibreHardwareMonitor" in explanation


@pytest.mark.unit
def test_all_sources_unavailable_returns_standard_explanation():
    """When no accessible source returns a reading, reports 'unavailable' with required message."""
    collector = CpuTemperatureCollector(cache_ttl_seconds=4.0)

    with patch.object(collector, "_query_perf_counters", return_value=(None, "unavailable", "")), \
         patch.object(collector, "_query_hardware_monitors", return_value=(None, "unavailable", "")), \
         patch.object(collector, "_query_acpi", return_value=(None, "unavailable", "")), \
         patch.object(collector, "_query_probes", return_value=(None, "unavailable", "")), \
         patch.object(collector, "_query_psutil", return_value=(None, "unavailable", "")):

        temp, status, explanation = collector.get_temperature(force_refresh=True)
        assert temp is None
        assert status == "unavailable"
        assert "does not expose CPU temperature to SENTRON without elevated access" in explanation
        assert "Other CrashGuard monitoring remains active" in explanation


@pytest.mark.unit
def test_temperature_monitoring_never_requests_elevation():
    """Verify that temperature monitoring never calls UAC/elevation APIs or relaunches with runas."""
    collector = CpuTemperatureCollector()

    # Intercept any potential elevation invocation
    with patch("ctypes.windll.shell32.ShellExecuteW", side_effect=RuntimeError("Elevation attempted!")) if hasattr(sys, "getwindowsversion") else patch("os.system"), \
         patch("subprocess.Popen", side_effect=RuntimeError("Process spawn attempted!")):

        # Sampling temperature under normal user context must never raise or invoke elevation
        temp, status, explanation = collector._sample_temperature()
        assert status in ("available", "unavailable")


@pytest.mark.unit
def test_stale_readings_never_reused_after_cache_expiry():
    """Once cache TTL expires, if the sensor becomes unavailable, stale readings are NOT reused."""
    collector = CpuTemperatureCollector(cache_ttl_seconds=0.1)

    # First query succeeds
    with patch.object(collector, "_sample_temperature", return_value=(55.0, "available", "Active Sensor")):
        temp1, status1, _ = collector.get_temperature(force_refresh=True)
        assert temp1 == 55.0
        assert status1 == "available"

    # Sleep past cache TTL
    time.sleep(0.15)

    # Second query fails (sensor dropped / became unavailable)
    with patch.object(collector, "_sample_temperature", return_value=(None, "unavailable", UNAVAILABLE_EXPLANATION)):
        temp2, status2, _ = collector.get_temperature()
        # Must NOT reuse 55.0
        assert temp2 is None
        assert status2 == "unavailable"


@pytest.mark.unit
def test_caching_within_ttl_avoids_excessive_polling():
    """Queries within cache TTL return cached values without re-querying hardware."""
    collector = CpuTemperatureCollector(cache_ttl_seconds=5.0)

    call_count = 0
    def mock_sample():
        nonlocal call_count
        call_count += 1
        return (50.0, "available", "Cached")

    with patch.object(collector, "_sample_temperature", side_effect=mock_sample):
        collector.get_temperature()
        collector.get_temperature()
        collector.get_temperature()
        assert call_count == 1


@pytest.mark.unit
def test_temperature_advisory_alert_triggered():
    """High CPU temperature (>= 80°C) triggers an advisory alert distinct from 93% resource risk."""
    detector = SustainedRiskDetector(
        cpu_threshold=93.0,
        memory_threshold=93.0,
        temperature_threshold=80.0,
        sustained_duration_seconds=5.0,
        cooldown_seconds=30.0,
    )

    t0 = 1000.0
    detector._first_breach_time["CPUTemperature"] = t0 - 6.0

    snap = SystemSnapshot(
        timestamp=t0,
        cpu_percent=40.0,
        memory_percent=50.0,
        memory_available_bytes=8 * 1024**3,
        disk_free_bytes=100 * 1024**3,
        disk_busy_percent=5.0,
        top_processes=[],
        unavailable_metrics=(),
        cpu_temperature_c=85.0,
        cpu_temperature_status="available",
    )

    alerts = detector.evaluate_snapshot(snap)
    assert len(alerts) == 1
    alert = alerts[0]
    assert alert.metric_name == "CPUTemperature"
    assert alert.observed_value == 85.0
    assert alert.threshold_value == 80.0
    assert alert.severity == "warning"
    assert alert.threshold_value != DEFAULT_RESOURCE_RISK_THRESHOLD


@pytest.mark.unit
def test_crashguard_remains_operational_when_temperature_unavailable():
    """When temperature is unavailable, overall resource risk detection functions normally."""
    detector = SustainedRiskDetector(
        cpu_threshold=93.0,
        sustained_duration_seconds=5.0,
        cooldown_seconds=30.0,
    )

    t0 = 1000.0
    detector._first_breach_time["CPU"] = t0 - 6.0

    snap = SystemSnapshot(
        timestamp=t0,
        cpu_percent=95.0,
        memory_percent=50.0,
        memory_available_bytes=8 * 1024**3,
        disk_free_bytes=100 * 1024**3,
        disk_busy_percent=5.0,
        top_processes=[],
        unavailable_metrics=(),
        cpu_temperature_c=None,
        cpu_temperature_status="unavailable",
        cpu_temperature_reason=UNAVAILABLE_EXPLANATION,
    )

    alerts = detector.evaluate_snapshot(snap)
    assert len(alerts) == 1
    assert alerts[0].metric_name == "CPU"
    assert alerts[0].observed_value == 95.0


@pytest.mark.unit
def test_ui_temperature_unavailable_card_message(qapp, tmp_path):
    """UI stat card displays 'Unavailable' and the required information notice when temperature is None."""
    db_file = tmp_path / "test_ui_temp.db"
    app, window = create_application(db_path=db_file)

    try:
        snap = SystemSnapshot(
            timestamp=time.time(),
            cpu_percent=15.0,
            memory_percent=40.0,
            memory_available_bytes=8 * 1024**3,
            disk_free_bytes=100 * 1024**3,
            disk_busy_percent=5.0,
            top_processes=[],
            unavailable_metrics=(),
            cpu_temperature_c=None,
            cpu_temperature_status="unavailable",
            cpu_temperature_reason=UNAVAILABLE_EXPLANATION,
        )

        panel = window.crashguard_panel
        panel.update_snapshot(snap)

        temp_val = panel.card_temp.findChild(QLabel, "valLabel")
        temp_sub = panel.card_temp.findChild(QLabel, "subLabel")

        assert temp_val.text() == "Unavailable"
        assert "does not expose CPU temperature to SENTRON without elevated access" in temp_sub.text()
        assert "Other CrashGuard monitoring remains active" in temp_sub.text()

    finally:
        window.exit_application()
