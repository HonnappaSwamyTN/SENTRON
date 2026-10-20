"""Suspicious-Input Analyzer for AgentGuard (AC-01 - Dev1).

Deterministic, rule-based detection for prompt injections, system instruction
overrides, jailbreaks, delimiter/context breakout attempts, and data exfiltration.
Produces structured RiskSignal findings with evidence snippets and risk levels.
Advisory signals for policy review; never independently authorizes or executes actions.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from sentron.core.models import RiskSignal

_RISK_LEVEL_ORDER: dict[str, int] = {
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}

_MAX_EVIDENCE_LENGTH = 80


@dataclass(frozen=True)
class _RiskRule:
    finding_type: str
    pattern: re.Pattern
    risk_level: str
    details: str


# Deterministic detection rules for prompt injection and input manipulation
_RISK_RULES: tuple[_RiskRule, ...] = (
    # 1. System Prompt & Instruction Overrides (AC-01)
    _RiskRule(
        finding_type="PROMPT_INJECTION_OVERRIDE",
        pattern=re.compile(
            r"\bignore\s+(?:all\s+)?(?:previous|prior|above)\s+instructions\b",
            re.IGNORECASE,
        ),
        risk_level="critical",
        details="Attempt to override or ignore prior system instructions.",
    ),
    _RiskRule(
        finding_type="PROMPT_INJECTION_OVERRIDE",
        pattern=re.compile(
            r"\bdisregard\s+(?:all\s+)?(?:previous|prior|above|safety)\s+(?:instructions|rules|directives|prompts)\b",
            re.IGNORECASE,
        ),
        risk_level="critical",
        details="Attempt to disregard previous instructions, directives, or safety rules.",
    ),
    _RiskRule(
        finding_type="PROMPT_INJECTION_OVERRIDE",
        pattern=re.compile(
            r"\bforget\s+(?:all\s+)?(?:previous|prior|above)\s+(?:instructions|rules|context)\b",
            re.IGNORECASE,
        ),
        risk_level="critical",
        details="Attempt to erase or forget previous instructions or context.",
    ),
    _RiskRule(
        finding_type="PROMPT_INJECTION_OVERRIDE",
        pattern=re.compile(
            r"\boverride\s+(?:system|safety)\s+(?:prompt|rules|instructions|directives)\b",
            re.IGNORECASE,
        ),
        risk_level="critical",
        details="Explicit directive to override system or safety instructions.",
    ),
    _RiskRule(
        finding_type="PROMPT_INJECTION_OVERRIDE",
        pattern=re.compile(
            r"\bbypass\s+(?:safety|system|guardrail)\s+(?:rules|filters|instructions|policies)\b",
            re.IGNORECASE,
        ),
        risk_level="critical",
        details="Attempt to bypass system security rules, guardrails, or filters.",
    ),
    _RiskRule(
        finding_type="PROMPT_INJECTION_OVERRIDE",
        pattern=re.compile(
            r"\bnew\s+system\s+directive\b",
            re.IGNORECASE,
        ),
        risk_level="high",
        details="Attempt to inject an unverified new system directive.",
    ),
    _RiskRule(
        finding_type="PROMPT_INJECTION_OVERRIDE",
        pattern=re.compile(
            r"\breset\s+(?:all\s+)?(?:system\s+)?(?:instructions|directives)\b",
            re.IGNORECASE,
        ),
        risk_level="high",
        details="Attempt to reset system instructions or directives.",
    ),
    # 2. Jailbreak Signatures & Role-play Exploits
    _RiskRule(
        finding_type="JAILBREAK_ATTEMPT",
        pattern=re.compile(
            r"\bDAN\s+mode\b",
            re.IGNORECASE,
        ),
        risk_level="critical",
        details="Detected classic 'Do Anything Now' (DAN) jailbreak signature.",
    ),
    _RiskRule(
        finding_type="JAILBREAK_ATTEMPT",
        pattern=re.compile(
            r"\bdo\s+anything\s+now\b",
            re.IGNORECASE,
        ),
        risk_level="critical",
        details="Detected 'do anything now' jailbreak phrasing.",
    ),
    _RiskRule(
        finding_type="JAILBREAK_ATTEMPT",
        pattern=re.compile(
            r"\bdeveloper\s+mode\s+(?:override|enabled|activated|on)\b",
            re.IGNORECASE,
        ),
        risk_level="high",
        details="Detected developer mode override exploit phrasing.",
    ),
    _RiskRule(
        finding_type="JAILBREAK_ATTEMPT",
        pattern=re.compile(
            r"\b(?:switch\s+to|enable)\s+(?:unrestricted|unfiltered)\s+mode\b",
            re.IGNORECASE,
        ),
        risk_level="high",
        details="Attempt to switch agent into unrestricted or unfiltered mode.",
    ),
    _RiskRule(
        finding_type="JAILBREAK_ATTEMPT",
        pattern=re.compile(
            r"\bpretend\s+you\s+have\s+no\s+(?:rules|restrictions|limits|guidelines)\b",
            re.IGNORECASE,
        ),
        risk_level="high",
        details="Role-play exploit instructing agent to ignore rules and restrictions.",
    ),
    _RiskRule(
        finding_type="JAILBREAK_ATTEMPT",
        pattern=re.compile(
            r"\bjailbreak(?:ed)?\b",
            re.IGNORECASE,
        ),
        risk_level="high",
        details="Explicit mention of jailbreak in command context.",
    ),
    # 3. Delimiter & Context Breakout Attempts
    _RiskRule(
        finding_type="CONTEXT_DELIMITER_BREAKOUT",
        pattern=re.compile(
            r"</?system>|\[/?system\]",
            re.IGNORECASE,
        ),
        risk_level="high",
        details="Artificial system delimiter tag injection.",
    ),
    _RiskRule(
        finding_type="CONTEXT_DELIMITER_BREAKOUT",
        pattern=re.compile(
            r"<<SYS>>|<</SYS>>",
            re.IGNORECASE,
        ),
        risk_level="high",
        details="Artificial system delimiter token injection (<<SYS>>).",
    ),
    _RiskRule(
        finding_type="CONTEXT_DELIMITER_BREAKOUT",
        pattern=re.compile(
            r"<\|im_start\|>|<\|im_end\|>",
            re.IGNORECASE,
        ),
        risk_level="high",
        details="Artificial ChatML boundary token injection.",
    ),
    _RiskRule(
        finding_type="CONTEXT_DELIMITER_BREAKOUT",
        pattern=re.compile(
            r"\[/?INST\]",
            re.IGNORECASE,
        ),
        risk_level="high",
        details="Artificial instruction boundary tag injection ([INST]).",
    ),
    _RiskRule(
        finding_type="CONTEXT_DELIMITER_BREAKOUT",
        pattern=re.compile(
            r"""["']role["']\s*:\s*["']system["']""",
            re.IGNORECASE,
        ),
        risk_level="medium",
        details="Simulated JSON system role dictionary injection.",
    ),
    # 4. Data Exfiltration Instructions (preserved from main)
    _RiskRule(
        finding_type="EXFILTRATION_INSTRUCTION",
        pattern=re.compile(
            r"\b(?:send|upload|post|exfiltrate|transmit)\s+(?:secrets?|credentials?|passwords?|keys?|tokens?)\s+(?:to\s+http|to\s+https|externally)\b",
            re.IGNORECASE,
        ),
        risk_level="critical",
        details="Directive to exfiltrate or secretly transmit internal data.",
    ),
)


def analyze_input_risk(text: str | None) -> list[RiskSignal]:
    """Analyze input text for prompt injections, jailbreaks, and delimiter breakouts.

    This function is strictly deterministic, non-authorizing, and read-only.
    It produces findings with evidence snippets truncated to at most 80 characters.

    Args:
        text: Untrusted string to inspect.

    Returns:
        List of RiskSignal objects representing detected suspicious patterns.
    """
    if not text or not isinstance(text, str):
        return []

    signals: list[RiskSignal] = []
    for rule in _RISK_RULES:
        for match in rule.pattern.finditer(text):
            matched_raw = match.group(0)
            evidence = matched_raw[:_MAX_EVIDENCE_LENGTH]
            signals.append(
                RiskSignal(
                    finding_type=rule.finding_type,
                    evidence_snippet=evidence,
                    risk_level=rule.risk_level,
                    details=rule.details,
                )
            )

    return signals


def to_risk_flags(
    signals: Iterable[RiskSignal],
    min_level: str = "medium",
) -> tuple[str, ...]:
    """Convert RiskSignals to deduplicated finding_type flag strings.

    Filters signals to include only those at or above min_level.
    Uses finding_type as the flag string, deduplicating while preserving stable order.

    Args:
        signals: Iterable of RiskSignal objects.
        min_level: Minimum risk level required to include a flag ('low', 'medium', 'high', 'critical').

    Returns:
        tuple of unique finding_type strings for consumption by PolicyEngine.
    """
    level_key = min_level.strip().lower()
    if level_key not in _RISK_LEVEL_ORDER:
        raise ValueError(
            f"Invalid min_level '{min_level}'; must be one of {tuple(_RISK_LEVEL_ORDER.keys())}"
        )

    min_rank = _RISK_LEVEL_ORDER[level_key]
    flags: list[str] = []
    seen: set[str] = set()

    for signal in signals:
        signal_rank = _RISK_LEVEL_ORDER.get(signal.risk_level.lower(), 0)
        if signal_rank >= min_rank and signal.finding_type not in seen:
            seen.add(signal.finding_type)
            flags.append(signal.finding_type)

    return tuple(flags)


class SuspiciousInputAnalyzer:
    """Deterministic analyzer class wrapping input risk analysis for AgentGuard."""

    def analyze(self, text: str | None) -> list[RiskSignal]:
        """Analyze text and return RiskSignal findings."""
        return analyze_input_risk(text)

    def scan(self, text: str | None) -> list[RiskSignal]:
        """Scan untrusted text and return all matched RiskSignal items (compatibility alias)."""
        return analyze_input_risk(text)

    def extract_flags(
        self,
        text: str | None,
        min_level: str = "medium",
    ) -> tuple[str, ...]:
        """Analyze text and return deduplicated risk flags at or above min_level."""
        signals = self.analyze(text)
        return to_risk_flags(signals, min_level=min_level)


__all__ = [
    "RiskSignal",
    "SuspiciousInputAnalyzer",
    "analyze_input_risk",
    "to_risk_flags",
]
