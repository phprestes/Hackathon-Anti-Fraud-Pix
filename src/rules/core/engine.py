from dataclasses import dataclass, field
from datetime import timedelta

from constants import (
    GRAPH_RISK_MODEL,
    GRAPHSAGE_MODEL,
    HMM_MODEL,
    RULE_FLAGGED_WINDOW_DAYS,
    RULE_GRAPH_RISK_MAX_AGE_MINUTES,
    RULE_POISSON_LOOKBACK_DAYS,
    RULE_POISSON_WINDOW_MINUTES,
    RULE_PROFILE_LOOKBACK_DAYS,
    RULE_SET_VERSION,
    RULE_SPLITTING_MAX_AMOUNT_CENTS,
    RULE_VELOCITY_WINDOW_MINUTES,
)
from rules.core.base_rule import BaseRule, RuleResult
from rules.core.decision import APPROVED, SEVERITY
from rules.core.features import build_features
from rules.core.history_port import HistoryPort
from rules.core.pix_snapshot import PixSnapshot
from rules.core.rule_context import RuleContext


@dataclass(frozen=True)
class EngineResult:
    status: str
    results: list[RuleResult]
    shadow_results: list[RuleResult] = field(default_factory=list)
    features: dict[str, float] = field(default_factory=dict)


def build_context(snapshot: PixSnapshot, history: HistoryPort) -> RuleContext:
    t = snapshot.transaction_date
    source, pix_id = snapshot.source_document, snapshot.pix_id
    destination = snapshot.destination_document
    poisson_start = t - timedelta(minutes=RULE_POISSON_WINDOW_MINUTES)
    graph_risk = history.latest_account_risk_score(
        destination, GRAPH_RISK_MODEL, t - timedelta(minutes=RULE_GRAPH_RISK_MAX_AGE_MINUTES), t
    )
    max_age = timedelta(minutes=RULE_GRAPH_RISK_MAX_AGE_MINUTES)
    graphsage = history.latest_account_risk_score(destination, GRAPHSAGE_MODEL, t - max_age, t)
    sequence = history.latest_payer_sequence_score(source, HMM_MODEL, t - max_age, t)
    return RuleContext(
        source_attempts_last_velocity_window=history.count_source_attempts_since(
            source, t - timedelta(minutes=RULE_VELOCITY_WINDOW_MINUTES), t, pix_id
        ),
        source_sum_last_24h_cents=history.sum_source_not_rejected_since(source, t - timedelta(hours=24), t, pix_id),
        source_history_size=history.count_source_history(source, t, pix_id),
        device_seen_for_source=history.source_used_device(source, snapshot.device_id, t, pix_id),
        destination_seen_for_source=history.source_paid_destination_not_rejected(source, destination, t, pix_id),
        device_distinct_other_sources_last_24h=history.count_device_other_sources_since(
            snapshot.device_id, source, t - timedelta(hours=24), t, pix_id
        ),
        destination_distinct_other_sources_last_1h=history.count_destination_other_sources_since(
            destination, source, t - timedelta(hours=1), t, pix_id
        ),
        source_amounts_last_30d_cents=history.list_source_amounts_not_rejected_since(
            source, t - timedelta(days=RULE_PROFILE_LOOKBACK_DAYS), t, pix_id
        ),
        source_attempts_poisson_window=history.count_source_attempts_since(source, poisson_start, t, pix_id),
        source_attempts_poisson_lookback=history.count_source_attempts_since(
            source, t - timedelta(days=RULE_POISSON_LOOKBACK_DAYS), poisson_start, pix_id
        ),
        source_first_seen=history.first_source_transaction_date(source, t, pix_id),
        source_last_geolocation=history.last_source_geolocation(source, t, pix_id),
        source_new_destinations_last_24h=history.count_source_new_destinations_since(
            source, t - timedelta(hours=24), t, pix_id
        ),
        destination_used_before=history.source_used_destination(source, destination, t, pix_id),
        source_small_attempts_last_24h=history.count_source_small_attempts_since(
            source, RULE_SPLITTING_MAX_AMOUNT_CENTS, t - timedelta(hours=24), t, pix_id
        ),
        destination_rejected_by_others_last_window=history.count_destination_rejected_by_others_since(
            destination, source, t - timedelta(days=RULE_FLAGGED_WINDOW_DAYS), t, pix_id
        ),
        destination_graph_risk=graph_risk.score if graph_risk else None,
        destination_graph_risk_age_minutes=(t - graph_risk.computed_at).total_seconds() / 60 if graph_risk else None,
        destination_graph_risk_contributions=graph_risk.contributions if graph_risk else (),
        destination_graphsage_score=graphsage.score if graphsage else None,
        source_sequence_score=sequence.score if sequence else None,
    )


def evaluate(snapshot: PixSnapshot, context: RuleContext, rules: list[BaseRule]) -> EngineResult:
    results = _fired([rule for rule in rules if not rule.shadow], snapshot, context)
    shadow_results = _fired([rule for rule in rules if rule.shadow], snapshot, context)
    status = max(results, key=lambda result: SEVERITY[result.decision]).decision if results else APPROVED
    return EngineResult(status, results, shadow_results, build_features(snapshot, context))


def metadata_from(result: EngineResult) -> dict:
    return {
        "reasons": [{"rule": r.code, "decision": r.decision, "reason": r.reason} for r in result.results],
        "signals": {r.code: r.signals for r in result.results},
        "features": result.features,
        "shadow": [
            {"rule": r.code, "would_decide": r.decision, "reason": r.reason, "signals": r.signals}
            for r in result.shadow_results
        ],
        "rule_set_version": RULE_SET_VERSION,
    }


def _fired(rules: list[BaseRule], snapshot: PixSnapshot, context: RuleContext) -> list[RuleResult]:
    fired = [result for rule in rules if (result := rule.evaluate(snapshot, context)) is not None]
    # sorted() is stable, so ACTIVE_RULES order still breaks ties.
    return sorted(fired, key=lambda result: -SEVERITY[result.decision])
