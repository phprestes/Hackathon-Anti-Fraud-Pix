import logging
import sys

from constants import APP_ENV, SERVICE_NAME
from utils.request_context import get_request_id


LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s [%(request_id)s] - %(message)s"


class RequestIdFilter(logging.Filter):
    """Adds request_id to every record; it never drops a line (always True)."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id()
        return True


def setup_logging() -> None:
    """Called once at startup."""
    level = logging.INFO
    if APP_ENV.upper() in ("LOCAL", "TEST"):
        level = logging.DEBUG

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(LOG_FORMAT))

    # On the handler, not a logger, so library lines get the field too and formatting never breaks.
    handler.addFilter(RequestIdFilter())

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers = [handler]

    # urllib3 debug output is connection noise from our dependencies.
    for biblioteca_falante in ["urllib3"]:
        logging.getLogger(biblioteca_falante).setLevel(logging.CRITICAL)


def get_logger(class_name: str) -> logging.Logger:
    """Logger named after the caller, so each line says where it came from."""
    return logging.getLogger(f"{SERVICE_NAME}.{class_name}")
