import re
import uuid
from contextvars import ContextVar


# De facto convention that proxies and log tools already read.
REQUEST_ID_HEADER = "X-Request-ID"

SAFE_REQUEST_ID = re.compile(r"[A-Za-z0-9_-]{1,64}")

# Logged when no request is running (startup, worker).
NO_REQUEST_ID = "-"


# ContextVar keeps one value per in-flight request. Lives in utils/ because the logger needs it
# and importing middlewares/ from the logger would close an import cycle.
_request_id: ContextVar[str] = ContextVar("request_id", default=NO_REQUEST_ID)


def get_request_id() -> str:
    """Id of the request being served now."""
    return _request_id.get()


def set_request_id(request_id: str) -> None:
    """Called by the request_context middleware."""
    _request_id.set(request_id)


def build_request_id(received_request_id: str = None) -> str:
    """Reuses the caller's id when it is safe; fullmatch blocks log injection (e.g. a newline)."""
    if received_request_id is not None and SAFE_REQUEST_ID.fullmatch(received_request_id):
        return received_request_id

    return str(uuid.uuid4())
