"""
Integration tests for Offline Operation & Zero External AI (Core).
Governing Criteria: AC-18
"""
from pathlib import Path
import pytest
from sentron.agentguard.approval import ApprovalManager
from sentron.agentguard.audit import SqliteAuditLog
from sentron.agentguard.executor import ControlledExecutor
from sentron.agentguard.policy import PolicyEngine, PolicyRule
from sentron.core.models import ActionRequest, Decision
from sentron.crashguard.metrics import MetricsCollector
from sentron.crashguard.recovery import SafeRecoveryAdvisor
from sentron.crashguard.risk import SustainedRiskDetector


@pytest.mark.integration
@pytest.mark.offline
def test_core_functionality_operates_without_network_or_external_ai():
    """
    AC-18: Core functionality works without an AI service or external internet access.
    """
    # 1. Verify codebase has zero imports of cloud AI SDKs in src/sentron
    src_dir = Path(__file__).resolve().parent.parent.parent / "src" / "sentron"
    forbidden_imports = ["openai", "anthropic", "google.generativeai", "langchain", "groq"]

    for py_file in src_dir.rglob("*.py"):
        content = py_file.read_text(encoding="utf-8")
        for forbidden in forbidden_imports:
            assert f"import {forbidden}" not in content, f"Forbidden cloud AI import '{forbidden}' in {py_file.name}"
            assert f"from {forbidden}" not in content, f"Forbidden cloud AI import '{forbidden}' in {py_file.name}"

    # 2. Verify complete end-to-end operation is local
    audit = SqliteAuditLog(db_path=":memory:")
    policy = PolicyEngine([
        PolicyRule(
            decision=Decision.ALLOW,
            agent_id="local-agent",
            tool_name="file_tool",
            operation="read_file",
            target="test.txt",
        )
    ])
    approvals = ApprovalManager()
    executor = ControlledExecutor(policy, approvals, lambda req: {"local_ok": True}, audit)

    req = ActionRequest(agent_id="local-agent", tool_name="file_tool", operation="read_file", target="test.txt")
    result = executor.execute(req)
    assert result.status == "executed"

    # 3. Verify CrashGuard operates purely locally
    collector = MetricsCollector()
    snapshot = collector.collect_snapshot()
    assert snapshot.cpu_percent >= 0.0

    detector = SustainedRiskDetector()
    alerts = detector.evaluate_snapshot(snapshot)

    advisor = SafeRecoveryAdvisor()
    recs = advisor.generate_recommendations(alerts[0] if alerts else None, snapshot)
    assert len(recs) > 0
