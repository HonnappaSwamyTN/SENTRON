"""Suspicious-Input Analyzer for AgentGuard (AC-01).

Uses deterministic rule-based pattern matching to identify prompt injection,
system prompt overrides, jailbreak attempts, and agent manipulation.
Emits structured RiskSignal objects for policy review.
Never independently authorizes or executes actions.
"""
from __future__ import annotations

import re
from sentron.core.models import RiskSignal


# Deterministic pattern rules for suspicious input scanning
_INJECTION_RULES: tuple[tuple[str, str, str, re.Pattern], ...] = (
    (
        "PROMPT_INJECTION_OVERRIDE",
        "high",
        "Attempt to override prior system prompt or developer directives.",
        re.compile(r"(?i)\b(ignore|disregard|forget|bypass)\s+(all\s+)?(previous|prior|above)\s+(instructions|directives|rules|prompts?)\b"),
    ),
    (
        "PROMPT_INJECTION_OVERRIDE",
        "high",
        "Attempt to inject new system-level directive.",
        re.compile(r"(?i)\b(new\s+system\s+(directive|instruction|rule)|system\s+prompt\s+override|reset\s+all\s+directives)\b"),
    ),
    (
        "JAILBREAK_ROLEPLAY",
        "high",
        "Known jailbreak persona or unconstrained roleplay exploit signature.",
        re.compile(r"(?i)\b(dan\s+mode|developer\s+mode\s+override|unrestricted\s+mode|jailbreak|do\s+anything\s+now)\b"),
    ),
    (
        "DELIMITER_BREAKOUT",
        "medium",
        "Artificial delimiter or boundary breakout attempt.",
        re.compile(r"(?i)(<\/?system>|<\/?instruction>|\[SYSTEM\]|\[INST\]|```\s*system)"),
    ),
    (
        "EXFILTRATION_INSTRUCTION",
        "critical",
        "Directive to exfiltrate or secretly transmit internal data.",
        re.compile(r"(?i)\b(send|upload|post|exfiltrate|transmit)\s+(secrets?|credentials?|passwords?|keys?|tokens?)\s+(to\s+http|to\s+https|externally)\b"),
    ),
)


class SuspiciousInputAnalyzer:
    """Deterministic analyzer scanning untrusted text for manipulation signals.

    NOTE: Pattern-based matching provides early indicators/signals and cannot
    guarantee detection of all novel or obfuscated prompt injection attacks.
    Findings are advisory signals for the Policy Engine and never independently
    authorize or execute any operation.
    """

    def __init__(self) -> None:
        pass

    def scan(self, text: str | None) -> list[RiskSignal]:
        """Scan untrusted text and return all matched RiskSignal items."""
        if not text or not text.strip():
            return []

        signals: list[RiskSignal] = []
        for finding_type, risk_level, details, pattern in _INJECTION_RULES:
            match = pattern.search(text)
            if match:
                evidence = match.group(0)
                signals.append(
                    RiskSignal(
                        finding_type=finding_type,
                        evidence_snippet=evidence,
                        risk_level=risk_level,
                        details=details,
                    )
                )

        return signals
