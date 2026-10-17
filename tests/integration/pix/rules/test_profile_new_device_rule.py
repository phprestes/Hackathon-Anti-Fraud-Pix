from tests.utils import DEFAULT_AT, PayloadGenerator, RandomGenerator, RequestGenerator, shifted


def _first_pix(document: str, device_id: str):
    RequestGenerator.POST_pix(
        PayloadGenerator.pix(payer_document=document, device_id=device_id, at=shifted(DEFAULT_AT, days=-1))
    )


def _post(document: str, amount: int, device_id: str = None):
    _, body = RequestGenerator.POST_pix(PayloadGenerator.pix(payer_document=document, amount=amount, device_id=device_id))
    return body


def _rules(body: dict) -> list:
    return [reason["rule"] for reason in body["metadata"]["reasons"]]


class TestProfileNewDeviceRule:
    def test_post_first_pix_of_payer_returns_approved(self):
        """PROFILE_NEW_DEVICE: sem histórico não há device 'novo'."""
        body = _post(RandomGenerator.generate_cpf(), 50000)

        assert "PROFILE_NEW_DEVICE" not in _rules(body)

    def test_post_new_device_at_minimum_amount_returns_two_factor_required(self):
        """PROFILE_NEW_DEVICE: pagador com histórico, device novo e R$ 500,00 pede 2FA."""
        document = RandomGenerator.generate_cpf()
        _first_pix(document, "dvc-old")

        body = _post(document, 50000)

        assert body["status"] == "two_factor_required"
        assert "PROFILE_NEW_DEVICE" in _rules(body)
        assert body["metadata"]["signals"]["PROFILE_NEW_DEVICE"] == {"history_size": 1, "amount_cents": 50000}

    def test_post_new_device_below_minimum_amount_returns_approved(self):
        """PROFILE_NEW_DEVICE: R$ 499,99 não dispara."""
        document = RandomGenerator.generate_cpf()
        _first_pix(document, "dvc-old")

        body = _post(document, 49999)

        assert body["status"] == "approved"

    def test_post_known_device_returns_approved(self):
        """PROFILE_NEW_DEVICE: device já usado pelo pagador não dispara."""
        document = RandomGenerator.generate_cpf()
        _first_pix(document, "dvc-old")

        body = _post(document, 50000, device_id="dvc-old")

        assert "PROFILE_NEW_DEVICE" not in _rules(body)
