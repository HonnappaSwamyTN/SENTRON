"""Sensitive-Data Detector and secret redaction for AgentGuard (AC-02).

Detects API keys, tokens, and passwords in action arguments and text.
Ensures sensitive tokens are sanitized before logging or database persistence.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from sentron.agentguard.audit import redact_sensitive_text


@dataclass(frozen=True, slots=True)
class SecretFinding:
    category: str
    matched_snippet: str
    redacted_replacement: str


# Regex rules for detecting specific sensitive secret categories
_DETECTION_PATTERNS: tuple[tuple[str, re.Pattern, str], ...] = (
    ("API_KEY", re.compile(r"\bsk-[a-zA-Z0-9_\-]{16,}\b"), "[REDACTED_API_KEY]"),
    ("TOKEN", re.compile(r"\bghp_[a-zA-Z0-9]{20,}\b"), "[REDACTED_TOKEN]"),
    ("AWS_KEY", re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "[REDACTED_AWS_KEY]"),
    ("TOKEN", re.compile(r"(?i)\b(bearer\s+)[a-zA-Z0-9_\-\.]{16,}\b"), r"\1[REDACTED_TOKEN]"),
    ("PASSWORD", re.compile(r"(?i)\b(password|passwd|secret)\s*([:=])\s*([^\s,;\"']+)"), r"\1\2[REDACTED_SECRET]"),
    ("PASSWORD", re.compile(r"(?i)([\"'](?:password|passwd|secret)[\"']\s*:\s*[\"'])([^\"']+)([\"'])"), r"\1[REDACTED_SECRET]\3"),
)


class SensitiveDataDetector:
    """Detects credentials, keys, and confidential tokens in payloads.

    LIMITATION NOTICE: Regular expressions cannot detect all novel or encrypted
    secret formats. Unrecognized formats require human review.
    """

    def scan(self, text: str | None) -> list[SecretFinding]:
        """Scan text and return findings with categories."""
        if not text:
            return []

        findings: list[SecretFinding] = []
        for category, pattern, replacement in _DETECTION_PATTERNS:
            for match in pattern.finditer(text):
                findings.append(
                    SecretFinding(
                        category=category,
                        matched_snippet=match.group(0),
                        redacted_replacement=replacement,
                    )
                )
        return findings

    def redact(self, text: str | None) -> tuple[str | None, bool]:
        """Sanitize text by masking recognized secrets with [REDACTED_*]."""
        return redact_sensitive_text(text)
