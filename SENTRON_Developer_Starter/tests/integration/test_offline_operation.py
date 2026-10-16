"""
Integration tests for Offline Operation & Zero External AI (Core).
Governing Criteria: AC-18
"""
import pytest

@pytest.mark.integration
@pytest.mark.offline
@pytest.mark.skip(reason="Pending full subsystem integration to verify offline functionality (AC-18)")
def test_core_functionality_operates_without_network_or_external_ai():
    """
    AC-18: Core functionality works without an AI service or external internet access.
    """
    raise NotImplementedError("Integration Owner must implement offline verification test")
