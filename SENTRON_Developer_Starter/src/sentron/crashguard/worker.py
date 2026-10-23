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
from typing import TYPE_CHECKING, Callable

from sentron.core.models import (
    RecoveryRecommendation,
    RiskAlert,
    SystemSnapshot,
    WindowsEvidence,
)
from sentron.crashguard.evidence import (
    WindowsEvidenceCollector,
    load_seen_ids_from_json,
    persist_windows_evidence,
    save_seen_ids_to_json,
)
from sentron.crashguard.metrics import MetricsCollector
from sentron.crashguard.process_control import ProcessController
from sentron.crashguard.recovery import SafeRecoveryAdvisor
from sentron.crashguard.risk import DEFAULT_RESOURCE_RISK_THRESHOLD, SustainedRiskDetector

if TYPE_CHECKING:
    from pathlib import Path
    from sentron.core.storage import EventStore


class MonitoringWorker:
    """Dedicated background thread for sampling host system metrics."""

    def __init__(
        self,
        interval_seconds: float = 2.0,
        buffer_capacity: int = 60,
        collector: MetricsCollector | None = None,
        detector: SustainedRiskDetector | None = None,
        advisor: SafeRecoveryAdvisor | None = None,
        evidence_collector: WindowsEvidenceCollector | None = None,
        event_store: EventStore | None = None,
        evidence_interval_seconds: float = 60.0,
        state_file_path: str | Path | None = None,
        on_snapshot: Callable[[SystemSnapshot], None] | None = None,
        on_alert: Callable[[RiskAlert, list[RecoveryRecommendation]], None] | None = None,
        on_evidence: Callable[[list[WindowsEvidence], list[str]], None] | None = None,
    ) -> None:
        self.interval_seconds = interval_seconds
        self.buffer_capacity = buffer_capacity
        self.collector = collector or MetricsCollector()
        self.detector = detector or SustainedRiskDetector(
            resource_risk_threshold=DEFAULT_RESOURCE_RISK_THRESHOLD,
            sustained_duration_seconds=10.0,
            cooldown_seconds=30.0,
        )
        self.advisor = advisor or SafeRecoveryAdvisor()
        self.evidence_collector = evidence_collector or WindowsEvidenceCollector()
        self.process_controller = ProcessController.get_instance()
        self.event_store = event_store
        self.evidence_interval_seconds = evidence_interval_seconds
        self.state_file_path = state_file_path

        self.on_snapshot = on_snapshot
        self.on_alert = on_alert
        self.on_evidence = on_evidence

        # Evidence collection state and threading
        self._last_evidence_time: float = 0.0
        self._evidence_thread: threading.Thread | None = None
        self._evidence_lock = threading.Lock()
        self._latest_evidence: list[WindowsEvidence] = []
        self._latest_evidence_warnings: list[str] = []
        self._seen_evidence_ids: set[str] = (
            load_seen_ids_from_json(state_file_path) if state_file_path else set()
        )

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
        """Cleanly stop worker thread within timeout and safely resume any paused processes."""
        t_start = time.time()
        self._stop_event.set()
        self._wake_event.set()
        self._is_active = False

        # Budget join timeouts so total elapsed time never exceeds the given timeout
        budget = max(0.01, timeout - 0.05)

        if self._thread is not None and self._thread.is_alive():
            elapsed = time.time() - t_start
            remaining = budget - elapsed
            if remaining > 0.005:
                self._thread.join(timeout=remaining)

        if self._evidence_thread is not None and self._evidence_thread.is_alive():
            elapsed = time.time() - t_start
            remaining = budget - elapsed
            if remaining > 0.005:
                self._evidence_thread.join(timeout=remaining)

        if self.state_file_path and self._seen_evidence_ids:
            save_seen_ids_to_json(self._seen_evidence_ids, self.state_file_path)


        # Release any processes suspended by SENTRON so none remain held
        try:
            self.process_controller.resume_all_suspended()
        except Exception:
            pass

    def get_latest_snapshot(self) -> SystemSnapshot | None:
        """Return the most recent snapshot in buffer."""
        with self._lock:
            return self.snapshot_buffer[-1] if self.snapshot_buffer else None

    def get_snapshot_history(self) -> list[SystemSnapshot]:
        """Return full history currently in buffer."""
        with self._lock:
            return list(self.snapshot_buffer)

    def trigger_synthetic_demo_load(self, metric_name: str = "CPU", value: float = 94.0) -> None:
        """Inject a synthetic high-load snapshot for demonstration testing.

        Backdates the sustained breach window so the demonstration transition alert
        triggers immediately without requiring minutes of artificial delay.
        """
        base = self.collector.collect_snapshot(top_n_processes=3)
        cpu_val = value if metric_name == "CPU" else base.cpu_percent
        mem_val = value if metric_name == "Memory" else base.memory_percent
        temp_val = value if metric_name == "CPUTemperature" else base.cpu_temperature_c
        temp_status = "available" if metric_name == "CPUTemperature" else base.cpu_temperature_status
        temp_reason = (
            "Simulated thermal zone [SIMULATED / TEST DATA]"
            if metric_name == "CPUTemperature"
            else base.cpu_temperature_reason
        )

        synthetic = SystemSnapshot(
            timestamp=time.time(),
            cpu_percent=cpu_val,
            memory_percent=mem_val,
            memory_available_bytes=base.memory_available_bytes,
            disk_free_bytes=base.disk_free_bytes,
            disk_busy_percent=base.disk_busy_percent,
            top_processes=base.top_processes,
            unavailable_metrics=("synthetic_demo_mode",),
            cpu_temperature_c=temp_val,
            cpu_temperature_status=temp_status,
            cpu_temperature_reason=temp_reason,
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
        self.detector.reset_metric("CPUTemperature")
        self._wake_event.set()

    def is_severe_load(self, snapshot: SystemSnapshot) -> bool:
        """Return True if system is under severe pressure (CPU > 95% or available RAM < 5%)."""
        if snapshot.cpu_percent > 95.0:
            return True
        if snapshot.memory_percent > 95.0:
            return True
        return False

    def trigger_evidence_collection_async(self, force: bool = False) -> bool:
        """Trigger non-blocking background collection of Windows crash evidence.

        Suppresses collection under severe load unless force=True (Security Rules §7.3).
        Returns True if a collection thread was dispatched, False otherwise.
        """
        with self._evidence_lock:
            if self._evidence_thread is not None and self._evidence_thread.is_alive():
                return False
            latest = self.get_latest_snapshot()
            if not force and latest is not None and self.is_severe_load(latest):
                return False
            self._last_evidence_time = time.time()
            self._evidence_thread = threading.Thread(
                target=self._run_evidence_collection,
                name="SentronCrashGuardEvidenceCollector",
                daemon=True,
            )
            self._evidence_thread.start()
            return True

    def _run_evidence_collection(self) -> tuple[list[WindowsEvidence], list[str]]:
        """Executed on dedicated background thread to keep telemetry non-blocking."""
        if self._stop_event.is_set():
            return [], []
        try:
            records, warnings = self.evidence_collector.collect_evidence(limit=5)
        except Exception as exc:
            records, warnings = [], [f"windows_evidence_error:{exc}"]

        with self._evidence_lock:
            self._latest_evidence = list(records)
            self._latest_evidence_warnings = list(warnings)

        if self.event_store is not None and records:
            try:
                persist_windows_evidence(
                    store=self.event_store,
                    evidence_list=records,
                    collector=self.evidence_collector,
                    seen_ids=self._seen_evidence_ids,
                    state_file_path=self.state_file_path,
                )
            except Exception:
                pass

        if self.on_evidence:
            try:
                self.on_evidence(records, warnings)
            except Exception:
                pass

        return records, warnings

    def poll_evidence(self, limit: int = 5) -> tuple[list[WindowsEvidence], list[str]]:
        """Synchronously collect evidence, persist with deduplication, and notify listener."""
        self._last_evidence_time = time.time()
        try:
            records, warnings = self.evidence_collector.collect_evidence(limit=limit)
        except Exception as exc:
            records, warnings = [], [f"windows_evidence_error:{exc}"]

        with self._evidence_lock:
            self._latest_evidence = list(records)
            self._latest_evidence_warnings = list(warnings)

        if self.event_store is not None and records:
            try:
                persist_windows_evidence(
                    store=self.event_store,
                    evidence_list=records,
                    collector=self.evidence_collector,
                    seen_ids=self._seen_evidence_ids,
                    state_file_path=self.state_file_path,
                )
            except Exception:
                pass

        if self.on_evidence:
            try:
                self.on_evidence(records, warnings)

            except Exception:
                pass

        return records, warnings

    def get_latest_evidence(self) -> tuple[list[WindowsEvidence], list[str]]:
        """Return the most recently collected evidence records and warnings."""
        with self._evidence_lock:
            return list(self._latest_evidence), list(self._latest_evidence_warnings)

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

        # Trigger evidence collection on authentic sustained-risk alert or conservative interval (30-60s)
        # Suppressed under severe load (>95% CPU or >95% RAM) to prevent system strain (Security Rules §7.3)
        now = time.time()
        has_risk_alert = len(alerts) > 0 and not is_simulated
        interval_due = (
            self._last_evidence_time == 0.0 or (now - self._last_evidence_time >= self.evidence_interval_seconds)
        )
        severe_load = self.is_severe_load(snapshot)
        if (has_risk_alert or interval_due) and not severe_load:
            self.trigger_evidence_collection_async()

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
