"""Helpers for keeping configured secrets out of diagnostics."""

from collections.abc import Iterable

from pydantic import SecretStr


def redact_secrets(message: str, secrets: Iterable[str | SecretStr | None]) -> str:
    """Replace known non-empty secret values in a diagnostic string."""

    redacted = message
    for secret in secrets:
        value = secret.get_secret_value() if isinstance(secret, SecretStr) else secret
        if value:
            redacted = redacted.replace(value, "[REDACTED]")
    return redacted
