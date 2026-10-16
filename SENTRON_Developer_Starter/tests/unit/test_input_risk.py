"""
Unit tests for Suspicious-Input Analyzer (AgentGuard A - Dev1).
Governing Criteria: AC-01
"""
import pytest

@pytest.mark.unit
@pytest.mark.skip(reason="Pending implementation by Dev1 in agentguard.input_risk (AC-01)")
def test_known_suspicious_input_produces_finding_with_evidence():
    """
    AC-01: Known suspicious input produces a finding with supporting evidence.
    Verifies that prompt injection patterns return structured risk signals with evidence snippets.
    """
    raise NotImplementedError("Dev1 must implement agentguard.input_risk and this test")


@pytest.mark.unit
@pytest.mark.skip(reason="Pending implementation by Dev1 in agentguard.input_risk (AC-01)")
def test_benign_input_does_not_flag_critical_risk():
    """
    AC-01: Benign prompts do not generate critical risk signals.
    """
    raise NotImplementedError("Dev1 must implement agentguard.input_risk and this test")
