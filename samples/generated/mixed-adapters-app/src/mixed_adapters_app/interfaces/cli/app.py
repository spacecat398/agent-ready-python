from mixed_adapters_app.interfaces.cli.core import (
    create_core_cli,
)
from mixed_adapters_app.interfaces.cli.retrieval import (
    register_retrieval_commands,
)
from mixed_adapters_app.interfaces.cli.text_generation import (
    register_text_generation_commands,
)

app = create_core_cli()
register_retrieval_commands(app)
register_text_generation_commands(app)

def main() -> None:
    app()
