from tests.utils import DEFAULT_AT, DbUtils, PayloadGenerator, RandomGenerator, RequestGenerator, shifted
from tests.utils.worker import run_worker_once

GRAPHSAGE = "MODEL_GRAPHSAGE"
SEQUENCE = "MODEL_SEQUENCE_HMM"


def _post(**kwargs) -> dict:
    _, body = RequestGenerator.POST_pix(PayloadGenerator.pix(**kwargs))
    return body


def _shadow(body: dict) -> dict:
    return {entry["rule"]: entry for entry in body["metadata"]["shadow"]}


def _mule_and_ordinary_destinations() -> tuple[str, str, str]:
    """A fresh account paid by 10 payers in 10 minutes, an old account paid once; returns (mule, ordinary, last_at)."""
    mule, ordinary = RandomGenerator.generate_cpf(), RandomGenerator.generate_cpf()
    opening = shifted(DEFAULT_AT, days=-2)
    for minute in range(10):
        _post(destination_document=mule, destination_opening_date=opening, amount=80000,
              at=shifted(DEFAULT_AT, minutes=minute))
    _post(destination_document=ordinary, amount=15000, at=shifted(DEFAULT_AT, minutes=10))
    return mule, ordinary, shifted(DEFAULT_AT, minutes=10)


class TestColdPathShadowModels:
    def test_post_destination_without_worker_scores_returns_no_graphsage_entry(self):
        """G6: sem ciclo do worker não há score de GraphSAGE e a regra shadow não aparece."""
        DbUtils.rollback()

        body = _post(destination_document=RandomGenerator.generate_cpf())

        assert GRAPHSAGE not in _shadow(body)
        assert SEQUENCE not in _shadow(body)
        assert body["metadata"]["features"]["destination_graphsage_score"] == -1
        assert body["metadata"]["features"]["source_sequence_score"] == -1

    def test_post_mule_destination_after_worker_returns_graphsage_score_above_ordinary(self):
        """G6/MODEL_GRAPHSAGE: destino-mula (10 pagadores, conta nova) pontua acima do destino comum; decisão não muda."""
        DbUtils.rollback()
        mule, ordinary, last = _mule_and_ordinary_destinations()
        run_worker_once()

        mule_body = _post(destination_document=mule, at=shifted(last, minutes=5))
        ordinary_body = _post(destination_document=ordinary, at=shifted(last, minutes=5))

        mule_entry = _shadow(mule_body)[GRAPHSAGE]
        ordinary_entry = _shadow(ordinary_body)[GRAPHSAGE]
        assert 0 <= ordinary_entry["signals"]["score"] < mule_entry["signals"]["score"] <= 1
        assert mule_entry["would_decide"] == "two_factor_required"
        assert ordinary_entry["would_decide"] == "approved"
        assert not any(r["rule"].startswith("MODEL_") for r in mule_body["metadata"]["reasons"])
        assert mule_body["metadata"]["features"]["destination_graphsage_score"] == mule_entry["signals"]["score"]

    def test_post_payer_with_history_after_worker_returns_sequence_score_in_range(self):
        """G6/MODEL_SEQUENCE_HMM: pagador com 6 Pix recebe score de sequência em [0, 1] no shadow."""
        DbUtils.rollback()
        payer = RandomGenerator.generate_cpf()
        destination = RandomGenerator.generate_cpf()
        for minute in range(6):
            _post(payer_document=payer, destination_document=destination, at=shifted(DEFAULT_AT, hours=minute))
        run_worker_once()

        body = _post(payer_document=payer, destination_document=destination, at=shifted(DEFAULT_AT, hours=6, minutes=30))

        entry = _shadow(body)[SEQUENCE]
        assert 0 <= entry["signals"]["score"] <= 1
        assert entry["would_decide"] in ("approved", "two_factor_required")
        assert body["metadata"]["features"]["source_sequence_score"] == entry["signals"]["score"]
        assert not any(r["rule"].startswith("MODEL_") for r in body["metadata"]["reasons"])
