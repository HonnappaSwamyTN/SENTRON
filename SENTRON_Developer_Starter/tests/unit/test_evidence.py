"""
Unit tests for Windows Evidence Collector (CrashGuard B - Dev4).
Governing Criteria: AC-11
"""
import pytest

@pytest.mark.unit
@pytest.mark.windows_only
@pytest.mark.skip(reason="Pending implementation by Dev4 in crashguard.evidence (AC-11)")
def test_windows_evidence_collection_separates_observation_from_cause():
    """
    AC-11: Relevant Windows evidence is displayed when available, separating observations from inferred causes.
    """
    raise NotImplementedError("Dev4 must implement crashguard.evidence and this test")
