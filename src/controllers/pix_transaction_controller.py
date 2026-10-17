import json
from datetime import datetime, timedelta

from sqlalchemy.exc import IntegrityError

from constants import (
    RULE_POISSON_LOOKBACK_DAYS,
    RULE_POISSON_WINDOW_MINUTES,
    RULE_PROFILE_LOOKBACK_DAYS,
    RULE_SET_VERSION,
    RULE_VELOCITY_WINDOW_MINUTES,
)
from controllers.base_controller import BaseController
from dtos import PixAnalysisDTO
from errors import InvalidSchema, NotFoundPixTransaction, PixIdConflict
from repositories import PixTransactionRepository
from rules import ACTIVE_RULES
from rules.decision import APPROVED, SEVERITY
from rules.pix_snapshot import PixSnapshot
from rules.rule_context import RuleContext


def _canonical(payload: dict) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _build_snapshot(payload: dict) -> PixSnapshot:
    source = payload["source_account"]
    destination = payload["destination_account"]
    origin = payload["source"]
    geolocation = origin.get("geolocation") or {}

    return PixSnapshot(
        pix_id=payload["id"],
        amount=payload["amount"],
        transaction_date=datetime.fromisoformat(payload["transaction_date"]),
        source_document=source["owner"]["document_number"],
        source_opening_date=datetime.fromisoformat(source["opening_date"]),
        destination_document=destination["owner"]["document_number"],
        destination_participant=destination["participant"],
        destination_opening_date=datetime.fromisoformat(destination["opening_date"]),
        device_id=origin["device_id"],
        channel=origin["channel"],
        ip=origin["ip"],
        latitude=geolocation.get("latitude"),
        longitude=geolocation.get("longitude"),
    )


class PixTransactionController(BaseController):
    def __init__(self) -> None:
        super().__init__(__name__)
        self.pix_transaction_repository = PixTransactionRepository(self.context)

    def analyze(self, payload: dict) -> tuple[dict, bool]:
        """Returns (dto, is_replay)."""
        existing = self._find_replay(payload)
        if existing is not None:
            return existing, True

        try:
            snapshot = _build_snapshot(payload)
        except ValueError as error:
            raise InvalidSchema(f"Invalid date: {error}")

        context = self._build_context(snapshot)
        results = [result for rule in ACTIVE_RULES if (result := rule.evaluate(snapshot, context)) is not None]
        results.sort(key=lambda result: -SEVERITY[result.decision])
        decision = self._decide(results)

        metadata = {
            "reasons": [{"rule": r.code, "decision": r.decision, "reason": r.reason} for r in results],
            "signals": {r.code: r.signals for r in results},
            "rule_set_version": RULE_SET_VERSION,
        }
        reasons = [{"rule_code": r.code, "decision": r.decision, "reason": r.reason} for r in results]

        try:
            pix_analysis = self.pix_transaction_repository.create(
                payload=payload,
                snapshot=snapshot,
                status_enumerator=decision,
                metadata=metadata,
                rule_set_version=RULE_SET_VERSION,
                reasons=reasons,
            )
            pix_analysis_dto = PixAnalysisDTO.obj_to_dict(pix_analysis)
            self.session.commit()
        except IntegrityError:
            # Lost the race on pix_id UNIQUE: the winner's row is the answer.
            self.session.rollback()
            existing = self._find_replay(payload)
            if existing is None:
                raise
            return existing, True

        return pix_analysis_dto, False

    def get_by_pix_id(self, pix_id: str) -> dict:
        pix_analysis = self.pix_transaction_repository.get_by_pix_id(pix_id)

        if pix_analysis is None:
            raise NotFoundPixTransaction(pix_id)

        return PixAnalysisDTO.obj_to_dict(pix_analysis)

    def _build_context(self, snapshot: PixSnapshot) -> RuleContext:
        t = snapshot.transaction_date
        attempts = self.pix_transaction_repository.count_source_attempts_since(
            snapshot.source_document,
            t - timedelta(minutes=RULE_VELOCITY_WINDOW_MINUTES),
            t,
            snapshot.pix_id,
        )
        sum_24h = self.pix_transaction_repository.sum_source_not_rejected_since(
            snapshot.source_document, t - timedelta(hours=24), t, snapshot.pix_id
        )
        repository = self.pix_transaction_repository
        source, pix_id = snapshot.source_document, snapshot.pix_id
        poisson_start = t - timedelta(minutes=RULE_POISSON_WINDOW_MINUTES)
        return RuleContext(
            source_attempts_last_velocity_window=attempts,
            source_sum_last_24h_cents=sum_24h,
            source_history_size=repository.count_source_history(source, t, pix_id),
            device_seen_for_source=repository.source_used_device(source, snapshot.device_id, t, pix_id),
            destination_seen_for_source=repository.source_paid_destination_not_rejected(
                source, snapshot.destination_document, t, pix_id
            ),
            device_distinct_other_sources_last_24h=repository.count_device_other_sources_since(
                snapshot.device_id, source, t - timedelta(hours=24), t, pix_id
            ),
            destination_distinct_other_sources_last_1h=repository.count_destination_other_sources_since(
                snapshot.destination_document, source, t - timedelta(hours=1), t, pix_id
            ),
            source_amounts_last_30d_cents=repository.list_source_amounts_not_rejected_since(
                source, t - timedelta(days=RULE_PROFILE_LOOKBACK_DAYS), t, pix_id
            ),
            source_attempts_poisson_window=repository.count_source_attempts_since(source, poisson_start, t, pix_id),
            source_attempts_poisson_lookback=repository.count_source_attempts_since(
                source, t - timedelta(days=RULE_POISSON_LOOKBACK_DAYS), poisson_start, pix_id
            ),
            source_first_seen=repository.first_source_transaction_date(source, t, pix_id),
            source_last_geolocation=repository.last_source_geolocation(source, t, pix_id),
        )

    @staticmethod
    def _decide(results: list) -> str:
        if not results:
            return APPROVED
        return max(results, key=lambda result: SEVERITY[result.decision]).decision

    def _find_replay(self, payload: dict) -> dict | None:
        pix_analysis = self.pix_transaction_repository.get_by_pix_id(payload["id"])

        if pix_analysis is None:
            return None

        if _canonical(pix_analysis.pix_transaction.payload) != _canonical(payload):
            raise PixIdConflict(payload["id"])

        return PixAnalysisDTO.obj_to_dict(pix_analysis)
