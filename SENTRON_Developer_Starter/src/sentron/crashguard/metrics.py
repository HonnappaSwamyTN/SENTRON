"""Metrics Collector for CrashGuard (AC-09, AC-14).

Gathers authentic Windows hardware and process telemetry via psutil.
Handles access restrictions and missing counters gracefully.
Simulated data is never presented as authentic telemetry.
"""
from __future__ import annotations

import os
import time
from typing import List
import psutil

from sentron.core.models import ProcessSummary, SystemSnapshot


class MetricsCollector:
    """Collects genuine system telemetry from the local host OS."""

    def __init__(self) -> None:
        # Prime psutil cpu_percent non-blocking call
        try:
            psutil.cpu_percent(interval=None)
        except Exception:
            pass

    def collect_snapshot(self, top_n_processes: int = 5) -> SystemSnapshot:
        """Sample genuine CPU, RAM, Disk, and Process telemetry."""
        timestamp = time.time()
        unavailable: list[str] = []

        # 1. CPU utilization
        try:
            cpu_percent = float(psutil.cpu_percent(interval=None))
        except Exception:
            cpu_percent = 0.0
            unavailable.append("cpu_percent")

        # 2. Virtual Memory
        try:
            vm = psutil.virtual_memory()
            memory_percent = float(vm.percent)
            memory_available_bytes = int(vm.available)
        except Exception:
            memory_percent = 0.0
            memory_available_bytes = 0
            unavailable.append("virtual_memory")

        # 3. Disk usage
        try:
            target_path = "C:\\" if os.name == "nt" else "/"
            disk = psutil.disk_usage(target_path)
            disk_free_bytes = int(disk.free)
            disk_busy_percent = float(disk.percent)
        except Exception:
            disk_free_bytes = 0
            disk_busy_percent = None
            unavailable.append("disk_usage")

        # 4. Top N processes by memory usage
        top_procs: list[ProcessSummary] = []
        try:
            collected_procs = []
            for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_info"]):
                try:
                    info = proc.info
                    pid = info.get("pid") or 0
                    name = info.get("name") or "unknown"
                    mem_info = info.get("memory_info")
                    rss_mb = (mem_info.rss / (1024 * 1024)) if mem_info else 0.0
                    p_cpu = float(info.get("cpu_percent") or 0.0)
                    collected_procs.append((rss_mb, pid, name, p_cpu))
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue

            # Sort by memory descending
            collected_procs.sort(key=lambda p: p[0], reverse=True)
            for rss_mb, pid, name, p_cpu in collected_procs[:top_n_processes]:
                top_procs.append(
                    ProcessSummary(
                        pid=pid,
                        name=name,
                        cpu_percent=p_cpu,
                        memory_mb=round(rss_mb, 1),
                    )
                )
        except Exception:
            unavailable.append("process_list")

        return SystemSnapshot(
            timestamp=timestamp,
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            memory_available_bytes=memory_available_bytes,
            disk_free_bytes=disk_free_bytes,
            disk_busy_percent=disk_busy_percent,
            top_processes=tuple(top_procs),
            unavailable_metrics=tuple(unavailable),
        )
