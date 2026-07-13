from retrieval_app.interfaces.cli.core import (
    create_core_cli,
)
from retrieval_app.interfaces.cli.retrieval import (
    register_retrieval_commands,
)

app = create_core_cli()
register_retrieval_commands(app)

def main() -> None:
    app()
