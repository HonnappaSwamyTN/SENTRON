"""Unit tests for Light and Dark themes, persistence, and switcher in SENTRON.

Tests cover:
- Theme selection and stylesheet generation
- Light mode palette: warm-white surfaces, dark readable text, charcoal elements, gold accents
- Dark mode palette: dark charcoal surfaces, light readable text, gold accents
- Settings persistence and restoring theme on startup without requiring user to re-toggle
- Theme change signal propagation to Main Window
"""

import tempfile
from pathlib import Path
import pytest
from PySide6.QtWidgets import QApplication

from sentron.core.settings import AppSettings, SettingsManager
from sentron.ui.styles import (
    get_theme_qss,
    LIGHT_THEME_QSS,
    DARK_THEME_QSS,
)
from sentron.main import create_application


@pytest.fixture
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.mark.unit
def test_light_theme_palette_compliance():
    """Light theme uses warm-white surfaces, dark readable text, and gold accents."""
    qss = get_theme_qss("light")
    
    # Warm-white surfaces (#F5F2E9 or #FFFFFF)
    assert "#F5F2E9" in qss or "#f5f2e9" in qss.lower()
    # Dark readable text (#171717 or #2B2B2B)
    assert "#171717" in qss or "#171717" in qss.lower()
    # Gold accents (#E2B83B or #C49B24)
    assert "#E2B83B" in qss or "#e2b83b" in qss.lower()


@pytest.mark.unit
def test_dark_theme_palette_compliance():
    """Dark theme uses dark charcoal surfaces, light readable text, and gold accents."""
    qss = get_theme_qss("dark")
    
    # Dark charcoal surfaces (#141414 or #1C1C1C)
    assert "#141414" in qss or "#141414" in qss.lower()
    # Light readable text (#F5F2E9 or #E6EDF3)
    assert "#F5F2E9" in qss or "#f5f2e9" in qss.lower()
    # Gold accents (#E2B83B or #F0C952)
    assert "#E2B83B" in qss or "#e2b83b" in qss.lower()


@pytest.mark.unit
def test_settings_persistence_saves_and_restores_theme(tmp_path):
    """SettingsManager persists user theme selection to disk and restores it on startup."""
    settings_file = tmp_path / "sentron_settings.json"
    mgr1 = SettingsManager(config_path=settings_file)
    
    # Default is dark
    assert mgr1.get_theme() == "dark"
    
    # Switch to light mode and save
    mgr1.set_theme("light")
    assert mgr1.get_theme() == "light"
    assert settings_file.exists()
    
    # Initialize a fresh SettingsManager instance to simulate next application launch
    mgr2 = SettingsManager(config_path=settings_file)
    # Saved theme must be restored automatically without user re-toggling
    assert mgr2.get_theme() == "light"
    
    # Switch back to dark mode
    mgr2.set_theme("dark")
    assert mgr2.get_theme() == "dark"
    
    # Verify again with fresh instance
    mgr3 = SettingsManager(config_path=settings_file)
    assert mgr3.get_theme() == "dark"


@pytest.mark.unit
def test_theme_toggle_updates_main_window(qapp, tmp_path):
    """Clicking theme toggle in SentronMainWindow switches stylesheet and updates button text."""
    db_file = tmp_path / "test_theme_ui.db"
    settings_file = tmp_path / "test_theme_settings.json"
    
    app, window = create_application(db_path=db_file)
    window.settings_manager = SettingsManager(config_path=settings_file)
    
    try:
        # Initial theme is dark
        window.apply_theme("dark")
        assert window.current_theme == "dark"
        assert "🌙 Dark" in window.btn_theme_toggle.text()
        assert window.settings_manager.get_theme() == "dark"
        
        # Toggle to light theme
        window.btn_theme_toggle.click()
        assert window.current_theme == "light"
        assert "☀️ Light" in window.btn_theme_toggle.text()
        assert window.settings_manager.get_theme() == "light"
        
        # Toggle back to dark theme
        window.btn_theme_toggle.click()
        assert window.current_theme == "dark"
        assert "🌙 Dark" in window.btn_theme_toggle.text()
        assert window.settings_manager.get_theme() == "dark"
    finally:
        window.exit_application()


@pytest.mark.unit
def test_theme_propagation_to_all_panels(qapp, tmp_path):
    """Switching theme propagates to AgentGuard, CrashGuard, Timeline, and Test panels."""
    db_file = tmp_path / "test_theme_prop.db"
    settings_file = tmp_path / "test_theme_prop_settings.json"

    app, window = create_application(db_path=db_file)
    window.settings_manager = SettingsManager(config_path=settings_file)

    try:
        # 1. Dark Mode
        window.apply_theme("dark")
        assert window.current_theme == "dark"
        assert window.agentguard_panel._theme == "dark"
        assert window.timeline_panel._theme == "dark"
        assert window.test_panel._theme == "dark"
        assert window.crashguard_panel._theme == "dark"

        # Check inspector, approval box, and disclaimer dark styling
        assert "#1E1E1E" in window.agentguard_panel.req_text.styleSheet()
        assert "#2D2200" in window.agentguard_panel.approval_box.styleSheet()
        assert "#2D2200" in window.timeline_panel.disclaimer_box.styleSheet()
        assert "#2D2200" in window.test_panel.disclaimer_frame.styleSheet()

        # 2. Light Mode
        window.apply_theme("light")
        assert window.current_theme == "light"
        assert window.agentguard_panel._theme == "light"
        assert window.timeline_panel._theme == "light"
        assert window.test_panel._theme == "light"
        assert window.crashguard_panel._theme == "light"

        # Check inspector, approval box, and disclaimer light styling
        assert "#FFFFFF" in window.agentguard_panel.req_text.styleSheet()
        assert "#FAF6ED" in window.agentguard_panel.approval_box.styleSheet()
        assert "#FAF6ED" in window.timeline_panel.disclaimer_box.styleSheet()
        assert "#FAF6ED" in window.test_panel.disclaimer_frame.styleSheet()

        # 3. Toggle via button switches back to dark
        window.btn_theme_toggle.click()
        assert window.current_theme == "dark"
        assert window.agentguard_panel._theme == "dark"
        assert window.timeline_panel._theme == "dark"
        assert window.test_panel._theme == "dark"
    finally:
        window.exit_application()


@pytest.mark.unit
def test_agentguard_audit_text_contrast_in_both_themes(qapp, tmp_path):
    """Audit feed text maintains accessible contrast in both Dark and Light themes."""
    import time
    from sentron.agentguard.audit import SqliteAuditLog
    from sentron.agentguard.approval import ApprovalManager
    from sentron.agentguard.executor import ControlledExecutor
    from sentron.agentguard.policy import PolicyEngine
    from sentron.core.models import AuditEvent, Decision
    from sentron.ui.agentguard_panel import AgentGuardPanel

    db_path = str(tmp_path / "test_ag_audit_contrast.db")
    audit_log = SqliteAuditLog(db_path=db_path)
    policy_engine = PolicyEngine()
    approval_manager = ApprovalManager()
    executor = ControlledExecutor(
        policy_engine=policy_engine,
        approval_manager=approval_manager,
        action_handler=lambda req: None,
        audit_sink=audit_log,
    )

    # Record test event
    ev = AuditEvent(
        event_type="policy_decision",
        action_id="test-contrast-act-1",
        agent_id="test-agent",
        decision=Decision.ALLOW,
        execution_status="executed",
    )
    audit_log.record_event(ev)

    panel = AgentGuardPanel(
        executor=executor,
        policy_engine=policy_engine,
        approval_manager=approval_manager,
        audit_log=audit_log,
    )

    try:
        # Dark Theme
        panel.set_theme("dark")
        assert panel.audit_table.rowCount() >= 1
        item_time = panel.audit_table.item(0, 0)
        assert item_time is not None
        # Must be light readable text (#F5F2E9) in Dark mode, NOT dark #171717
        assert item_time.foreground().color().name().upper() == "#F5F2E9"
        # Outcome color for ALLOW in Dark mode is green #22C55E
        item_outcome = panel.audit_table.item(0, 3)
        assert item_outcome is not None
        assert item_outcome.foreground().color().name().upper() == "#22C55E"

        # Light Theme
        panel.set_theme("light")
        item_time_light = panel.audit_table.item(0, 0)
        assert item_time_light is not None
        # Must be dark readable text (#171717) in Light mode
        assert item_time_light.foreground().color().name().upper() == "#171717"
        # Outcome color for ALLOW in Light mode is dark green #137333
        item_outcome_light = panel.audit_table.item(0, 3)
        assert item_outcome_light is not None
        assert item_outcome_light.foreground().color().name().upper() == "#137333"
    finally:
        panel.close()
        audit_log.close()


@pytest.mark.unit
def test_timeline_severity_contrast_in_both_themes(qapp):
    """Timeline severity items use accessible blue (#58A6FF / #0969DA) instead of unreadable cyan."""
    import time
    from sentron.core.models import UnifiedEvent
    from sentron.core.storage import EventStore
    from sentron.ui.timeline_panel import UnifiedTimelinePanel

    store = EventStore(db_path=":memory:")
    t0 = time.time()
    store.record_unified_event(
        UnifiedEvent(
            event_id="ev-info-1",
            timestamp=t0,
            subsystem="AgentGuard",
            event_type="TEST_INFO",
            severity="info",
            summary="Info event contrast check",
            payload_json="{}",
        )
    )

    panel = UnifiedTimelinePanel(event_store=store)
    try:
        # 1. Dark Mode
        panel.set_theme("dark")
        assert panel.table.rowCount() == 1
        sev_item_dark = panel.table.item(0, 3)
        assert sev_item_dark is not None
        # Must be #58A6FF in Dark Mode (accessible blue, NOT cyan)
        assert sev_item_dark.foreground().color().name().upper() == "#58A6FF"
        time_item_dark = panel.table.item(0, 0)
        assert time_item_dark.foreground().color().name().upper() == "#F5F2E9"

        # 2. Light Mode
        panel.set_theme("light")
        sev_item_light = panel.table.item(0, 3)
        assert sev_item_light is not None
        # Must be #0969DA in Light Mode (accessible blue with high contrast against white, NOT cyan)
        assert sev_item_light.foreground().color().name().upper() == "#0969DA"
        time_item_light = panel.table.item(0, 0)
        assert time_item_light.foreground().color().name().upper() == "#171717"
    finally:
        panel.close()
        store.close()
