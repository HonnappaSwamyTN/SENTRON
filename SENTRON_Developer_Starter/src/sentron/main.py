"""SENTRON: Local Security Guard for AI Actions and System Stability.

Desktop Entry Point (Windows PySide6 Application).
Runs offline with zero external cloud AI or external APIs.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication

from sentron.agentguard.approval import ApprovalManager
from sentron.agentguard.audit import SqliteAuditLog
from sentron.agentguard.executor import ControlledExecutor
from sentron.agentguard.policy import PolicyEngine, PolicyRule
from sentron.core.models import ActionRequest, Decision
from sentron.core.paths import get_app_log_path, get_default_db_path, is_frozen, verify_db_accessible
from sentron.core.storage import EventStore
from sentron.crashguard.worker import MonitoringWorker
from sentron.ui.main_window import SentronMainWindow

SINGLETON_PIPE_NAME = "sentron_desktop_singleton"


def _check_and_notify_running_instance() -> bool:
    """Connect to any running instance to bring it forward and prevent duplicates."""
    socket = QLocalSocket()
    socket.connectToServer(SINGLETON_PIPE_NAME)
    if socket.waitForConnected(300):
        command = b"SHOW_DASHBOARD\n" if "--dashboard" in sys.argv else b"SHOW_SHIELD\n"
        socket.write(command)
        socket.waitForBytesWritten(300)
        socket.disconnectFromServer()
        return True
    return False


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


_ACTIVE_WORKER: MonitoringWorker | None = None


def _find_app_icon() -> Path | None:
    """Locate the golden shield application icon in packaged or dev environments."""
    if hasattr(sys, "_MEIPASS"):
        meipass_icon = Path(sys._MEIPASS) / "sentron.ico"
        if meipass_icon.exists():
            return meipass_icon
    internal_icon = Path(sys.executable).parent / "_internal" / "sentron.ico"
    if internal_icon.exists():
        return internal_icon
    exe_icon = Path(sys.executable).parent / "sentron.ico"
    if exe_icon.exists():
        return exe_icon
    repo_icon = Path(__file__).resolve().parent.parent.parent / "packaging" / "assets" / "sentron.ico"
    if repo_icon.exists():
        return repo_icon
    return None


def _setup_packaged_logging() -> None:
    """In frozen/packaged mode, redirect unhandled exceptions to %LOCALAPPDATA%\\SENTRON\\sentron.log."""
    if not is_frozen():
        return
    log_file = get_app_log_path()
    try:
        import logging
        logging.basicConfig(
            filename=str(log_file),
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            encoding="utf-8",
        )
        def _exception_hook(exctype, value, tb):
            import traceback
            logging.error("Unhandled exception:\n%s", "".join(traceback.format_exception(exctype, value, tb)))
            sys.__excepthook__(exctype, value, tb)
        sys.excepthook = _exception_hook
    except Exception:
        pass


def create_application(
    db_path: str | Path | None = None,
    start_worker: bool = True,
) -> tuple[QApplication, SentronMainWindow]:
    """Factory to assemble the application components and UI window."""
    global _ACTIVE_WORKER
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    if db_path is None:
        db_path = get_default_db_path()
    else:
        db_path = Path(db_path)
    verify_db_accessible(db_path)

    # Shared SQLite database and lock for AuditLog and Unified EventStore
    audit_log = SqliteAuditLog(db_path=db_path)
    event_store = EventStore(connection=audit_log._conn, lock=audit_log._lock)

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

    # CrashGuard background worker with unified event store (preventing duplicate workers)
    if _ACTIVE_WORKER is not None and _ACTIVE_WORKER.is_active:
        _ACTIVE_WORKER.stop(timeout=1.0)

    worker = MonitoringWorker(interval_seconds=2.0, buffer_capacity=60, event_store=event_store)
    _ACTIVE_WORKER = worker
    if start_worker:
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
    _setup_packaged_logging()

    print("================================================================")
    print("  SENTRON — Local Security Guard for AI Actions & System Health ")
    print("  Local-first Windows Desktop MVP • 0 External APIs • Offline   ")
    print("================================================================")

    # 1. Prevent duplicate instances where practical
    temp_app = QApplication.instance() or QApplication(sys.argv)
    if _check_and_notify_running_instance():
        print("[SENTRON] Another instance is already running. Brought existing instance to front.")
        return 0

    # 2. Initialize application and singleton IPC server
    app, window = create_application()

    icon_path = _find_app_icon()
    if icon_path:
        from PySide6.QtGui import QIcon
        icon = QIcon(str(icon_path))
        app.setWindowIcon(icon)
        window.setWindowIcon(icon)

    ipc_server = QLocalServer()
    QLocalServer.removeServer(SINGLETON_PIPE_NAME)
    ipc_server.listen(SINGLETON_PIPE_NAME)

    def _on_ipc_connection() -> None:
        client = ipc_server.nextPendingConnection()
        if client:
            def _handle_cmd():
                data = client.readAll().data().decode("utf-8", errors="ignore").strip()
                if "SHOW_DASHBOARD" in data:
                    window.showNormal()
                    window.activateWindow()
                else:
                    window.floating_hub.show()
                    window.floating_hub.raise_()
                    window.floating_hub.activateWindow()
            client.readyRead.connect(_handle_cmd)

    ipc_server.newConnection.connect(_on_ipc_connection)

    def _cleanup_ipc() -> None:
        try:
            ipc_server.close()
            QLocalServer.removeServer(SINGLETON_PIPE_NAME)
        except Exception:
            pass

    app.aboutToQuit.connect(_cleanup_ipc)

    # 3. Startup display behavior:
    # Display the floating shield icon by default; show dashboard only if explicitly requested
    if "--dashboard" in sys.argv or "--full" in sys.argv:
        window.show()
    else:
        window.floating_hub.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
