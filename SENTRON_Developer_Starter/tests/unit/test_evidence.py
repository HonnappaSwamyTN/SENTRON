"""
Unit tests for Windows Evidence Collector (CrashGuard B - Dev4).
Governing Criteria: AC-11
"""
import pytest
from sentron.core.models import WindowsEvidence
from sentron.crashguard.evidence import WindowsEvidenceCollector


@pytest.mark.unit
def test_evidence_separates_confirmed_observations_from_inferred_hypotheses():
    """
    AC-11: Formats diagnostic statements explicitly distinguishing confirmed facts from inferred causes.
    """
    collector = WindowsEvidenceCollector()
    mock_ev = WindowsEvidence(
        event_id=1000,
        log_channel="Application",
        source="faulty_service.exe",
        event_time="2026-10-19T10:15:30Z",
        description="Faulting application name: faulty_service.exe, version: 1.0.0.0",
    )

    confirmed, inferred = collector.format_diagnostic_statement(mock_ev)
    assert "Confirmed:" in confirmed
    assert "Application Error" in confirmed
    assert "faulty_service.exe" in confirmed
    assert "Suspected:" in inferred
