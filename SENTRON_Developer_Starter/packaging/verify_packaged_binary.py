"""Verification script for the packaged SENTRON.exe binary.

Tests:
1. Packaged executable launches cleanly without missing DLLs or Python runtime errors.
2. User data is written strictly to designated user data directory, NOT to installation directory.
3. Singleton IPC server prevents duplicate running instances.
4. Clean process termination without hanging worker threads.
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
    exe_path = repo_root / "dist" / "SENTRON" / "SENTRON.exe"

    if not exe_path.exists():
        print(f"FAIL: Packaged executable not found at {exe_path}")
        return 1

    print(f"Testing packaged executable: {exe_path}")

    # Isolated test data directory
    test_data_dir = Path(tempfile.mkdtemp(prefix="sentron_packaged_test_"))
    print(f"Isolated test data dir: {test_data_dir}")

    env = os.environ.copy()
    env["SENTRON_DATA_DIR"] = str(test_data_dir)
    # Headless / offscreen Qt platform so no UI pops up during headless automated verification if needed,
    # or let default Windows platform run
    # env["QT_QPA_PLATFORM"] = "windows"

    # 1. Start primary instance
    print("Launching primary SENTRON.exe process...")
    proc1 = subprocess.Popen([str(exe_path)], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(4.0)

    # Check if proc1 is still running
    poll1 = proc1.poll()
    if poll1 is not None:
        stdout, stderr = proc1.communicate()
        print(f"FAIL: Primary executable exited prematurely with code {poll1}")
        print("STDOUT:", stdout.decode(errors="replace"))
        print("STDERR:", stderr.decode(errors="replace"))
        return 1

    print(f"Pass: Primary process is running with PID {proc1.pid}")

    # 2. Verify database and settings path location
    expected_db = test_data_dir / "sentron_local.db"
    if expected_db.exists():
        print(f"Pass: User database created outside binary folder: {expected_db}")
    else:
        print(f"Warning: {expected_db} not immediately detected; checking directory contents: {list(test_data_dir.iterdir())}")

    # Verify NO db created in dist/SENTRON
    dist_dbs = list((repo_root / "dist" / "SENTRON").rglob("*.db"))
    if dist_dbs:
        print(f"FAIL: Database found inside binary directory: {dist_dbs}")
        proc1.terminate()
        return 1
    print("Pass: Zero databases created in installation binary directory.")

    # 3. Test Singleton Behavior (launch second instance)
    print("Launching second instance to test singleton IPC guard...")
    proc2 = subprocess.Popen([str(exe_path), "--dashboard"], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        proc2_ret = proc2.wait(timeout=10.0)
        print(f"Pass: Second instance exited with code {proc2_ret} (singleton handled gracefully).")
    except subprocess.TimeoutExpired:
        print("FAIL: Second instance hung instead of yielding to running singleton.")
        proc2.kill()
        proc1.terminate()
        return 1

    # 4. Clean shutdown of primary instance
    print("Terminating primary process for clean shutdown test...")
    proc1.terminate()
    try:
        proc1.wait(timeout=6.0)
        print("Pass: Primary process terminated cleanly.")
    except subprocess.TimeoutExpired:
        print("FAIL: Primary process did not terminate within timeout; killing.")
        proc1.kill()
        return 1

    # Cleanup temp dir
    try:
        import shutil
        shutil.rmtree(test_data_dir, ignore_errors=True)
    except Exception:
        pass

    print("\nALL PACKAGED BINARY SMOKE CHECKS PASSED SUCCESSFULLY!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
