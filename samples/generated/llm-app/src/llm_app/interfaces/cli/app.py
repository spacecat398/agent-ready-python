from llm_app.interfaces.cli.core import (
    create_core_cli,
)
from llm_app.interfaces.cli.text_generation import (
    register_text_generation_commands,
)

app = create_core_cli()
register_text_generation_commands(app)

def main() -> None:
    app()
