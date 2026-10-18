from tests.utils import DEFAULT_AT, PayloadGenerator, RandomGenerator, RequestGenerator, shifted


def _post(document: str, amount: int, hours_ago: int = 1, **kwargs):
    payload = PayloadGenerator.pix(payer_document=document, amount=amount, at=shifted(DEFAULT_AT, hours=-hours_ago), **kwargs)
    return RequestGenerator.POST_pix(payload)


def _current(document: str):
    _, body = RequestGenerator.POST_pix(PayloadGenerator.pix(payer_document=document, amount=15000))
    return body


class TestAmountSourceDailySumRule:
    def test_post_daily_sum_at_limit_returns_approved(self):
        """AMOUNT_SOURCE_DAILY_SUM: soma exatamente R$ 45.000,00 não dispara."""
        document = RandomGenerator.generate_cpf()
        _post(document, 4485000)

        body = _current(document)

        assert body["status"] == "approved"

    def test_post_daily_sum_above_limit_returns_two_factor_required(self):
        """AMOUNT_SOURCE_DAILY_SUM: R$ 0,01 acima do teto pede 2FA."""
        document = RandomGenerator.generate_cpf()
        _post(document, 4485001)

        body = _current(document)

        assert body["status"] == "two_factor_required"
        assert body["metadata"]["reasons"][0]["rule"] == "AMOUNT_SOURCE_DAILY_SUM"
        assert body["metadata"]["signals"]["AMOUNT_SOURCE_DAILY_SUM"] == {
            "sum_24h_cents": 4500001,
            "limit_cents": 4500000,
        }

    def test_post_previous_pix_older_than_24h_returns_approved(self):
        """AMOUNT_SOURCE_DAILY_SUM: Pix de 25h atrás fica fora da janela."""
        document = RandomGenerator.generate_cpf()
        _post(document, 3000000, hours_ago=25)

        body = _current(document)

        assert body["status"] == "approved"

    def test_post_previous_rejected_pix_not_summed_returns_approved(self):
        """ADR 0021: Pix reprovado não entra na soma diária."""
        document = RandomGenerator.generate_cpf()
        _, rejected = _post(document, 3000000, destination_opening_date=shifted(DEFAULT_AT, days=-1))
        assert rejected["status"] == "rejected"

        body = _current(document)

        assert body["status"] == "approved"

    def test_post_cnpj_above_cpf_limit_returns_approved(self):
        """ADR 0021: CNPJ tem teto próprio de R$ 50.000,00."""
        document = RandomGenerator.generate_cnpj()
        _post(document, 4485001)

        body = _current(document)

        assert body["status"] == "approved"

    def test_post_cnpj_above_pj_limit_returns_two_factor_required(self):
        """AMOUNT_SOURCE_DAILY_SUM: CNPJ acima de R$ 50.000,00 pede 2FA."""
        document = RandomGenerator.generate_cnpj()
        _post(document, 4985001)

        body = _current(document)

        assert body["status"] == "two_factor_required"
