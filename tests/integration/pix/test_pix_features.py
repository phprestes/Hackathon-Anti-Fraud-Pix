from tests.utils import PayloadGenerator, RequestGenerator

EXPECTED_FEATURE_NAMES = [
    "amount",
    "log_amount",
    "local_hour",
    "weekday",
    "source_age_days",
    "destination_age_days",
    "is_self_transfer",
    "is_legal_entity_source",
    "has_geolocation",
    "source_attempts_last_velocity_window",
    "source_sum_last_24h_cents",
    "source_history_size",
    "device_seen_for_source",
    "destination_seen_for_source",
    "device_distinct_other_sources_last_24h",
    "destination_distinct_other_sources_last_1h",
    "source_attempts_poisson_window",
    "source_attempts_poisson_lookback",
    "source_new_destinations_last_24h",
    "destination_used_before",
    "source_small_attempts_last_24h",
    "destination_rejected_by_others_last_window",
    "history_30d_size",
    "history_30d_median_cents",
    "amount_robust_z",
    "hours_since_first_seen",
    "km_since_last_geolocation",
    "speed_kmh_since_last_geolocation",
    "poisson_tail_log10",
]


def test_post_pix_any_payload_returns_shadow_list_empty():
    """G1: sem regra shadow ativa, metadata.shadow existe e é lista vazia."""
    _, body = RequestGenerator.POST_pix(PayloadGenerator.pix())

    assert body["metadata"]["shadow"] == []


def test_post_pix_any_payload_returns_exact_feature_vector():
    """G1: metadata.features tem exatamente FEATURE_NAMES, na ordem, só números."""
    _, body = RequestGenerator.POST_pix(PayloadGenerator.pix())

    features = body["metadata"]["features"]
    assert list(features) == EXPECTED_FEATURE_NAMES
    assert all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in features.values())


def test_post_pix_first_transaction_returns_sentinel_features():
    """G1: sem histórico, sentinelas -1 e zeros."""
    payload = PayloadGenerator.pix(amount=15000)
    _, body = RequestGenerator.POST_pix(payload)

    features = body["metadata"]["features"]
    assert features["amount"] == 15000
    assert features["local_hour"] == 14
    assert features["hours_since_first_seen"] == -1
    assert features["km_since_last_geolocation"] == -1
    assert features["has_geolocation"] == 0
    assert features["amount_robust_z"] == 0
    assert features["poisson_tail_log10"] == 0
    assert features["history_30d_size"] == 0


def test_get_pix_after_post_returns_same_features():
    """G1: GET devolve a análise gravada, features incluídas."""
    payload = PayloadGenerator.pix()
    _, posted = RequestGenerator.POST_pix(payload)

    _, fetched = RequestGenerator.GET_pix(payload["id"])

    assert fetched == posted
    assert "features" in fetched["metadata"]
