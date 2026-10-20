"""SENTRON: Local Security Guard for AI Actions and System Stability.

Desktop Entry Point (Windows PySide6 Application).
Runs offline with zero external cloud AI or external APIs.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from sentron.agentguard.approval import ApprovalManager
from sentron.agentguard.audit import SqliteAuditLog
from sentron.agentguard.executor import ControlledExecutor
from sentron.agentguard.policy import PolicyEngine, PolicyRule
from sentron.core.models import ActionRequest, Decision
from sentron.core.storage import EventStore
from sentron.crashguard.worker import MonitoringWorker
from sentron.ui.main_window import SentronMainWindow


def safe_mock_handler(request: ActionRequest) -> dict:
    """Safe mock action handler for V1 demonstration.

    Does not execute shell commands, alter system files, or access external networks.
    """
    return {
        "status": "success",
        "mock_execution": True,
        "action_id": request.action_id,
        "operation": request.operation,
        "target": request.target or request.destination or "unspecified",
        "message": f"Simulated mock execution of '{request.operation}' succeeded safely.",
    }


def create_application(db_path: str | Path | None = None) -> tuple[QApplication, SentronMainWindow]:
    """Factory to assemble the application components and UI window."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    if db_path is None:
        db_path = Path("sentron_local.db")

    # Shared SQLite database for AuditLog and Unified EventStore
    audit_log = SqliteAuditLog(db_path=db_path)
    event_store = EventStore(connection=audit_log._conn)

    # Policy Engine with demo rules
    configured_rules = [
        PolicyRule(
            decision=Decision.ALLOW,
            agent_id="demo-doc-agent",
            tool_name="mock_file_tool",
            operation="read_file",
            target="sample_log.txt",
            reason_code="demo_read_allowed",
            explanation="Explicitly permitted mock document read.",
        ),
    ]
    policy_engine = PolicyEngine(rules=configured_rules)
    approval_manager = ApprovalManager()

    controlled_executor = ControlledExecutor(
        policy_engine=policy_engine,
        approval_manager=approval_manager,
        action_handler=safe_mock_handler,
        audit_sink=audit_log,
    )

    # CrashGuard background worker with unified event store
    worker = MonitoringWorker(interval_seconds=2.0, buffer_capacity=60, event_store=event_store)
    worker.start()


    window = SentronMainWindow(
        executor=controlled_executor,
        policy_engine=policy_engine,
        approval_manager=approval_manager,
        audit_log=audit_log,
        event_store=event_store,
        worker=worker,
    )

    return app, window


def main() -> int:
    """SENTRON desktop main entry point."""
    print("================================================================")
    print("  SENTRON — Local Security Guard for AI Actions & System Health ")
    print("  Local-first Windows Desktop MVP • 0 External APIs • Offline   ")
    print("================================================================")
    app, window = create_application()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
