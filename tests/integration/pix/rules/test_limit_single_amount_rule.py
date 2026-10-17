from tests.utils import PayloadGenerator, RandomGenerator, RequestGenerator


def _post(amount: int, cnpj: bool = False):
    document = RandomGenerator.generate_cnpj() if cnpj else RandomGenerator.generate_cpf()
    _, body = RequestGenerator.POST_pix(PayloadGenerator.pix(amount=amount, payer_document=document))
    return body


def _rules(body: dict) -> list:
    return [reason["rule"] for reason in body["metadata"]["reasons"]]


class TestLimitSingleAmountRule:
    def test_post_individual_at_ceiling_returns_approved(self):
        """LIMIT_SINGLE_AMOUNT: exatamente R$ 50.000,00 não dispara."""
        body = _post(5000000)

        assert "LIMIT_SINGLE_AMOUNT" not in _rules(body)

    def test_post_individual_above_ceiling_returns_two_factor_required(self):
        """LIMIT_SINGLE_AMOUNT: R$ 50.000,01 pede 2FA."""
        body = _post(5000001)

        assert body["status"] == "two_factor_required"
        assert "LIMIT_SINGLE_AMOUNT" in _rules(body)

    def test_post_legal_entity_above_individual_ceiling_returns_approved(self):
        """LIMIT_SINGLE_AMOUNT: CNPJ tem teto maior."""
        body = _post(5000001, cnpj=True)

        assert "LIMIT_SINGLE_AMOUNT" not in _rules(body)

    def test_post_legal_entity_above_ceiling_returns_two_factor_required(self):
        """LIMIT_SINGLE_AMOUNT: CNPJ acima de R$ 200.000,00 pede 2FA."""
        body = _post(20000001, cnpj=True)

        assert body["status"] == "two_factor_required"
        assert "LIMIT_SINGLE_AMOUNT" in _rules(body)
