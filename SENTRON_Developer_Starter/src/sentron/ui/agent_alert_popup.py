"""AgentGuard Dedicated Alert & Approval Notification Popup.

Provides an accessible, theme-consistent on-screen dialog for:
1. Sensitive data access (confidential files, credentials, protected info)
2. Prompt injection detected (suspicious directives or context overrides)
3. Prohibited actions blocked fail-closed under policy (with NO approve button)
4. Approval required (explicit human-in-the-loop gatekeeping)

Non-modal, top-level window (Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
that displays even when the main dashboard is hidden, without stealing focus.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable
from uuid import uuid4

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from sentron.core.models import ActionRequest, Decision, ExecutionResult


@dataclass
class AgentGuardAlert:
    """Structured data model representing an AgentGuard notification or gatekeeper event."""

    alert_type: str  # "approval_required", "prohibited_blocked", "prompt_injection", "sensitive_data"
    decision: Decision  # Decision.ASK, Decision.BLOCK, Decision.ALLOW
    title: str
    agent_id: str
    tool_name: str
    operation: str
    target: str = ""
    destination: str = ""
    reason: str = ""
    reason_code: str = ""
    is_simulated: bool = False
    action_request: ActionRequest | None = None
    execution_result: ExecutionResult | None = None
    risk_flags: tuple[str, ...] = ()
    redaction_summary: str | None = None
    timestamp: float = field(default_factory=time.time)
    alert_id: str = field(default_factory=lambda: str(uuid4()))


class AgentAlertDeduplicator:
    """Safely deduplicates repeated alerts and prevents spam popup loops."""

    def __init__(self, cooldown_seconds: float = 2.5) -> None:
        self.cooldown_seconds = cooldown_seconds
        self._history: dict[str, float] = {}

    def is_duplicate(self, alert: AgentGuardAlert) -> bool:
        now = time.time()
        # Clean up stale entries (>60s)
        self._history = {k: ts for k, ts in self._history.items() if now - ts < 60.0}

        # Check action_id exact match first
        action_id = alert.action_request.action_id if alert.action_request else None
        if action_id:
            key_action = f"action_id:{action_id}"
            last_ts = self._history.get(key_action)
            if last_ts is not None and (now - last_ts) < self.cooldown_seconds:
                return True
            self._history[key_action] = now

        # Fingerprint: agent + operation + target + decision + alert_type
        key_generic = f"{alert.agent_id}:{alert.operation}:{alert.target}:{alert.decision.value}:{alert.alert_type}"
        last_gen_ts = self._history.get(key_generic)
        if last_gen_ts is not None and (now - last_gen_ts) < self.cooldown_seconds:
            return True

        self._history[key_generic] = now
        return False


class AgentGuardAlertPopup(QDialog):
    """Dedicated on-screen security popup for AgentGuard gatekeeper decisions."""

    def __init__(
        self,
        parent: QWidget | None = None,
        on_approve: Callable[[AgentGuardAlert], None] | None = None,
        on_reject: Callable[[AgentGuardAlert], None] | None = None,
        on_view_details: Callable[[AgentGuardAlert], None] | None = None,
        on_dismiss: Callable[[AgentGuardAlert], None] | None = None,
        theme: str = "light",
    ) -> None:
        super().__init__(parent)
        self.on_approve = on_approve
        self.on_reject = on_reject
        self.on_view_details = on_view_details
        self.on_dismiss = on_dismiss
        self.theme = (theme or "light").lower()
        self.current_alert: AgentGuardAlert | None = None

        self.deduplicator = AgentAlertDeduplicator(cooldown_seconds=2.5)

        # Set up non-modal, top-level, non-focus-stealing flags
        self.setWindowFlags(
            Qt.Tool
            | Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setMinimumWidth(480)
        self.setMaximumWidth(540)

        self._init_ui()

    def set_theme(self, theme_name: str) -> None:
        """Update active theme styling."""
        self.theme = (theme_name or "light").lower()
        if self.current_alert:
            self._apply_card_style(
                decision=self.current_alert.decision,
                is_simulated=self.current_alert.is_simulated,
                alert_type=self.current_alert.alert_type,
            )
        if self.isVisible():
            self.update()

    def _init_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Outer card container
        self.card = QFrame()
        self.card.setObjectName("agentAlertCard")

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(16, 14, 16, 14)
        card_layout.setSpacing(10)

        # --- Top Header Bar ---
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)

        self.lbl_title = QLabel("🛡️ AgentGuard — Approval Required")
        self.lbl_title.setObjectName("agentAlertTitle")
        self.lbl_title.setStyleSheet("font-size: 13px; font-weight: 800;")
        header_layout.addWidget(self.lbl_title)

        # Simulated Demo Badge
        self.lbl_sim_badge = QLabel("[SIMULATED / TEST DATA]")
        self.lbl_sim_badge.setObjectName("agentSimBadge")
        self.lbl_sim_badge.setStyleSheet(
            "background-color: #451a03; color: #fbbf24; border: 1px solid #d97706; "
            "font-size: 10px; font-weight: 800; border-radius: 4px; padding: 2px 7px;"
        )
        self.lbl_sim_badge.setVisible(False)
        header_layout.addWidget(self.lbl_sim_badge)

        header_layout.addStretch()

        # Timestamp
        self.lbl_timestamp = QLabel("--:--:--")
        self.lbl_timestamp.setStyleSheet("color: #8b949e; font-size: 11px;")
        header_layout.addWidget(self.lbl_timestamp)

        # Top-right quick close button (dismisses fail-closed)
        self.btn_close_x = QPushButton("✕")
        self.btn_close_x.setObjectName("btnCloseX")
        self.btn_close_x.setToolTip("Dismiss alert (does NOT approve action)")
        self.btn_close_x.setStyleSheet(
            "background: transparent; border: none; font-size: 13px; font-weight: bold; padding: 2px 5px;"
        )
        self.btn_close_x.clicked.connect(self._handle_dismiss)
        header_layout.addWidget(self.btn_close_x)

        card_layout.addLayout(header_layout)

        # --- Structured Summary Block ---
        self.structured_box = QFrame()
        self.structured_box.setObjectName("agentStructuredBox")
        struct_layout = QVBoxLayout(self.structured_box)
        struct_layout.setContentsMargins(10, 8, 10, 8)
        struct_layout.setSpacing(4)

        self.lbl_agent = QLabel("• <b>Agent Identity:</b> Unknown")
        self.lbl_agent.setStyleSheet("font-size: 12px;")
        struct_layout.addWidget(self.lbl_agent)

        self.lbl_action = QLabel("• <b>Requested Action:</b> Unknown")
        self.lbl_action.setStyleSheet("font-size: 12px;")
        struct_layout.addWidget(self.lbl_action)

        self.lbl_target = QLabel("• <b>Target Resource:</b> None")
        self.lbl_target.setStyleSheet("font-size: 12px;")
        struct_layout.addWidget(self.lbl_target)

        self.lbl_decision = QLabel("• <b>Policy Decision:</b> ASK HUMAN")
        self.lbl_decision.setStyleSheet("font-size: 12px;")
        struct_layout.addWidget(self.lbl_decision)

        self.lbl_reason = QLabel("• <b>Alert Reason:</b> Awaiting evaluation.")
        self.lbl_reason.setStyleSheet("font-size: 12px;")
        self.lbl_reason.setWordWrap(True)
        struct_layout.addWidget(self.lbl_reason)

        self.lbl_risk_signals = QLabel("• <b>Risk Signals:</b> None detected")
        self.lbl_risk_signals.setStyleSheet("font-size: 12px; color: #da3633;")
        self.lbl_risk_signals.setWordWrap(True)
        self.lbl_risk_signals.setVisible(False)
        struct_layout.addWidget(self.lbl_risk_signals)

        self.lbl_redaction = QLabel("• <b>Redaction / Boundary:</b> Active")
        self.lbl_redaction.setStyleSheet("font-size: 12px; color: #2ea043;")
        self.lbl_redaction.setWordWrap(True)
        self.lbl_redaction.setVisible(False)
        struct_layout.addWidget(self.lbl_redaction)

        card_layout.addWidget(self.structured_box)

        # --- Simulated Disclaimer Banner ---
        self.lbl_sim_disclaimer = QLabel(
            "⚠️ [SIMULATED / TEST DATA] This event is a simulated test scenario in an isolated test harness. "
            "Approving will NOT grant real host file access or modify actual system permissions."
        )
        self.lbl_sim_disclaimer.setStyleSheet(
            "color: #d29922; font-size: 11px; font-style: italic; background-color: #1c1503; "
            "border-left: 3px solid #d29922; padding: 5px 8px; border-radius: 3px;"
        )
        self.lbl_sim_disclaimer.setWordWrap(True)
        self.lbl_sim_disclaimer.setVisible(False)
        card_layout.addWidget(self.lbl_sim_disclaimer)

        # --- Action Buttons Row ---
        self.actions_layout = QHBoxLayout()
        self.actions_layout.setSpacing(8)

        self.btn_approve = QPushButton("Approve Once")
        self.btn_approve.setObjectName("btnApprove")
        self.btn_approve.setToolTip("Grant single-use scoped approval for this exact action")
        self.btn_approve.setStyleSheet("font-weight: 700; font-size: 11px; padding: 6px 14px;")
        self.btn_approve.clicked.connect(self._handle_approve)
        self.actions_layout.addWidget(self.btn_approve)

        self.btn_reject = QPushButton("Reject")
        self.btn_reject.setObjectName("btnReject")
        self.btn_reject.setToolTip("Halt execution fail-closed and record user rejection")
        self.btn_reject.setStyleSheet("font-weight: 700; font-size: 11px; padding: 6px 14px;")
        self.btn_reject.clicked.connect(self._handle_reject)
        self.actions_layout.addWidget(self.btn_reject)

        self.actions_layout.addStretch()

        self.btn_view_details = QPushButton("View Details")
        self.btn_view_details.setObjectName("btnViewDetails")
        self.btn_view_details.setToolTip("Bring SENTRON dashboard forward and inspect full request audit")
        self.btn_view_details.setStyleSheet("font-weight: 600; font-size: 11px; padding: 6px 12px;")
        self.btn_view_details.clicked.connect(self._handle_view_details)
        self.actions_layout.addWidget(self.btn_view_details)

        self.btn_dismiss = QPushButton("Dismiss")
        self.btn_dismiss.setObjectName("btnDismiss")
        self.btn_dismiss.setToolTip("Dismiss popup notification (does NOT approve action)")
        self.btn_dismiss.setStyleSheet("font-weight: 600; font-size: 11px; padding: 6px 12px;")
        self.btn_dismiss.clicked.connect(self._handle_dismiss)
        self.actions_layout.addWidget(self.btn_dismiss)

        card_layout.addLayout(self.actions_layout)
        root_layout.addWidget(self.card)
        self._apply_card_style(Decision.ASK, is_simulated=False, alert_type="approval_required")

    def _apply_card_style(self, decision: Decision, is_simulated: bool, alert_type: str) -> None:
        is_dark = self.theme == "dark"
        bg_color = "#161b22" if is_dark else "#FFFFFF"
        text_color = "#F5F2E9" if is_dark else "#171717"
        box_bg = "rgba(255, 255, 255, 0.05)" if is_dark else "rgba(0, 0, 0, 0.05)"

        if decision == Decision.BLOCK:
            border_color = "#da3633" if is_dark else "#A51B17"
        elif alert_type == "prompt_injection":
            border_color = "#ea580c" if is_dark else "#C2410C"
        elif decision == Decision.ASK:
            border_color = "#f59e0b" if is_simulated else ("#e3b341" if is_dark else "#8A4500")
        else:
            border_color = "#238636" if is_dark else "#137333"

        self.card.setStyleSheet(
            f"QFrame#agentAlertCard {{"
            f"  background-color: {bg_color};"
            f"  color: {text_color};"
            f"  border: 2px solid {border_color};"
            f"  border-radius: 10px;"
            f"}}"
        )
        if hasattr(self, "structured_box") and self.structured_box:
            self.structured_box.setStyleSheet(
                f"QFrame#agentStructuredBox {{"
                f"  background-color: {box_bg};"
                f"  border-radius: 6px;"
                f"}}"
            )

    def should_suppress(self, alert: AgentGuardAlert) -> bool:
        """Return True if this alert is a rapid duplicate that should be suppressed."""
        return self.deduplicator.is_duplicate(alert)

    def is_simulated(self) -> bool:
        """Return True if the active popup displays a simulated scenario."""
        return self.current_alert.is_simulated if self.current_alert else False

    def display_alert(self, alert: AgentGuardAlert) -> None:
        """Populate content, adjust layout, position at top-right, and display without focus-stealing."""
        self.current_alert = alert

        # Title
        self.lbl_title.setText(alert.title)

        # Simulation badge & disclaimer
        self.lbl_sim_badge.setVisible(alert.is_simulated)
        self.lbl_sim_disclaimer.setVisible(alert.is_simulated)

        # Timestamp
        time_str = datetime.fromtimestamp(alert.timestamp).strftime("%H:%M:%S")
        self.lbl_timestamp.setText(time_str)

        # Agent Identity
        self.lbl_agent.setText(f"• <b>Agent Identity:</b> {alert.agent_id or 'Unknown'}")

        # Requested Action
        action_desc = f"{alert.operation} (Tool: <i>{alert.tool_name}</i>)" if alert.tool_name else alert.operation
        self.lbl_action.setText(f"• <b>Requested Action:</b> {action_desc}")

        # Target Resource / Destination
        target_str = alert.target or alert.destination or "None specified"
        self.lbl_target.setText(f"• <b>Target Resource:</b> {target_str}")

        # Policy Decision text & color badge
        if alert.decision == Decision.ASK:
            dec_badge = "<span style='color: #d97706; font-weight: 800;'>[⏳ ASK HUMAN]</span>"
            dec_text = f"{dec_badge} Explicit operator approval required before execution."
        elif alert.decision == Decision.BLOCK:
            dec_badge = "<span style='color: #da3633; font-weight: 800;'>[✕ BLOCK]</span>"
            dec_text = f"{dec_badge} Prohibited by safety policy. Action terminated fail-closed."
        else:
            dec_badge = "<span style='color: #238636; font-weight: 800;'>[✓ ALLOW]</span>"
            dec_text = f"{dec_badge} Authorized under policy rules."
        self.lbl_decision.setText(f"• <b>Policy Decision:</b> {dec_text}")

        # Reason
        reason_txt = alert.reason or "Evaluation completed."
        self.lbl_reason.setText(f"• <b>Alert Reason:</b> {reason_txt}")

        # Risk signals
        if alert.risk_flags:
            flags_str = ", ".join(alert.risk_flags)
            self.lbl_risk_signals.setText(f"• <b>Risk Signals:</b> {flags_str}")
            self.lbl_risk_signals.setVisible(True)
        else:
            self.lbl_risk_signals.setVisible(False)

        # Redaction summary
        if alert.redaction_summary:
            self.lbl_redaction.setText(f"• <b>Redaction / Boundary:</b> {alert.redaction_summary}")
            self.lbl_redaction.setVisible(True)
        else:
            self.lbl_redaction.setVisible(False)

        # Enforce button availability rules:
        # 1. Prohibited (BLOCK) actions must NEVER show an Approve button
        # 2. Prompt injection warning popups are advisory security alerts (no approve)
        # 3. Only approval-required (ASK) non-injection actions show Approve Once & Reject
        if alert.decision == Decision.ASK and alert.alert_type != "prompt_injection":
            self.btn_approve.setVisible(True)
            self.btn_reject.setVisible(True)
        else:
            # Blocked actions or security warnings
            self.btn_approve.setVisible(False)
            self.btn_reject.setVisible(False)

        # Style card according to decision and theme
        self._apply_card_style(alert.decision, alert.is_simulated, alert.alert_type)

        self.reposition()
        self.show()
        self.raise_()

    def reposition(self) -> None:
        """Position at the top-right corner of the primary screen or dashboard parent."""
        self.adjustSize()
        margin = 24
        parent_widget = self.parentWidget()

        if parent_widget and parent_widget.isVisible() and not parent_widget.isMinimized():
            parent_geo = parent_widget.geometry()
            x = parent_geo.x() + parent_geo.width() - self.width() - margin
            y = parent_geo.y() + 70
        else:
            screen = QApplication.primaryScreen()
            if screen:
                screen_geo = screen.availableGeometry()
                x = screen_geo.x() + screen_geo.width() - self.width() - margin
                y = screen_geo.y() + 70
            else:
                x = 100
                y = 70

        self.move(max(0, x), max(0, y))

    def _handle_approve(self) -> None:
        """Handle Approve Once button click."""
        if not self.current_alert:
            return
        # Strict security constraint: Prohibited actions blocked by policy must NEVER be approved
        if self.current_alert.decision == Decision.BLOCK:
            return

        self.close()
        if self.on_approve:
            try:
                self.on_approve(self.current_alert)
            except Exception:
                pass

    def _handle_reject(self) -> None:
        """Handle Reject button click."""
        if not self.current_alert:
            return
        self.close()
        if self.on_reject:
            try:
                self.on_reject(self.current_alert)
            except Exception:
                pass

    def _handle_view_details(self) -> None:
        """Handle View Details button click."""
        self.close()
        if self.on_view_details and self.current_alert:
            try:
                self.on_view_details(self.current_alert)
            except Exception:
                pass

    def _handle_dismiss(self) -> None:
        """Dismiss popup without silently approving or resuming pending execution (fail closed)."""
        self.close()
        if self.on_dismiss and self.current_alert:
            try:
                self.on_dismiss(self.current_alert)
            except Exception:
                pass
