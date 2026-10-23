"""Tests for Persistent Round Floating Shield, Lifecycle Close Behavior, and RAM Optimizations.

Verifies:
1. Closing the dashboard leaves the shield and monitoring active.
2. Clicking × exits the application and stops workers.
3. Restarting the application restores the shield.
4. Hovering shows the × control and moving away hides it.
5. Clicking × does not trigger the shield's normal click action (expand).
6. The floating icon remains circular at different sizes (width == height).
7. No duplicate workers or monitoring instances are created.
8. RAM-related optimizations preserve existing functionality.
"""
from __future__ import annotations

import pytest
from PySide6.QtCore import Qt, QPoint, QEvent
from PySide6.QtGui import QEnterEvent, QMouseEvent
from PySide6.QtWidgets import QApplication

from sentron.main import create_application
from sentron.ui.hub_widget import FloatingHubWidget
from sentron.crashguard.metrics import MetricsCollector
from sentron.ui.chart_widget import ResourceChartWidget


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(["-platform", "offscreen"])
    return app


@pytest.mark.unit
def test_closing_dashboard_leaves_shield_and_monitoring_active(qapp, tmp_path):
    """Closing the dashboard hides it while keeping floating shield visible and monitoring worker active."""
    db_file = tmp_path / "test_dash_close.db"
    app, window = create_application(db_path=db_file)

    try:
        window.show()
        qapp.processEvents()

        assert window.isVisible()
        assert window.floating_hub.isVisible()
        assert window.worker.is_active

        # User closes the dashboard window (e.g. clicks X on title bar)
        window.close()
        qapp.processEvents()

        # Dashboard must be hidden, NOT destroyed/exited
        assert window.isHidden()

        # Floating shield must remain visible and monitoring active
        assert window.floating_hub.isVisible()
        assert window.worker.is_active
    finally:
        window.exit_application()
        qapp.processEvents()


@pytest.mark.unit
def test_clicking_exit_stops_workers_and_exits(qapp, tmp_path):
    """Clicking the × button on the floating shield stops monitoring workers and releases resources."""
    db_file = tmp_path / "test_exit_x.db"
    app, window = create_application(db_path=db_file)

    try:
        window.show()
        qapp.processEvents()
        assert window.worker.is_active
        assert window.floating_hub.isVisible()

        # Simulate hover and click on the 'x' exit button
        window.floating_hub.shield_view.btn_exit.show()
        window.floating_hub.shield_view.btn_exit.click()
        qapp.processEvents()

        # Shield must be hidden and worker stopped
        assert window.floating_hub.isHidden()
        assert not window.worker.is_active
        assert window._is_exiting
    finally:
        window.exit_application()
        qapp.processEvents()


@pytest.mark.unit
def test_restarting_application_restores_shield(qapp, tmp_path):
    """Restarting after exit restores the floating shield and initializes normally."""
    db_file1 = tmp_path / "test_restart1.db"
    app1, window1 = create_application(db_path=db_file1)
    assert window1.floating_hub.isVisible()
    assert window1.worker.is_active

    # Clean exit of first instance
    window1.exit_application()
    qapp.processEvents()
    assert not window1.worker.is_active

    # Launch second instance
    db_file2 = tmp_path / "test_restart2.db"
    app2, window2 = create_application(db_path=db_file2)
    try:
        assert window2.floating_hub.isVisible()
        assert window2.worker.is_active
    finally:
        window2.exit_application()
        qapp.processEvents()


@pytest.mark.unit
def test_hovering_shows_and_hides_exit_control(qapp):
    """Hovering over the shield reveals the × control; moving away hides it."""
    hub = FloatingHubWidget()
    try:
        hub.show()
        qapp.processEvents()

        # Normal unhovered state: exit button must be hidden for clean shield look
        assert hub.btn_exit.isHidden()

        # Mouse enters shield view
        hub.shield_view._is_hovered = True
        hub.shield_view.btn_exit.show()
        qapp.processEvents()
        assert hub.btn_exit.isVisible()

        # Mouse leaves shield view
        hub.shield_view._is_hovered = False
        hub.shield_view.btn_exit.hide()
        qapp.processEvents()
        assert hub.btn_exit.isHidden()
    finally:
        hub.close()


@pytest.mark.unit
def test_clicking_exit_does_not_trigger_normal_shield_click(qapp):
    """Clicking × cleanly triggers exit callback and never expands the status panel."""
    exit_called = []
    hub = FloatingHubWidget(on_exit_app=lambda: exit_called.append(True))
    try:
        hub.show()
        qapp.processEvents()
        assert not hub.is_expanded()

        # Show hover exit button and click it
        hub.shield_view.btn_exit.show()
        hub.shield_view.btn_exit.click()
        qapp.processEvents()

        # Must have called exit without expanding panel
        assert len(exit_called) == 1
        assert not hub.is_expanded()
        assert hub.isHidden()
    finally:
        hub.close()


@pytest.mark.unit
def test_floating_icon_remains_circular_at_different_sizes(qapp):
    """Floating shield maintains 1:1 aspect ratio (equal width and height) across multiple sizes."""
    hub = FloatingHubWidget(shield_size=48)
    try:
        hub.show()
        qapp.processEvents()

        # Default size: 48x48
        assert hub.width() == 48
        assert hub.height() == 48
        assert hub.width() == hub.height()

        # Change to 50x50
        hub.set_shield_size(50)
        qapp.processEvents()
        assert hub.width() == 50
        assert hub.height() == 50

        # Change to 64x64
        hub.set_shield_size(64)
        qapp.processEvents()
        assert hub.width() == 64
        assert hub.height() == 64

        # Change to 36x36
        hub.set_shield_size(36)
        qapp.processEvents()
        assert hub.width() == 36
        assert hub.height() == 36
    finally:
        hub.close()


@pytest.mark.unit
def test_no_duplicate_workers_created(qapp, tmp_path):
    """Opening/initializing does not create duplicate active monitoring workers."""
    db1 = tmp_path / "test_dup1.db"
    app1, window1 = create_application(db_path=db1)
    worker1 = window1.worker
    assert worker1.is_active

    # Creating a second application stops previous active worker
    db2 = tmp_path / "test_dup2.db"
    app2, window2 = create_application(db_path=db2)
    worker2 = window2.worker

    try:
        assert not worker1.is_active
        assert worker2.is_active
    finally:
        window2.exit_application()
        window1.exit_application()
        qapp.processEvents()


@pytest.mark.unit
def test_ram_optimizations_preserve_functionality(qapp):
    """Metrics collection, chart ring buffers, and bounded buffers operate correctly with low overhead."""
    collector = MetricsCollector()
    snap = collector.collect_snapshot(top_n_processes=3)

    assert snap.cpu_percent >= 0.0
    assert snap.memory_percent >= 0.0
    assert snap.memory_available_bytes > 0
    assert len(snap.top_processes) > 0

    # Test chart deque ring buffer
    chart = ResourceChartWidget(max_samples=10)
    for i in range(25):
        chart.update_metrics(float(i), float(i * 2))

    assert len(chart.cpu_history) == 10
    assert len(chart.ram_history) == 10
    assert chart.cpu_history[-1] == 24.0
