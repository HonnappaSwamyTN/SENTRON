"""CrashGuard: Real-time system monitoring, sustained risk detection, and safe recovery."""
from sentron.crashguard.evidence import (
    WindowsEvidenceCollector,
    make_evidence_unified_event,
    persist_windows_evidence,
)
from sentron.crashguard.metrics import MetricsCollector
from sentron.crashguard.recovery import SafeRecoveryAdvisor
from sentron.crashguard.risk import SustainedRiskDetector
from sentron.crashguard.worker import MonitoringWorker

__all__ = [
    "MetricsCollector",
    "MonitoringWorker",
    "SafeRecoveryAdvisor",
    "SustainedRiskDetector",
    "WindowsEvidenceCollector",
    "make_evidence_unified_event",
    "persist_windows_evidence",
]
