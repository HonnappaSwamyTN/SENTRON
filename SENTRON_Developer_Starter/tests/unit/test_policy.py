"""
Unit tests for Deterministic Policy Engine (AgentGuard B - Dev2).
Governing Criteria: AC-03, AC-06
"""
import pytest

@pytest.mark.unit
@pytest.mark.skip(reason="Pending implementation by Dev2 in agentguard.policy (AC-03)")
def test_blocked_action_evaluation():
    """
    AC-03: Blocked actions evaluate to PolicyDecision.BLOCK with reason code.
    """
    raise NotImplementedError("Dev2 must implement agentguard.policy and this test")


@pytest.mark.unit
@pytest.mark.skip(reason="Pending implementation by Dev2 in agentguard.policy (AC-06)")
def test_unknown_or_underspecified_high_impact_action_not_auto_allowed():
    """
    AC-06: Unknown or underspecified high-impact actions must return ASK or BLOCK, never ALLOW.
    """
    raise NotImplementedError("Dev2 must implement agentguard.policy and this test")
