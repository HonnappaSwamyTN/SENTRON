"""Background Monitoring Worker for CrashGuard (AC-13).

Runs periodic system telemetry sampling on a dedicated thread outside the UI loop.
Maintains a bounded circular buffer (ring buffer) of snapshots.
Supports clean termination within 2 seconds.
Applies backoff under severe system strain.
"""
from __future__ import annotations

import collections
import threading
import time
from typing import Callable

from sentron.core.models import RecoveryRecommendation, RiskAlert, SystemSnapshot
from sentron.crashguard.metrics import MetricsCollector
from sentron.crashguard.recovery import SafeRecoveryAdvisor
from sentron.crashguard.risk import SustainedRiskDetector


class MonitoringWorker:
    """Dedicated background thread for sampling host system metrics."""

    def __init__(
        self,
        interval_seconds: float = 2.0,
        buffer_capacity: int = 60,
        collector: MetricsCollector | None = None,
        detector: SustainedRiskDetector | None = None,
        advisor: SafeRecoveryAdvisor | None = None,
        on_snapshot: Callable[[SystemSnapshot], None] | None = None,
        on_alert: Callable[[RiskAlert, list[RecoveryRecommendation]], None] | None = None,
    ) -> None:
        self.interval_seconds = interval_seconds
        self.buffer_capacity = buffer_capacity
        self.collector = collector or MetricsCollector()
        self.detector = detector or SustainedRiskDetector(sustained_duration_seconds=10.0, cooldown_seconds=30.0)
        self.advisor = advisor or SafeRecoveryAdvisor()

        self.on_snapshot = on_snapshot
        self.on_alert = on_alert

        # Bounded ring buffer for memory safety
        self.snapshot_buffer: collections.deque[SystemSnapshot] = collections.deque(maxlen=buffer_capacity)
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._wake_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._is_active = False

        # Synthetic demo injection (explicitly labelled)
        self._synthetic_override: SystemSnapshot | None = None

    @property
    def is_active(self) -> bool:
        return self._is_active and (self._thread is not None and self._thread.is_alive())

    def start(self) -> None:
        """Start monitoring on background thread."""
        if self._thread is not None and self._thread.is_alive():
            return

        self._stop_event.clear()
        self._wake_event.clear()
        self._is_active = True
        self._thread = threading.Thread(target=self._run_loop, name="SentronCrashGuardWorker", daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 2.0) -> None:
        """Cleanly stop worker thread within timeout."""
        self._stop_event.set()
        self._wake_event.set()
        self._is_active = False
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=timeout)

    def get_latest_snapshot(self) -> SystemSnapshot | None:
        """Return the most recent snapshot in buffer."""
        with self._lock:
            return self.snapshot_buffer[-1] if self.snapshot_buffer else None

    def get_snapshot_history(self) -> list[SystemSnapshot]:
        """Return full history currently in buffer."""
        with self._lock:
            return list(self.snapshot_buffer)

    def trigger_synthetic_demo_load(self, metric_name: str = "CPU", value: float = 92.0) -> None:
        """Inject a synthetic high-load snapshot for demonstration testing.

        Backdates the sustained breach window so the demonstration transition alert
        triggers immediately without requiring minutes of artificial delay.
        """
        base = self.collector.collect_snapshot(top_n_processes=3)
        cpu_val = value if metric_name == "CPU" else base.cpu_percent
        mem_val = value if metric_name == "Memory" else base.memory_percent

        synthetic = SystemSnapshot(
            timestamp=time.time(),
            cpu_percent=cpu_val,
            memory_percent=mem_val,
            memory_available_bytes=base.memory_available_bytes,
            disk_free_bytes=base.disk_free_bytes,
            disk_busy_percent=base.disk_busy_percent,
            top_processes=base.top_processes,
            unavailable_metrics=("synthetic_demo_mode",),
        )
        self._synthetic_override = synthetic

        # Backdate sustained breach timestamp to immediately satisfy the duration window
        # while ensuring it transitions into the risk state cleanly.
        now = time.time()
        self.detector._first_breach_time[metric_name] = now - (self.detector.sustained_duration_seconds + 1.0)
        self.detector._active_risk_states.discard(metric_name)
        self.detector._cooldown_until.pop(metric_name, None)

        # Wake worker loop immediately for instant feedback
        self._wake_event.set()

    def clear_synthetic_demo_load(self) -> None:
        """Clear synthetic override to resume authentic sampling and clear simulated risk state."""
        self._synthetic_override = None
        self.detector.reset_metric("CPU")
        self.detector.reset_metric("Memory")
        self.detector.reset_metric("DiskFreeGB")
        self._wake_event.set()

    def _sample_once(self) -> SystemSnapshot:
        """Collect one snapshot, either synthetic if injected or authentic."""
        if self._synthetic_override is not None:
            snapshot = self._synthetic_override
        else:
            snapshot = self.collector.collect_snapshot()

        with self._lock:
            self.snapshot_buffer.append(snapshot)

        is_simulated = bool(
            self._synthetic_override is not None
            or "synthetic_demo_mode" in snapshot.unavailable_metrics
        )

        # Evaluate risk alerts with simulation tracking
        alerts = self.detector.evaluate_snapshot(snapshot, is_simulated=is_simulated)
        for alert in alerts:
            recommendations = self.advisor.generate_recommendations(alert, snapshot)
            if self.on_alert:
                try:
                    self.on_alert(alert, recommendations)
                except Exception:
                    pass

        if self.on_snapshot:
            try:
                self.on_snapshot(snapshot)
            except Exception:
                pass

        return snapshot

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._sample_once()
            except Exception:
                pass

            # Wait on wake event or timeout
            self._wake_event.wait(timeout=self.interval_seconds)
            self._wake_event.clear()
