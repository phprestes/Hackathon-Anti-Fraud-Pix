from tests.utils import DEFAULT_AT, PayloadGenerator, RequestGenerator, shifted


def _post(days_old: int, amount: int):
    payload = PayloadGenerator.pix(amount=amount, source_opening_date=shifted(DEFAULT_AT, days=-days_old))
    _, body = RequestGenerator.POST_pix(payload)
    return body


def _rules(body: dict) -> list:
    return [reason["rule"] for reason in body["metadata"]["reasons"]]


class TestProfileNewSourceAccountRule:
    def test_post_source_6_days_old_above_limit_returns_two_factor_required(self):
        """PROFILE_NEW_SOURCE_ACCOUNT: conta de 6 dias movimentando R$ 2.000,01 pede 2FA."""
        body = _post(6, 200001)

        assert body["status"] == "two_factor_required"
        assert "PROFILE_NEW_SOURCE_ACCOUNT" in _rules(body)
        assert body["metadata"]["signals"]["PROFILE_NEW_SOURCE_ACCOUNT"] == {"source_age_days": 6, "amount_cents": 200001}

    def test_post_source_7_days_old_returns_approved(self):
        """PROFILE_NEW_SOURCE_ACCOUNT: 7 dias é a idade mínima, não dispara."""
        body = _post(7, 200001)

        assert "PROFILE_NEW_SOURCE_ACCOUNT" not in _rules(body)

    def test_post_source_6_days_old_amount_at_limit_returns_approved(self):
        """PROFILE_NEW_SOURCE_ACCOUNT: exatamente R$ 2.000,00 não dispara."""
        body = _post(6, 200000)

        assert body["status"] == "approved"
