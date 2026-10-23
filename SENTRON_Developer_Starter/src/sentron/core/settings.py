"""Application settings and persistence for SENTRON.

Manages user-configurable preferences including dashboard theme,
CrashGuard resource-risk thresholds, and temperature advisory warnings.
Offline, local-first JSON persistence with safe defaults.
"""
from __future__ import annotations

import json
import os
import threading
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from sentron.core.paths import get_default_settings_path

DEFAULT_SETTINGS_FILENAME = "sentron_settings.json"


@dataclass
class AppSettings:
    """Configurable settings for SENTRON."""

    theme: str = "dark"  # "light" or "dark"
    resource_risk_threshold: float = 93.0  # Single source of truth for CrashGuard sustained risk (%)
    temperature_warning_threshold: float = 80.0  # Advisory CPU temperature warning (°C)
    sustained_duration_seconds: float = 10.0  # Duration required before risk alert fires (seconds)
    cooldown_seconds: float = 30.0  # Alert cooldown period (seconds)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AppSettings:
        valid_keys = {
            "theme",
            "resource_risk_threshold",
            "temperature_warning_threshold",
            "sustained_duration_seconds",
            "cooldown_seconds",
        }
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        # Validate theme
        if filtered.get("theme") not in ("light", "dark"):
            filtered["theme"] = "dark"
        # Validate threshold
        if "resource_risk_threshold" in filtered:
            try:
                filtered["resource_risk_threshold"] = float(filtered["resource_risk_threshold"])
            except (ValueError, TypeError):
                filtered["resource_risk_threshold"] = 93.0
        return cls(**filtered)


class SettingsManager:
    """Thread-safe manager for loading, modifying, and persisting application settings."""

    _instance: SettingsManager | None = None
    _lock = threading.Lock()

    def __init__(self, filepath: str | Path | None = None, config_path: str | Path | None = None) -> None:
        target = config_path if config_path is not None else filepath
        if target is not None:
            self.filepath = Path(target)
        else:
            self.filepath = get_default_settings_path()
        self._settings = AppSettings()
        self._rw_lock = threading.Lock()
        self.load()

    @classmethod
    def get_instance(cls, filepath: str | Path | None = None) -> SettingsManager:
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls(filepath)
            return cls._instance

    @property
    def settings(self) -> AppSettings:
        with self._rw_lock:
            return self._settings

    def load(self) -> AppSettings:
        """Load settings from JSON file if it exists, otherwise retain defaults."""
        with self._rw_lock:
            if self.filepath.exists():
                try:
                    with open(self.filepath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if isinstance(data, dict):
                        self._settings = AppSettings.from_dict(data)
                except Exception:
                    # In case of corrupted file, fallback gracefully to default settings
                    pass
            return self._settings

    def save(self) -> bool:
        """Save current settings to JSON file atomically."""
        with self._rw_lock:
            try:
                self.filepath.parent.mkdir(parents=True, exist_ok=True)
                temp_file = self.filepath.with_suffix(".tmp")
                with open(temp_file, "w", encoding="utf-8") as f:
                    json.dump(self._settings.to_dict(), f, indent=2)
                temp_file.replace(self.filepath)
                return True
            except Exception:
                return False

    def update(self, **kwargs: Any) -> AppSettings:
        """Update one or more settings and persist them."""
        with self._rw_lock:
            current_dict = self._settings.to_dict()
            current_dict.update(kwargs)
            self._settings = AppSettings.from_dict(current_dict)
        self.save()
        return self._settings

    def get_theme(self) -> str:
        with self._rw_lock:
            return self._settings.theme

    def set_theme(self, theme: str) -> None:
        if theme in ("light", "dark"):
            self.update(theme=theme)

    def get_resource_risk_threshold(self) -> float:
        with self._rw_lock:
            return self._settings.resource_risk_threshold

    def set_resource_risk_threshold(self, threshold: float) -> None:
        self.update(resource_risk_threshold=float(threshold))

    def get_temperature_warning_threshold(self) -> float:
        with self._rw_lock:
            return self._settings.temperature_warning_threshold

    def set_temperature_warning_threshold(self, threshold: float) -> None:
        self.update(temperature_warning_threshold=float(threshold))
