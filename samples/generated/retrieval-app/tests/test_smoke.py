from typer.testing import CliRunner

from retrieval_app.interfaces.cli.app import app

runner = CliRunner()


def test_version() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert result.stdout.strip() == "0.1.0"


def test_check() -> None:
    result = runner.invoke(app, ["check"])
    assert result.exit_code == 0
    assert "Python: OK" in result.stdout


def test_local_search(tmp_path) -> None:
    document = tmp_path / "notes.txt"
    document.write_text("offline needle content", encoding="utf-8")
    result = runner.invoke(app, ["search", str(document), "needle"])
    assert result.exit_code == 0
    assert "needle" in result.stdout
