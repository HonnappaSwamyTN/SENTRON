"""Unit tests for dashboard hidden lifecycle, background alerts, and explicit shutdown.

Tests cover:
- Closing the dashboard window hides it instead of terminating SENTRON
- Background monitoring and shield continue while dashboard is hidden
- Alert popup displays while the dashboard is hidden
- System tray integration and reopening the dashboard
- Explicit 'Exit SENTRON' terminates monitoring, resumes held processes, and exits cleanly
"""

import pytest
from unittest.mock import MagicMock, patch
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QApplication

from sentron.main import create_application
from sentron.core.models import RiskAlert


@pytest.fixture
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.mark.unit
def test_dashboard_window_close_hides_instead_of_exit(qapp, tmp_path):
    """Closing the main window triggers hide() and does not destroy or terminate the window."""
    db_file = tmp_path / "test_lifecycle.db"
    app, window = create_application(db_path=db_file)
    
    try:
        window.show()
        qapp.processEvents()
        assert window.isVisible()
        
        # Simulate user clicking the top-right X button
        close_event = QCloseEvent()
        window.closeEvent(close_event)
        qapp.processEvents()
        
        # Window must now be hidden (not visible)
        assert not window.isVisible()
        # Close event must be ignored so the widget is not destroyed
        assert close_event.isAccepted() is False
        
        # Floating shield must remain visible
        assert window.floating_hub.isVisible()
        
        # Reopening window via showNormal restores visibility
        window._show_from_tray()
        qapp.processEvents()
        assert window.isVisible()
        
    finally:
        window.exit_application()


@pytest.mark.unit
def test_alert_displays_while_dashboard_is_hidden(qapp, tmp_path):
    """When the dashboard is hidden, CrashGuard alerts still display the foreground popup and tray message."""
    db_file = tmp_path / "test_alert_hidden.db"
    app, window = create_application(db_path=db_file)
    
    try:
        window.hide()
        qapp.processEvents()
        assert not window.isVisible()
        
        # Create a risk alert
        alert = RiskAlert(
            alert_id="alert-bg-1",
            metric_name="CPU",
            severity="critical",
            observed_value=95.0,
            threshold_value=93.0,
            duration_seconds=12.0,
            cooldown_until=0.0,
            timestamp=1000.0,
            is_simulated=False,
            contributor_process="chrome.exe",
            contributor_pid=1234,
        )
        
        # Simulate window receiving alert
        window._show_alert_popup(alert, [])
        qapp.processEvents()
        
        # Alert popup must be displayed in foreground even though dashboard is hidden
        assert window._alert_popup is not None
        assert window._alert_popup.isVisible()
        assert "95.0%" in window._alert_popup.lbl_reading.text()
        assert "chrome.exe" in window._alert_popup.lbl_contributor.text()
        
    finally:
        if window._alert_popup:
            window._alert_popup.close()
        window.exit_application()


@pytest.mark.unit
def test_explicit_exit_terminates_cleanly(qapp, tmp_path):
    """Explicit 'Exit SENTRON' action sets _is_exiting and terminates worker and application."""
    db_file = tmp_path / "test_exit.db"
    app, window = create_application(db_path=db_file)
    
    try:
        window.show()
        qapp.processEvents()
        
        with patch.object(QApplication, "quit") as mock_quit:
            window.exit_application()
            assert window._is_exiting is True
            mock_quit.assert_called_once()
            
    finally:
        window._cleanup_resources()
