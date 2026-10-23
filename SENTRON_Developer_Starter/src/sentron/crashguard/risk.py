"""Sustained-Risk Detector for CrashGuard (AC-10, Requirements 1 & 5).

Evaluates telemetry against sustained thresholds and duration windows.
Single source of truth for the configurable 93% system resource-risk threshold.
Filters out transient spikes. Enforces cooldown periods to prevent alert spam.
Distinguishes resource pressure (CPU/Memory at 93%) from advisory temperature warnings.
"""
from __future__ import annotations

import time
from uuid import uuid4

from sentron.core.models import RiskAlert, SystemSnapshot
from sentron.crashguard.process_control import ProcessController

DEFAULT_RESOURCE_RISK_THRESHOLD: float = 93.0
DEFAULT_TEMPERATURE_ADVISORY_THRESHOLD: float = 80.0


class SustainedRiskDetector:
    """Detects persistent, potentially hazardous system resource pressure."""

    def __init__(
        self,
        resource_risk_threshold: float = DEFAULT_RESOURCE_RISK_THRESHOLD,
        cpu_threshold: float | None = None,
        memory_threshold: float | None = None,
        disk_free_gb_threshold: float = 5.0,
        temperature_threshold: float = DEFAULT_TEMPERATURE_ADVISORY_THRESHOLD,
        sustained_duration_seconds: float = 30.0,
        cooldown_seconds: float = 60.0,
    ) -> None:
        self.resource_risk_threshold = resource_risk_threshold
        self.cpu_threshold = cpu_threshold if cpu_threshold is not None else resource_risk_threshold
        self.memory_threshold = memory_threshold if memory_threshold is not None else resource_risk_threshold
        self.disk_free_gb_threshold = disk_free_gb_threshold
        self.temperature_threshold = temperature_threshold
        self.sustained_duration_seconds = sustained_duration_seconds
        self.cooldown_seconds = cooldown_seconds

        # Internal state tracking
        self._first_breach_time: dict[str, float] = {}
        self._cooldown_until: dict[str, float] = {}
        self._active_risk_states: set[str] = set()

    def reset(self) -> None:
        """Reset internal tracking states."""
        self._first_breach_time.clear()
        self._cooldown_until.clear()
        self._active_risk_states.clear()

    def reset_metric(self, metric_name: str) -> None:
        """Reset tracking state for a specific metric (clears condition)."""
        self._first_breach_time.pop(metric_name, None)
        self._cooldown_until.pop(metric_name, None)
        self._active_risk_states.discard(metric_name)

    def is_active_risk(self, metric_name: str) -> bool:
        """Return True if metric is currently in an active sustained risk state."""
        return metric_name in self._active_risk_states

    def evaluate_snapshot(
        self,
        snapshot: SystemSnapshot,
        now: float | None = None,
        is_simulated: bool = False,
    ) -> list[RiskAlert]:
        """Evaluate a snapshot against sustained-pressure rules.

        Returns a list of RiskAlert instances triggered on transition into risk.
        Suppresses repeated alerts for the same continuous condition.
        """
        current_time = now if now is not None else snapshot.timestamp
        simulated = is_simulated or ("synthetic_demo_mode" in snapshot.unavailable_metrics)
        alerts: list[RiskAlert] = []

        # Analyze main suspected contributor from genuine processes
        controller = ProcessController.get_instance()
        top_contrib, is_chrome, contrib_details = controller.analyze_contributor(snapshot)
        contrib_proc = top_contrib.name if top_contrib else None
        contrib_pid = top_contrib.pid if top_contrib else None

        # Determine severity: at or above 95% is critical, otherwise warning
        cpu_sev = "warning" if snapshot.cpu_percent < 95.0 else "critical"
        mem_sev = "warning" if snapshot.memory_percent < 95.0 else "critical"

        metrics_to_check: list[tuple[str, float, float, bool, str]] = [
            (
                "CPU",
                snapshot.cpu_percent,
                self.cpu_threshold,
                snapshot.cpu_percent >= self.cpu_threshold,
                cpu_sev,
            ),
            (
                "Memory",
                snapshot.memory_percent,
                self.memory_threshold,
                snapshot.memory_percent >= self.memory_threshold,
                mem_sev,
            ),
            (
                "DiskFreeGB",
                round(snapshot.disk_free_bytes / (1024**3), 2),
                self.disk_free_gb_threshold,
                (snapshot.disk_free_bytes / (1024**3)) < self.disk_free_gb_threshold and snapshot.disk_free_bytes > 0,
                "warning" if (snapshot.disk_free_bytes / (1024**3)) > 1.0 else "critical",
            ),
        ]

        # Temperature Advisory Warning (Clearly distinguished from 93% system resource risk)
        if snapshot.cpu_temperature_c is not None:
            metrics_to_check.append((
                "CPUTemperature",
                snapshot.cpu_temperature_c,
                self.temperature_threshold,
                snapshot.cpu_temperature_c >= self.temperature_threshold,
                "warning",  # advisory
            ))

        for metric_name, observed_val, thresh_val, is_breached, severity in metrics_to_check:
            if is_breached:
                if metric_name not in self._first_breach_time:
                    self._first_breach_time[metric_name] = current_time

                duration = current_time - self._first_breach_time[metric_name]

                # Check if sustained beyond required duration window
                if duration >= self.sustained_duration_seconds:
                    cooldown_expiry = self._cooldown_until.get(metric_name, 0.0)
                    # Trigger alert strictly on transition into risk state.
                    # Suppress repeated alerts while the continuous condition persists.
                    if metric_name not in self._active_risk_states and current_time >= cooldown_expiry:
                        self._active_risk_states.add(metric_name)
                        cooldown_target = current_time + self.cooldown_seconds
                        self._cooldown_until[metric_name] = cooldown_target

                        alerts.append(
                            RiskAlert(
                                alert_id=str(uuid4()),
                                metric_name=metric_name,
                                severity=severity,
                                observed_value=observed_val,
                                threshold_value=thresh_val,
                                duration_seconds=round(duration, 1),
                                cooldown_until=cooldown_target,
                                timestamp=current_time,
                                is_simulated=simulated,
                                contributor_process=contrib_proc,
                                contributor_pid=contrib_pid,
                                contributor_details=contrib_details,
                            )
                        )
            else:
                # Reset breach timer, active risk state, and cooldown when condition clears.
                # A subsequent breach will transition into risk and trigger a new alert.
                self._first_breach_time.pop(metric_name, None)
                self._active_risk_states.discard(metric_name)
                self._cooldown_until.pop(metric_name, None)

        return alerts
