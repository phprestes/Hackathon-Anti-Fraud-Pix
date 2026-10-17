from tests.utils import DEFAULT_AT, PayloadGenerator, RandomGenerator, RequestGenerator, shifted

SAO_PAULO = {"latitude": -23.55, "longitude": -46.63}
RIO = {"latitude": -22.91, "longitude": -43.17}
NEAR_SAO_PAULO = {"latitude": -23.55, "longitude": -46.35}


def _post(document: str, geolocation: dict = None, **delta) -> dict:
    _, body = RequestGenerator.POST_pix(PayloadGenerator.pix(
        payer_document=document,
        device_id="dvc-geo",
        amount=5000,
        geolocation=geolocation,
        at=shifted(DEFAULT_AT, **delta),
    ))
    return body


def _rules(body: dict) -> list:
    return [reason["rule"] for reason in body["metadata"]["reasons"]]


class TestProfileGeoVelocityRule:
    def test_post_impossible_travel_returns_two_factor_required(self):
        """PROFILE_GEO_VELOCITY: São Paulo para o Rio em 10 min pede 2FA."""
        document = RandomGenerator.generate_cpf()
        _post(document, SAO_PAULO, minutes=-10)

        body = _post(document, RIO)

        assert body["status"] == "two_factor_required"
        assert "PROFILE_GEO_VELOCITY" in _rules(body)
        signals = body["metadata"]["signals"]["PROFILE_GEO_VELOCITY"]
        assert 350 < signals["distance_km"] < 365
        assert signals["speed_kmh"] > 900

    def test_post_same_trip_after_six_hours_returns_approved(self):
        """PROFILE_GEO_VELOCITY: 357 km em 6 h (~60 km/h) é plausível."""
        document = RandomGenerator.generate_cpf()
        _post(document, SAO_PAULO, hours=-6)

        body = _post(document, RIO)

        assert "PROFILE_GEO_VELOCITY" not in _rules(body)

    def test_post_without_current_geolocation_returns_approved(self):
        """PROFILE_GEO_VELOCITY: sem geolocalização atual não avalia."""
        document = RandomGenerator.generate_cpf()
        _post(document, SAO_PAULO, minutes=-10)

        body = _post(document)

        assert "PROFILE_GEO_VELOCITY" not in _rules(body)

    def test_post_without_previous_geolocation_returns_approved(self):
        """PROFILE_GEO_VELOCITY: sem Pix anterior geolocalizado não avalia."""
        document = RandomGenerator.generate_cpf()
        _post(document, minutes=-10)

        body = _post(document, RIO)

        assert "PROFILE_GEO_VELOCITY" not in _rules(body)

    def test_post_short_distance_fast_returns_approved(self):
        """PROFILE_GEO_VELOCITY: 30 km em 1 min fica abaixo da distância mínima."""
        document = RandomGenerator.generate_cpf()
        _post(document, SAO_PAULO, minutes=-1)

        body = _post(document, NEAR_SAO_PAULO)

        assert "PROFILE_GEO_VELOCITY" not in _rules(body)
