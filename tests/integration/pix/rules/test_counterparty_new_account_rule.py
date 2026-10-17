from tests.utils import DEFAULT_AT, PayloadGenerator, RandomGenerator, RequestGenerator, shifted


def _post(days_old: int, amount: int = 15000, self_transfer: bool = False):
    document = RandomGenerator.generate_cpf()
    payload = PayloadGenerator.pix(
        amount=amount,
        payer_document=document,
        destination_document=document if self_transfer else None,
        destination_opening_date=shifted(DEFAULT_AT, days=-days_old),
    )
    return RequestGenerator.POST_pix(payload)


def _rules(body: dict) -> list:
    return [reason["rule"] for reason in body["metadata"]["reasons"]]


class TestCounterpartyNewAccountRule:
    def test_post_destination_30_days_old_returns_approved(self):
        """COUNTERPARTY_NEW_ACCOUNT: 30 dias é o mínimo, não dispara."""
        _, body = _post(30)

        assert body["status"] == "approved"
        assert "COUNTERPARTY_NEW_ACCOUNT" not in _rules(body)

    def test_post_destination_29_days_old_returns_two_factor_required(self):
        """COUNTERPARTY_NEW_ACCOUNT: abaixo de 30 dias pede 2FA."""
        _, body = _post(29)

        assert body["status"] == "two_factor_required"
        assert "COUNTERPARTY_NEW_ACCOUNT" in _rules(body)
        assert body["metadata"]["signals"]["COUNTERPARTY_NEW_ACCOUNT"] == {"destination_age_days": 29}

    def test_post_destination_2_days_old_high_amount_returns_rejected(self):
        """COUNTERPARTY_NEW_ACCOUNT: conta crítica (<3 dias) acima de R$ 1.000,00 reprova."""
        _, body = _post(2, amount=100001)

        assert body["status"] == "rejected"
        assert body["metadata"]["reasons"][0]["rule"] == "COUNTERPARTY_NEW_ACCOUNT"

    def test_post_destination_2_days_old_amount_at_limit_returns_two_factor_required(self):
        """COUNTERPARTY_NEW_ACCOUNT: exatamente R$ 1.000,00 não reprova."""
        _, body = _post(2, amount=100000)

        assert body["status"] == "two_factor_required"

    def test_post_self_transfer_to_new_account_returns_approved(self):
        """ADR 0021: self-transfer não dispara regra de contraparte."""
        _, body = _post(1, self_transfer=True)

        assert body["status"] == "approved"
        assert body["metadata"]["reasons"] == []
