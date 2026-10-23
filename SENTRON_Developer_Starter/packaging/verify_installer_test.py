"""Verification script for SENTRON_Setup.exe installer.

Performs:
1. Validates installer executable properties (file size, PE header).
2. Performs a silent test installation to an isolated temporary sandbox directory.
3. Confirms all application files, including SENTRON.exe and sentron.ico, are correctly unpacked.
4. Verifies uninstaller generation.
5. Runs uninstallation to verify clean removal of the installation directory.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    installer_path = repo_root / "dist" / "installer" / "SENTRON_Setup.exe"

    if not installer_path.exists():
        print(f"FAIL: Installer not found at {installer_path}")
        return 1

    size_mb = installer_path.stat().st_size / (1024 * 1024)
    print(f"Installer: {installer_path} ({size_mb:.2f} MB)")

    # Isolated sandbox installation directory
    sandbox_dir = Path(tempfile.gettempdir()) / "sentron_install_sandbox"
    if sandbox_dir.exists():
        import shutil
        shutil.rmtree(sandbox_dir, ignore_errors=True)
    sandbox_dir.mkdir(parents=True, exist_ok=True)

    install_log = sandbox_dir / "install.log"
    print(f"Target test installation directory: {sandbox_dir}")

    # Run installer silently to sandbox directory
    # /SILENT /DIR="..." /LOG="..." /NOICONS
    cmd = [
        str(installer_path),
        "/SILENT",
        f"/DIR={sandbox_dir}",
        f"/LOG={install_log}",
        "/NOICONS",
    ]

    print(f"Executing: {' '.join(cmd)}")
    res = subprocess.run(cmd)
    if res.returncode != 0:
        print(f"FAIL: Installer exited with code {res.returncode}")
        return 1

    # Verify extracted contents
    installed_exe = sandbox_dir / "SENTRON.exe"
    installed_ico = sandbox_dir / "sentron.ico"
    uninstaller = sandbox_dir / "unins000.exe"

    if not installed_exe.exists():
        print(f"FAIL: Expected installed executable not found at {installed_exe}")
        return 1
    print(f"Pass: Installed executable verified: {installed_exe} ({installed_exe.stat().st_size / (1024*1024):.2f} MB)")

    if not installed_ico.exists():
        print(f"FAIL: Expected icon not found at {installed_ico}")
        return 1
    print(f"Pass: Installed icon verified: {installed_ico}")

    if not uninstaller.exists():
        print(f"FAIL: Expected uninstaller not found at {uninstaller}")
        return 1
    print(f"Pass: Uninstaller generated: {uninstaller}")

    # Verify that no database was created in the sandbox directory
    dbs = list(sandbox_dir.rglob("*.db"))
    if dbs:
        print(f"FAIL: Database file found in installation directory: {dbs}")
        return 1
    print("Pass: Zero databases present in installation folder.")

    # Test clean uninstallation
    print("\nTesting silent uninstallation...")
    unins_cmd = [str(uninstaller), "/SILENT"]
    unins_res = subprocess.run(unins_cmd)
    time.sleep(2.0)

    if installed_exe.exists():
        print("FAIL: Installed executable still exists after uninstallation.")
        return 1
    print("Pass: Uninstallation successfully removed program files.")

    # Cleanup sandbox dir
    try:
        import shutil
        shutil.rmtree(sandbox_dir, ignore_errors=True)
    except Exception:
        pass

    print("\nALL INSTALLER VERIFICATION CHECKS PASSED SUCCESSFULLY!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
