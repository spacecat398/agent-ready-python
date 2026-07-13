from minimal_app.interfaces.cli.core import (
    create_core_cli,
)

app = create_core_cli()

def main() -> None:
    app()
