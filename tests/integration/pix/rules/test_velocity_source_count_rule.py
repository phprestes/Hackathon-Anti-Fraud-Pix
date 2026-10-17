from tests.utils import DEFAULT_AT, PayloadGenerator, RandomGenerator, RequestGenerator, shifted


def _history(document: str, minutes_ago: list, **kwargs) -> list:
    payloads = []
    for minutes in minutes_ago:
        payload = PayloadGenerator.pix(payer_document=document, at=shifted(DEFAULT_AT, minutes=-minutes), **kwargs)
        RequestGenerator.POST_pix(payload)
        payloads.append(payload)
    return payloads


def _current(document: str):
    _, body = RequestGenerator.POST_pix(PayloadGenerator.pix(payer_document=document))
    return body


def _rules(body: dict) -> list:
    return [reason["rule"] for reason in body["metadata"]["reasons"]]


class TestVelocitySourceCountRule:
    def test_post_fourth_pix_in_window_returns_approved(self):
        """VELOCITY_SOURCE_COUNT: 4 tentativas em 10 min ainda não disparam."""
        document = RandomGenerator.generate_cpf()
        _history(document, [1, 2, 3])

        body = _current(document)

        assert body["status"] == "approved"

    def test_post_fifth_pix_in_window_returns_two_factor_required(self):
        """VELOCITY_SOURCE_COUNT: 5ª tentativa em 10 min pede 2FA."""
        document = RandomGenerator.generate_cpf()
        _history(document, [1, 2, 3, 4])

        body = _current(document)

        assert body["status"] == "two_factor_required"
        assert "VELOCITY_SOURCE_COUNT" in _rules(body)
        assert body["metadata"]["signals"]["VELOCITY_SOURCE_COUNT"] == {"attempts_in_window": 5, "window_minutes": 10}

    def test_post_tenth_pix_in_window_returns_rejected(self):
        """VELOCITY_SOURCE_COUNT: 10ª tentativa em 10 min reprova."""
        document = RandomGenerator.generate_cpf()
        _history(document, [1, 2, 3, 4, 5, 6, 7, 8, 9])

        body = _current(document)

        assert body["status"] == "rejected"
        assert "VELOCITY_SOURCE_COUNT" in _rules(body)

    def test_post_pix_older_than_window_returns_approved(self):
        """VELOCITY_SOURCE_COUNT: Pix de 11 min atrás fica fora da janela."""
        document = RandomGenerator.generate_cpf()
        _history(document, [1, 2, 3, 11])

        body = _current(document)

        assert body["status"] == "approved"

    def test_post_after_rejected_attempt_returns_two_factor_required(self):
        """ADR 0021: tentativa reprovada anterior conta na janela de velocity."""
        document = RandomGenerator.generate_cpf()
        _history(document, [1, 2, 3])
        RequestGenerator.POST_pix(PayloadGenerator.pix(
            payer_document=document,
            at=shifted(DEFAULT_AT, minutes=-4),
            amount=100001,
            destination_opening_date=shifted(DEFAULT_AT, days=-1),
        ))

        body = _current(document)

        assert body["status"] == "two_factor_required"
        assert "VELOCITY_SOURCE_COUNT" in _rules(body)

    def test_post_idempotent_replays_returns_approved(self):
        """ADR 0012: replay não grava Pix novo, então não aumenta a contagem."""
        document = RandomGenerator.generate_cpf()
        payloads = _history(document, [1, 2, 3])
        for payload in payloads:
            RequestGenerator.POST_pix(payload)
            RequestGenerator.POST_pix(payload)

        body = _current(document)

        assert body["status"] == "approved"
