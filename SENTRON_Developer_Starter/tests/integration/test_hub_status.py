"""
Integration tests for Desktop Hub Operational Status (UI / Core).
Governing Criteria: AC-15
"""
import pytest

@pytest.mark.integration
@pytest.mark.skip(reason="Pending implementation by Integration Owner in ui/hub (AC-15)")
def test_floating_hub_exposes_modules_and_accurately_represents_status():
    """
    AC-15: The floating hub exposes both modules and accurately represents their status.
    Never claims a module is active or protecting if its background worker is stopped.
    """
    raise NotImplementedError("Integration Owner must implement ui hub and this test")
