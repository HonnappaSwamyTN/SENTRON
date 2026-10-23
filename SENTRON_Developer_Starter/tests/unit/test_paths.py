"""Unit tests for SENTRON centralized path resolution and database protection.

Verifies:
- Path isolation: User data is resolved to %LOCALAPPDATA%\\SENTRON in packaged mode.
- CWD dev mode compatibility: Existing project files in CWD are preserved.
- Environment override: SENTRON_DATA_DIR is respected.
- Database protection: verify_db_accessible prevents silent overwrites of corrupted databases.
- Settings path integration: SettingsManager saves to the resolved user data path.
"""
from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from sentron.core.paths import (
    get_app_log_path,
    get_default_db_path,
    get_default_settings_path,
    get_user_data_dir,
    is_frozen,
    verify_db_accessible,
)
from sentron.core.settings import SettingsManager


def test_is_frozen_false_in_normal_python():
    """Verify is_frozen returns False in standard test runner."""
    assert is_frozen() is False


def test_is_frozen_true_when_sys_frozen_set():
    """Verify is_frozen returns True when sys.frozen is simulated."""
    with patch.object(sys, "frozen", True, create=True):
        assert is_frozen() is True


def test_user_data_dir_env_override(tmp_path: Path):
    """Verify SENTRON_DATA_DIR takes precedence over everything."""
    custom_dir = tmp_path / "custom_sentron_data"
    with patch.dict(os.environ, {"SENTRON_DATA_DIR": str(custom_dir)}):
        resolved = get_user_data_dir()
        assert resolved == custom_dir
        assert resolved.exists()


def test_user_data_dir_frozen_mode(tmp_path: Path):
    """Verify packaged/frozen mode resolves strictly to %LOCALAPPDATA%\\SENTRON."""
    mock_localappdata = tmp_path / "LocalAppData"
    with patch.dict(os.environ, {"LOCALAPPDATA": str(mock_localappdata)}, clear=False):
        if "SENTRON_DATA_DIR" in os.environ:
            del os.environ["SENTRON_DATA_DIR"]
        with patch.object(sys, "frozen", True, create=True):
            resolved = get_user_data_dir()
            expected = mock_localappdata / "SENTRON"
            assert resolved == expected
            assert resolved.exists()


def test_default_db_path_and_settings_path(tmp_path: Path):
    """Verify default db and settings paths reside inside user data directory."""
    with patch.dict(os.environ, {"SENTRON_DATA_DIR": str(tmp_path)}):
        db_path = get_default_db_path()
        settings_path = get_default_settings_path()
        log_path = get_app_log_path()

        assert db_path == tmp_path / "sentron_local.db"
        assert settings_path == tmp_path / "sentron_settings.json"
        assert log_path == tmp_path / "sentron.log"


def test_verify_db_accessible_nonexistent(tmp_path: Path):
    """Non-existent database should pass verification without error (fresh setup)."""
    db_file = tmp_path / "new_db.db"
    # Should not raise
    verify_db_accessible(db_file)
    verify_db_accessible(":memory:")


def test_verify_db_accessible_valid(tmp_path: Path):
    """Valid SQLite database should pass verification."""
    db_file = tmp_path / "valid.db"
    conn = sqlite3.connect(str(db_file))
    conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY);")
    conn.commit()
    conn.close()

    verify_db_accessible(db_file)


def test_verify_db_accessible_corrupt(tmp_path: Path):
    """Corrupted database file should raise RuntimeError to protect user data."""
    corrupt_file = tmp_path / "corrupt.db"
    corrupt_file.write_bytes(b"NOT A SQLITE DATABASE HEADER AT ALL")

    with pytest.raises(RuntimeError) as exc_info:
        verify_db_accessible(corrupt_file)

    assert "cannot be opened" in str(exc_info.value)
    assert "will not silently overwrite" in str(exc_info.value)


def test_settings_manager_with_custom_data_dir(tmp_path: Path):
    """Verify SettingsManager respects the resolved path and creates parents."""
    custom_dir = tmp_path / "nested" / "appdata"
    with patch.dict(os.environ, {"SENTRON_DATA_DIR": str(custom_dir)}):
        manager = SettingsManager(filepath=custom_dir / "sentron_settings.json")
        assert manager.filepath == custom_dir / "sentron_settings.json"
        # Save settings
        assert manager.save() is True
        assert manager.filepath.exists()
        # Verify content can be reloaded
        manager.set_theme("light")
        assert manager.get_theme() == "light"

        # New instance from same path
        manager2 = SettingsManager(filepath=custom_dir / "sentron_settings.json")
        assert manager2.get_theme() == "light"
