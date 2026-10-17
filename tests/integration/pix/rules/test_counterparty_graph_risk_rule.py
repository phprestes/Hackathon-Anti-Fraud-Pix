from tests.utils import DEFAULT_AT, DbUtils, PayloadGenerator, RandomGenerator, RequestGenerator, shifted
from tests.utils.worker import run_worker_once

RULE = "COUNTERPARTY_GRAPH_RISK"


def _post(**kwargs) -> dict:
    _, body = RequestGenerator.POST_pix(PayloadGenerator.pix(**kwargs))
    return body


def _mule_funnel(mule: str, payers: int, destinations: int) -> str:
    """Funnel in, dispersion out; returns the timestamp of the last Pix (the data clock)."""
    for index in range(payers):
        _post(destination_document=mule, at=shifted(DEFAULT_AT, minutes=index))
    last = shifted(DEFAULT_AT, minutes=payers + 5)
    for _ in range(destinations):
        _post(payer_document=mule, at=last)
    return last


def _rule(body: dict) -> dict | None:
    return next((r for r in body["metadata"]["reasons"] if r["rule"] == RULE), None)


class TestCounterpartyGraphRiskRule:
    def test_post_funnel_then_dispersion_destination_returns_two_factor_required(self):
        """COUNTERPARTY_GRAPH_RISK: destino-mula (8 pagadores, 6 destinos) com score >= 0,6 pede 2FA."""
        DbUtils.rollback()
        mule = RandomGenerator.generate_cpf()
        last = _mule_funnel(mule, payers=8, destinations=6)
        run_worker_once()

        body = _post(destination_document=mule, at=shifted(last, minutes=10))

        reason = _rule(body)
        assert reason is not None and reason["decision"] == "two_factor_required"
        assert body["status"] in ("two_factor_required", "rejected")
        signals = body["metadata"]["signals"][RULE]
        assert 0.6 <= signals["score"] < 0.9
        assert signals["top_features"]
        assert body["metadata"]["features"]["destination_graph_risk"] == signals["score"]

    def test_post_large_funnel_and_dispersion_destination_returns_rejected(self):
        """COUNTERPARTY_GRAPH_RISK: score >= 0,9 reprova."""
        DbUtils.rollback()
        mule = RandomGenerator.generate_cpf()
        last = _mule_funnel(mule, payers=15, destinations=8)
        run_worker_once()

        body = _post(destination_document=mule, at=shifted(last, minutes=10))

        assert body["status"] == "rejected"
        assert _rule(body)["decision"] == "rejected"
        assert body["metadata"]["signals"][RULE]["score"] >= 0.9

    def test_post_ordinary_destination_returns_approved_without_graph_risk(self):
        """COUNTERPARTY_GRAPH_RISK: destino comum recebe score baixo e a regra não dispara."""
        DbUtils.rollback()
        destination = RandomGenerator.generate_cpf()
        _post(destination_document=destination)
        run_worker_once()

        body = _post(destination_document=destination, at=shifted(DEFAULT_AT, minutes=10))

        assert body["status"] == "approved"
        assert _rule(body) is None
        assert 0 <= body["metadata"]["features"]["destination_graph_risk"] < 0.2

    def test_post_score_older_than_max_age_returns_no_graph_risk(self):
        """COUNTERPARTY_GRAPH_RISK: score com mais de 120 min de idade é ignorado."""
        DbUtils.rollback()
        mule = RandomGenerator.generate_cpf()
        last = _mule_funnel(mule, payers=8, destinations=6)
        run_worker_once()

        body = _post(destination_document=mule, at=shifted(last, hours=3))

        assert _rule(body) is None
        assert body["metadata"]["features"]["destination_graph_risk"] == -1
        assert body["metadata"]["features"]["destination_graph_risk_age_minutes"] == -1

    def test_post_destination_without_score_returns_no_graph_risk(self):
        """COUNTERPARTY_GRAPH_RISK: sem linha do worker a regra não dispara."""
        DbUtils.rollback()

        body = _post(destination_document=RandomGenerator.generate_cpf())

        assert _rule(body) is None
        assert body["metadata"]["features"]["destination_graph_risk"] == -1
