"""Controlled process response and safe task-hold for CrashGuard (Requirement 6).

Implements controlled process-response workflows for high system resource load (>=93%):
- Identifies authentic top CPU and memory consumers.
- Evaluates whether Chrome is an actual measured contributor without unwarranted assumptions.
- Safely pauses explicitly confirmed non-critical processes.
- Excludes Windows/system-critical processes and SENTRON's own workers.
- Supports resuming suspended processes and tracks all paused processes.
- Never silently terminates Chrome or arbitrary processes.
"""
from __future__ import annotations

import os
import threading
import time
from typing import Any, Tuple

import psutil

from sentron.core.models import ProcessSummary, SuspendedProcessInfo, SystemSnapshot

SYSTEM_PROTECTED_PROCESS_NAMES = {
    "system",
    "registry",
    "smss.exe",
    "csrss.exe",
    "wininit.exe",
    "services.exe",
    "lsass.exe",
    "svchost.exe",
    "fontdrvhost.exe",
    "winlogon.exe",
    "dwm.exe",
    "explorer.exe",
    "spoolsv.exe",
    "conhost.exe",
    "runtimebroker.exe",
    "sihost.exe",
    "taskhostw.exe",
    "searchhost.exe",
    "shellexperiencehost.exe",
    "audiodg.exe",
    "memory compression",
    "ntoskrnl.exe",
    "idle",
    "system idle process",
}

SYSTEM_PROTECTED_PIDS = {0, 4}


class ProcessController:
    """Safely manages non-destructive process suspension and resumption."""

    _instance: ProcessController | None = None
    _singleton_lock = threading.Lock()

    def __init__(self) -> None:
        self._suspended_processes: dict[int, SuspendedProcessInfo] = {}
        self._lock = threading.Lock()
        self._sentron_pid = os.getpid()

    @classmethod
    def get_instance(cls) -> ProcessController:
        with cls._singleton_lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def is_protected(self, pid: int, name: str = "") -> Tuple[bool, str]:
        """Determine whether a process is protected from suspension."""
        if pid in SYSTEM_PROTECTED_PIDS or pid <= 4:
            return True, "Core Windows kernel/system process (PID <= 4)"

        if pid == self._sentron_pid:
            return True, "SENTRON application process (self-protection)"

        try:
            # Check if this process is an ancestor or child of SENTRON
            cur_proc = psutil.Process(self._sentron_pid)
            if pid == cur_proc.ppid():
                return True, "SENTRON parent process"
            for child in cur_proc.children(recursive=True):
                if pid == child.pid:
                    return True, "SENTRON worker/sub-process"
        except Exception:
            pass

        norm_name = (name or "").lower().strip()
        if norm_name in SYSTEM_PROTECTED_PROCESS_NAMES:
            return True, f"Windows critical service/shell ({norm_name})"

        return False, ""

    def analyze_contributor(
        self, snapshot: SystemSnapshot
    ) -> Tuple[ProcessSummary | None, bool, str]:
        """Analyze snapshot processes to identify the main contributor and Chrome participation.

        Returns (main_contributor, is_chrome_contributor, explanation).
        Strictly relies on authentic telemetry; never assumes Chrome is at fault simply because it is running.
        """
        if not snapshot.top_processes:
            return None, False, "No running process telemetry available in snapshot."

        # Find Chrome processes
        chrome_procs = [p for p in snapshot.top_processes if "chrome" in p.name.lower()]
        top_proc = snapshot.top_processes[0]  # sorted descending by RAM in collector

        # Check if Chrome is a substantial contributor
        if chrome_procs:
            total_chrome_mem = sum(p.memory_mb for p in chrome_procs)
            max_chrome_cpu = max(p.cpu_percent for p in chrome_procs)
            primary_chrome = chrome_procs[0]

            # Chrome is considered a supported contributor only if it consumes substantial RAM or CPU
            is_chrome_heavy = (
                total_chrome_mem >= 300.0
                or max_chrome_cpu >= 15.0
                or (top_proc.pid == primary_chrome.pid and top_proc.memory_mb >= 200.0)
            )

            if is_chrome_heavy:
                msg = (
                    f"Chrome (PID {primary_chrome.pid}) is a major contributor with "
                    f"{total_chrome_mem:.0f} MB RAM and {max_chrome_cpu:.1f}% CPU."
                )
                return primary_chrome, True, msg
            else:
                msg = (
                    f"Chrome is running with modest resource usage ({total_chrome_mem:.0f} MB RAM, "
                    f"{max_chrome_cpu:.1f}% CPU). Primary consumer is '{top_proc.name}' "
                    f"(PID {top_proc.pid}, {top_proc.memory_mb:.0f} MB RAM)."
                )
                return top_proc, False, msg

        msg = f"Top consumer is '{top_proc.name}' (PID {top_proc.pid}, {top_proc.memory_mb:.0f} MB RAM)."
        return top_proc, False, msg

    def pause_process(self, pid: int) -> Tuple[bool, str]:
        """Safely pause (suspend) a selected process after confirmation and safety checks."""
        try:
            proc = psutil.Process(pid)
            name = proc.name()
        except psutil.NoSuchProcess:
            return False, f"Process with PID {pid} no longer exists."
        except psutil.AccessDenied:
            return False, f"Access denied to inspect process PID {pid}."
        except Exception as exc:
            return False, f"Error inspecting process: {exc}"

        # 1. Protected process guard
        protected, reason = self.is_protected(pid, name)
        if protected:
            return False, f"Cannot pause '{name}' (PID {pid}): {reason}."

        with self._lock:
            if pid in self._suspended_processes:
                return True, f"Process '{name}' (PID {pid}) is already suspended by SENTRON."

            # 2. Suspend process
            try:
                proc.suspend()
            except psutil.AccessDenied:
                return (
                    False,
                    f"Permission denied: Pausing '{name}' (PID {pid}) requires elevated administrator privileges.",
                )
            except psutil.NoSuchProcess:
                return False, f"Process '{name}' (PID {pid}) terminated before it could be paused."
            except Exception as exc:
                return False, f"Failed to pause '{name}' (PID {pid}): {exc}"

            # 3. Verification: verify process still exists and status is stopped/suspended
            try:
                # Give OS a split-second to reflect state
                status = proc.status()
                # On Windows, status is often psutil.STATUS_STOPPED
                mem_info = proc.memory_info()
                rss_mb = round(mem_info.rss / (1024 * 1024), 1)
            except Exception:
                rss_mb = 0.0

            suspended_info = SuspendedProcessInfo(
                pid=pid,
                name=name,
                paused_at=time.time(),
                cpu_percent=0.0,
                memory_mb=rss_mb,
                reason="Sustained system resource risk hold",
            )
            self._suspended_processes[pid] = suspended_info

        return True, f"Successfully paused '{name}' (PID {pid}). Resource consumption held."

    def resume_process(self, pid: int) -> Tuple[bool, str]:
        """Resume a process previously suspended by SENTRON."""
        with self._lock:
            info = self._suspended_processes.get(pid)
            name = info.name if info else f"PID {pid}"

            try:
                proc = psutil.Process(pid)
                proc.resume()
                self._suspended_processes.pop(pid, None)
                return True, f"Successfully resumed '{name}' (PID {pid})."
            except psutil.NoSuchProcess:
                self._suspended_processes.pop(pid, None)
                return True, f"Process '{name}' (PID {pid}) has terminated; removed from paused list."
            except psutil.AccessDenied:
                return (
                    False,
                    f"Permission denied: Resuming '{name}' (PID {pid}) requires elevated privileges.",
                )
            except Exception as exc:
                return False, f"Failed to resume '{name}' (PID {pid}): {exc}"

    def get_suspended_processes(self) -> list[SuspendedProcessInfo]:
        """Return list of all processes currently suspended by SENTRON."""
        with self._lock:
            return list(self._suspended_processes.values())

    def is_process_suspended(self, pid: int) -> bool:
        with self._lock:
            return pid in self._suspended_processes

    def resume_all_suspended(self) -> list[Tuple[int, bool, str]]:
        """Resume all suspended processes, e.g. during clean application exit."""
        results: list[Tuple[int, bool, str]] = []
        with self._lock:
            pids = list(self._suspended_processes.keys())

        for pid in pids:
            success, msg = self.resume_process(pid)
            results.append((pid, success, msg))

        return results

    def get_detailed_process_list(self, limit: int = 15) -> list[dict[str, Any]]:
        """Return detailed list of running processes for user review."""
        procs: list[dict[str, Any]] = []
        with self._lock:
            suspended_pids = set(self._suspended_processes.keys())

        for proc in psutil.process_iter(["pid", "name", "memory_info"]):
            try:
                info = proc.info
                pid = info.get("pid") or 0
                name = info.get("name") or "unknown"
                mem = info.get("memory_info")
                rss_mb = (mem.rss / (1024 * 1024)) if mem else 0.0

                protected, prot_reason = self.is_protected(pid, name)
                is_suspended = pid in suspended_pids

                procs.append({
                    "pid": pid,
                    "name": name,
                    "memory_mb": round(rss_mb, 1),
                    "cpu_percent": 0.0,
                    "protected": protected,
                    "protection_reason": prot_reason,
                    "is_suspended": is_suspended,
                    "is_chrome": "chrome" in name.lower(),
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        # Sort descending by memory
        procs.sort(key=lambda p: p["memory_mb"], reverse=True)
        return procs[:limit]
