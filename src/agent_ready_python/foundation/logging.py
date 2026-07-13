"""Safe stderr logging configuration."""

import logging
import sys


def configure_logging(level: str) -> None:
    """Configure the application logger without writing diagnostics to stdout."""

    logger = logging.getLogger("agent_ready_python")
    logger.setLevel(level)
    logger.propagate = False

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
        logger.addHandler(handler)

    for handler in logger.handlers:
        handler.setLevel(level)
