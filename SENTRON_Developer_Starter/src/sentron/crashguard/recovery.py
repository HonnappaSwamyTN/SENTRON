"""Safe Recovery Advisor for CrashGuard (AC-12).

Generates safe, non-destructive user recommendations for system pressure.
Strictly separates confirmed observations from suspected causes.
Guarantees is_automated=False. NEVER automatically terminates or suspends processes.
"""
from __future__ import annotations

from uuid import uuid4
from sentron.core.models import (
    RecoveryRecommendation,
    RiskAlert,
    SystemSnapshot,
    WindowsEvidence,
)


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
                help_url="https://support.microsoft.com/windows/save-and-back-up-your-files-and-apps",
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
                    help_url="https://support.microsoft.com/windows/tips-to-improve-pc-performance-in-windows",
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
                    help_url="https://support.microsoft.com/windows/identify-and-stop-high-cpu-usage-apps",
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
                    help_url="https://support.microsoft.com/windows/free-up-drive-space-in-windows",
                )
            )

        # 5. Elevated CPU Temperature guidance (Advisory)
        if alert and alert.metric_name == "CPUTemperature":
            recommendations.append(
                RecoveryRecommendation(
                    recommendation_id=str(uuid4()),
                    severity="warning",
                    title="Elevated CPU Temperature Advisory",
                    suggested_action=(
                        f"Observed CPU temperature of {alert.observed_value:.1f}°C is elevated (advisory threshold: {alert.threshold_value:.1f}°C). "
                        "Check device ventilation and consider reducing heavy compute loads. Note: This warning is an advisory notification, not a universal hardware safety limit."
                    ),
                    confirmed_observations=(
                        f"CPU hardware sensor reading: {alert.observed_value:.1f}°C sustained for {alert.duration_seconds:.0f}s.",
                    ),
                    suspected_causes=(
                        "Prolonged compute workload, restricted airflow, or elevated ambient room temperature.",
                    ),
                    is_automated=False,
                )
            )

        return recommendations

    def generate_evidence_recommendations(
        self,
        evidence: WindowsEvidence,
    ) -> list[RecoveryRecommendation]:
        """Generate safe, non-destructive recovery recommendations for Windows crash/hang evidence."""
        recommendations: list[RecoveryRecommendation] = []
        ev_id = evidence.event_id

        if ev_id == 1000:
            recommendations.append(
                RecoveryRecommendation(
                    recommendation_id=str(uuid4()),
                    severity="critical",
                    title="Resolve Application Crash",
                    suggested_action=(
                        f"Check for available updates for '{evidence.source}' or verify its installed dependencies. "
                        "Do not forcefully kill related services without saving state."
                    ),
                    confirmed_observations=(
                        f"Application Error event 1000 recorded for '{evidence.source}' at {evidence.event_time}.",
                    ),
                    suspected_causes=(
                        "Unhandled runtime exception, access violation, or corrupt dynamic link library.",
                    ),
                    is_automated=False,
                    help_url="https://learn.microsoft.com/troubleshoot/windows-client/application-management/application-crashes-troubleshooting",
                )
            )
        elif ev_id == 1001:
            recommendations.append(
                RecoveryRecommendation(
                    recommendation_id=str(uuid4()),
                    severity="warning",
                    title="Review Windows Error Report (WER)",
                    suggested_action=(
                        f"Review WER diagnostic bucket details for '{evidence.source}' in Reliability Monitor "
                        "or Event Viewer to identify the faulting module."
                    ),
                    confirmed_observations=(
                        f"Windows Error Reporting event 1001 recorded diagnostic fault for '{evidence.source}'.",
                    ),
                    suspected_causes=(
                        "Application fault bucket generated following an unexpected termination.",
                    ),
                    is_automated=False,
                    help_url="https://learn.microsoft.com/windows/win32/wer/windows-error-reporting",
                )
            )
        elif ev_id == 1002:
            recommendations.append(
                RecoveryRecommendation(
                    recommendation_id=str(uuid4()),
                    severity="warning",
                    title="Resolve Application Hang",
                    suggested_action=(
                        f"Allow pending I/O operations for '{evidence.source}' to finish. "
                        "If permanently frozen, save other active work before manually restarting the application."
                    ),
                    confirmed_observations=(
                        f"Application Hang event 1002 recorded for '{evidence.source}' at {evidence.event_time}.",
                    ),
                    suspected_causes=(
                        "Main thread deadlock, slow network/disk I/O, or unresponsive window message pump.",
                    ),
                    is_automated=False,
                    help_url="https://learn.microsoft.com/troubleshoot/windows-client/application-management/application-hangs-troubleshooting",
                )
            )
        elif ev_id in (6008, 41):
            recommendations.append(
                RecoveryRecommendation(
                    recommendation_id=str(uuid4()),
                    severity="critical",
                    title="Investigate Unexpected System Loss / Shutdown",
                    suggested_action=(
                        "Inspect system hardware stability, cooling/thermal metrics, and power supply. "
                        "Review Windows minidump logs if a blue screen (BSOD) accompanied the restart."
                    ),
                    confirmed_observations=(
                        f"System event {ev_id} recorded abrupt shutdown or power loss at {evidence.event_time}.",
                    ),
                    suspected_causes=(
                        "Sudden power loss, forced hard restart, thermal throttling, or kernel bugcheck.",
                    ),
                    is_automated=False,
                    help_url="https://learn.microsoft.com/troubleshoot/windows-client/performance/event-id-41-restart",
                )
            )
        elif ev_id == 1074:
            recommendations.append(
                RecoveryRecommendation(
                    recommendation_id=str(uuid4()),
                    severity="info",
                    title="Review Planned System Restart / Shutdown",
                    suggested_action=(
                        f"Verify whether the restart initiated by '{evidence.source}' was scheduled "
                        "by Windows Update, maintenance scripts, or deliberate user action."
                    ),
                    confirmed_observations=(
                        f"System event 1074 recorded shutdown initiation by '{evidence.source}'.",
                    ),
                    suspected_causes=(
                        "Orderly OS reboot or shutdown request.",
                    ),
                    is_automated=False,
                    help_url="https://learn.microsoft.com/windows/client-management/system-shutdown-events",
                )
            )
        elif ev_id == 219:
            recommendations.append(
                RecoveryRecommendation(
                    recommendation_id=str(uuid4()),
                    severity="warning",
                    title="Check Device Driver Configuration",
                    suggested_action=(
                        f"Open Device Manager to verify device '{evidence.source}'. "
                        "Ensure driver firmware is up to date and compatible with this Windows version."
                    ),
                    confirmed_observations=(
                        f"Kernel-PnP event 219 failed to load driver for device '{evidence.source}'.",
                    ),
                    suspected_causes=(
                        "Missing, corrupt, or incompatible hardware device driver.",
                    ),
                    is_automated=False,
                    help_url="https://support.microsoft.com/windows/update-drivers-manually-in-windows",
                )
            )
        else:
            recommendations.append(
                RecoveryRecommendation(
                    recommendation_id=str(uuid4()),
                    severity="info",
                    title=f"Review Windows Event {ev_id}",
                    suggested_action="Inspect Windows Event Viewer details for diagnostic context.",
                    confirmed_observations=(
                        f"Event ID {ev_id} recorded in {evidence.log_channel} by '{evidence.source}'.",
                    ),
                    suspected_causes=("Operating system diagnostic event logged.",),
                    is_automated=False,
                    help_url="https://learn.microsoft.com/windows/win32/wes/windows-event-log",
                )
            )

        return recommendations

