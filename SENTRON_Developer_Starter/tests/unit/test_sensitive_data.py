"""Unit tests for Sensitive-Data Detector (AgentGuard A - Dev1).

Governing Criteria: AC-02
"""
from __future__ import annotations

import json
from copy import deepcopy

import pytest

from sentron.agentguard.sensitive_data import (
    SecretFinding,
    SensitiveDataDetector,
    detect_sensitive_data,
    redact_payload,
    redact_text,
)


@pytest.mark.unit
def test_recognizable_secret_is_detected_and_redacted():
    """AC-02: A recognizable test secret is detected and redacted from payload.

    Verifies that:
    - Payload with 'sk-abcdef1234567890abcdef123456789012345678' and database password
      produces findings with categories API_KEY and PASSWORD.
    - json.dumps(redacted_payload) contains [REDACTED_API_KEY] and [REDACTED_PASSWORD].
    - Cleartext secrets are never present in the serialized output.
    """
    raw_api_key = "sk-abcdef1234567890abcdef123456789012345678"
    raw_password = "synthetic_db_password_987654321"

    payload = {
        "operation": "connect_database",
        "target": "db.internal.local",
        "api_key": raw_api_key,
        "db_password": raw_password,
        "query": f"SELECT * FROM users WHERE auth = '{raw_api_key}';",
    }

    # Verify detection on serialized/string text
    serialized_raw = json.dumps(payload)
    findings = detect_sensitive_data(serialized_raw)
    categories = {f.category for f in findings}

    assert "API_KEY" in categories
    assert "PASSWORD" in categories

    # Verify redaction on structured payload
    redacted_data, was_redacted = redact_payload(payload)
    assert was_redacted is True

    serialized_redacted = json.dumps(redacted_data)

    assert "[REDACTED_API_KEY]" in serialized_redacted
    assert "[REDACTED_PASSWORD]" in serialized_redacted
    assert raw_api_key not in serialized_redacted
    assert raw_password not in serialized_redacted


@pytest.mark.unit
def test_recognizable_secret_in_string_detected_and_redacted():
    """AC-02: String with Bearer token, API key, and password is detected and redacted via detector.scan/redact."""
    detector = SensitiveDataDetector()
    payload = "Bearer sk-1234567890abcdef1234567890abcdef with password=SuperSecretPassword123"

    findings = detector.scan(payload)
    categories = [f.category for f in findings]
    assert "API_KEY" in categories or "BEARER_TOKEN" in categories
    assert "PASSWORD" in categories

    redacted_text, was_redacted = detector.redact(payload)
    assert was_redacted is True
    assert "sk-1234567890abcdef1234567890abcdef" not in redacted_text
    assert "SuperSecretPassword123" not in redacted_text
    assert "[REDACTED_" in redacted_text


@pytest.mark.unit
def test_findings_never_contain_raw_secrets():
    """Verify SecretFinding previews contain only known prefixes or '****' and never secret characters."""
    raw_sk = "sk-dummysecretkey12345678901234567890"
    raw_ghp = "ghp_0123456789abcdefghij0123456789abcdef"
    raw_akia = "AKIAIOSFODNN7EXAMPLE"
    raw_aiza = "AIzaSyD-1234567890123456789012345678901"
    raw_password = "dummy_password_secret_998877"
    raw_email = "security-admin@example.com"
    raw_bearer = "Bearer sample_bearer_token_1234567890"

    text = (
        f"sk={raw_sk} ghp={raw_ghp} akia={raw_akia} aiza={raw_aiza} "
        f"password={raw_password} email={raw_email} auth={raw_bearer}"
    )
    findings = detect_sensitive_data(text)

    # Map category/preview
    api_key_findings = [f for f in findings if f.category == "API_KEY"]
    previews = {f.preview for f in api_key_findings}
    assert "sk-****" in previews
    assert "ghp_****" in previews
    assert "AKIA****" in previews
    assert "AIza****" in previews

    # Bearer token must show 'Bearer ****'
    bearer_finding = next(f for f in findings if f.category == "BEARER_TOKEN")
    assert bearer_finding.preview == "Bearer ****"

    # Verify no finding preview contains characters from the secret part
    for f in findings:
        assert isinstance(f, SecretFinding)
        for secret in (raw_sk[3:], raw_ghp[4:], raw_akia[4:], raw_aiza[4:], raw_password, raw_email):
            assert secret not in f.preview
            assert secret not in f.details


@pytest.mark.unit
def test_email_detection_and_conditional_redaction():
    """Verify EMAIL is detected, but only redacted when redact_emails=True."""
    sample_text = "Send notification to dev-lead@example.com for verification."

    # 1. detect_sensitive_data finds EMAIL
    findings = detect_sensitive_data(sample_text)
    assert any(f.category == "EMAIL" for f in findings)

    # 2. redact_text with default redact_emails=False leaves email intact
    sanitized_default, was_redacted_default = redact_text(sample_text)
    assert sanitized_default == sample_text
    assert was_redacted_default is False

    # 3. redact_text with redact_emails=True replaces email
    sanitized_redacted, was_redacted_true = redact_text(sample_text, redact_emails=True)
    assert "[REDACTED_EMAIL]" in sanitized_redacted
    assert "dev-lead@example.com" not in sanitized_redacted
    assert was_redacted_true is True

    # 4. redact_payload respects redact_emails flag
    payload = {"recipient": "dev-lead@example.com", "action": "send_email"}
    p_default, p_was_red_default = redact_payload(payload, redact_emails=False)
    assert p_default["recipient"] == "dev-lead@example.com"
    assert p_was_red_default is False

    p_redacted, p_was_red_true = redact_payload(payload, redact_emails=True)
    assert p_redacted["recipient"] == "[REDACTED_EMAIL]"
    assert p_was_red_true is True


@pytest.mark.unit
def test_uuid_and_sha256_hash_are_not_redacted():
    """Verify non-credential strings like UUIDs and SHA-256 hashes are NOT detected or redacted."""
    uuid_str = "c3b9d05e-4498-4e0d-8fc0-c652fa6c062a"
    sha256_str = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

    text = f"Action ID: {uuid_str}, Content hash: {sha256_str}"

    findings = detect_sensitive_data(text)
    assert findings == []

    sanitized, was_redacted = redact_text(text)
    assert sanitized == text
    assert was_redacted is False

    payload = {"action_id": uuid_str, "file_hash": sha256_str}
    red_payload, p_was_red = redact_payload(payload)
    assert red_payload == payload
    assert p_was_red is False


@pytest.mark.unit
def test_bearer_token_only_matches_explicit_headers():
    """Verify BEARER_TOKEN requires 'Bearer <token>' or 'Authorization:' syntax."""
    # Explicit Bearer headers match
    bearer_text = "Bearer synthetic_oauth_token_1234567890"
    auth_header = "Authorization: Bearer synthetic_oauth_token_1234567890"

    assert len(detect_sensitive_data(bearer_text)) >= 1
    assert len(detect_sensitive_data(auth_header)) >= 1

    sanitized_bearer, r1 = redact_text(bearer_text)
    assert r1 is True
    assert sanitized_bearer == "Bearer [REDACTED_TOKEN]"

    sanitized_auth, r2 = redact_text(auth_header)
    assert r2 is True
    assert sanitized_auth == "Authorization: Bearer [REDACTED_TOKEN]"

    # Arbitrary long strings without header syntax are NOT treated as Bearer tokens
    arbitrary_token = "abcdefghijklmnopqrstuvwxyz0123456789"
    assert detect_sensitive_data(arbitrary_token) == []
    assert redact_text(arbitrary_token) == (arbitrary_token, False)


@pytest.mark.unit
def test_password_assignments_preserve_key_name():
    """Verify that password assignments keep the key name intact."""
    samples = (
        ("password=secret123", "password=[REDACTED_PASSWORD]"),
        ("passwd: secret456", "passwd:[REDACTED_PASSWORD]"),
        ("db_password=superpass", "db_password=[REDACTED_PASSWORD]"),
        ('{"db_password": "pass"}', '{"db_password": "[REDACTED_PASSWORD]"}'),
    )
    for raw, expected in samples:
        sanitized, was_redacted = redact_text(raw)
        assert was_redacted is True
        assert sanitized == expected


@pytest.mark.unit
def test_benign_text_unchanged():
    """Verify benign text without credentials is unchanged and was_redacted is False."""
    benign = "System CPU utilization is 42% and free memory is 8192 MB."
    findings = detect_sensitive_data(benign)
    assert findings == []

    sanitized, was_redacted = redact_text(benign)
    assert sanitized == benign
    assert was_redacted is False


@pytest.mark.unit
def test_none_and_empty_inputs():
    """Verify safe handling of None, empty strings, and empty structures."""
    assert detect_sensitive_data(None) == []
    assert detect_sensitive_data("") == []
    assert detect_sensitive_data("    ") == []

    assert redact_text(None) == (None, False)
    assert redact_text("") == ("", False)

    assert redact_payload(None) == (None, False)
    assert redact_payload({}) == ({}, False)
    assert redact_payload([]) == ([], False)


@pytest.mark.unit
def test_idempotency_of_redaction():
    """Verify redacting already-sanitized text or payloads yields the same output with was_redacted=False."""
    raw_text = (
        "api_key=sk-abcdef1234567890abcdef123456789012345678 "
        "password=secret_db_pass Bearer auth_token_abcdef123456"
    )

    t1, r1 = redact_text(raw_text)
    assert r1 is True

    t2, r2 = redact_text(t1)
    assert t2 == t1
    assert r2 is False

    payload = {
        "api_key": "sk-abcdef1234567890abcdef123456789012345678",
        "db_password": "secret_db_pass",
        "nested": ["Bearer auth_token_abcdef123456"],
    }

    p1, pr1 = redact_payload(payload)
    assert pr1 is True

    p2, pr2 = redact_payload(p1)
    assert p2 == p1
    assert pr2 is False


@pytest.mark.unit
def test_nested_payload_redaction_and_immutability():
    """Verify deep traversal of dicts, lists, tuples, sets without mutating input."""
    raw_key = "sk-synthetic-key-12345678901234567890"
    raw_pw = "secret_db_pass_123"

    original = {
        "config": {
            "auth": {
                "api_key": raw_key,
                "password": raw_pw,
            },
            "tokens": ["Bearer synthetic_oauth_bearer_token_12345", "harmless_string"],
            "options": ("plain_option", f"password={raw_pw}"),
            "whitelist": {"test@example.com"},
        },
        "count": 42,
        "active": True,
    }

    snapshot = deepcopy(original)
    sanitized, was_redacted = redact_payload(original, redact_emails=True)

    assert was_redacted is True
    # Ensure input was NOT mutated in place
    assert original == snapshot

    # Verify nested items are redacted
    assert sanitized["config"]["auth"]["api_key"] == "[REDACTED_API_KEY]"
    assert sanitized["config"]["auth"]["password"] == "[REDACTED_PASSWORD]"
    assert sanitized["config"]["tokens"][0] == "Bearer [REDACTED_TOKEN]"
    assert sanitized["config"]["options"][1] == "password=[REDACTED_PASSWORD]"
    assert sanitized["config"]["whitelist"] == {"[REDACTED_EMAIL]"}
    assert sanitized["count"] == 42
    assert sanitized["active"] is True


@pytest.mark.unit
def test_detector_class_wrapper():
    """Verify SensitiveDataDetector class wrapper methods."""
    detector = SensitiveDataDetector()
    raw = "Connect with api_key=sk-abcdef1234567890abcdef123456789012345678"

    findings = detector.detect(raw)
    assert len(findings) >= 1
    assert findings[0].category == "API_KEY"

    # scan compatibility
    scan_findings = detector.scan(raw)
    assert len(scan_findings) >= 1
    assert scan_findings[0].category == "API_KEY"

    sanitized, was_redacted = detector.redact(raw)
    assert was_redacted is True
    assert "[REDACTED_API_KEY]" in sanitized

    payload = {"key": "sk-abcdef1234567890abcdef123456789012345678"}
    red_payload, p_red = detector.redact_payload(payload)
    assert p_red is True
    assert red_payload["key"] == "[REDACTED_API_KEY]"
