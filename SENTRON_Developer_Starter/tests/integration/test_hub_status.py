"""
Integration tests for Desktop Hub Operational Status (UI / Core).
Governing Criteria: AC-15
"""
import sys
import pytest
from PySide6.QtWidgets import QApplication
from sentron.ui.hub_widget import FloatingHubWidget


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(["-platform", "offscreen"])
    return app


@pytest.mark.integration
def test_floating_hub_exposes_modules_and_accurately_represents_status(qapp):
    """
    AC-15: The floating hub exposes both modules and accurately represents their status.
    Never claims a module is active or protecting if its background worker is stopped.
    """
    hub = FloatingHubWidget()

    # 1. Repositioning works
    hub.move(100, 200)
    assert hub.pos().x() == 100
    assert hub.pos().y() == 200

    # 2. Honest status: when worker is stopped / inactive, status must reflect Inactive/Degraded, never Active
    hub.update_status(agent_pending_count=0, crash_active=False, cpu_pct=0.0, ram_pct=0.0)
    assert "Inactive" in hub.lbl_crashguard.text() or "Stopped" in hub.lbl_crashguard.text()
    assert "DEGRADED" in hub.lbl_overall.text()
    assert "Active" not in hub.lbl_crashguard.text().split()[1:]

    # 3. When active, reflects live stats
    hub.update_status(agent_pending_count=0, crash_active=True, cpu_pct=25.0, ram_pct=45.0)
    assert "25%" in hub.lbl_crashguard.text()
    assert "PROTECTED" in hub.lbl_overall.text()

    # 4. When pending approvals exist, count is accurately reflected
    hub.update_status(agent_pending_count=2, crash_active=True, cpu_pct=25.0, ram_pct=45.0)
    assert "2 Awaiting Approval" in hub.lbl_agentguard.text()

    hub.close()
