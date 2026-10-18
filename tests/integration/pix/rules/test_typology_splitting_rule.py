from tests.utils import DEFAULT_AT, PayloadGenerator, RandomGenerator, RequestGenerator, shifted


def _send(payer: str, destination: str = None, amount: int = 190000, hours_ago: int = 0) -> dict:
    _, body = RequestGenerator.POST_pix(PayloadGenerator.pix(
        payer_document=payer,
        destination_document=destination,
        amount=amount,
        at=shifted(DEFAULT_AT, hours=-hours_ago),
    ))
    return body


def _rules(body: dict) -> list:
    return [reason["rule"] for reason in body["metadata"]["reasons"]]


class TestTypologySplittingRule:
    def test_post_sixth_small_pix_to_four_destinations_returns_rejected(self):
        """TYPOLOGY_SPLITTING: 8 Pix pequenos para 4+ destinos somando acima do piso reprova."""
        payer = RandomGenerator.generate_cpf()
        for hours_ago in range(7, 0, -1):
            _send(payer, hours_ago=hours_ago)

        body = _send(payer)

        assert body["status"] == "rejected"
        assert "TYPOLOGY_SPLITTING" in _rules(body)
        signals = body["metadata"]["signals"]["TYPOLOGY_SPLITTING"]
        assert signals["small_count_24h"] == 8
        assert signals["sum_24h_cents"] == 1520000
        reason = next(r for r in body["metadata"]["reasons"] if r["rule"] == "TYPOLOGY_SPLITTING")
        assert reason["reason"] == "Padrão de fracionamento: 8 Pix pequenos para 8 destinos somando R$ 15.200,00 em 24 h."

    def test_post_fifth_small_pix_returns_two_factor_required(self):
        """TYPOLOGY_SPLITTING: 5 Pix pequenos (mais um grande) acima do teto não dispara."""
        payer = RandomGenerator.generate_cpf()
        _send(payer, amount=3700000, hours_ago=5)
        for hours_ago in range(4, 0, -1):
            _send(payer, hours_ago=hours_ago)

        body = _send(payer)

        assert "TYPOLOGY_SPLITTING" not in _rules(body)
        assert "AMOUNT_SOURCE_DAILY_SUM" in _rules(body)

    def test_post_six_small_pix_to_three_destinations_returns_two_factor_required(self):
        """TYPOLOGY_SPLITTING: 8 Pix (soma acima do piso) para só 3 destinos não dispara."""
        payer = RandomGenerator.generate_cpf()
        destinations = [RandomGenerator.generate_cpf() for _ in range(2)]
        for hours_ago in range(7, 0, -1):
            _send(payer, destination=destinations[hours_ago % 2], hours_ago=hours_ago)

        body = _send(payer)

        assert "TYPOLOGY_SPLITTING" not in _rules(body)

    def test_post_six_small_pix_below_daily_ceiling_returns_approved(self):
        """TYPOLOGY_SPLITTING: 6 Pix pequenos para 6 destinos abaixo do teto não dispara."""
        payer = RandomGenerator.generate_cpf()
        for hours_ago in range(5, 0, -1):
            _send(payer, amount=10000, hours_ago=hours_ago)

        body = _send(payer, amount=10000)

        assert "TYPOLOGY_SPLITTING" not in _rules(body)

    def test_post_six_small_pix_to_four_known_destinations_returns_no_splitting(self):
        """TYPOLOGY_SPLITTING: destinos já conhecidos antes das 24 h não contam como destinos novos."""
        payer = RandomGenerator.generate_cpf()
        destinations = [RandomGenerator.generate_cpf() for _ in range(4)]
        for destination in destinations:
            _send(payer, destination=destination, amount=10000, hours_ago=72)
        for hours_ago in range(7, 0, -1):
            _send(payer, destination=destinations[hours_ago % 4], hours_ago=hours_ago)

        body = _send(payer, destination=destinations[0])

        assert "TYPOLOGY_SPLITTING" not in _rules(body)

    def test_post_six_small_pix_summing_exactly_threshold_returns_no_splitting(self):
        """TYPOLOGY_SPLITTING: soma de 24 h igual ao piso (R$ 15.000,00) não dispara."""
        payer = RandomGenerator.generate_cpf()
        for hours_ago in range(7, 0, -1):
            _send(payer, amount=200000, hours_ago=hours_ago)

        body = _send(payer, amount=100000)

        assert "TYPOLOGY_SPLITTING" not in _rules(body)

    def test_post_six_small_pix_summing_just_above_threshold_returns_rejected(self):
        """TYPOLOGY_SPLITTING: soma de 24 h um centavo acima do piso dispara."""
        payer = RandomGenerator.generate_cpf()
        for hours_ago in range(7, 0, -1):
            _send(payer, amount=200000, hours_ago=hours_ago)

        body = _send(payer, amount=100001)

        assert body["status"] == "rejected"
        assert "TYPOLOGY_SPLITTING" in _rules(body)
