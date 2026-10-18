from constants import GRAPHSAGE_MODEL, WORKER_LOOKBACK_HOURS
from controllers.base_controller import BaseController
from repositories import GraphSageRepository
from worker.models import graphsage
from worker.models.model_files import load_model


class GraphSageJob(BaseController):
    def __init__(self) -> None:
        super().__init__(__name__)
        self.repository = GraphSageRepository(self.context)
        self.model = load_model("graphsage.json")

    def run_cycle(self, previous: tuple | None = None) -> tuple | None:
        """Scores the destinations of the trailing window over the subgraph of the same window."""
        clock = self.repository.data_clock()
        if clock is None or self.model is None:
            return None
        marker = (clock, self.repository.transaction_count())
        if marker == previous:
            return marker

        rows = self.repository.node_features(clock, WORKER_LOOKBACK_HOURS)
        raw = {row["doc"]: row for row in rows}
        targets = [row["doc"] for row in rows if row["was_destination"]]
        scores = graphsage.score_nodes(self.model, raw, self.repository.edges(clock, WORKER_LOOKBACK_HOURS), targets)
        scored = [
            (doc, round(value, 5), {"model_version": self.model["version"], "in_degree": raw[doc]["in_degree"]})
            for doc, value in scores.items()
        ]
        self.repository.add_scores(GRAPHSAGE_MODEL, clock, scored)
        self.logger.info("graphsage scored %d destinations at %s", len(scored), clock.isoformat())
        self.session.commit()
        return marker
