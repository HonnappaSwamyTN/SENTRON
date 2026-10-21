"""
Unit tests for Background Monitoring Worker (CrashGuard A - Dev3).
Governing Criteria: AC-13, AC-11, AC-16
"""
import time
from unittest.mock import MagicMock
import pytest

from sentron.core.models import SystemSnapshot, WindowsEvidence
from sentron.core.storage import EventStore
from sentron.crashguard.evidence import WindowsEvidenceCollector
from sentron.crashguard.metrics import MetricsCollector
from sentron.crashguard.risk import SustainedRiskDetector
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
    while time.time() - start_wait < 6.0:
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


@pytest.mark.unit
def test_worker_evidence_cadence_and_alert_triggering():
    """
    Evidence collection is not queried on every telemetry sample,
    but is triggered when a sustained-risk alert occurs or conservative interval elapses.
    """
    mock_metrics = MagicMock(spec=MetricsCollector)
    mock_metrics.collect_snapshot.return_value = SystemSnapshot(
        timestamp=time.time(),
        cpu_percent=10.0,
        memory_percent=20.0,
        memory_available_bytes=4 * 1024**3,
        disk_free_bytes=50 * 1024**3,
        top_processes=(),
    )

    mock_evidence_collector = MagicMock(spec=WindowsEvidenceCollector)
    mock_evidence_collector.collect_evidence.return_value = ([], [])

    detector = SustainedRiskDetector(sustained_duration_seconds=5.0, cooldown_seconds=10.0)

    evidence_received = []

    worker = MonitoringWorker(
        interval_seconds=0.05,
        collector=mock_metrics,
        detector=detector,
        evidence_collector=mock_evidence_collector,
        evidence_interval_seconds=60.0,
        on_evidence=lambda evs, warns: evidence_received.append((evs, warns)),
    )

    # First sample: initial trigger occurs
    worker._sample_once()
    time.sleep(0.05)
    first_call_count = mock_evidence_collector.collect_evidence.call_count
    assert first_call_count >= 1

    # Second sample (normal load, < 60s elapsed): must NOT trigger query again
    worker._sample_once()
    time.sleep(0.05)
    assert mock_evidence_collector.collect_evidence.call_count == first_call_count

    # Third sample: inject sustained alert -> MUST trigger evidence query
    high_snap = SystemSnapshot(
        timestamp=time.time(),
        cpu_percent=95.0,
        memory_percent=20.0,
        memory_available_bytes=4 * 1024**3,
        disk_free_bytes=50 * 1024**3,
        top_processes=(),
    )
    # Backdate breach to trigger alert
    detector._first_breach_time["CPU"] = time.time() - 10.0
    mock_metrics.collect_snapshot.return_value = high_snap

    worker._sample_once()
    time.sleep(0.05)
    # Evidence collector must have been called due to sustained risk alert
    assert mock_evidence_collector.collect_evidence.call_count > first_call_count


@pytest.mark.unit
def test_worker_evidence_non_blocking_and_clean_shutdown():
    """Slow evidence collection does not block worker telemetry and terminates cleanly."""
    mock_evidence_collector = MagicMock(spec=WindowsEvidenceCollector)

    def slow_collect(limit=5):
        time.sleep(0.3)
        return ([
            WindowsEvidence(
                event_id=1000,
                log_channel="Application",
                source="test_app.exe",
                event_time="2026-10-20T12:00:00Z",
                description="Test crash",
            )
        ], [])

    mock_evidence_collector.collect_evidence.side_effect = slow_collect
    mock_evidence_collector.format_diagnostic_statement.return_value = ("Confirmed: crash", "Suspected: fault")

    store = EventStore(db_path=":memory:")
    worker = MonitoringWorker(
        interval_seconds=0.05,
        evidence_collector=mock_evidence_collector,
        event_store=store,
    )

    worker.start()
    assert worker.is_active

    # Trigger async evidence collection
    worker.trigger_evidence_collection_async()

    # Clean shutdown within 2.0s
    t_start = time.time()
    worker.stop(timeout=2.0)
    elapsed = time.time() - t_start

    assert elapsed < 2.0
    assert not worker.is_active
    store.close()


@pytest.mark.unit
def test_worker_severe_load_backoff_suppresses_expensive_evidence_query():
    """
    AC-13 / Security Rules §7.3: When host CPU exceeds 95% or available memory drops below 5%,
    monitoring worker suppresses expensive secondary diagnostics (Windows Event Log queries)
    to prevent adding strain to an overloaded system.
    """
    mock_metrics = MagicMock(spec=MetricsCollector)
    mock_evidence_collector = MagicMock(spec=WindowsEvidenceCollector)
    mock_evidence_collector.collect_evidence.return_value = ([], [])

    detector = SustainedRiskDetector(sustained_duration_seconds=5.0, cooldown_seconds=10.0)

    worker = MonitoringWorker(
        interval_seconds=0.05,
        collector=mock_metrics,
        detector=detector,
        evidence_collector=mock_evidence_collector,
        evidence_interval_seconds=1.0,
    )

    # 1. Normal snapshot: verify helper identifies non-severe load
    normal_snap = SystemSnapshot(
        timestamp=time.time(),
        cpu_percent=40.0,
        memory_percent=50.0,
        memory_available_bytes=4 * 1024**3,
        disk_free_bytes=50 * 1024**3,
        top_processes=(),
    )
    assert not worker.is_severe_load(normal_snap)

    # 2. Severe CPU load (>95%): e.g. 97.5%
    severe_cpu_snap = SystemSnapshot(
        timestamp=time.time(),
        cpu_percent=97.5,
        memory_percent=50.0,
        memory_available_bytes=4 * 1024**3,
        disk_free_bytes=50 * 1024**3,
        top_processes=(),
    )
    assert worker.is_severe_load(severe_cpu_snap)

    # 3. Severe RAM pressure (>95% used / <5% available): e.g. 96.0%
    severe_mem_snap = SystemSnapshot(
        timestamp=time.time(),
        cpu_percent=40.0,
        memory_percent=96.0,
        memory_available_bytes=200 * 1024**2,
        disk_free_bytes=50 * 1024**3,
        top_processes=(),
    )
    assert worker.is_severe_load(severe_mem_snap)

    # 4. Under severe load, evidence collection should NOT be dispatched
    mock_metrics.collect_snapshot.return_value = severe_cpu_snap
    # Backdate breach to trigger alert
    detector._first_breach_time["CPU"] = time.time() - 10.0

    worker._sample_once()
    time.sleep(0.05)
    # The expensive evidence query must be suppressed under severe load
    assert mock_evidence_collector.collect_evidence.call_count == 0

    # Also directly invoking trigger_evidence_collection_async() without force must return False
    dispatched = worker.trigger_evidence_collection_async(force=False)
    assert not dispatched
    assert mock_evidence_collector.collect_evidence.call_count == 0

    # Forced invocation still succeeds if explicitly requested
    dispatched_forced = worker.trigger_evidence_collection_async(force=True)
    assert dispatched_forced

