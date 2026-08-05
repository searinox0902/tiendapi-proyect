import logging
import sys

from app.core.config import settings


def configure_logging() -> None:
    """Logging a stdout (visible con `docker logs`), nivel desde settings."""
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)-8s %(name)s | %(message)s")
    )

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers = [handler]
