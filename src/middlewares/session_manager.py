from fastapi import FastAPI, Request

from database import clear_context, open_context


def register_session_manager_middleware(application: FastAPI) -> None:
    """Rollback on exception, close always, commit never (the controller commits).

    Innermost middleware; why it never commits and why the session may not exist:
    docs/02-arquitetura/camadas.md#sessão-por-requisição.
    """

    @application.middleware("http")
    async def manage_session(request: Request, call_next):
        context = open_context()

        try:
            response = await call_next(request)
        except Exception:
            # close() would also discard it; rollback states the intent explicitly.
            if context.db_session is not None:
                context.db_session.rollback()
            raise
        finally:
            # The session is lazy: routes without a controller (/, /health_check) never create one.
            if context.db_session is not None:
                context.db_session.close()
            clear_context()

        return response
