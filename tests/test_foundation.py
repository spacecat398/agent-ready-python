from agent_ready_python.foundation.lifecycle import ResourceScope
from agent_ready_python.foundation.secrets import redact_secrets


def test_secret_redaction() -> None:
    assert redact_secrets("key=secret", ["secret"]) == "key=[REDACTED]"


def test_resource_scope_closes_callbacks() -> None:
    events: list[str] = []

    with ResourceScope() as resources:
        resources.callback(events.append, "closed")

    assert events == ["closed"]
