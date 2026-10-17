from uuid import uuid4

from tests.utils import DEFAULT_AT, PayloadGenerator, RandomGenerator, RequestGenerator, shifted

SAO_PAULO = {"latitude": -23.55, "longitude": -46.63}
RIO = {"latitude": -22.91, "longitude": -43.17}


def _new_device() -> str:
    return f"dvc-new-{uuid4().hex[:8]}"


def _history(document: str, last_geolocation: dict = None) -> str:
    device = f"dvc-owner-{uuid4().hex[:8]}"
    for days_ago in range(5, 0, -1):
        RequestGenerator.POST_pix(PayloadGenerator.pix(
            payer_document=document,
            device_id=device,
            amount=20000,
            at=shifted(DEFAULT_AT, days=-days_ago),
        ))
    if last_geolocation is not None:
        RequestGenerator.POST_pix(PayloadGenerator.pix(
            payer_document=document,
            device_id=device,
            amount=20000,
            geolocation=last_geolocation,
            at=shifted(DEFAULT_AT, minutes=-10),
        ))
    return device


def _current(document: str, device_id: str, amount: int = 20000, geolocation: dict = None) -> dict:
    _, body = RequestGenerator.POST_pix(PayloadGenerator.pix(
        payer_document=document, device_id=device_id, amount=amount, geolocation=geolocation
    ))
    return body


def _rules(body: dict) -> list:
    return [reason["rule"] for reason in body["metadata"]["reasons"]]


class TestTypologyAccountTakeoverRule:
    def test_post_new_device_and_impossible_travel_returns_rejected(self):
        """TYPOLOGY_ACCOUNT_TAKEOVER: aparelho novo + 357 km em 10 min reprova."""
        document = RandomGenerator.generate_cpf()
        _history(document, SAO_PAULO)

        body = _current(document, _new_device(), geolocation=RIO)

        assert body["status"] == "rejected"
        assert "TYPOLOGY_ACCOUNT_TAKEOVER" in _rules(body)
        signals = body["metadata"]["signals"]["TYPOLOGY_ACCOUNT_TAKEOVER"]
        assert signals["elapsed_minutes"] == 10
        reason = next(r for r in body["metadata"]["reasons"] if r["rule"] == "TYPOLOGY_ACCOUNT_TAKEOVER")
        assert reason["reason"].startswith("Padrão de conta tomada: aparelho novo e deslocamento de 36")

    def test_post_new_device_and_unusual_amount_returns_rejected(self):
        """TYPOLOGY_ACCOUNT_TAKEOVER: aparelho novo + valor 20x o padrão reprova."""
        document = RandomGenerator.generate_cpf()
        _history(document)

        body = _current(document, _new_device(), amount=400000)

        assert body["status"] == "rejected"
        assert "TYPOLOGY_ACCOUNT_TAKEOVER" in _rules(body)
        assert body["metadata"]["signals"]["TYPOLOGY_ACCOUNT_TAKEOVER"]["z"] > 3

    def test_post_new_device_without_travel_or_unusual_amount_returns_approved(self):
        """TYPOLOGY_ACCOUNT_TAKEOVER: aparelho novo sozinho não reprova."""
        document = RandomGenerator.generate_cpf()
        _history(document)

        body = _current(document, _new_device())

        assert "TYPOLOGY_ACCOUNT_TAKEOVER" not in _rules(body)

    def test_post_new_device_without_history_returns_approved(self):
        """TYPOLOGY_ACCOUNT_TAKEOVER: pagador sem histórico com aparelho novo não dispara."""
        body = _current(RandomGenerator.generate_cpf(), _new_device(), amount=400000)

        assert "TYPOLOGY_ACCOUNT_TAKEOVER" not in _rules(body)

    def test_post_known_device_with_impossible_travel_returns_two_factor_required(self):
        """TYPOLOGY_ACCOUNT_TAKEOVER: aparelho conhecido com viagem impossível fica só com o 2FA da geo."""
        document = RandomGenerator.generate_cpf()
        owner_device = _history(document, SAO_PAULO)

        body = _current(document, owner_device, geolocation=RIO)

        assert body["status"] == "two_factor_required"
        assert "TYPOLOGY_ACCOUNT_TAKEOVER" not in _rules(body)
