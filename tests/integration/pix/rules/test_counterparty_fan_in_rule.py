from tests.utils import DEFAULT_AT, PayloadGenerator, RandomGenerator, RequestGenerator, shifted


def _history(destination: str, minutes_ago: list):
    for minutes in minutes_ago:
        RequestGenerator.POST_pix(
            PayloadGenerator.pix(destination_document=destination, at=shifted(DEFAULT_AT, minutes=-minutes))
        )


def _current(destination: str):
    _, body = RequestGenerator.POST_pix(PayloadGenerator.pix(destination_document=destination))
    return body


def _rules(body: dict) -> list:
    return [reason["rule"] for reason in body["metadata"]["reasons"]]


class TestCounterpartyFanInRule:
    def test_post_tenth_distinct_payer_returns_approved(self):
        """COUNTERPARTY_FAN_IN: 10 pagadores distintos em 1h ainda não disparam."""
        destination = RandomGenerator.generate_cpf()
        _history(destination, range(1, 10))

        body = _current(destination)

        assert body["status"] == "approved"

    def test_post_eleventh_distinct_payer_returns_rejected(self):
        """COUNTERPARTY_FAN_IN: 11º pagador distinto em 1h reprova."""
        destination = RandomGenerator.generate_cpf()
        _history(destination, range(1, 11))

        body = _current(destination)

        assert body["status"] == "rejected"
        assert "COUNTERPARTY_FAN_IN" in _rules(body)
        assert body["metadata"]["signals"]["COUNTERPARTY_FAN_IN"] == {"distinct_sources_1h": 11, "max_sources": 10}

    def test_post_payer_61_minutes_ago_returns_approved(self):
        """COUNTERPARTY_FAN_IN: pagador de 61 min atrás fica fora da janela."""
        destination = RandomGenerator.generate_cpf()
        _history(destination, [*range(1, 10), 61])

        body = _current(destination)

        assert body["status"] == "approved"
