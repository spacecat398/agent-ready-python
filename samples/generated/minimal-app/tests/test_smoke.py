from typer.testing import CliRunner

from minimal_app.interfaces.cli.app import app

runner = CliRunner()


def test_version() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert result.stdout.strip() == "0.1.0"


def test_check() -> None:
    result = runner.invoke(app, ["check"])
    assert result.exit_code == 0
    assert "Python: OK" in result.stdout
