"""
Unit tests for Core Storage & Retention (Core / Integration Owner).
Governing Criteria: AC-17
"""
import pytest

@pytest.mark.unit
@pytest.mark.skip(reason="Pending implementation by Integration Owner in core.storage (AC-17)")
def test_sensitive_values_redacted_and_retention_configurable():
    """
    AC-17: Sensitive values are redacted where detected, and event retention is configurable.
    """
    raise NotImplementedError("Integration Owner must implement core.storage and this test")
