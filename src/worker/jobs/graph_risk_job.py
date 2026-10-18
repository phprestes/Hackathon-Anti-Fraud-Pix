from constants import GRAPH_RISK_MODEL, WORKER_LOOKBACK_HOURS
from controllers.base_controller import BaseController
from repositories import GraphRiskRepository
from worker.models import scoring

FEATURE_KEYS = [
    "in_distinct_payers_24h",
    "in_amount_24h_cents",
    "dispersion_out_distinct_6h",
    "two_hop_flagged",
    "account_age_days",
]


class GraphRiskJob(BaseController):
    def __init__(self) -> None:
        super().__init__(__name__)
        self.repository = GraphRiskRepository(self.context)

    def run_cycle(self, previous: tuple | None = None) -> tuple | None:
        """Scores every recent destination; returns the data marker it scored (None when there is no data)."""
        clock = self.repository.data_clock()
        if clock is None:
            return None

        # Without new data the cycle would only append identical rows.
        marker = (clock, self.repository.transaction_count())
        if marker == previous:
            return marker

        scored = []
        for row in self.repository.destination_graph_features(clock, WORKER_LOOKBACK_HOURS):
            features = {key: int(row[key]) for key in FEATURE_KEYS}
            value, parts = scoring.score(features)
            scored.append((row["doc"], value, {**features, "contributions": parts}))

        self.repository.add_scores(GRAPH_RISK_MODEL, clock, scored)
        self.logger.info("graph_sql scored %d destinations at %s", len(scored), clock.isoformat())
        self.session.commit()
        return marker
