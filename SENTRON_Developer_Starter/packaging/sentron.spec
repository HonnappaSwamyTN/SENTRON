# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build specification for SENTRON Windows Desktop Application.

Builds a standalone onedir Windows executable bundle with PySide6, psutil,
and internal SQLite/models, ready for Inno Setup installer compilation.
Excludes test suites, developer databases, caches, and unnecessary heavy packages.
"""
import os
import sys
from pathlib import Path

# Resolve base directories
spec_dir = os.path.dirname(os.path.abspath(SPEC))
project_root = os.path.abspath(os.path.join(spec_dir, ".."))
src_dir = os.path.join(project_root, "src")
assets_dir = os.path.join(spec_dir, "assets")

icon_path = os.path.join(assets_dir, "sentron.ico")
png_path = os.path.join(assets_dir, "sentron.png")

added_files = [
    (icon_path, "."),
    (png_path, "."),
]

hidden_imports = [
    "sentron",
    "sentron.agentguard",
    "sentron.agentguard.approval",
    "sentron.agentguard.audit",
    "sentron.agentguard.executor",
    "sentron.agentguard.policy",
    "sentron.agentguard.sensitive_data",
    "sentron.core",
    "sentron.core.models",
    "sentron.core.paths",
    "sentron.core.settings",
    "sentron.core.storage",
    "sentron.crashguard",
    "sentron.crashguard.evidence",
    "sentron.crashguard.metrics",
    "sentron.crashguard.process_control",
    "sentron.crashguard.recovery",
    "sentron.crashguard.risk",
    "sentron.crashguard.temperature",
    "sentron.crashguard.worker",
    "sentron.platform",
    "sentron.platform.windows",
    "sentron.platform.windows.event_log",
    "sentron.platform.windows.psutil_backend",
    "sentron.ui",
    "sentron.ui.agent_alert_popup",
    "sentron.ui.agentguard_panel",
    "sentron.ui.alert_popup",
    "sentron.ui.chart_widget",
    "sentron.ui.crashguard_panel",
    "sentron.ui.demo_panel",
    "sentron.ui.hub_widget",
    "sentron.ui.main_window",
    "sentron.ui.process_dialog",
    "sentron.ui.styles",
    "sentron.ui.timeline_panel",
    "psutil",
    "sqlite3",
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "PySide6.QtNetwork",
]

excluded_modules = [
    "pytest",
    "_pytest",
    "hypothesis",
    "tests",
    "unittest",
    "tkinter",
    "matplotlib",
    "scipy",
    "numpy",
    "IPython",
    "jupyter",
]

a = Analysis(
    [os.path.join(src_dir, "sentron", "main.py")],
    pathex=[src_dir, project_root],
    binaries=[],
    datas=added_files,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excluded_modules,
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="SENTRON",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,  # Windowed GUI application
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_path,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="SENTRON",
)
