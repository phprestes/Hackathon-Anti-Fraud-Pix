from tests.utils import DEFAULT_AT, PayloadGenerator, RandomGenerator, RequestGenerator, shifted

DEVICE = "dvc-poisson"


def _post_at(document: str, **delta) -> dict:
    _, body = RequestGenerator.POST_pix(PayloadGenerator.pix(
        payer_document=document, device_id=f"{DEVICE}-{document}", amount=5000, at=shifted(DEFAULT_AT, **delta)
    ))
    return body


def _last_hour(document: str):
    for minutes in (45, 30, 15):
        _post_at(document, minutes=-minutes)


def _rules(body: dict) -> list:
    return [reason["rule"] for reason in body["metadata"]["reasons"]]


class TestVelocityPoissonGammaRule:
    def test_post_burst_from_intense_payer_returns_approved(self):
        """VELOCITY_POISSON_GAMMA: 4 Pix/h é normal para quem faz ~1 Pix/h há 3 dias."""
        document = RandomGenerator.generate_cpf()
        for hours in range(72, 1, -1):
            _post_at(document, hours=-hours)
        _last_hour(document)

        body = _post_at(document)

        assert "VELOCITY_POISSON_GAMMA" not in _rules(body)

    def test_post_burst_from_light_payer_returns_two_factor_required(self):
        """VELOCITY_POISSON_GAMMA: 4 Pix/h é improvável para quem faz 1 Pix a cada 4 dias."""
        document = RandomGenerator.generate_cpf()
        for days in (20, 16, 12, 8, 4):
            _post_at(document, days=-days)
        _last_hour(document)

        body = _post_at(document)

        assert body["status"] == "two_factor_required"
        assert "VELOCITY_POISSON_GAMMA" in _rules(body)
        signals = body["metadata"]["signals"]["VELOCITY_POISSON_GAMMA"]
        assert signals["k"] == 4
        assert 0 < signals["tail"] < 0.001

    def test_post_burst_from_new_payer_returns_approved(self):
        """VELOCITY_POISSON_GAMMA: sem 24 h de exposição a regra não avalia."""
        document = RandomGenerator.generate_cpf()
        _last_hour(document)

        body = _post_at(document)

        assert "VELOCITY_POISSON_GAMMA" not in _rules(body)
