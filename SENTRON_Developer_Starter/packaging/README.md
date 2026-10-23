# SENTRON Windows Installer & Packaging Guide

This directory contains the automated packaging and Windows installer configuration for **SENTRON** (Local Security Guard for AI Actions and System Stability).

---

## 1. Architecture & Design Principles

### Clean Isolation of Binaries and User Data
- **Application Binaries (Read-Only):** Installed into `%LOCALAPPDATA%\Programs\SENTRON` via per-user installation (`PrivilegesRequired=lowest`). No administrator elevation is required.
- **User Data (Writable, Persistent):**
  - Database: `%LOCALAPPDATA%\SENTRON\sentron_local.db`
  - Settings: `%LOCALAPPDATA%\SENTRON\sentron_settings.json`
  - Application Logs: `%LOCALAPPDATA%\SENTRON\sentron.log`
- **Zero Leak Guarantee:** The packaging pipeline rigorously scans the distribution bundle and prevents any developer SQLite databases, test logs, settings, or development credentials from being packaged.
- **Uninstallation Safety:** The uninstaller removes only application program files from `%LOCALAPPDATA%\Programs\SENTRON`. User audit databases and configuration in `%LOCALAPPDATA%\SENTRON` are preserved.

---

## 2. Directory Structure

```
packaging/
├── assets/
│   ├── sentron.ico         # Multi-resolution golden shield Windows icon (16, 24, 32, 48, 64, 128, 256)
│   └── sentron.png         # High-resolution (256x256) master icon
├── generate_icon.py        # Offline vector rendering script for icon generation
├── sentron.spec            # PyInstaller onedir GUI build specification
├── installer.iss           # Inno Setup 6 compilation script
├── build_installer.py      # One-click automated build pipeline
└── README.md               # This documentation
```

---

## 3. Prerequisites

1. **Python 3.13+** with project dependencies:
   ```powershell
   pip install pyinstaller pillow psutil PySide6
   ```
2. **Inno Setup 6**:
   Install via Windows Package Manager:
   ```powershell
   winget install JRSoftware.InnoSetup
   ```
   *The build script automatically detects `ISCC.exe` in `%LOCALAPPDATA%\Programs\Inno Setup 6` or `Program Files`.*

---

## 4. Build Instructions

### One-Click Automated Build
Run the build script from the repository root:
```powershell
python packaging/build_installer.py
```

This pipeline automatically:
1. Verifies/generates `packaging/assets/sentron.ico` (multi-res 16–256px).
2. Runs PyInstaller with `packaging/sentron.spec` to produce `dist/SENTRON/SENTRON.exe`.
3. Performs a security check ensuring no `.db`, `.sqlite`, or `test_*.py` files are bundled.
4. Invokes Inno Setup (`ISCC.exe`) to compile `dist/installer/SENTRON_Setup.exe`.
5. Computes file size and SHA-256 integrity hash.

### Manual Step-by-Step Build
If you prefer running individual steps manually:
```powershell
# 1. Generate icon
python packaging/generate_icon.py

# 2. Build executable bundle
pyinstaller --noconfirm --clean --distpath dist --workpath build packaging/sentron.spec

# 3. Compile installer
& "C:\Users\Honnu\AppData\Local\Programs\Inno Setup 6\ISCC.exe" packaging/installer.iss
```

---

## 5. Output Artifacts

- **Executable Bundle:** `dist\SENTRON\SENTRON.exe`
- **Windows Installer:** `dist\installer\SENTRON_Setup.exe`

---

## 6. Runtime & Verification Checks

1. **Pre-build Test Suite:**
   ```powershell
   python -m compileall -q src tests
   python -m pytest tests -ra -q
   ```
2. **Executable Smoke Test:**
   ```powershell
   .\dist\SENTRON\SENTRON.exe
   ```
   - Verifies the floating golden shield appears.
   - Verifies clicking the shield opens the status panel.
   - Verifies single-instance enforcement (second launch brings first to front).
   - Verifies clean shutdown via shield close button or tray Exit.
3. **Installer Verification:**
   - Run `dist\installer\SENTRON_Setup.exe`.
   - Verify installation wizard finishes without admin elevation.
   - Verify Start Menu shortcut `SENTRON` and Desktop shortcut are created with the golden shield icon.
   - Verify user database is created in `%LOCALAPPDATA%\SENTRON\sentron_local.db` rather than the install directory.
