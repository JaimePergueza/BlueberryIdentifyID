import logging
import sys

from blueberry_microid.infrastructure.config.settings import Settings
from blueberry_microid.infrastructure.logging.formatters import ConsoleLogFormatter, JsonLogFormatter


def configure_logging(settings: Settings) -> None:
    """Configure the root logger once, at application startup.

    No external logging service is used — this only wires the standard
    library's `logging` module to a single stdout stream handler with a
    structured formatter, controlled entirely by `LOG_LEVEL`/`LOG_FORMAT`.
    """
    handler = logging.StreamHandler(sys.stdout)
    if settings.log_format.lower() == "json":
        handler.setFormatter(JsonLogFormatter())
    else:
        handler.setFormatter(ConsoleLogFormatter())

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(settings.log_level.upper())
