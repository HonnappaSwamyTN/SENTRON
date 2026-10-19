"""Safe Recovery Advisor for CrashGuard (AC-12).

Generates safe, non-destructive user recommendations for system pressure.
Strictly separates confirmed observations from suspected causes.
Guarantees is_automated=False. NEVER automatically terminates or suspends processes.
"""
from __future__ import annotations

from uuid import uuid4
from sentron.core.models import RecoveryRecommendation, RiskAlert, SystemSnapshot


class SafeRecoveryAdvisor:
    """Formulates non-destructive recovery steps for the user."""

    def generate_recommendations(
        self,
        alert: RiskAlert | None,
        snapshot: SystemSnapshot,
    ) -> list[RecoveryRecommendation]:
        """Produce safe recovery recommendations without any automatic process kills."""
        recommendations: list[RecoveryRecommendation] = []

        # 1. Baseline universal safe advice: Save open work
        confirmed_baseline = [
            f"Observed system state: CPU {snapshot.cpu_percent:.1f}%, RAM {snapshot.memory_percent:.1f}%."
        ]
        if alert:
            confirmed_baseline.append(
                f"Sustained {alert.metric_name} pressure at {alert.observed_value} (threshold {alert.threshold_value}) for {alert.duration_seconds}s."
            )

        recommendations.append(
            RecoveryRecommendation(
                recommendation_id=str(uuid4()),
                severity="info" if not alert else alert.severity,
                title="Preserve Unsaved Work",
                suggested_action="Save all open files and documents in active applications immediately to prevent data loss.",
                confirmed_observations=tuple(confirmed_baseline),
                suspected_causes=("Heavy workload or background computation occurring.",),
                is_automated=False,
            )
        )

        # 2. Memory pressure guidance
        if snapshot.memory_percent >= 80.0 or (alert and alert.metric_name == "Memory"):
            top_mem = snapshot.top_processes[0] if snapshot.top_processes else None
            observations = [
                f"RAM utilization is at {snapshot.memory_percent:.1f}%.",
                f"Available physical memory: {snapshot.memory_available_bytes / (1024**2):.0f} MB.",
            ]
            if top_mem:
                observations.append(
                    f"Highest consumer: '{top_mem.name}' (PID {top_mem.pid}) is using {top_mem.memory_mb:.1f} MB RAM."
                )

            suggested = "Consider saving your work and manually closing non-essential applications or unused browser tabs."
            if top_mem:
                suggested = (
                    f"Process '{top_mem.name}' (PID {top_mem.pid}) is consuming {top_mem.memory_mb:.1f} MB RAM. "
                    "If this application is idle or unnecessary, save your work and close it manually."
                )

            recommendations.append(
                RecoveryRecommendation(
                    recommendation_id=str(uuid4()),
                    severity="warning" if snapshot.memory_percent < 90.0 else "critical",
                    title="Manage High Memory Usage",
                    suggested_action=suggested,
                    confirmed_observations=tuple(observations),
                    suspected_causes=(
                        "Multiple concurrent applications running or potential memory leakage in heavy processes.",
                    ),
                    is_automated=False,
                )
            )

        # 3. CPU pressure guidance
        if snapshot.cpu_percent >= 80.0 or (alert and alert.metric_name == "CPU"):
            top_cpu = max(snapshot.top_processes, key=lambda p: p.cpu_percent) if snapshot.top_processes else None
            observations = [f"Observed total CPU load: {snapshot.cpu_percent:.1f}%."]
            if top_cpu:
                observations.append(f"Top CPU consumer: '{top_cpu.name}' (PID {top_cpu.pid}) using {top_cpu.cpu_percent:.1f}% CPU.")

            recommendations.append(
                RecoveryRecommendation(
                    recommendation_id=str(uuid4()),
                    severity="warning" if snapshot.cpu_percent < 95.0 else "critical",
                    title="Investigate Sustained CPU Load",
                    suggested_action=(
                        "Allow current background compilation/rendering tasks to complete, or investigate "
                        "if a background process has entered a tight compute loop."
                    ),
                    confirmed_observations=tuple(observations),
                    suspected_causes=(
                        "Compute-intensive workload or active background compilation/indexing.",
                    ),
                    is_automated=False,
                )
            )

        # 4. Low Disk guidance
        free_gb = snapshot.disk_free_bytes / (1024**3)
        if free_gb < 5.0 and snapshot.disk_free_bytes > 0:
            recommendations.append(
                RecoveryRecommendation(
                    recommendation_id=str(uuid4()),
                    severity="critical" if free_gb < 2.0 else "warning",
                    title="Free System Storage",
                    suggested_action="Delete temporary files or move large media files to an external drive.",
                    confirmed_observations=(f"Free disk space on primary drive is only {free_gb:.1f} GB.",),
                    suspected_causes=("Accumulation of temp files, caches, or large build artifacts.",),
                    is_automated=False,
                )
            )

        return recommendations
