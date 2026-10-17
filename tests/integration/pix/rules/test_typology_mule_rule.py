from tests.utils import DEFAULT_AT, PayloadGenerator, RandomGenerator, RequestGenerator, shifted

NEW_ACCOUNT = shifted(DEFAULT_AT, days=-2)


def _payers(destination: str, count: int, opening: str):
    for minutes in range(1, count + 1):
        RequestGenerator.POST_pix(PayloadGenerator.pix(
            destination_document=destination,
            destination_opening_date=opening,
            amount=20000,
            at=shifted(DEFAULT_AT, minutes=-minutes),
        ))


def _current(destination: str, opening: str) -> dict:
    _, body = RequestGenerator.POST_pix(PayloadGenerator.pix(
        destination_document=destination, destination_opening_date=opening, amount=20000
    ))
    return body


def _rules(body: dict) -> list:
    return [reason["rule"] for reason in body["metadata"]["reasons"]]


class TestTypologyMuleRule:
    def test_post_fifth_payer_to_new_account_returns_rejected(self):
        """TYPOLOGY_MULE: conta de 2 dias recebendo de 5 pagadores em 1 h reprova."""
        destination = RandomGenerator.generate_cpf()
        _payers(destination, 4, NEW_ACCOUNT)

        body = _current(destination, NEW_ACCOUNT)

        assert body["status"] == "rejected"
        assert "TYPOLOGY_MULE" in _rules(body)
        assert body["metadata"]["signals"]["TYPOLOGY_MULE"] == {"destination_age_days": 2, "distinct_sources_1h": 5}
        reason = next(r for r in body["metadata"]["reasons"] if r["rule"] == "TYPOLOGY_MULE")
        assert reason["reason"] == "Padrão de conta laranja: conta de 2 dias recebendo de 5 pagadores em 1 h."

    def test_post_fourth_payer_to_new_account_returns_two_factor_required(self):
        """TYPOLOGY_MULE: 4 pagadores ainda não dispara; só a conta nova pede 2FA."""
        destination = RandomGenerator.generate_cpf()
        _payers(destination, 3, NEW_ACCOUNT)

        body = _current(destination, NEW_ACCOUNT)

        assert body["status"] == "two_factor_required"
        assert "TYPOLOGY_MULE" not in _rules(body)

    def test_post_fifth_payer_to_old_account_returns_approved(self):
        """TYPOLOGY_MULE: conta de 30 dias ou mais com 5 pagadores não dispara."""
        destination = RandomGenerator.generate_cpf()
        old = shifted(DEFAULT_AT, days=-30)
        _payers(destination, 4, old)

        body = _current(destination, old)

        assert "TYPOLOGY_MULE" not in _rules(body)
