from tests.utils import DEFAULT_AT, PayloadGenerator, RequestGenerator, shifted

ABOVE_SINGLE_LIMIT = 5000001


class TestDecision:
    def test_post_two_two_factor_rules_returns_two_factor_required(self):
        """ADR 0006: dois disparos 2FA resultam em 2FA com dois motivos."""
        _, body = RequestGenerator.POST_pix(PayloadGenerator.pix(
            amount=ABOVE_SINGLE_LIMIT,
            destination_opening_date=shifted(DEFAULT_AT, days=-7),
        ))

        assert body["status"] == "two_factor_required"
        assert {reason["rule"] for reason in body["metadata"]["reasons"]} == {
            "COUNTERPARTY_NEW_ACCOUNT",
            "LIMIT_SINGLE_AMOUNT",
        }

    def test_post_two_factor_and_rejected_rules_returns_rejected_ordered(self):
        """ADR 0006: a pior decisão vence e os motivos saem do mais grave ao menos."""
        _, body = RequestGenerator.POST_pix(PayloadGenerator.pix(
            amount=ABOVE_SINGLE_LIMIT,
            destination_opening_date=shifted(DEFAULT_AT, days=-1),
        ))

        assert body["status"] == "rejected"
        assert [(r["rule"], r["decision"]) for r in body["metadata"]["reasons"]] == [
            ("COUNTERPARTY_NEW_ACCOUNT", "rejected"),
            ("LIMIT_SINGLE_AMOUNT", "two_factor_required"),
        ]

    def test_post_metadata_returns_version_and_signals_of_fired_rules(self):
        """ADR 0021: metadata traz rule_set_version e sinais só das regras disparadas."""
        _, body = RequestGenerator.POST_pix(PayloadGenerator.pix(
            destination_opening_date=shifted(DEFAULT_AT, days=-7),
        ))

        assert body["metadata"]["rule_set_version"]
        assert body["metadata"]["signals"] == {"COUNTERPARTY_NEW_ACCOUNT": {"destination_age_days": 7}}
        assert body["metadata"]["reasons"][0]["reason"] == "Conta de destino aberta há 7 dias."

    def test_get_after_post_returns_same_body_with_reasons(self):
        """Enunciado 3.3: o GET devolve a análise gravada, motivos inclusos."""
        payload = PayloadGenerator.pix(destination_opening_date=shifted(DEFAULT_AT, days=-7))
        _, posted = RequestGenerator.POST_pix(payload)

        status, fetched = RequestGenerator.GET_pix(payload["id"])

        assert status == 200
        assert fetched == posted
        assert fetched["metadata"]["reasons"]
