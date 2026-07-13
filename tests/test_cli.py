from pathlib import Path

from typer.testing import CliRunner

from agent_ready_python.interfaces.cli.app import app
from agent_ready_python.interfaces.cli.core import create_core_cli

runner = CliRunner()


def test_version() -> None:
    result = runner.invoke(app, ["version"])

    assert result.exit_code == 0
    assert result.stdout.strip() == "0.1.0"


def test_core_check_works_without_optional_command_registration() -> None:
    result = runner.invoke(create_core_cli(), ["check"])

    assert result.exit_code == 0
    assert "Python: OK" in result.stdout


def test_fake_ask_requires_no_key_or_network() -> None:
    result = runner.invoke(app, ["ask", "hello"])

    assert result.exit_code == 0
    assert result.stdout.strip() == "Fake provider response"


def test_remote_ask_without_key_has_stable_exit_code() -> None:
    result = runner.invoke(
        app,
        ["ask", "hello"],
        env={"AI_LLM_PROVIDER": "openai_compatible"},
    )

    assert result.exit_code == 2
    assert "AI_LLM_API_KEY" in result.stderr
    assert "Traceback" not in result.stderr


def test_llm_check_does_not_contact_provider() -> None:
    result = runner.invoke(
        app,
        ["llm-check"],
        env={"AI_LLM_PROVIDER": "openai_compatible"},
    )

    assert result.exit_code == 0
    assert "API key: missing" in result.stdout


def test_retrieval_check_defaults_to_local_keyword_mode() -> None:
    result = runner.invoke(app, ["retrieval-check"])

    assert result.exit_code == 0
    assert "Retrieval mode: keyword" in result.stdout


def test_search_uses_local_keyword_retrieval(tmp_path: Path) -> None:
    document = tmp_path / "notes.txt"
    document.write_text(
        "Python modules are reusable. RAG retrieves relevant documents.",
        encoding="utf-8",
    )

    result = runner.invoke(app, ["search", str(document), "RAG documents"])

    assert result.exit_code == 0
    assert "RAG retrieves relevant documents" in result.stdout


def test_search_does_not_enable_remote_embeddings_from_key_alone(tmp_path: Path) -> None:
    document = tmp_path / "private.txt"
    document.write_text("private searchable content", encoding="utf-8")

    result = runner.invoke(
        app,
        ["search", str(document), "searchable"],
        env={"AI_EMBEDDING_API_KEY": "host-key"},
    )

    assert result.exit_code == 0
    assert "private searchable content" in result.stdout


def test_pipeline_check_uses_in_memory_store() -> None:
    result = runner.invoke(app, ["pipeline-check"])

    assert result.exit_code == 0
    assert "Artifact store: OK" in result.stdout
    assert "Automatic activation: disabled" in result.stdout
