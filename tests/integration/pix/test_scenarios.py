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


def test_mule_account_receiving_from_many_victims_returns_rejected():
    """Cenário do time: conta laranja de 2 dias recebendo de 11 pagadores em 1h."""
    mule = RandomGenerator.generate_cpf()
    opening = shifted(DEFAULT_AT, days=-2)
    for minutes in range(1, 11):
        RequestGenerator.POST_pix(PayloadGenerator.pix(
            destination_document=mule,
            destination_opening_date=opening,
            amount=20000,
            at=shifted(DEFAULT_AT, minutes=-minutes),
        ))

    _, body = RequestGenerator.POST_pix(
        PayloadGenerator.pix(destination_document=mule, destination_opening_date=opening, amount=20000)
    )

    assert body["status"] == "rejected"
    assert "COUNTERPARTY_FAN_IN" in _rules(body)


def test_account_takeover_new_device_high_amount_returns_two_factor():
    """Cenário do time: device novo + destino novo + valor alto pede 2FA."""
    victim = RandomGenerator.generate_cpf()
    for days_ago in range(5, 0, -1):
        RequestGenerator.POST_pix(PayloadGenerator.pix(
            payer_document=victim,
            device_id="dvc-owner",
            amount=20000,
            at=shifted(DEFAULT_AT, days=-days_ago),
        ))

    _, body = RequestGenerator.POST_pix(PayloadGenerator.pix(
        payer_document=victim, device_id="dvc-attacker", amount=400000
    ))

    assert body["status"] == "two_factor_required"
    assert {"PROFILE_NEW_DEVICE", "COUNTERPARTY_FIRST_TIME_HIGH"} <= set(_rules(body))
