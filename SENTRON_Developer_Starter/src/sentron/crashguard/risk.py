"""Sustained-Risk Detector for CrashGuard (AC-10).

Evaluates telemetry against sustained thresholds and duration windows.
Filters out transient spikes. Enforces cooldown periods to prevent alert spam.
Distinguishes resource pressure from definitive crash predictions.
"""
from __future__ import annotations

import time
from uuid import uuid4

from sentron.core.models import RiskAlert, SystemSnapshot


class SustainedRiskDetector:
    """Detects persistent, potentially hazardous system resource pressure."""

    def __init__(
        self,
        cpu_threshold: float = 85.0,
        memory_threshold: float = 85.0,
        disk_free_gb_threshold: float = 5.0,
        sustained_duration_seconds: float = 30.0,
        cooldown_seconds: float = 60.0,
    ) -> None:
        self.cpu_threshold = cpu_threshold
        self.memory_threshold = memory_threshold
        self.disk_free_gb_threshold = disk_free_gb_threshold
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

        metrics_to_check = [
            (
                "CPU",
                snapshot.cpu_percent,
                self.cpu_threshold,
                snapshot.cpu_percent >= self.cpu_threshold,
                "warning" if snapshot.cpu_percent < 95.0 else "critical",
            ),
            (
                "Memory",
                snapshot.memory_percent,
                self.memory_threshold,
                snapshot.memory_percent >= self.memory_threshold,
                "warning" if snapshot.memory_percent < 95.0 else "critical",
            ),
            (
                "DiskFreeGB",
                round(snapshot.disk_free_bytes / (1024**3), 2),
                self.disk_free_gb_threshold,
                (snapshot.disk_free_bytes / (1024**3)) < self.disk_free_gb_threshold and snapshot.disk_free_bytes > 0,
                "warning" if (snapshot.disk_free_bytes / (1024**3)) > 1.0 else "critical",
            ),
        ]

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
                            )
                        )
            else:
                # Reset breach timer, active risk state, and cooldown when condition clears.
                # A subsequent breach will transition into risk and trigger a new alert.
                self._first_breach_time.pop(metric_name, None)
                self._active_risk_states.discard(metric_name)
                self._cooldown_until.pop(metric_name, None)

        return alerts
