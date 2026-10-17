from tests.utils import DEFAULT_AT, PayloadGenerator, RandomGenerator, RequestGenerator, shifted


def _payer_with_history(destination: str = None, amount: int = 15000):
    document = RandomGenerator.generate_cpf()
    RequestGenerator.POST_pix(PayloadGenerator.pix(
        payer_document=document,
        destination_document=destination,
        amount=amount,
        device_id=f"dvc-{document}",
        at=shifted(DEFAULT_AT, days=-1),
    ))
    return document


def _post(document: str, destination: str = None, amount: int = 300001):
    _, body = RequestGenerator.POST_pix(PayloadGenerator.pix(
        payer_document=document, destination_document=destination, amount=amount, device_id=f"dvc-{document}"
    ))
    return body


def _rules(body: dict) -> list:
    return [reason["rule"] for reason in body["metadata"]["reasons"]]


class TestCounterpartyFirstTimeHighRule:
    def test_post_new_destination_above_limit_returns_two_factor_required(self):
        """COUNTERPARTY_FIRST_TIME_HIGH: histórico + destino novo + R$ 3.000,01 pede 2FA."""
        document = _payer_with_history()

        body = _post(document)

        assert body["status"] == "two_factor_required"
        assert "COUNTERPARTY_FIRST_TIME_HIGH" in _rules(body)

    def test_post_new_destination_at_limit_returns_approved(self):
        """COUNTERPARTY_FIRST_TIME_HIGH: exatamente R$ 3.000,00 não dispara."""
        document = _payer_with_history()

        body = _post(document, amount=300000)

        assert "COUNTERPARTY_FIRST_TIME_HIGH" not in _rules(body)

    def test_post_first_pix_of_payer_returns_approved(self):
        """COUNTERPARTY_FIRST_TIME_HIGH: sem histórico não dispara."""
        body = _post(RandomGenerator.generate_cpf())

        assert "COUNTERPARTY_FIRST_TIME_HIGH" not in _rules(body)

    def test_post_destination_paid_before_returns_approved(self):
        """COUNTERPARTY_FIRST_TIME_HIGH: destino já pago e aprovado é conhecido."""
        destination = RandomGenerator.generate_cpf()
        document = _payer_with_history(destination)

        body = _post(document, destination)

        assert "COUNTERPARTY_FIRST_TIME_HIGH" not in _rules(body)

    def test_post_destination_only_rejected_before_returns_two_factor_required(self):
        """ADR 0021: retentar após reprovação não torna o destino conhecido."""
        destination = RandomGenerator.generate_cpf()
        document = _payer_with_history(amount=20000)
        _, rejected = RequestGenerator.POST_pix(PayloadGenerator.pix(
            payer_document=document,
            destination_document=destination,
            amount=100001,
            device_id=f"dvc-{document}",
            destination_opening_date=shifted(DEFAULT_AT, days=-1),
        ))
        assert rejected["status"] == "rejected"

        body = _post(document, destination)

        assert "COUNTERPARTY_FIRST_TIME_HIGH" in _rules(body)

    def test_post_self_transfer_returns_approved(self):
        """ADR 0021: self-transfer não dispara regra de contraparte."""
        document = _payer_with_history()

        body = _post(document, destination=document)

        assert body["status"] == "approved"
