"""CLI composition root."""

from agent_ready_python.interfaces.cli.core import create_core_cli
from agent_ready_python.interfaces.cli.pipeline import register_pipeline_commands
from agent_ready_python.interfaces.cli.retrieval import register_retrieval_commands
from agent_ready_python.interfaces.cli.text_generation import register_text_generation_commands

app = create_core_cli()
register_text_generation_commands(app)
register_retrieval_commands(app)
register_pipeline_commands(app)


def main() -> None:
    app()
