"""
Unit tests for Scoped Approval Manager (AgentGuard B - Dev2).
Governing Criteria: AC-04, AC-05
"""
import pytest

@pytest.mark.unit
@pytest.mark.skip(reason="Pending implementation by Dev2 in agentguard.approval (AC-04)")
def test_action_requiring_approval_cannot_execute_before_approval():
    """
    AC-04: An action requiring approval cannot execute before approval is granted.
    """
    raise NotImplementedError("Dev2 must implement agentguard.approval and this test")


@pytest.mark.unit
@pytest.mark.skip(reason="Pending implementation by Dev2 in agentguard.approval (AC-05)")
def test_scope_mutation_invalidates_prior_approval():
    """
    AC-05: Changing an approved action's target or destination invalidates approval when the change exceeds its scope.
    """
    raise NotImplementedError("Dev2 must implement agentguard.approval and this test")
