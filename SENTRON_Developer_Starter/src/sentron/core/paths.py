"""Centralized path resolution for SENTRON user data, settings, and logging.

Enforces:
- Clean isolation between application binaries (read-only) and user data (writable).
- User data default location: %LOCALAPPDATA%\\SENTRON on Windows.
- Backward compatibility: preserves local CWD database/settings when running from source repo.
- Environment override: SENTRON_DATA_DIR for test/CI/custom installations.
- Safe data preservation: Never deletes or overwrites existing user data.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def is_frozen() -> bool:
    """Return True if running as a compiled/packaged binary (e.g. PyInstaller)."""
    return getattr(sys, "frozen", False)


def get_user_data_dir() -> Path:
    """Resolve and return the writable user data directory for SENTRON.

    Resolution order:
    1. SENTRON_DATA_DIR environment variable (if set).
    2. Frozen / packaged application: %LOCALAPPDATA%\\SENTRON (or platform equivalent).
    3. Source / development mode:
       - If sentron_local.db or sentron_settings.json exists in CWD, use CWD (preserves local dev state).
       - Otherwise, use %LOCALAPPDATA%\\SENTRON.
    """
    env_dir = os.environ.get("SENTRON_DATA_DIR")
    if env_dir:
        target = Path(env_dir)
        target.mkdir(parents=True, exist_ok=True)
        return target

    if is_frozen():
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            base = Path(local_app_data)
        else:
            base = Path.home() / "AppData" / "Local"
        target = base / "SENTRON"
        target.mkdir(parents=True, exist_ok=True)
        return target

    # Development / source mode:
    cwd = Path.cwd()
    if (cwd / "sentron_local.db").exists() or (cwd / "sentron_settings.json").exists():
        return cwd

    # Default fallback when running from source without existing local files:
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        base = Path(local_app_data)
    else:
        base = Path.home() / "AppData" / "Local"
    target = base / "SENTRON"
    target.mkdir(parents=True, exist_ok=True)
    return target


def get_default_db_path() -> Path:
    """Return the resolved default database file path."""
    data_dir = get_user_data_dir()
    db_path = data_dir / "sentron_local.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return db_path


def get_default_settings_path() -> Path:
    """Return the resolved default settings file path."""
    data_dir = get_user_data_dir()
    settings_path = data_dir / "sentron_settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    return settings_path


def get_app_log_path() -> Path:
    """Return the path for diagnostic application logging in packaged mode."""
    data_dir = get_user_data_dir()
    log_path = data_dir / "sentron.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    return log_path


def verify_db_accessible(db_path: Path | str) -> None:
    """Verify an existing database file can be accessed without corruption.

    Raises RuntimeError if an existing database file is corrupt or unreadable,
    preventing silent fresh database overwrite.
    """
    path = Path(db_path)
    if not path.exists() or str(db_path) == ":memory:":
        return

    import sqlite3
    try:
        conn = sqlite3.connect(str(path))
        conn.execute("PRAGMA schema_version;")
        conn.close()
    except Exception as exc:
        raise RuntimeError(
            f"Existing SENTRON database at '{path}' cannot be opened: {exc}. "
            "SENTRON will not silently overwrite your data. Please check permissions or restore from backup."
        ) from exc
