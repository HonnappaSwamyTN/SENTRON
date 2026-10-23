"""Automated build script for SENTRON Windows Executable and Inno Setup Installer.

Orchestrates:
1. Multi-resolution icon generation (packaging/assets/sentron.ico).
2. PyInstaller build (dist/SENTRON/SENTRON.exe).
3. Leak check (ensures no developer databases, test logs, or secrets in bundle).
4. Inno Setup 6 compilation (dist/installer/SENTRON_Setup.exe).
5. Post-build integrity verification.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path


def find_iscc() -> Path | None:
    """Find Inno Setup Compiler executable (ISCC.exe)."""
    # 1. Check PATH
    which_iscc = shutil.which("ISCC.exe") or shutil.which("iscc")
    if which_iscc:
        return Path(which_iscc)

    # 2. Check LocalAppData Programs
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        candidate = Path(local_app_data) / "Programs" / "Inno Setup 6" / "ISCC.exe"
        if candidate.exists():
            return candidate

    # 3. Check Program Files
    prog_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
    candidate = Path(prog_files_x86) / "Inno Setup 6" / "ISCC.exe"
    if candidate.exists():
        return candidate

    prog_files = os.environ.get("ProgramFiles", r"C:\Program Files")
    candidate = Path(prog_files) / "Inno Setup 6" / "ISCC.exe"
    if candidate.exists():
        return candidate

    return None


def calculate_sha256(filepath: Path) -> str:
    """Compute SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent

    print("==================================================================")
    print("  SENTRON Windows Installer Build Pipeline                        ")
    print("==================================================================")
    print(f"Project root: {repo_root}")

    # 1. Verify / Generate assets
    ico_path = script_dir / "assets" / "sentron.ico"
    if not ico_path.exists():
        print("[1/5] Generating multi-resolution golden shield icons...")
        gen_script = script_dir / "generate_icon.py"
        res = subprocess.run([sys.executable, str(gen_script)], cwd=str(repo_root))
        if res.returncode != 0:
            print("ERROR: Icon generation failed.")
            return 1
    else:
        print(f"[1/5] Found existing icon: {ico_path}")

    # 2. Run PyInstaller
    print("\n[2/5] Building standalone executable with PyInstaller...")
    spec_path = script_dir / "sentron.spec"
    dist_dir = repo_root / "dist"
    build_dir = repo_root / "build"

    pyinstaller_cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--distpath",
        str(dist_dir),
        "--workpath",
        str(build_dir),
        str(spec_path),
    ]

    print(f"Running: {' '.join(pyinstaller_cmd)}")
    build_res = subprocess.run(pyinstaller_cmd, cwd=str(repo_root))
    if build_res.returncode != 0:
        print("ERROR: PyInstaller build failed.")
        return 1

    exe_path = dist_dir / "SENTRON" / "SENTRON.exe"
    if not exe_path.exists():
        print(f"ERROR: Expected executable not found at {exe_path}")
        return 1
    # Ensure icon files exist at root of onedir bundle
    shutil.copy2(ico_path, dist_dir / "SENTRON" / "sentron.ico")
    shutil.copy2(script_dir / "assets" / "sentron.png", dist_dir / "SENTRON" / "sentron.png")
    print(f"Successfully built: {exe_path} ({exe_path.stat().st_size / (1024*1024):.2f} MB)")

    # 3. Security & Leak Check
    print("\n[3/5] Performing leak verification on bundled payload...")
    sentron_dist = dist_dir / "SENTRON"
    leak_patterns = ["*.db", "*.sqlite*", "sentron_settings.json", "test_*.py", "*.log"]
    found_leaks = []
    for pattern in leak_patterns:
        for leak in sentron_dist.rglob(pattern):
            found_leaks.append(leak)

    if found_leaks:
        print("SECURITY ALERT: Found unexpected sensitive/dev files in build output:")
        for lk in found_leaks:
            print(f"  - {lk}")
        return 1
    print("Pass: Zero user databases, test suites, or settings files present in build bundle.")

    # 4. Inno Setup Compilation
    print("\n[4/5] Compiling Inno Setup Windows installer...")
    iscc_path = find_iscc()
    if not iscc_path:
        print("ERROR: Inno Setup compiler (ISCC.exe) not found on system.")
        return 1
    print(f"Using Inno Setup compiler: {iscc_path}")

    iss_path = script_dir / "installer.iss"
    inno_cmd = [str(iscc_path), str(iss_path)]
    print(f"Running: {' '.join(inno_cmd)}")
    inno_res = subprocess.run(inno_cmd, cwd=str(script_dir))
    if inno_res.returncode != 0:
        print("ERROR: Inno Setup compilation failed.")
        return 1

    # 5. Output Verification
    installer_exe = dist_dir / "installer" / "SENTRON_Setup.exe"
    if not installer_exe.exists():
        print(f"ERROR: Setup installer not found at {installer_exe}")
        return 1

    installer_size_mb = installer_exe.stat().st_size / (1024 * 1024)
    installer_sha = calculate_sha256(installer_exe)

    print("\n[5/5] Installer build verified successfully!")
    print("==================================================================")
    print(f"Installer: {installer_exe}")
    print(f"Size:      {installer_size_mb:.2f} MB")
    print(f"SHA-256:   {installer_sha}")
    print("==================================================================")
    return 0


if __name__ == "__main__":
    sys.exit(main())
