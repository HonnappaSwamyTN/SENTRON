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


@pytest.mark.unit
def test_metrics_handles_permission_error_and_counter_failures_gracefully(monkeypatch):
    """
    AC-14: If specific hardware counters or APIs raise AccessDenied / OSError,
    MetricsCollector continues operating and records failures in unavailable_metrics.
    """
    import psutil

    def raise_denied(*args, **kwargs):
        raise psutil.AccessDenied(pid=0, name="access_denied_test")

    monkeypatch.setattr(psutil, "cpu_percent", raise_denied)
    monkeypatch.setattr(psutil, "virtual_memory", raise_denied)
    monkeypatch.setattr(psutil, "disk_usage", raise_denied)
    monkeypatch.setattr(psutil, "process_iter", raise_denied)

    collector = MetricsCollector()
    snapshot = collector.collect_snapshot(top_n_processes=3)

    assert snapshot.timestamp > 0
    assert snapshot.cpu_percent == 0.0
    assert snapshot.memory_percent == 0.0
    assert snapshot.memory_available_bytes == 0
    assert snapshot.disk_free_bytes == 0
    assert snapshot.top_processes == ()

    # All 4 failing subsystems are explicitly recorded
    assert "cpu_percent" in snapshot.unavailable_metrics
    assert "virtual_memory" in snapshot.unavailable_metrics
    assert "disk_usage" in snapshot.unavailable_metrics
    assert "process_list" in snapshot.unavailable_metrics


@pytest.mark.unit
def test_metrics_process_iter_skips_inaccessible_processes(monkeypatch):
    """
    AC-14 / AC-09: Unprivileged or transient processes that raise AccessDenied /
    NoSuchProcess during process iteration are skipped without failing the snapshot.
    """
    import psutil
    from unittest.mock import MagicMock

    class MockProc:
        def __init__(self, pid, name, rss, cpu, raise_on_info=False):
            self.raise_on_info = raise_on_info
            mem_mock = MagicMock()
            mem_mock.rss = rss
            self._info = {
                "pid": pid,
                "name": name,
                "cpu_percent": cpu,
                "memory_info": mem_mock,
            }

        @property
        def info(self):
            if self.raise_on_info:
                raise psutil.AccessDenied(pid=999, name="protected.exe")
            return self._info

    mock_procs = [
        MockProc(101, "app1.exe", rss=200 * 1024 * 1024, cpu=5.0),
        MockProc(999, "protected.exe", rss=0, cpu=0.0, raise_on_info=True),
        MockProc(102, "app2.exe", rss=400 * 1024 * 1024, cpu=12.0),
    ]

    monkeypatch.setattr(psutil, "process_iter", lambda attrs: mock_procs)

    collector = MetricsCollector()
    snapshot = collector.collect_snapshot(top_n_processes=5)

    # Process list was collected without fatal error
    assert "process_list" not in snapshot.unavailable_metrics
    assert len(snapshot.top_processes) == 2
    # Sorted by memory descending: app2 (400MB) followed by app1 (200MB)
    assert snapshot.top_processes[0].name == "app2.exe"
    assert snapshot.top_processes[0].memory_mb == 400.0
    assert snapshot.top_processes[1].name == "app1.exe"
    assert snapshot.top_processes[1].memory_mb == 200.0

