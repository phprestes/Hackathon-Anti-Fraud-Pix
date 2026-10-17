from tests.utils import DEFAULT_AT, PayloadGenerator, RandomGenerator, RequestGenerator, shifted

MODEL_RULES = {"MODEL_LOGREG", "MODEL_LIGHTGBM", "MODEL_IFOREST"}


def _shadow(body: dict) -> dict:
    return {entry["rule"]: entry for entry in body["metadata"]["shadow"]}


def test_post_pix_normal_payer_returns_approved_with_three_model_scores():
    """G4/ADR 0022: os 3 modelos em shadow gravam score em [0,1] sem mudar a decisão."""
    _, body = RequestGenerator.POST_pix(PayloadGenerator.pix())

    shadow = _shadow(body)
    assert body["status"] == "approved"
    assert body["metadata"]["reasons"] == []
    assert set(shadow) == MODEL_RULES
    for entry in shadow.values():
        assert 0 <= entry["signals"]["score"] <= 1
        assert 0 <= entry["signals"]["threshold"] <= 1
        assert entry["would_decide"] in ("approved", "two_factor_required")


def test_post_pix_mule_scenario_returns_rejected_and_models_never_reject():
    """G4/ADR 0022: a mula segue reprovada pelas regras; modelo só sugere 2FA, nunca rejected."""
    mule = RandomGenerator.generate_cpf()
    opening = shifted(DEFAULT_AT, days=-2)
    for minutes in range(1, 5):
        RequestGenerator.POST_pix(PayloadGenerator.pix(
            destination_document=mule, destination_opening_date=opening, amount=20000,
            at=shifted(DEFAULT_AT, minutes=-minutes),
        ))

    _, body = RequestGenerator.POST_pix(PayloadGenerator.pix(
        destination_document=mule, destination_opening_date=opening, amount=20000
    ))

    assert body["status"] == "rejected"
    assert "TYPOLOGY_MULE" in [r["rule"] for r in body["metadata"]["reasons"]]
    assert not any(r["rule"].startswith("MODEL_") for r in body["metadata"]["reasons"])
    assert set(_shadow(body)) == MODEL_RULES
    assert all(e["would_decide"] != "rejected" for e in body["metadata"]["shadow"])
