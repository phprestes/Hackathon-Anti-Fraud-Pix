import json
import logging
import os

from constants import WORKER_MODEL_DIR

logger = logging.getLogger(__name__)


def load_model(filename: str) -> dict | None:
    path = os.path.join(WORKER_MODEL_DIR, filename)
    if not os.path.isfile(path):
        logger.warning("model file %s not found; job skipped", path)
        return None
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)
