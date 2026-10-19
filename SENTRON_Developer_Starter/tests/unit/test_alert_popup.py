"""Tests for CrashGuard Threshold-Crossing Alert Popup and Transition State Tracking.

Covers:
- Threshold crossing and sustained risk duration enforcement
- Repeated alert suppression for continuous risk conditions
- Risk clearing and re-crossing alert triggering
- Disk free space threshold crossing with units
- Multi-resource combination into one alert dialog
- Synthetic demo alert labeling ([SIMULATED DEMO ALERT]) and reset behavior
- View Details and Dismiss action behaviors
- Thread-safe signal invocation and non-focus-stealing window attributes
"""
import time
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from sentron.core.models import RiskAlert, SystemSnapshot
from sentron.crashguard.risk import SustainedRiskDetector
from sentron.crashguard.worker import MonitoringWorker
from sentron.ui.alert_popup import CrashGuardAlertPopup
from sentron.main import create_application


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(["-platform", "offscreen"])
    return app


def _make_snapshot(
    ts: float,
    cpu: float = 20.0,
    ram: float = 30.0,
    disk_free_gb: float = 50.0,
    unavailable: tuple[str, ...] = (),
) -> SystemSnapshot:
    return SystemSnapshot(
        timestamp=ts,
        cpu_percent=cpu,
        memory_percent=ram,
        memory_available_bytes=4 * 1024**3,
        disk_free_bytes=int(disk_free_gb * 1024**3),
        unavailable_metrics=unavailable,
    )


# =========================================================================
# 1. RISK LOGIC & TRANSITION TESTS
# =========================================================================

@pytest.mark.unit
def test_transient_spike_does_not_trigger_popup_alert():
    """Noisy single samples or brief spikes under sustained duration must not trigger alerts."""
    detector = SustainedRiskDetector(
        cpu_threshold=85.0,
        sustained_duration_seconds=10.0,
        cooldown_seconds=30.0,
    )
    t0 = 1000.0

    # Normal reading
    assert detector.evaluate_snapshot(_make_snapshot(t0, cpu=20.0)) == []

    # Spike at t0 + 3s (duration 3s < 10s) -> no alert
    assert detector.evaluate_snapshot(_make_snapshot(t0 + 3.0, cpu=95.0)) == []

    # Drop back down at t0 + 6s
    assert detector.evaluate_snapshot(_make_snapshot(t0 + 6.0, cpu=30.0)) == []
    assert not detector.is_active_risk("CPU")


@pytest.mark.unit
def test_transition_into_sustained_risk_triggers_alert():
    """Sustained pressure beyond required duration triggers alert on transition."""
    detector = SustainedRiskDetector(
        cpu_threshold=85.0,
        sustained_duration_seconds=10.0,
        cooldown_seconds=30.0,
    )
    t0 = 1000.0

    # Start high CPU
    assert detector.evaluate_snapshot(_make_snapshot(t0, cpu=90.0)) == []
    assert not detector.is_active_risk("CPU")

    # At t0 + 5s (still below 10s window) -> no alert
    assert detector.evaluate_snapshot(_make_snapshot(t0 + 5.0, cpu=90.0)) == []

    # At t0 + 11s (> 10s window) -> transition into risk state! Exactly 1 alert emitted
    alerts = detector.evaluate_snapshot(_make_snapshot(t0 + 11.0, cpu=90.0))
    assert len(alerts) == 1
    assert alerts[0].metric_name == "CPU"
    assert alerts[0].observed_value == 90.0
    assert alerts[0].threshold_value == 85.0
    assert alerts[0].duration_seconds >= 10.0
    assert detector.is_active_risk("CPU")


@pytest.mark.unit
def test_repeated_alert_suppression_for_continuous_risk():
    """Subsequent snapshots during continuous risk condition must NOT emit repeat alerts."""
    detector = SustainedRiskDetector(
        cpu_threshold=85.0,
        sustained_duration_seconds=10.0,
        cooldown_seconds=30.0,
    )
    t0 = 1000.0

    # Initial breach and sustained transition
    detector.evaluate_snapshot(_make_snapshot(t0, cpu=92.0))
    alerts1 = detector.evaluate_snapshot(_make_snapshot(t0 + 12.0, cpu=92.0))
    assert len(alerts1) == 1

    # Continuous risk at t0 + 14s, 16s, 20s, 35s, 50s -> all must be suppressed!
    assert detector.evaluate_snapshot(_make_snapshot(t0 + 14.0, cpu=93.0)) == []
    assert detector.evaluate_snapshot(_make_snapshot(t0 + 20.0, cpu=91.0)) == []
    assert detector.evaluate_snapshot(_make_snapshot(t0 + 45.0, cpu=94.0)) == []
    assert detector.evaluate_snapshot(_make_snapshot(t0 + 80.0, cpu=92.0)) == []
    assert detector.is_active_risk("CPU")


@pytest.mark.unit
def test_risk_clearing_and_recrossing_allows_new_popup():
    """When the condition clears and later re-crosses threshold, a new alert is generated."""
    detector = SustainedRiskDetector(
        cpu_threshold=85.0,
        sustained_duration_seconds=10.0,
        cooldown_seconds=30.0,
    )
    t0 = 1000.0

    # 1. First breach
    detector.evaluate_snapshot(_make_snapshot(t0, cpu=90.0))
    alerts1 = detector.evaluate_snapshot(_make_snapshot(t0 + 11.0, cpu=90.0))
    assert len(alerts1) == 1
    assert detector.is_active_risk("CPU")

    # 2. Risk clears: CPU drops to normal (25%)
    clear_alerts = detector.evaluate_snapshot(_make_snapshot(t0 + 15.0, cpu=25.0))
    assert len(clear_alerts) == 0
    assert not detector.is_active_risk("CPU")

    # 3. CPU breaches again at t0 + 30s
    assert detector.evaluate_snapshot(_make_snapshot(t0 + 30.0, cpu=95.0)) == []

    # 4. CPU sustained for >10s at t0 + 42s -> NEW transition alert triggered!
    alerts2 = detector.evaluate_snapshot(_make_snapshot(t0 + 42.0, cpu=95.0))
    assert len(alerts2) == 1
    assert alerts2[0].metric_name == "CPU"
    assert alerts2[0].observed_value == 95.0
    assert detector.is_active_risk("CPU")


@pytest.mark.unit
def test_disk_free_gb_threshold_crossing():
    """Disk free space dropping below threshold triggers transition alert with GB units."""
    detector = SustainedRiskDetector(
        disk_free_gb_threshold=5.0,
        sustained_duration_seconds=5.0,
    )
    t0 = 2000.0

    # Normal free space (50 GB)
    assert detector.evaluate_snapshot(_make_snapshot(t0, disk_free_gb=50.0)) == []

    # Low disk free space (3.2 GB < 5.0 GB threshold)
    assert detector.evaluate_snapshot(_make_snapshot(t0 + 1.0, disk_free_gb=3.2)) == []
    # Sustained for > 5s
    alerts = detector.evaluate_snapshot(_make_snapshot(t0 + 7.0, disk_free_gb=3.2))
    assert len(alerts) == 1
    assert alerts[0].metric_name == "DiskFreeGB"
    assert alerts[0].observed_value == 3.2
    assert alerts[0].threshold_value == 5.0


@pytest.mark.unit
def test_simulated_alert_flag_and_reset():
    """Synthetic demo triggers simulated alert and resetting clears simulated risk state."""
    worker = MonitoringWorker(interval_seconds=1.0)
    worker.detector.sustained_duration_seconds = 5.0

    # Trigger synthetic CPU demo
    worker.trigger_synthetic_demo_load(metric_name="CPU", value=92.0)
    assert worker._synthetic_override is not None

    # Sample snapshot
    snap = worker._sample_once()
    assert "synthetic_demo_mode" in snap.unavailable_metrics

    # Check detector active risk state
    assert worker.detector.is_active_risk("CPU")

    # Reset to authentic
    worker.clear_synthetic_demo_load()
    assert worker._synthetic_override is None
    assert not worker.detector.is_active_risk("CPU")


# =========================================================================
# 2. UI POPUP WIDGET TESTS
# =========================================================================

@pytest.mark.unit
def test_alert_popup_visual_elements_and_units(qapp):
    """Popup displays title, metric name, measured value and threshold with units, and timestamp."""
    alert = RiskAlert(
        alert_id="test-alert-1",
        metric_name="CPU",
        severity="critical",
        observed_value=93.5,
        threshold_value=85.0,
        duration_seconds=12.0,
        cooldown_until=time.time() + 30.0,
        timestamp=time.time(),
        is_simulated=False,
    )

    popup = CrashGuardAlertPopup()
    popup.add_alert(alert)

    # 1. Title verification
    assert "SENTRON CrashGuard Alert" in popup.lbl_title.text()

    # 2. Simulated badge must be hidden for authentic alert
    assert not popup.lbl_sim_badge.isVisible()
    assert not popup.lbl_sim_disclaimer.isVisible()

    # 3. Units verification: CPU must show %
    assert popup.resources_layout.count() == 1
    row_widget = popup.resources_layout.itemAt(0).widget()
    labels = row_widget.findChildren(type(popup.lbl_title))
    text_combined = " ".join(lbl.text() for lbl in labels)
    assert "CPU" in text_combined
    assert "93.5%" in text_combined
    assert "85.0%" in text_combined
    assert "CRITICAL" in text_combined

    # 4. Safe recovery notice
    assert "Safe Recovery" in popup.lbl_recovery_notice.text()
    assert "will not terminate" in popup.lbl_recovery_notice.text()

    popup.close()


@pytest.mark.unit
def test_alert_popup_simulated_demo_badge(qapp):
    """Synthetic alert prominently displays [SIMULATED DEMO ALERT] badge and disclaimer."""
    sim_alert = RiskAlert(
        alert_id="test-sim-1",
        metric_name="CPU",
        severity="critical",
        observed_value=92.0,
        threshold_value=85.0,
        duration_seconds=10.0,
        cooldown_until=time.time() + 30.0,
        timestamp=time.time(),
        is_simulated=True,
    )

    popup = CrashGuardAlertPopup()
    popup.add_alert(sim_alert)
    popup.show()
    qapp.processEvents()

    # Simulated badge & disclaimer must be visible
    assert popup.is_simulated()
    assert popup.lbl_sim_badge.isVisible()
    assert "SIMULATED DEMO ALERT" in popup.lbl_sim_badge.text()
    assert popup.lbl_sim_disclaimer.isVisible()
    assert "DEMO MODE" in popup.lbl_sim_disclaimer.text()

    popup.close()


@pytest.mark.unit
def test_alert_popup_combines_simultaneous_resources(qapp):
    """Multiple simultaneous threshold breaches are combined into one alert dialog."""
    alert_cpu = RiskAlert(
        alert_id="alert-cpu",
        metric_name="CPU",
        severity="critical",
        observed_value=94.0,
        threshold_value=85.0,
        duration_seconds=15.0,
        cooldown_until=time.time() + 30.0,
        timestamp=time.time(),
    )
    alert_ram = RiskAlert(
        alert_id="alert-ram",
        metric_name="Memory",
        severity="warning",
        observed_value=88.0,
        threshold_value=85.0,
        duration_seconds=12.0,
        cooldown_until=time.time() + 30.0,
        timestamp=time.time(),
    )

    popup = CrashGuardAlertPopup()
    popup.add_alert(alert_cpu)
    popup.add_alert(alert_ram)

    # Both resources should be present in the same popup layout
    assert popup.resources_layout.count() == 2
    assert "CPU" in popup._alerts
    assert "Memory" in popup._alerts
    assert "CPU, Memory" in popup.lbl_trigger_reason.text() or "Memory, CPU" in popup.lbl_trigger_reason.text()

    popup.close()


@pytest.mark.unit
def test_alert_popup_actions_view_details_and_dismiss(qapp):
    """'View Details' triggers callback, 'Dismiss' closes popup without error."""
    view_details_called = []
    dismiss_called = []

    popup = CrashGuardAlertPopup(
        on_view_details=lambda: view_details_called.append(True),
        on_dismiss=lambda: dismiss_called.append(True),
    )

    alert = RiskAlert(
        alert_id="a1",
        metric_name="CPU",
        severity="warning",
        observed_value=89.0,
        threshold_value=85.0,
        duration_seconds=10.0,
        cooldown_until=time.time() + 30.0,
        timestamp=time.time(),
    )
    popup.add_alert(alert)

    # Test View Details
    popup.btn_view_details.click()
    assert len(view_details_called) == 1

    # Test Dismiss
    popup.btn_dismiss.click()
    assert len(dismiss_called) == 1


@pytest.mark.unit
def test_alert_popup_window_attributes_and_focus(qapp):
    """Popup must not steal keyboard focus (WA_ShowWithoutActivating)."""
    popup = CrashGuardAlertPopup()
    assert popup.testAttribute(Qt.WA_ShowWithoutActivating)
    flags = popup.windowFlags()
    assert bool(flags & Qt.WindowStaysOnTopHint)
    assert bool(flags & Qt.Tool)
    popup.close()


# =========================================================================
# 3. INTEGRATION WITH SENTRON MAIN WINDOW
# =========================================================================

def test_main_window_alert_popup_integration(qapp, tmp_path):
    """Emitting alert signal in main window opens popup and persists in SQLite event store."""
    db_file = tmp_path / "test_alert_window.db"
    app, window = create_application(db_path=db_file)

    try:
        window.show()
        qapp.processEvents()

        # Emit simulated alert
        alert = RiskAlert(
            alert_id="integration-test-alert",
            metric_name="CPU",
            severity="critical",
            observed_value=92.0,
            threshold_value=85.0,
            duration_seconds=11.0,
            cooldown_until=time.time() + 30.0,
            timestamp=time.time(),
            is_simulated=True,
        )

        window.alert_received.emit(alert, [])
        qapp.processEvents()

        # Verify alert popup was instantiated and displayed
        assert window._alert_popup is not None
        assert window._alert_popup.isVisible()
        assert window._alert_popup.is_simulated()

        # Verify event was recorded into SQLite event store
        timeline_events = window.event_store.get_recent_events(subsystem="CrashGuard")
        assert len(timeline_events) >= 1
        assert timeline_events[0].event_type == "SYSTEM_ALERT"
        assert "[SIMULATED DEMO ALERT]" in timeline_events[0].summary

        # Verify switching via View Details
        # Switch to tab 1 (Timeline) first
        window.tabs.setCurrentIndex(1)
        assert window.tabs.currentIndex() == 1

        # Click View Details
        window.show_crashguard_details()
        qapp.processEvents()
        # Must switch back to dashboard tab (0)
        assert window.tabs.currentIndex() == 0

        # Resetting demo clears simulated popup
        window.dismiss_simulated_alerts()
        assert not window._alert_popup.isVisible()

    finally:
        window.close()
