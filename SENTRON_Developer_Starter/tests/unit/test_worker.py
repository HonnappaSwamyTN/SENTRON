"""
Unit tests for Background Monitoring Worker (CrashGuard A - Dev3).
Governing Criteria: AC-13
"""
import time
import pytest
from sentron.crashguard.worker import MonitoringWorker


@pytest.mark.unit
def test_worker_lifecycle_and_bounded_buffer():
    """
    AC-13: Worker starts, captures snapshots into a bounded buffer, and stops cleanly within 2s.
    """
    buffer_cap = 5
    worker = MonitoringWorker(interval_seconds=0.05, buffer_capacity=buffer_cap)

    assert not worker.is_active
    worker.start()
    assert worker.is_active

    # Wait for at least one snapshot to be collected (real OS process iteration may take ~1s)
    start_wait = time.time()
    while time.time() - start_wait < 3.0:
        if len(worker.get_snapshot_history()) > 0:
            break
        time.sleep(0.1)

    history = worker.get_snapshot_history()
    assert len(history) <= buffer_cap
    assert len(history) > 0

    # Test clean shutdown within 2.0s
    t_start = time.time()
    worker.stop(timeout=2.0)
    t_elapsed = time.time() - t_start

    assert t_elapsed < 2.0
    assert not worker.is_active
