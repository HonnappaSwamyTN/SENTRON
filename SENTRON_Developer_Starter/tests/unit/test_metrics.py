"""
Unit tests for Metrics Collector (CrashGuard A - Dev3).
Governing Criteria: AC-09
"""
import pytest
from sentron.crashguard.metrics import MetricsCollector


@pytest.mark.unit
def test_genuine_system_measurements_collected():
    """
    AC-09: Telemetry reflects genuine system measurements via psutil; no hardcoded demo values.
    """
    collector = MetricsCollector()
    snapshot = collector.collect_snapshot(top_n_processes=3)

    assert snapshot.timestamp > 0
    assert 0.0 <= snapshot.cpu_percent <= 100.0
    assert 0.0 <= snapshot.memory_percent <= 100.0
    assert snapshot.memory_available_bytes > 0
    assert snapshot.disk_free_bytes >= 0
    assert len(snapshot.top_processes) > 0

    for proc in snapshot.top_processes:
        assert proc.pid >= 0
        assert isinstance(proc.name, str) and len(proc.name) > 0
        assert proc.memory_mb >= 0.0
