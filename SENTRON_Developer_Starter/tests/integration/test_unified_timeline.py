"""
Integration tests for Unified Event Timeline & Correlation (Core / UI).
Governing Criteria: AC-16
"""
import time
import pytest
from PySide6.QtWidgets import QApplication
from sentron.core.models import UnifiedEvent
from sentron.core.storage import EventStore
from sentron.ui.timeline_panel import UnifiedTimelinePanel


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(["-platform", "offscreen"])
    return app


@pytest.mark.integration
def test_security_and_health_events_searchable_in_unified_timeline(qapp):
    """
    AC-16: Security and system-health events are searchable in the unified timeline.
    Correlation does not imply causation.
    """
    store = EventStore(db_path=":memory:")

    t0 = time.time()
    # 1. Record AgentGuard security event
    store.record_unified_event(
        UnifiedEvent(
            event_id="ag-event-1",
            timestamp=t0,
            subsystem="AgentGuard",
            event_type="POLICY_EVAL",
            severity="info",
            summary="Allowed read_file on sample.txt",
            payload_json="{}",
        )
    )

    # 2. Record CrashGuard health event
    store.record_unified_event(
        UnifiedEvent(
            event_id="cg-event-2",
            timestamp=t0 + 1.0,
            subsystem="CrashGuard",
            event_type="SYSTEM_ALERT",
            severity="warning",
            summary="Sustained CPU pressure at 92.0%",
            payload_json="{}",
        )
    )

    # 3. Interleaved timeline query
    timeline = store.get_unified_timeline(start_time=t0 - 10.0, end_time=t0 + 10.0)
    assert len(timeline) == 2
    subsystems = [ev.subsystem for ev in timeline]
    assert "AgentGuard" in subsystems
    assert "CrashGuard" in subsystems

    # 4. Verify UI includes causality disclaimer
    panel = UnifiedTimelinePanel(event_store=store)
    all_text = panel.findChildren(object)
    label_texts = " ".join(getattr(child, "text", lambda: "")() for child in all_text)
    assert "causality" in label_texts.lower() or "correlation" in label_texts.lower()

    panel.close()
    store.close()
