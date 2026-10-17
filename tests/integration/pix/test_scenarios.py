from uuid import uuid4

from tests.utils import DEFAULT_AT, PayloadGenerator, RandomGenerator, RequestGenerator, shifted


def _rules(body: dict) -> list:
    return [reason["rule"] for reason in body["metadata"]["reasons"]]


def test_regular_payer_paying_rent_returns_approved():
    """Cenário do time: aluguel recorrente, mesmo destino e device, de dia."""
    payer = RandomGenerator.generate_cpf()
    landlord = RandomGenerator.generate_cpf()
    for weeks_ago in range(5, 0, -1):
        RequestGenerator.POST_pix(PayloadGenerator.pix(
            payer_document=payer,
            destination_document=landlord,
            device_id="dvc-rent",
            amount=150000,
            at=shifted("2026-10-17T10:00:00-03:00", days=-7 * weeks_ago),
        ))

    _, body = RequestGenerator.POST_pix(PayloadGenerator.pix(
        payer_document=payer,
        destination_document=landlord,
        device_id="dvc-rent",
        amount=155000,
        at="2026-10-17T10:00:00-03:00",
    ))

    assert body["status"] == "approved"
    assert body["metadata"]["reasons"] == []


def _mule_scenario() -> str:
    mule = RandomGenerator.generate_cpf()
    opening = shifted(DEFAULT_AT, days=-2)
    for minutes in range(1, 5):
        RequestGenerator.POST_pix(PayloadGenerator.pix(
            destination_document=mule,
            destination_opening_date=opening,
            amount=20000,
            at=shifted(DEFAULT_AT, minutes=-minutes),
        ))
    return mule


def test_mule_account_receiving_from_fifth_payer_returns_rejected():
    """Cenário do time: conta laranja de 2 dias reprova já no 5º pagador em 1h."""
    mule = _mule_scenario()

    _, body = RequestGenerator.POST_pix(PayloadGenerator.pix(
        destination_document=mule, destination_opening_date=shifted(DEFAULT_AT, days=-2), amount=20000
    ))

    assert body["status"] == "rejected"
    assert "TYPOLOGY_MULE" in _rules(body)


def test_destination_flagged_after_mule_returns_two_factor():
    """ADR 0019: depois de reprovar a mula, outro pagador 2 dias depois recebe 2FA."""
    mule = _mule_scenario()
    opening = shifted(DEFAULT_AT, days=-2)
    _, rejected = RequestGenerator.POST_pix(
        PayloadGenerator.pix(destination_document=mule, destination_opening_date=opening, amount=20000)
    )
    assert rejected["status"] == "rejected"

    _, body = RequestGenerator.POST_pix(PayloadGenerator.pix(
        destination_document=mule, destination_opening_date=opening, amount=20000, at=shifted(DEFAULT_AT, days=2)
    ))

    assert body["status"] == "two_factor_required"
    assert "COUNTERPARTY_FLAGGED" in _rules(body)


def test_account_takeover_new_device_far_away_returns_rejected():
    """Cenário do time: device novo + deslocamento impossível + valor alto reprova (conta tomada)."""
    victim = RandomGenerator.generate_cpf()
    owner = f"dvc-{uuid4().hex[:8]}"
    for days_ago in range(5, 0, -1):
        RequestGenerator.POST_pix(PayloadGenerator.pix(
            payer_document=victim,
            device_id=owner,
            amount=20000,
            geolocation={"latitude": -23.55, "longitude": -46.63},
            at=shifted(DEFAULT_AT, days=-days_ago),
        ))
    RequestGenerator.POST_pix(PayloadGenerator.pix(
        payer_document=victim,
        device_id=owner,
        amount=20000,
        geolocation={"latitude": -23.55, "longitude": -46.63},
        at=shifted(DEFAULT_AT, minutes=-10),
    ))

    _, body = RequestGenerator.POST_pix(PayloadGenerator.pix(
        payer_document=victim,
        device_id=f"dvc-{uuid4().hex[:8]}",
        amount=400000,
        geolocation={"latitude": -22.91, "longitude": -43.17},
    ))

    assert body["status"] == "rejected"
    assert {"TYPOLOGY_ACCOUNT_TAKEOVER", "PROFILE_NEW_DEVICE", "PROFILE_GEO_VELOCITY"} <= set(_rules(body))
