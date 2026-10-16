"""
Unit tests for Sensitive-Data Detector (AgentGuard A - Dev1).
Governing Criteria: AC-02
"""
import pytest

@pytest.mark.unit
@pytest.mark.skip(reason="Pending implementation by Dev1 in agentguard.sensitive_data (AC-02)")
def test_recognizable_secret_is_detected_and_redacted():
    """
    AC-02: A recognizable test secret is detected and redacted from logs.
    Verifies that known API keys (e.g., sk-..., ghp_...) are masked into [REDACTED_*].
    """
    raise NotImplementedError("Dev1 must implement agentguard.sensitive_data and this test")
