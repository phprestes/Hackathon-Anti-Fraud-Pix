from tests.utils import PayloadGenerator, RandomGenerator, RequestGenerator


def _post(at: str, amount: int = 100001, cnpj: bool = False):
    document = RandomGenerator.generate_cnpj() if cnpj else RandomGenerator.generate_cpf()
    _, body = RequestGenerator.POST_pix(PayloadGenerator.pix(amount=amount, at=at, payer_document=document))
    return body


def _rules(body: dict) -> list:
    return [reason["rule"] for reason in body["metadata"]["reasons"]]


class TestLimitNightAmountRule:
    def test_post_evening_before_night_returns_approved(self):
        """LIMIT_NIGHT_AMOUNT: 19:59 ainda é horário diurno."""
        body = _post("2026-10-17T19:59:00-03:00")

        assert body["status"] == "approved"
        assert "LIMIT_NIGHT_AMOUNT" not in _rules(body)

    def test_post_night_start_returns_two_factor_required(self):
        """LIMIT_NIGHT_AMOUNT: 20:00 acima de R$ 1.000,00 pede 2FA."""
        body = _post("2026-10-17T20:00:00-03:00")

        assert body["status"] == "two_factor_required"
        assert "LIMIT_NIGHT_AMOUNT" in _rules(body)
        assert body["metadata"]["signals"]["LIMIT_NIGHT_AMOUNT"]["local_hour"] == 20

    def test_post_before_night_end_returns_two_factor_required(self):
        """LIMIT_NIGHT_AMOUNT: 05:59 ainda é noite."""
        body = _post("2026-10-17T05:59:00-03:00")

        assert body["status"] == "two_factor_required"
        assert "LIMIT_NIGHT_AMOUNT" in _rules(body)

    def test_post_night_end_returns_approved(self):
        """LIMIT_NIGHT_AMOUNT: 06:00 já é diurno."""
        body = _post("2026-10-17T06:00:00-03:00")

        assert body["status"] == "approved"

    def test_post_night_amount_at_limit_returns_approved(self):
        """LIMIT_NIGHT_AMOUNT: exatamente R$ 1.000,00 à noite não dispara."""
        body = _post("2026-10-17T22:00:00-03:00", amount=100000)

        assert body["status"] == "approved"

    def test_post_other_offset_uses_local_hour_returns_two_factor_required(self):
        """LIMIT_NIGHT_AMOUNT: usa a hora local do offset recebido (21h em -05:00)."""
        body = _post("2026-10-17T21:00:00-05:00")

        assert body["status"] == "two_factor_required"
        assert "LIMIT_NIGHT_AMOUNT" in _rules(body)

    def test_post_legal_entity_at_night_returns_approved(self):
        """LIMIT_NIGHT_AMOUNT: limite noturno não vale para CNPJ."""
        body = _post("2026-10-17T22:00:00-03:00", cnpj=True)

        assert body["status"] == "approved"
        assert "LIMIT_NIGHT_AMOUNT" not in _rules(body)
