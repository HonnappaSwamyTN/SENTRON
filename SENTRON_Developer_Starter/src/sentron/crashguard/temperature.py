"""Windows Hardware CPU Temperature Monitor for CrashGuard.

Detects and displays genuine CPU temperature in °C where hardware and OS expose it
using the current user's normal permissions (never requires administrator privileges).

Uses best-effort, Windows-compatible sources:
1. WMI Performance Counters (root/cimv2:Win32_PerfFormattedData_Counters_ThermalZoneInformation)
2. OpenHardwareMonitor / LibreHardwareMonitor WMI interfaces (root/OpenHardwareMonitor, root/LibreHardwareMonitor)
3. ACPI Thermal Zones (root/wmi:MSAcpi_ThermalZoneTemperature)
4. Win32 Temperature Probes (root/cimv2:Win32_TemperatureProbe)
5. psutil sensors fallback (cross-platform)

Guarantees:
- Never requests administrator privileges or triggers UAC prompts.
- Never relaunches SENTRON as administrator or installs elevated background services.
- If a source returns Access Denied, is unsupported, or returns invalid readings,
  it safely advances to the next available source.
- Never fabricates, estimates, or reuses stale readings as if they were current.
- If no accessible source provides a valid reading, reports 'unavailable' with:
  "Your hardware or Windows configuration does not expose CPU temperature to SENTRON without elevated access. Other CrashGuard monitoring remains active."
"""
from __future__ import annotations

import os
import sys
import time
from typing import Tuple

import psutil


def convert_raw_temperature_to_celsius(raw_value: float) -> float | None:
    """Validate and convert raw sensor value (Kelvin, tenths of Kelvin, or Celsius) to Celsius.
    
    Accepts only physically plausible CPU temperatures (10.0°C to 125.0°C).
    Returns None for invalid or fabricated values (e.g. <= 0, > 130).
    """
    try:
        val = float(raw_value)
    except (ValueError, TypeError):
        return None

    if val <= 0:
        return None

    # Case A: Tenths of Kelvin (e.g., 2900 - 4000 for ~17°C to ~127°C)
    if val > 1000.0:
        celsius = (val - 2732.0) / 10.0
    # Case B: Kelvin directly (e.g., 283.15 to 398.15 for 10°C to 125°C)
    elif 200.0 <= val <= 500.0:
        celsius = val - 273.15
    # Case C: Already in Celsius (e.g., 10.0 to 125.0)
    elif 10.0 <= val <= 125.0:
        celsius = val
    else:
        return None

    if 10.0 <= celsius <= 125.0:
        return round(celsius, 1)
    return None


UNAVAILABLE_EXPLANATION = (
    "Your hardware or Windows configuration does not expose CPU temperature to SENTRON "
    "without elevated access. Other CrashGuard monitoring remains active."
)


class CpuTemperatureCollector:
    """Best-effort authentic CPU temperature reader requiring zero elevation."""

    def __init__(self, cache_ttl_seconds: float = 4.0) -> None:
        self.cache_ttl_seconds = cache_ttl_seconds
        self._last_reading_time: float = 0.0
        self._cached_temp: float | None = None
        self._cached_status: str = "unavailable"
        self._cached_explanation: str = UNAVAILABLE_EXPLANATION

    def get_temperature(self, force_refresh: bool = False) -> Tuple[float | None, str, str]:
        """Return (temperature_celsius, status, explanation).

        Status values: 'available' or 'unavailable'.
        Uses caching to avoid excessive polling, but never reuses stale readings
        once the cache TTL expires.
        """
        now = time.time()
        # Return cached reading only while within the valid TTL window
        if not force_refresh and (now - self._last_reading_time < self.cache_ttl_seconds):
            return self._cached_temp, self._cached_status, self._cached_explanation

        # Sample fresh reading using normal user permissions
        temp_c, status, explanation = self._sample_temperature()
        self._last_reading_time = now
        # Always update cache with fresh state (never retain stale values if sensor drops)
        self._cached_temp = temp_c
        self._cached_status = status
        self._cached_explanation = explanation
        return temp_c, status, explanation

    def _sample_temperature(self) -> Tuple[float | None, str, str]:
        """Perform best-effort hardware query across accessible sensor APIs without elevation."""
        if os.name != "nt":
            return self._query_psutil()

        try:
            import win32com.client
        except ImportError:
            return self._query_psutil()

        # Source 1: WMI Performance Counters (root/cimv2, accessible to standard non-elevated users)
        temp, status, desc = self._query_perf_counters(win32com.client)
        if status == "available" and temp is not None:
            return temp, "available", desc

        # Source 2: LibreHardwareMonitor / OpenHardwareMonitor WMI (accessible to standard users if running)
        temp, status, desc = self._query_hardware_monitors(win32com.client)
        if status == "available" and temp is not None:
            return temp, "available", desc

        # Source 3: ACPI Thermal Zone (root/wmi:MSAcpi_ThermalZoneTemperature)
        # Attempted safely; if Access Denied, caught immediately without prompting for elevation
        temp, status, desc = self._query_acpi(win32com.client)
        if status == "available" and temp is not None:
            return temp, "available", desc

        # Source 4: Win32 Temperature Probe (root/cimv2:Win32_TemperatureProbe)
        temp, status, desc = self._query_probes(win32com.client)
        if status == "available" and temp is not None:
            return temp, "available", desc

        # Source 5: psutil sensor fallback
        temp, status, desc = self._query_psutil()
        if status == "available" and temp is not None:
            return temp, "available", desc

        # All accessible sources returned no valid readings or access was restricted
        return None, "unavailable", UNAVAILABLE_EXPLANATION

    def _query_perf_counters(self, win32com_client) -> Tuple[float | None, str, str]:
        """Query standard user-accessible WMI thermal zone performance counters in root/cimv2."""
        for cls_name in (
            "Win32_PerfFormattedData_Counters_ThermalZoneInformation",
            "Win32_PerfRawData_Counters_ThermalZoneInformation",
        ):
            try:
                wmi = win32com_client.GetObject("winmgmts://./root/cimv2")
                instances = wmi.InstancesOf(cls_name)
                readings: list[float] = []
                for inst in instances:
                    raw_t = getattr(inst, "Temperature", None)
                    celsius = convert_raw_temperature_to_celsius(raw_t)
                    if celsius is not None:
                        readings.append(celsius)
                if readings:
                    return max(readings), "available", f"Thermal Zone Performance Counter ({len(readings)} zone(s))"
            except Exception:
                continue
        return None, "unavailable", ""

    def _query_hardware_monitors(self, win32com_client) -> Tuple[float | None, str, str]:
        """Query LibreHardwareMonitor or OpenHardwareMonitor if running."""
        for ns in ("root/LibreHardwareMonitor", "root/OpenHardwareMonitor"):
            try:
                wmi = win32com_client.GetObject(f"winmgmts://./{ns}")
                query = "SELECT Name, Value, SensorType FROM Sensor WHERE SensorType='Temperature'"
                sensors = wmi.ExecQuery(query)
                temps: list[float] = []
                for s in sensors:
                    name = str(getattr(s, "Name", "")).lower()
                    val = getattr(s, "Value", None)
                    if "cpu" in name or "package" in name or "core" in name or "temperature" in name:
                        celsius = convert_raw_temperature_to_celsius(val)
                        if celsius is not None:
                            temps.append(celsius)
                if temps:
                    return max(temps), "available", f"{ns.split('/')[-1]} Sensor"
            except Exception:
                continue
        return None, "unavailable", ""

    def _query_acpi(self, win32com_client) -> Tuple[float | None, str, str]:
        """Query ACPI Thermal Zones. Gracefully ignores Access Denied without prompting for UAC."""
        try:
            wmi_acpi = win32com_client.GetObject("winmgmts://./root/wmi")
            zones = wmi_acpi.InstancesOf("MSAcpi_ThermalZoneTemperature")
            readings: list[float] = []
            for zone in zones:
                kelvin_tenths = getattr(zone, "CurrentTemperature", None)
                celsius = convert_raw_temperature_to_celsius(kelvin_tenths)
                if celsius is not None:
                    readings.append(celsius)
            if readings:
                return max(readings), "available", f"ACPI Thermal Zone ({len(readings)} zone(s))"
        except Exception:
            # Handles Access Denied (0x80041003) or unsupported namespace without raising UAC
            pass
        return None, "unavailable", ""

    def _query_probes(self, win32com_client) -> Tuple[float | None, str, str]:
        """Query Win32_TemperatureProbe in root/cimv2."""
        try:
            wmi_cim = win32com_client.GetObject("winmgmts://./root/cimv2")
            probes = wmi_cim.InstancesOf("Win32_TemperatureProbe")
            readings: list[float] = []
            for p in probes:
                raw_reading = getattr(p, "CurrentReading", None)
                celsius = convert_raw_temperature_to_celsius(raw_reading)
                if celsius is not None:
                    readings.append(celsius)
            if readings:
                return max(readings), "available", "Win32 Temperature Probe"
        except Exception:
            pass
        return None, "unavailable", ""

    def _query_psutil(self) -> Tuple[float | None, str, str]:
        """Check psutil sensors_temperatures fallback (Linux/macOS or supported Windows)."""
        if hasattr(psutil, "sensors_temperatures"):
            try:
                sensors = psutil.sensors_temperatures()
                if sensors:
                    readings: list[float] = []
                    for name, entries in sensors.items():
                        for entry in entries:
                            celsius = convert_raw_temperature_to_celsius(getattr(entry, "current", None))
                            if celsius is not None:
                                readings.append(celsius)
                    if readings:
                        return max(readings), "available", "psutil Hardware Sensor"
            except Exception:
                pass
        return None, "unavailable", ""
