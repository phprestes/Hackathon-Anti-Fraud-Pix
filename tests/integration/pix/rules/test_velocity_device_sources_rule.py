from uuid import uuid4

from tests.utils import DEFAULT_AT, PayloadGenerator, RandomGenerator, RequestGenerator, shifted


def _history(device_id: str, minutes_ago: list, payers: list = None):
    for index, minutes in enumerate(minutes_ago):
        payer = payers[index] if payers else RandomGenerator.generate_cpf()
        RequestGenerator.POST_pix(
            PayloadGenerator.pix(payer_document=payer, device_id=device_id, at=shifted(DEFAULT_AT, minutes=-minutes))
        )


def _current(device_id: str):
    _, body = RequestGenerator.POST_pix(PayloadGenerator.pix(device_id=device_id))
    return body


def _rules(body: dict) -> list:
    return [reason["rule"] for reason in body["metadata"]["reasons"]]


class TestVelocityDeviceSourcesRule:
    def test_post_third_distinct_payer_on_device_returns_approved(self):
        """VELOCITY_DEVICE_SOURCES: 3 pagadores distintos no device ainda não disparam."""
        device = f"dvc-{uuid4().hex[:12]}"
        _history(device, [10, 20])

        body = _current(device)

        assert body["status"] == "approved"

    def test_post_fourth_distinct_payer_on_device_returns_rejected(self):
        """VELOCITY_DEVICE_SOURCES: 4º pagador distinto no device em 24h reprova."""
        device = f"dvc-{uuid4().hex[:12]}"
        _history(device, [10, 20, 30])

        body = _current(device)

        assert body["status"] == "rejected"
        assert "VELOCITY_DEVICE_SOURCES" in _rules(body)
        assert body["metadata"]["signals"]["VELOCITY_DEVICE_SOURCES"] == {"distinct_sources_24h": 4, "max_sources": 3}

    def test_post_same_payer_repeating_on_device_returns_approved(self):
        """VELOCITY_DEVICE_SOURCES: o mesmo pagador repetido não conta como distinto."""
        device = f"dvc-{uuid4().hex[:12]}"
        other = RandomGenerator.generate_cpf()
        _history(device, [10, 20, 30, 40], payers=[other] * 4)

        body = _current(device)

        assert body["status"] == "approved"

    def test_post_payer_25_hours_ago_returns_approved(self):
        """VELOCITY_DEVICE_SOURCES: pagador de 25h atrás fica fora da janela."""
        device = f"dvc-{uuid4().hex[:12]}"
        _history(device, [10, 20, 25 * 60])

        body = _current(device)

        assert body["status"] == "approved"
