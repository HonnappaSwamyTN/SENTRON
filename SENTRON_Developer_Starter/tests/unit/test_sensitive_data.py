"""
Unit tests for Sensitive-Data Detector (AgentGuard A - Dev1).
Governing Criteria: AC-02
"""
import pytest
from sentron.agentguard.sensitive_data import SensitiveDataDetector


@pytest.mark.unit
def test_recognizable_secret_is_detected_and_redacted():
    """
    AC-02: A recognizable test secret is detected and redacted from logs.
    Verifies that known API keys (e.g., sk-..., ghp_...) are masked into [REDACTED_*].
    """
    detector = SensitiveDataDetector()
    payload = "Bearer sk-1234567890abcdef1234567890abcdef with password=SuperSecretPassword123"

    findings = detector.scan(payload)
    categories = [f.category for f in findings]
    assert "API_KEY" in categories or "TOKEN" in categories
    assert "PASSWORD" in categories

    redacted_text, was_redacted = detector.redact(payload)
    assert was_redacted is True
    assert "sk-1234567890abcdef1234567890abcdef" not in redacted_text
    assert "SuperSecretPassword123" not in redacted_text
    assert "[REDACTED_" in redacted_text
