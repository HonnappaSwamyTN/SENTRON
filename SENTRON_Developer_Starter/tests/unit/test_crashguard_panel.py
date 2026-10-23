"""Unit tests for CrashGuardPanel Evidence Display and UI Integration (AC-11, AC-14, AC-16)."""
from unittest.mock import MagicMock
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from sentron.core.models import WindowsEvidence
from sentron.core.storage import EventStore
from sentron.crashguard.evidence import WindowsEvidenceCollector
from sentron.crashguard.worker import MonitoringWorker
from sentron.main import create_application
from sentron.ui.crashguard_panel import CrashGuardPanel


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(["-platform", "offscreen"])
    return app


@pytest.mark.unit
def test_crashguard_panel_evidence_table_population(qapp):
    """CrashGuardPanel displays evidence with timestamps, event IDs, source, and concise explanation."""
    mock_collector = MagicMock(spec=WindowsEvidenceCollector)
    mock_collector.format_diagnostic_statement.return_value = (
        "Confirmed: Application Error recorded in Application log by source 'agent_host.exe' at 2026-10-20T14:30:00Z.",
        "Suspected: The process associated with 'agent_host.exe' may have experienced an unhandled exception.",
    )

    worker = MonitoringWorker(interval_seconds=1.0, evidence_collector=mock_collector)
    panel = CrashGuardPanel(worker=worker)

    ev = WindowsEvidence(
        event_id=1000,
        log_channel="Application",
        source="agent_host.exe",
        event_time="2026-10-20T14:30:00.123Z",
        description="Faulting module name: ucrtbase.dll",
    )

    panel.update_evidence([ev], warnings=[])

    # Table row count and columns
    assert panel.get_evidence_count() == 1
    assert panel.evidence_table.rowCount() == 1
    assert panel.evidence_table.columnCount() == 4

    # Timestamp
    assert "14:30:00" in panel.evidence_table.item(0, 0).text()
    # Event ID
    assert panel.evidence_table.item(0, 1).text() == "1000"
    # Source
    assert panel.evidence_table.item(0, 2).text() == "agent_host.exe"
    # Explanation
    explanation = panel.evidence_table.item(0, 3).text()
    assert "Confirmed:" in explanation
    assert "Application Error" in explanation
    assert "Suspected:" in explanation
    assert "agent_host.exe" in explanation

    # Underlying model data
    stored_ev = panel.get_evidence_item(0)
    assert stored_ev == ev
    assert panel.evidence_table.item(0, 3).data(Qt.UserRole) == ev

    # Status label
    assert "1 diagnostic record" in panel.lbl_evidence_status.text()

    panel.close()


@pytest.mark.unit
def test_crashguard_panel_fallback_warnings_display(qapp):
    """Graceful degradation display when Windows Event Log is unavailable or permissions denied."""
    worker = MonitoringWorker(interval_seconds=1.0)
    panel = CrashGuardPanel(worker=worker)

    # Empty evidence with fallback warning
    panel.update_evidence([], warnings=["windows_event_log_unsupported_platform"])
    assert panel.evidence_table.rowCount() == 0
    assert "Fallback active" in panel.lbl_evidence_status.text()
    assert "windows_event_log_unsupported_platform" in panel.lbl_evidence_status.text()

    # Empty evidence with access denied
    panel.update_evidence([], warnings=["windows_event_log_access_denied"])
    assert panel.evidence_table.rowCount() == 0
    assert "windows_event_log_access_denied" in panel.lbl_evidence_status.text()

    panel.close()


@pytest.mark.unit
def test_main_window_evidence_flow_and_timeline_integration(qapp, tmp_path):
    """End-to-end evidence event flow into CrashGuard UI, EventStore persistence, and Unified Timeline."""
    db_file = tmp_path / "test_evidence_flow.db"
    app, window = create_application(db_path=db_file, start_worker=False)

    try:
        ev = WindowsEvidence(
            event_id=6008,
            log_channel="System",
            source="EventLog",
            event_time="2026-10-20T10:00:00Z",
            description="The previous system shutdown was unexpected.",
        )

        # Emit evidence signal through main window
        window.evidence_received.emit([ev], [])
        qapp.processEvents()

        # 1. CrashGuardPanel shows evidence
        assert window.crashguard_panel.get_evidence_count() == 1
        assert window.crashguard_panel.evidence_table.rowCount() == 1
        assert window.crashguard_panel.evidence_table.item(0, 1).text() == "6008"

        # 2. Persisted to EventStore
        recent = window.event_store.get_recent_events(limit=5, subsystem="CrashGuard")
        assert len(recent) >= 1
        crash_record = next((r for r in recent if r.event_type == "HOST_CRASH_EVIDENCE"), None)
        assert crash_record is not None
        assert crash_record.severity == "critical"
        assert "Unexpected System Shutdown" in crash_record.summary

        # 3. Timeline panel refreshed
        assert window.timeline_panel.table.rowCount() >= 1

    finally:
        window.exit_application()
