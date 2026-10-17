import argparse
import signal
import threading

from constants import WORKER_ENABLED, WORKER_INTERVAL_SECONDS
from database import clear_context, open_context
from utils.logger import get_logger, setup_logging
from worker.graph_risk_job import GraphRiskJob

logger = get_logger("worker")
stop = threading.Event()


def run_cycle(previous: tuple | None) -> tuple | None:
    context = open_context()
    try:
        return GraphRiskJob().run_cycle(previous)
    except Exception:
        # The tests wipe the schema under the worker; log and try again next cycle.
        logger.exception("cycle failed")
        context.db_session.rollback()
        return previous
    finally:
        context.db_session.close()
        clear_context()


def run_once() -> None:
    context = open_context()
    try:
        GraphRiskJob().run_cycle()
    finally:
        context.db_session.close()
        clear_context()


def main() -> int:
    parser = argparse.ArgumentParser(description="Cold-path worker")
    parser.add_argument("--once", action="store_true", help="run one cycle and exit, even when WORKER_ENABLED=false")
    args = parser.parse_args()
    setup_logging()

    if args.once:
        run_once()
        return 0

    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: stop.set())
    if not WORKER_ENABLED:
        logger.info("WORKER_ENABLED=false: idle")
    marker = None
    while not stop.is_set():
        if WORKER_ENABLED:
            marker = run_cycle(marker)
        stop.wait(WORKER_INTERVAL_SECONDS)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
