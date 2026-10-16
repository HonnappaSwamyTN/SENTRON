"""
Integration tests for Security Audit History & Search (AgentGuard / Core).
Governing Criteria: AC-08
"""
import pytest

@pytest.mark.integration
@pytest.mark.skip(reason="Pending implementation by Dev2 / Integration Owner in storage/ui (AC-08)")
def test_recent_security_events_displayed_and_searchable():
    """
    AC-08: Recent security events are displayed (latest 5) and older events can be searched.
    """
    raise NotImplementedError("Dev2 and Integration Owner must implement audit history and this test")
