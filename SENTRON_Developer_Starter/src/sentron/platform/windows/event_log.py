"""Windows Event Log adapter for CrashGuard (AC-11, AC-14).

Queries Application and System event log channels for hang/crash/shutdown events.
Gracefully handles access restrictions or non-Windows environments without crashing.
"""
from __future__ import annotations

import os
import subprocess
from typing import Any
from sentron.core.models import WindowsEvidence


class WindowsEventLogAdapter:
    """Safely queries Windows Event Logs for Application Error, Hang, and Shutdown events."""

    def __init__(self) -> None:
        self.is_windows = os.name == "nt"

    def query_recent_diagnostic_events(self, limit: int = 5) -> tuple[list[WindowsEvidence], list[str]]:
        """Query recent crash/hang event logs.

        Returns:
            (evidence_records, unavailable_warnings)
        """
        if not self.is_windows:
            return [], ["windows_event_log_unsupported_platform"]

        unavailable: list[str] = []
        evidence_list: list[WindowsEvidence] = []

        # Target event IDs:
        # 1000: Application Error (Crash) - Application log
        # 1002: Application Hang - Application log
        # 6008: Unexpected Shutdown - System log
        try:
            # Query Application (1000, 1002) and System (6008) event channels safely
            ps_script = (
                f"$e1 = Get-WinEvent -FilterHashtable @{{LogName='Application'; ID=1000,1002}} -MaxEvents {limit} -ErrorAction SilentlyContinue; "
                f"$e2 = Get-WinEvent -FilterHashtable @{{LogName='System'; ID=6008}} -MaxEvents {limit} -ErrorAction SilentlyContinue; "
                f"$events = @($e1) + @($e2) | Where-Object {{ $_ -ne $null }} | Sort-Object TimeCreated -Descending | Select-Object -First {limit}; "
                "foreach ($e in $events) { "
                "$time = $e.TimeCreated.ToString('o'); "
                "$id = $e.Id; "
                "$log = $e.LogName; "
                "$src = $e.ProviderName; "
                "$msg = $e.Message -replace \"[\r\n]+\", ' '; "
                "if ($msg.Length -gt 150) { $msg = $msg.Substring(0, 150) + '...' }; "
                "Write-Output \"$id|$log|$src|$time|$msg\" "
                "}"
            )
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_script],
                capture_output=True,
                text=True,
                timeout=3,
                check=False,
            )
            if result.returncode == 0 and result.stdout.strip():
                for line in result.stdout.strip().splitlines():
                    parts = line.split("|", 4)
                    if len(parts) == 5:
                        ev_id_str, log_chan, provider, ev_time, desc = parts
                        try:
                            ev_id = int(ev_id_str.strip())
                        except ValueError:
                            ev_id = 1000
                        evidence_list.append(
                            WindowsEvidence(
                                event_id=ev_id,
                                log_channel=log_chan.strip(),
                                source=provider.strip(),
                                event_time=ev_time.strip(),
                                description=desc.strip(),
                            )
                        )
                    elif len(parts) == 4:
                        # Backward compatibility if 4-part line returned
                        ev_id_str, provider, ev_time, desc = parts
                        try:
                            ev_id = int(ev_id_str.strip())
                        except ValueError:
                            ev_id = 1000
                        evidence_list.append(
                            WindowsEvidence(
                                event_id=ev_id,
                                log_channel="Application",
                                source=provider.strip(),
                                event_time=ev_time.strip(),
                                description=desc.strip(),
                            )
                        )
        except subprocess.TimeoutExpired:
            unavailable.append("windows_event_log_timeout")
        except PermissionError:
            unavailable.append("windows_event_log_access_denied")
        except Exception:
            unavailable.append("windows_event_log_unavailable")

        return evidence_list, unavailable
