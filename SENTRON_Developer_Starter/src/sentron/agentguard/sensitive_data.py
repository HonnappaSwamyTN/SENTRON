"""Sensitive-Data Detector and Redaction Utilities for AgentGuard (AC-02 - Dev1).

Limitations:
This detector is pattern-based (regular expressions and heuristics).
It cannot detect unknown, novel, proprietary, or custom secret formats, and
provides no guarantee of complete detection. It is designed to catch recognizable
common credentials (such as API keys, Bearer tokens, passwords, and standard PII)
to minimize accidental credential leakage in logs and serialized event records.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


# PROVISIONAL: SecretFinding will move to sentron.core.models once the Integration Owner accepts the RFC.
@dataclass(frozen=True)
class SecretFinding:
    category: str  # e.g. "API_KEY", "PASSWORD", "BEARER_TOKEN", "EMAIL"
    start: int
    end: int
    length: int
    preview: str  # Masked preview only (e.g., "sk-****", "****"), NEVER the raw secret
    details: str


def _create_masked_preview(category: str, secret: str) -> str:
    """Return a safe masked preview of a secret.

    - PASSWORD and EMAIL -> fully masked '****'.
    - API keys -> known public prefix only (e.g. 'sk-****', 'ghp_****', 'AKIA****', 'AIza****'),
      never characters from the secret part.
    - BEARER_TOKEN -> 'Bearer ****' or '****'.
    Never contains any characters from the secret part.
    """
    if category in ("PASSWORD", "EMAIL"):
        return "****"

    if category == "API_KEY":
        for prefix in ("sk-", "ghp_", "AKIA", "AIza"):
            if secret.startswith(prefix):
                return f"{prefix}****"
        return "****"

    if category == "BEARER_TOKEN":
        if secret.lower().startswith("bearer "):
            return "Bearer ****"
        return "****"

    return "****"


@dataclass(frozen=True)
class _SecretRule:
    category: str
    pattern: re.Pattern
    replacement: str
    details: str
    group_idx: int = 0


# Ordered rules: Specific patterns (API keys) MUST run before generic assignments
_SECRET_RULES: tuple[_SecretRule, ...] = (
    # 1. Specific API Keys (OpenAI, GitHub, AWS, Google)
    _SecretRule(
        category="API_KEY",
        pattern=re.compile(r"\bsk-[a-zA-Z0-9_\-]{16,}\b"),
        replacement="[REDACTED_API_KEY]",
        details="OpenAI or compatible LLM API key pattern.",
    ),
    _SecretRule(
        category="API_KEY",
        pattern=re.compile(r"\bghp_[a-zA-Z0-9]{20,}\b"),
        replacement="[REDACTED_API_KEY]",
        details="GitHub Personal Access Token pattern.",
    ),
    _SecretRule(
        category="API_KEY",
        pattern=re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
        replacement="[REDACTED_API_KEY]",
        details="AWS Access Key ID pattern.",
    ),
    _SecretRule(
        category="API_KEY",
        pattern=re.compile(r"\bAIza[0-9A-Za-z\-_]{32,40}\b"),
        replacement="[REDACTED_API_KEY]",
        details="Google API key pattern.",
    ),
    # 2. Bearer Authorization Tokens (explicit header/keyword syntax only)
    _SecretRule(
        category="BEARER_TOKEN",
        pattern=re.compile(r"(?i)\b(bearer\s+)(?!\[REDACTED_)[a-zA-Z0-9_\-\.]{16,}\b"),
        replacement=r"\1[REDACTED_TOKEN]",
        details="HTTP Bearer authorization token header pattern.",
        group_idx=0,
    ),
    _SecretRule(
        category="BEARER_TOKEN",
        pattern=re.compile(
            r"(?i)\b(authorization\s*:\s*(?:bearer\s+)?)(?!\[REDACTED_)[a-zA-Z0-9_\-\.]{16,}\b"
        ),
        replacement=r"\1[REDACTED_TOKEN]",
        details="Authorization header token pattern.",
        group_idx=0,
    ),
    # 3. Password Assignments (JSON and unquoted)
    _SecretRule(
        category="PASSWORD",
        pattern=re.compile(
            r"""(?i)(["'][a-zA-Z0-9_]*(?:password|passwd|pwd)["']\s*:\s*["'])(?!\[REDACTED_)([^"']+)(["'])"""
        ),
        replacement=r"\1[REDACTED_PASSWORD]\3",
        details="Quoted JSON password assignment.",
        group_idx=2,
    ),
    _SecretRule(
        category="PASSWORD",
        pattern=re.compile(
            r"(?i)\b([a-zA-Z0-9_]*(?:password|passwd|pwd))\s*([:=])\s*(?!\[REDACTED_)([^\s,;\"']+)"
        ),
        replacement=r"\1\2[REDACTED_PASSWORD]",
        details="Unquoted key-value password assignment.",
        group_idx=3,
    ),
    # 4. Explicit API Key Key-Value Assignments
    _SecretRule(
        category="API_KEY",
        pattern=re.compile(
            r"""(?i)(["'][a-zA-Z0-9_]*(?:api_key)["']\s*:\s*["'])(?!\[REDACTED_)([^"']+)(["'])"""
        ),
        replacement=r"\1[REDACTED_API_KEY]\3",
        details="Quoted JSON API key field assignment.",
        group_idx=2,
    ),
    _SecretRule(
        category="API_KEY",
        pattern=re.compile(
            r"(?i)\b([a-zA-Z0-9_]*(?:api_key))\s*([:=])\s*(?!\[REDACTED_)([^\s,;\"']+)"
        ),
        replacement=r"\1\2[REDACTED_API_KEY]",
        details="Unquoted key-value API key assignment.",
        group_idx=3,
    ),
    # 5. Personally Identifiable Information (PII) — Scoped strictly to Email
    _SecretRule(
        category="EMAIL",
        pattern=re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
        replacement="[REDACTED_EMAIL]",
        details="Email address pattern.",
        group_idx=0,
    ),
)


_PASSWORD_DICT_KEY = re.compile(r"(?i)^.*(?:password|passwd|pwd).*$")
_API_KEY_DICT_KEY = re.compile(r"(?i)^.*(?:api_key).*$")


def detect_sensitive_data(text: str | None) -> list[SecretFinding]:
    """Scan text for sensitive credentials and confidential patterns.

    Findings NEVER store the cleartext secret. A safe masked preview
    (e.g. 'sk-****', '****') is provided along with character offsets
    and classification category.

    Args:
        text: String to scan for secrets.

    Returns:
        List of SecretFinding objects sorted by character start position.
    """
    if not text or not isinstance(text, str):
        return []

    findings: list[SecretFinding] = []
    claimed_spans: list[tuple[int, int]] = []

    for rule in _SECRET_RULES:
        for match in rule.pattern.finditer(text):
            if rule.group_idx > 0 and rule.group_idx <= len(match.groups()):
                secret_start = match.start(rule.group_idx)
                secret_end = match.end(rule.group_idx)
                secret_raw = match.group(rule.group_idx)
            else:
                secret_start = match.start()
                secret_end = match.end()
                secret_raw = match.group(0)

            # Avoid recording duplicate/overlapping findings on the exact same span
            if any(s <= secret_start and secret_end <= e for s, e in claimed_spans):
                continue

            claimed_spans.append((secret_start, secret_end))
            findings.append(
                SecretFinding(
                    category=rule.category,
                    start=secret_start,
                    end=secret_end,
                    length=secret_end - secret_start,
                    preview=_create_masked_preview(rule.category, secret_raw),
                    details=rule.details,
                )
            )

    findings.sort(key=lambda f: f.start)
    return findings


def redact_text(
    text: str | None,
    redact_emails: bool = False,
) -> tuple[str | None, bool]:
    """Redact recognized secret patterns from text.

    Substitutions replace sensitive substrings with tokens like [REDACTED_API_KEY],
    [REDACTED_TOKEN], [REDACTED_PASSWORD], and [REDACTED_EMAIL].
    EMAIL is detected by detect_sensitive_data() but only redacted when redact_emails=True
    (e.g. to preserve recipient visibility in audit logs).

    Operation is idempotent: redacting already-sanitized text yields identical text
    with was_redacted=False.

    Args:
        text: String to sanitize.
        redact_emails: If True, redacts email addresses; defaults to False.

    Returns:
        (sanitized_text, was_redacted)
    """
    if text is None:
        return None, False

    sanitized = text
    total_redactions = 0

    for rule in _SECRET_RULES:
        if rule.category == "EMAIL" and not redact_emails:
            continue
        new_text, count = rule.pattern.subn(rule.replacement, sanitized)
        if count > 0:
            sanitized = new_text
            total_redactions += count

    return sanitized, (total_redactions > 0)


def redact_payload(
    obj: Any,
    redact_emails: bool = False,
) -> tuple[Any, bool]:
    """Recursively redact secrets from nested structures without mutating the input.

    Traverses dicts, lists, tuples, sets, and strings. Replaces secret patterns
    with [REDACTED_*] tokens. Keys indicating sensitive fields (e.g. 'db_password')
    have their string values automatically sanitized.

    Args:
        obj: Arbitrary Python object (dict, list, tuple, set, str, primitive).
        redact_emails: If True, redacts email addresses; defaults to False.

    Returns:
        (sanitized_obj, was_redacted)
    """
    if obj is None:
        return None, False

    if isinstance(obj, str):
        return redact_text(obj, redact_emails=redact_emails)

    if isinstance(obj, dict):
        new_dict: dict[Any, Any] = {}
        any_redacted = False
        for k, v in obj.items():
            new_k = k
            if isinstance(k, str):
                sanitized_k, k_redacted = redact_text(k, redact_emails=redact_emails)
                if k_redacted:
                    new_k = sanitized_k
                    any_redacted = True

            # If key explicitly indicates a sensitive password/key field and value is a raw string
            if isinstance(k, str) and isinstance(v, str) and not v.startswith("[REDACTED_"):
                v_sanitized, v_redacted = redact_text(v, redact_emails=redact_emails)
                if v_redacted:
                    new_dict[new_k] = v_sanitized
                    any_redacted = True
                elif _PASSWORD_DICT_KEY.match(k):
                    new_dict[new_k] = "[REDACTED_PASSWORD]"
                    any_redacted = True
                elif _API_KEY_DICT_KEY.match(k):
                    new_dict[new_k] = "[REDACTED_API_KEY]"
                    any_redacted = True
                else:
                    new_dict[new_k] = v
            else:
                new_v, v_redacted = redact_payload(v, redact_emails=redact_emails)
                if v_redacted:
                    any_redacted = True
                new_dict[new_k] = new_v

        return new_dict, any_redacted

    if isinstance(obj, list):
        new_list: list[Any] = []
        any_redacted = False
        for item in obj:
            new_item, item_redacted = redact_payload(item, redact_emails=redact_emails)
            if item_redacted:
                any_redacted = True
            new_list.append(new_item)
        return new_list, any_redacted

    if isinstance(obj, tuple):
        new_items: list[Any] = []
        any_redacted = False
        for item in obj:
            new_item, item_redacted = redact_payload(item, redact_emails=redact_emails)
            if item_redacted:
                any_redacted = True
            new_items.append(new_item)
        return tuple(new_items), any_redacted

    if isinstance(obj, set):
        new_set: set[Any] = set()
        any_redacted = False
        for item in obj:
            new_item, item_redacted = redact_payload(item, redact_emails=redact_emails)
            if item_redacted:
                any_redacted = True
            new_set.add(new_item)
        return new_set, any_redacted

    return obj, False


class SensitiveDataDetector:
    """Class wrapper providing sensitive data scanning and redaction for AgentGuard."""

    def detect(self, text: str | None) -> list[SecretFinding]:
        """Detect sensitive credentials in text."""
        return detect_sensitive_data(text)

    def redact(
        self,
        text: str | None,
        redact_emails: bool = False,
    ) -> tuple[str | None, bool]:
        """Redact sensitive credentials from text."""
        return redact_text(text, redact_emails=redact_emails)

    def redact_payload(
        self,
        obj: Any,
        redact_emails: bool = False,
    ) -> tuple[Any, bool]:
        """Recursively redact sensitive data from payload."""
        return redact_payload(obj, redact_emails=redact_emails)
