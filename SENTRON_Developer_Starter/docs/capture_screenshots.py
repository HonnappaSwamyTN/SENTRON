"""Script to capture authentic screenshots of the SENTRON V1 desktop application."""
import os
import sys
import time
from pathlib import Path

# Force UTF-8 encoding on Windows console
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Add src to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from sentron.main import create_application


def capture_all():
    out_dir = Path(__file__).resolve().parent / "images"
    out_dir.mkdir(parents=True, exist_ok=True)

    db_path = Path(__file__).resolve().parent / "screenshot_test.db"
    app, window = create_application(db_path=db_path)
    window.show()
    app.processEvents()

    # Step 1: Capture Floating Hub in initial active state
    app.processEvents()
    time.sleep(0.5)
    app.processEvents()
    pix_hub = window.floating_hub.grab()
    pix_hub.save(str(out_dir / "screenshot_floating_hub.png"))
    print(f"Captured floating hub: {out_dir / 'screenshot_floating_hub.png'}")

    # Step 2: Run Scenario B (Sensitive action requiring approval) on AgentGuard
    window.agentguard_panel._run_sensitive_scenario()
    # Collect real system snapshot for CrashGuard
    snap = window.worker.collector.collect_snapshot()
    window.crashguard_panel.update_snapshot(snap)
    app.processEvents()
    time.sleep(0.3)
    app.processEvents()

    # Capture Main Dashboard showing dual panels with approval box visible
    pix_main = window.grab()
    pix_main.save(str(out_dir / "screenshot_main_dashboard.png"))
    print(f"Captured main dashboard: {out_dir / 'screenshot_main_dashboard.png'}")

    # Step 3: Trigger CrashGuard CPU Alert to capture Alert Popup
    window.crashguard_panel.btn_sim_cpu.click()
    app.processEvents()
    time.sleep(0.5)
    app.processEvents()

    popup = window._alert_popup
    if popup and popup.isVisible():
        pix_popup = popup.grab()
        pix_popup.save(str(out_dir / "screenshot_alert_popup.png"))
        print(f"Captured alert popup: {out_dir / 'screenshot_alert_popup.png'}")

    # Step 4: Switch to Timeline Tab and capture Unified Timeline
    window.tabs.setCurrentIndex(1)
    window.timeline_panel.refresh_timeline()
    app.processEvents()
    time.sleep(0.3)
    app.processEvents()

    pix_timeline = window.grab()
    pix_timeline.save(str(out_dir / "screenshot_unified_timeline.png"))
    print(f"Captured unified timeline: {out_dir / 'screenshot_unified_timeline.png'}")

    # Step 5: Switch back to Dashboard, run Scenario C (Prohibited action)
    window.tabs.setCurrentIndex(0)
    window.agentguard_panel._run_prohibited_scenario()
    app.processEvents()
    time.sleep(0.3)
    app.processEvents()

    pix_blocked = window.agentguard_panel.grab()
    pix_blocked.save(str(out_dir / "screenshot_prohibited_blocked.png"))
    print(f"Captured prohibited blocked: {out_dir / 'screenshot_prohibited_blocked.png'}")

    window.close()
    if db_path.exists():
        try:
            db_path.unlink()
        except Exception:
            pass

    print("All screenshots successfully captured!")


if __name__ == "__main__":
    capture_all()
