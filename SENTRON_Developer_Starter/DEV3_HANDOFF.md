# Module Handoff Report — Dev3

> This handoff report documents the completion and verification of CrashGuard A (AC-09, AC-10, AC-13, and AC-14) by Dev3.

---

## 1. Module & Assignment Information
- **Developer Role**: Dev3
- **Subsystem**: CrashGuard A (Metrics Collector, Background Monitoring Worker, Sustained-Risk Detector)
- **Feature Branch**: `feature/dev3-system-metrics`
- **Assigned Files Modified**:
  - `src/sentron/crashguard/metrics.py` (Hardware & process metrics via `psutil`, graceful failure handling)
  - `src/sentron/crashguard/worker.py` (Dedicated background monitoring thread, ring buffer, severe load backoff)
  - `src/sentron/crashguard/risk.py` (Sustained-risk evaluation, duration windows, alert cooldowns)
  - `src/sentron/crashguard/__init__.py` (Co-maintained module entry points with Dev4)
  - `tests/unit/test_metrics.py` (AC-09 genuine telemetry & AC-14 counter degradation tests)
  - `tests/unit/test_risk.py` (AC-10 sustained thresholds, duration windows, multi-metric breaches, cooldowns)
  - `tests/unit/test_worker.py` (AC-13 lifecycle, bounded ring buffer, clean shutdown, severe load backoff)
- **Governing Acceptance Criteria Addressed**: `AC-09`, `AC-10`, `AC-13`, `AC-14` (metrics portion)

---

## 2. Public Interfaces & Contracts

### A. Metrics Collector (`sentron.crashguard.metrics.MetricsCollector`)
- **Inputs Consumed**:
  - `top_n_processes: int = 5`: Maximum number of top memory-consuming processes to record.
- **Outputs Produced**:
  - `SystemSnapshot` (from `sentron.core.models`):
    - `timestamp: float` (epoch time)
    - `cpu_percent: float` (0.0 to 100.0)
    - `memory_percent: float` (0.0 to 100.0)
    - `memory_available_bytes: int`
    - `disk_free_bytes: int`
    - `disk_busy_percent: float | None`
    - `top_processes: tuple[ProcessSummary, ...]`
    - `unavailable_metrics: tuple[str, ...]`
- **Exceptions & Error Handling**:
  - Unprivileged or transient processes that throw `psutil.AccessDenied`, `psutil.NoSuchProcess`, or `psutil.ZombieProcess` during process iteration are skipped silently without aborting sampling.
  - Failures in `cpu_percent`, `virtual_memory`, `disk_usage`, or `process_iter` are caught, assigned safe defaults, and explicitly listed in `unavailable_metrics`.

### B. Sustained-Risk Detector (`sentron.crashguard.risk.SustainedRiskDetector`)
- **Inputs Consumed**:
  - `cpu_threshold: float = 85.0`
  - `memory_threshold: float = 85.0`
  - `disk_free_gb_threshold: float = 5.0`
  - `sustained_duration_seconds: float = 30.0`
  - `cooldown_seconds: float = 60.0`
  - `evaluate_snapshot(snapshot: SystemSnapshot, now: float | None = None, is_simulated: bool = False) -> list[RiskAlert]`
- **Outputs Produced**:
  - `RiskAlert` (from `sentron.core.models`):
    - `alert_id: str` (UUID4)
    - `metric_name: str` ("CPU", "Memory", "DiskFreeGB")
    - `severity: str` ("warning" or "critical" for CPU/Memory >= 95.0% or Disk < 1.0 GB)
    - `observed_value: float`
    - `threshold_value: float`
    - `duration_seconds: float`
    - `cooldown_until: float`
    - `timestamp: float`
    - `is_simulated: bool`
- **Behavior Guarantees**:
  - Transient spikes below `sustained_duration_seconds` produce zero alerts.
  - Alerts are emitted strictly upon transition into sustained risk.
  - Subsequent alerts during `cooldown_seconds` are suppressed.
  - Resetting a metric or conditions normalizing clears active breach state and allows subsequent breaches to alert anew.

### C. Background Monitoring Worker (`sentron.crashguard.worker.MonitoringWorker`)
- **Inputs Consumed**:
  - `interval_seconds: float = 2.0`
  - `buffer_capacity: int = 60`
  - `evidence_interval_seconds: float = 60.0`
  - Callbacks: `on_snapshot`, `on_alert`, `on_evidence`
- **Outputs Produced**:
  - `get_latest_snapshot() -> SystemSnapshot | None`
  - `get_snapshot_history() -> list[SystemSnapshot]`
  - `is_severe_load(snapshot: SystemSnapshot) -> bool` (CPU > 95% or RAM available < 5%)
  - `trigger_evidence_collection_async(force: bool = False) -> bool`
  - Synthetic demo injection: `trigger_synthetic_demo_load()`, `clear_synthetic_demo_load()`
- **Lifecycle & Safety**:
  - Runs on a dedicated daemon thread `SentronCrashGuardWorker` outside the Qt main loop.
  - Bounded memory: `collections.deque(maxlen=buffer_capacity)` automatically purges oldest entries.
  - Clean shutdown within 2.0s upon calling `worker.stop(timeout=2.0)`.
  - **Severe Load Backoff**: Automatically suppresses secondary expensive diagnostics (such as Windows Event Log scans) when system CPU > 95% or available memory < 5%.

---

## 3. Test Verification & Actual Results

### Exact Test Commands Run
```powershell
pytest tests/unit/test_metrics.py tests/unit/test_risk.py tests/unit/test_worker.py -v
```

### Actual Terminal Output
```text
============================= test session starts =============================
platform win32 -- Python 3.14.0, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\Users\alans\Documents\SENTRON\SENTRON_Developer_Starter
configfile: pyproject.toml
plugins: anyio-4.12.1
collecting ... collected 12 items

tests/unit/test_metrics.py::test_genuine_system_measurements_collected PASSED [  8%]
tests/unit/test_metrics.py::test_metrics_handles_permission_error_and_counter_failures_gracefully PASSED [ 16%]
tests/unit/test_metrics.py::test_metrics_process_iter_skips_inaccessible_processes PASSED [ 25%]
tests/unit/test_risk.py::test_transient_spike_does_not_trigger_alert PASSED [ 33%]
tests/unit/test_risk.py::test_sustained_threshold_breach_generates_alert_with_cooldown PASSED [ 41%]
tests/unit/test_risk.py::test_memory_sustained_breach_and_recovery PASSED [ 50%]
tests/unit/test_risk.py::test_disk_free_gb_threshold_and_severities PASSED [ 58%]
tests/unit/test_risk.py::test_multiple_simultaneous_breaches PASSED      [ 66%]
tests/unit/test_worker.py::test_worker_lifecycle_and_bounded_buffer PASSED [ 75%]
tests/unit/test_worker.py::test_worker_evidence_cadence_and_alert_triggering PASSED [ 83%]
tests/unit/test_worker.py::test_worker_evidence_non_blocking_and_clean_shutdown PASSED [ 91%]
tests/unit/test_worker.py::test_worker_severe_load_backoff_suppresses_expensive_evidence_query PASSED [100%]

============================= 12 passed in 2.18s ==============================
```

### Full Backend Unit Test Verification
```powershell
pytest tests/unit/test_metrics.py tests/unit/test_risk.py tests/unit/test_worker.py tests/unit/test_platform_fallback.py tests/unit/test_input_risk.py tests/unit/test_sensitive_data.py tests/unit/test_policy.py tests/unit/test_approval.py tests/unit/test_executor.py tests/unit/test_storage.py tests/unit/test_evidence.py tests/unit/test_recovery.py -q
........................................................................................
============================= 88 passed in 2.35s ==============================
```

---

## 4. Security & Safety Compliance Verification
- [x] **No External AI APIs**: 100% offline, deterministic mathematical rules; zero cloud LLMs, network calls, or paid APIs.
- [x] **Secret Redaction**: CrashGuard processes metric counters only; no credential storage or raw text leakage.
- [x] **CrashGuard Non-Destructive**: **Zero process termination, suspension, or pausing logic exists in the codebase.**
- [x] **Genuine Telemetry**: All live data is sampled via `psutil`. Any synthetic testing mode is explicitly tagged with `is_simulated=True` or `"synthetic_demo_mode"` in `unavailable_metrics`.
- [x] **Bounded Memory**: Rolling history uses bounded `collections.deque(maxlen=60)`. Oldest samples are purged automatically.
- [x] **Severe Resource Pressure Backoff**: Suppresses expensive secondary diagnostic queries when CPU exceeds 95% or available RAM drops below 5%.

---

## 5. Known Limitations & Edge Cases
1. **First Process CPU Reading**:
   In non-blocking mode (`interval=None`), `proc.cpu_percent()` may return `0.0` on the very first invocation until delta time accumulates.
2. **Platform Root Path**:
   Disk usage checks target `C:\` on Windows (`os.name == "nt"`) and `/` on POSIX systems.
3. **Elevated Privileges**:
   Some protected Windows processes (system, antivirus) cannot have memory or CPU read without Administrator privileges. These are safely skipped via `psutil.AccessDenied`.

---

## 6. Integration Notes & Demo Steps

### Prerequisites
- Python 3.11+ with `psutil` installed.
- No external services or database migrations required.

### Quick Verification Script
```python
import time
from sentron.crashguard.metrics import MetricsCollector
from sentron.crashguard.risk import SustainedRiskDetector
from sentron.crashguard.worker import MonitoringWorker

# 1. Collect authentic snapshot
collector = MetricsCollector()
snapshot = collector.collect_snapshot(top_n_processes=3)
print(f"CPU: {snapshot.cpu_percent}%, Memory: {snapshot.memory_percent}%, Disk Free: {round(snapshot.disk_free_bytes / (1024**3), 1)} GB")
print(f"Top process: {snapshot.top_processes[0].name} ({snapshot.top_processes[0].memory_mb} MB)")

# 2. Worker Lifecycle with callbacks
def on_sample(snap):
    print(f"[Worker Sample] CPU: {snap.cpu_percent}% | RAM: {snap.memory_percent}%")

worker = MonitoringWorker(interval_seconds=1.0, buffer_capacity=10, on_snapshot=on_sample)
worker.start()
time.sleep(2.5)
worker.stop(timeout=2.0)
print(f"Worker stopped cleanly. Buffer samples: {len(worker.get_snapshot_history())}")
```
