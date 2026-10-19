"""Verification script: Launch actual GUI, trigger threshold crossing, and verify popup."""
import sys
import time
from pathlib import Path

# Force UTF-8 on Windows console
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr.encoding != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Add src to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from sentron.main import create_application


def run_verification():
    db_path = Path("test_gui_verification.db")
    app, window = create_application(db_path=db_path)
    window.show()

    results = {}

    def step1_trigger_alert():
        print("[Step 1] Simulating CPU load via CrashGuardPanel...")
        window.crashguard_panel.btn_sim_cpu.click()
        QTimer.singleShot(500, step2_verify_popup)

    def step2_verify_popup():
        print("[Step 2] Verifying popup visibility and contents...")
        popup = window._alert_popup
        assert popup is not None, "Popup was not created!"
        assert popup.isVisible(), "Popup is not visible!"
        print(f"  -> Popup visible: {popup.isVisible()}")
        print(f"  -> Popup geometry: {popup.geometry().getRect()}")
        print(f"  -> Title: '{popup.lbl_title.text()}'")
        assert "SENTRON CrashGuard Alert" in popup.lbl_title.text()
        print(f"  -> Simulated Badge visible: {popup.lbl_sim_badge.isVisible()}")
        assert popup.lbl_sim_badge.isVisible()
        assert "SIMULATED DEMO ALERT" in popup.lbl_sim_badge.text()
        print(f"  -> Reason: '{popup.lbl_trigger_reason.text()}'")

        # Check resource rows
        assert popup.resources_layout.count() >= 1
        row = popup.resources_layout.itemAt(0).widget()
        row_text = " ".join(lbl.text() for lbl in row.findChildren(type(popup.lbl_title)))
        print(f"  -> Row details: {row_text}")
        assert "CPU" in row_text
        assert "%" in row_text
        results["popup_verified"] = True

        # Switch main window to Timeline tab to verify popup stays visible across tabs
        print("[Step 3] Switching window to Timeline tab...")
        window.tabs.setCurrentIndex(1)
        assert window.tabs.currentIndex() == 1
        assert popup.isVisible(), "Popup disappeared when switching tabs!"
        print("  -> Popup remains visible across different application tabs.")

        # Test View Details
        print("[Step 4] Clicking 'View Details' action on popup...")
        popup.btn_view_details.click()
        QTimer.singleShot(200, step3_verify_details_action)

    def step3_verify_details_action():
        print("[Step 5] Verifying tab switched back to CrashGuard...")
        assert window.tabs.currentIndex() == 0, "Did not switch back to dashboard tab!"
        print(f"  -> Window active tab: {window.tabs.currentIndex()} ('Live Security & Health Dashboard')")

        # Test simulated reset
        print("[Step 6] Resetting simulation to authentic live...")
        window.crashguard_panel.btn_reset_live.click()
        assert not window.worker.detector.is_active_risk("CPU")
        print("  -> Simulated risk cleared. Real monitoring intact.")

        results["all_passed"] = True
        print("\n=== GUI ALERT POPUP VERIFICATION PASSED SUCCESSFULLY ===")
        QTimer.singleShot(200, app.quit)

    QTimer.singleShot(300, step1_trigger_alert)
    app.exec()

    # Cleanup test db
    if db_path.exists():
        try:
            db_path.unlink()
        except Exception:
            pass

    return results.get("all_passed", False)


if __name__ == "__main__":
    success = run_verification()
    sys.exit(0 if success else 1)
