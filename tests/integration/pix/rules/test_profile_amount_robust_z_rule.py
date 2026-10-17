from tests.utils import DEFAULT_AT, PayloadGenerator, RandomGenerator, RequestGenerator, shifted

DEVICE = "dvc-robust-z"


def _history(document: str, amounts: list):
    for index, amount in enumerate(amounts):
        RequestGenerator.POST_pix(PayloadGenerator.pix(
            payer_document=document,
            device_id=DEVICE,
            amount=amount,
            at=shifted(DEFAULT_AT, days=-(index + 1) * 3),
        ))


def _post(document: str, amount: int) -> dict:
    _, body = RequestGenerator.POST_pix(PayloadGenerator.pix(payer_document=document, device_id=DEVICE, amount=amount))
    return body


def _rules(body: dict) -> list:
    return [reason["rule"] for reason in body["metadata"]["reasons"]]


class TestProfileAmountRobustZRule:
    def test_post_amount_near_profile_returns_approved(self):
        """PROFILE_AMOUNT_ROBUST_Z: R$ 150 contra padrão de R$ 100 fica dentro do limiar."""
        document = RandomGenerator.generate_cpf()
        _history(document, [9800, 10000, 10200, 9900, 10100])

        body = _post(document, 15000)

        assert body["status"] == "approved"
        assert "PROFILE_AMOUNT_ROBUST_Z" not in _rules(body)

    def test_post_amount_far_above_profile_returns_two_factor_required(self):
        """PROFILE_AMOUNT_ROBUST_Z: R$ 2.000 contra padrão de R$ 100 pede 2FA."""
        document = RandomGenerator.generate_cpf()
        _history(document, [9800, 10000, 10200, 9900, 10100])

        body = _post(document, 200000)

        assert body["status"] == "two_factor_required"
        assert "PROFILE_AMOUNT_ROBUST_Z" in _rules(body)
        signals = body["metadata"]["signals"]["PROFILE_AMOUNT_ROBUST_Z"]
        assert signals["median_cents"] == 10000
        assert signals["z"] > 3.5

    def test_post_with_short_history_returns_approved(self):
        """PROFILE_AMOUNT_ROBUST_Z: 4 Pix de histórico não bastam para avaliar."""
        document = RandomGenerator.generate_cpf()
        _history(document, [9800, 10000, 10200, 9900])

        body = _post(document, 200000)

        assert "PROFILE_AMOUNT_ROBUST_Z" not in _rules(body)

    def test_post_identical_history_small_deviation_returns_approved(self):
        """PROFILE_AMOUNT_ROBUST_Z: MAD zero não vira z infinito (piso de escala)."""
        document = RandomGenerator.generate_cpf()
        _history(document, [10000] * 5)

        body = _post(document, 12000)

        assert "PROFILE_AMOUNT_ROBUST_Z" not in _rules(body)

    def test_post_amount_below_profile_returns_approved(self):
        """PROFILE_AMOUNT_ROBUST_Z: valor menor que o padrão nunca dispara."""
        document = RandomGenerator.generate_cpf()
        _history(document, [100000, 99000, 101000, 100500, 99500])

        body = _post(document, 100)

        assert "PROFILE_AMOUNT_ROBUST_Z" not in _rules(body)
