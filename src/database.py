"""Per-request database context (ContextVar). Design and trade-offs: docs/02-arquitetura/camadas.md#sessão-por-requisição."""
from contextvars import ContextVar
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from constants import DATABASE_URL


engine = create_engine(DATABASE_URL, pool_size=5, pool_recycle=600, pool_pre_ping=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False)


class Context:
    """Per-request state; a mutable object because a child task only sees a copy of the ContextVar."""

    def __init__(self) -> None:
        self.db_session: Optional[Session] = None

    def get_or_create_session(self) -> Session:
        if self.db_session is None:
            self.db_session = SessionLocal()

        return self.db_session


_context: ContextVar[Optional[Context]] = ContextVar("context", default=None)


def open_context() -> Context:
    """Called by the session_manager middleware and the worker loop; whoever opens it also closes it."""
    context = Context()
    _context.set(context)

    return context


def clear_context() -> None:
    """Without this, code outside a request would get the previous context with a closed session."""
    _context.set(None)


def get_context() -> Context:
    """Only controllers call this; the session stays lazy, so routes without a controller never touch the database."""
    context = _context.get()

    if context is None:
        raise Exception(
            "Nao existe contexto neste trabalho. "
            + "Quem prepara o contexto de cada requisicao e o middleware "
            + "src/middlewares/session_manager.py. Se voce chegou aqui, ele nao rodou."
        )

    return context
