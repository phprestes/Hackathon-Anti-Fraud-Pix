from datetime import datetime
from itertools import groupby

from constants import HMM_MODEL, WORKER_LOOKBACK_HOURS, WORKER_SEQUENCE_HISTORY_DAYS
from controllers.base_controller import BaseController
from repositories import SequenceRepository
from worker import hmm
from worker.model_files import load_model


class SequenceJob(BaseController):
    def __init__(self) -> None:
        super().__init__(__name__)
        self.repository = SequenceRepository(self.context)
        self.model = load_model("hmm.json")

    def run_cycle(self, previous: tuple | None = None) -> tuple | None:
        """Scores every payer active in the window by how unlikely their last Pix are under the legitimate HMM."""
        clock = self.repository.data_clock()
        if clock is None or self.model is None:
            return None
        marker = (clock, self.repository.transaction_count())
        if marker == previous:
            return marker

        history = self.repository.payer_history(clock, WORKER_LOOKBACK_HOURS, WORKER_SEQUENCE_HISTORY_DAYS)
        scored = []
        for payer, rows in groupby(history, key=lambda row: row["payer"]):
            symbols = hmm.symbol_sequence(
                [(row["destination"], row["amount"], datetime.fromisoformat(row["local_date"])) for row in rows],
                self.model,
            )
            result = hmm.anomaly_score(self.model, symbols)
            if result is not None:
                anomaly, mean_ll = result
                scored.append((payer, round(anomaly, 5), {
                    "model_version": self.model["version"],
                    "mean_log_likelihood": round(mean_ll, 4),
                    "last_symbols": symbols[-self.model["window"]:],
                }))

        self.repository.add_scores(HMM_MODEL, clock, scored)
        self.logger.info("hmm scored %d payers at %s", len(scored), clock.isoformat())
        self.session.commit()
        return marker
