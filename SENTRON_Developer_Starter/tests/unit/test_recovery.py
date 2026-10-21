"""
Unit tests for Safe Recovery Advisor (CrashGuard B - Dev4).
Governing Criteria: AC-12
"""
import pytest
from sentron.core.models import ProcessSummary, RiskAlert, SystemSnapshot, WindowsEvidence
from sentron.crashguard.recovery import SafeRecoveryAdvisor


@pytest.mark.unit
def test_warnings_produce_safe_recommendations_without_auto_kill():
    """
    AC-12: Warnings produce safe, relevant recovery recommendations. No processes are automatically killed or suspended.
    """
    advisor = SafeRecoveryAdvisor()
    snapshot = SystemSnapshot(
        timestamp=1000.0,
        cpu_percent=40.0,
        memory_percent=92.0,
        memory_available_bytes=500 * 1024**2,
        disk_free_bytes=50 * 1024**3,
        top_processes=(
            ProcessSummary(pid=4520, name="heavy_render.exe", cpu_percent=35.0, memory_mb=3800.0),
        ),
    )
    alert = RiskAlert(
        alert_id="test-alert-1",
        metric_name="Memory",
        severity="critical",
        observed_value=92.0,
        threshold_value=85.0,
        duration_seconds=35.0,
        cooldown_until=1100.0,
        timestamp=1000.0,
    )

    recs = advisor.generate_recommendations(alert, snapshot)
    assert len(recs) >= 2

    for rec in recs:
        # All recommendations must be non-automated advice to the user
        assert rec.is_automated is False
        assert len(rec.suggested_action) > 0
        assert len(rec.confirmed_observations) > 0

    # Verify safe advice presence
    actions_text = " ".join(r.suggested_action for r in recs)
    assert "save" in actions_text.lower()
    assert "heavy_render.exe" in actions_text or "manually" in actions_text.lower()


@pytest.mark.unit
def test_recovery_recommendations_have_help_urls():
    """AC-12: Recovery Enhancements - All recovery recommendations integrate relevant help URLs."""
    advisor = SafeRecoveryAdvisor()
    snapshot = SystemSnapshot(
        timestamp=1000.0,
        cpu_percent=90.0,
        memory_percent=85.0,
        memory_available_bytes=200 * 1024**2,
        disk_free_bytes=1 * 1024**3,  # Critical disk (< 2GB)
        top_processes=(
            ProcessSummary(pid=1001, name="compiler.exe", cpu_percent=85.0, memory_mb=4000.0),
        ),
    )
    alert = RiskAlert(
        alert_id="test-alert-cpu",
        metric_name="CPU",
        severity="warning",
        observed_value=90.0,
        threshold_value=85.0,
        duration_seconds=30.0,
        cooldown_until=1100.0,
        timestamp=1000.0,
    )

    recs = advisor.generate_recommendations(alert, snapshot)
    assert len(recs) >= 3

    for rec in recs:
        # Every recommendation must have a valid help URL
        assert rec.help_url is not None
        assert rec.help_url.startswith("https://")
        assert len(rec.help_urls) >= 1
        assert rec.help_urls[0] == rec.help_url
        assert rec.is_automated is False


@pytest.mark.unit
def test_evidence_recovery_recommendations_with_help_urls():
    """AC-12: Diagnostic recovery guidance for Windows crash/hang evidence provides targeted help URLs."""
    advisor = SafeRecoveryAdvisor()

    test_cases = [
        (1000, "Application", "bad_app.exe", "troubleshoot/windows-client/application-management"),
        (1001, "Application", "Windows Error Reporting", "windows/win32/wer"),
        (1002, "Application", "frozen_proc.exe", "application-hangs-troubleshooting"),
        (6008, "System", "EventLog", "event-id-41-restart"),
        (41, "System", "Kernel-Power", "event-id-41-restart"),
        (1074, "System", "USER32", "system-shutdown-events"),
        (219, "System", "Kernel-PnP", "update-drivers-manually"),
    ]

    for ev_id, chan, src, expected_url_keyword in test_cases:
        ev = WindowsEvidence(
            event_id=ev_id,
            log_channel=chan,
            source=src,
            event_time="2026-10-21T04:00:00Z",
            description=f"Test evidence for event {ev_id}",
        )
        recs = advisor.generate_evidence_recommendations(ev)
        assert len(recs) == 1
        rec = recs[0]
        assert rec.is_automated is False
        assert rec.help_url is not None
        assert rec.help_url.startswith("https://")
        assert expected_url_keyword in rec.help_url

