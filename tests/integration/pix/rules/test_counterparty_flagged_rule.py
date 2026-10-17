from tests.utils import DEFAULT_AT, PayloadGenerator, RandomGenerator, RequestGenerator, shifted


def _reject_pix_to(destination: str, payer: str, days_ago: int) -> dict:
    """Conta de destino de 2 dias com valor acima de R$ 1.000 reprova (COUNTERPARTY_NEW_ACCOUNT)."""
    at = shifted(DEFAULT_AT, days=-days_ago)
    _, body = RequestGenerator.POST_pix(PayloadGenerator.pix(
        payer_document=payer,
        destination_document=destination,
        destination_opening_date=shifted(at, days=-2),
        amount=200000,
        at=at,
    ))
    assert body["status"] == "rejected"
    return body


def _current(destination: str, payer: str = None) -> dict:
    _, body = RequestGenerator.POST_pix(PayloadGenerator.pix(
        payer_document=payer, destination_document=destination, amount=5000
    ))
    return body


def _rules(body: dict) -> list:
    return [reason["rule"] for reason in body["metadata"]["reasons"]]


class TestCounterpartyFlaggedRule:
    def test_post_destination_rejected_for_other_payer_returns_two_factor_required(self):
        """COUNTERPARTY_FLAGGED: destino com Pix reprovado de outro pagador pede 2FA."""
        destination = RandomGenerator.generate_cpf()
        _reject_pix_to(destination, RandomGenerator.generate_cpf(), days_ago=1)

        body = _current(destination)

        assert body["status"] == "two_factor_required"
        assert "COUNTERPARTY_FLAGGED" in _rules(body)
        assert body["metadata"]["signals"]["COUNTERPARTY_FLAGGED"] == {"rejected_by_others": 1, "window_days": 7}
        reason = next(r for r in body["metadata"]["reasons"] if r["rule"] == "COUNTERPARTY_FLAGGED")
        assert reason["reason"] == "Destino recebeu Pix reprovado de outro pagador nos últimos 7 dias."

    def test_post_destination_rejected_eight_days_ago_returns_approved(self):
        """COUNTERPARTY_FLAGGED: reprovação de 8 dias atrás fica fora da janela."""
        destination = RandomGenerator.generate_cpf()
        _reject_pix_to(destination, RandomGenerator.generate_cpf(), days_ago=8)

        body = _current(destination)

        assert body["status"] == "approved"

    def test_post_destination_rejected_for_same_payer_returns_approved(self):
        """COUNTERPARTY_FLAGGED: reprovação do próprio pagador não conta."""
        destination = RandomGenerator.generate_cpf()
        payer = RandomGenerator.generate_cpf()
        _reject_pix_to(destination, payer, days_ago=1)

        body = _current(destination, payer)

        assert "COUNTERPARTY_FLAGGED" not in _rules(body)
