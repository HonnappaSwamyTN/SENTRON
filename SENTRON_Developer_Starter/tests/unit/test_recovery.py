"""
Unit tests for Safe Recovery Advisor (CrashGuard B - Dev4).
Governing Criteria: AC-12
"""
import pytest
from sentron.core.models import ProcessSummary, RiskAlert, SystemSnapshot
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
