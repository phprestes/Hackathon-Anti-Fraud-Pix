from types import SimpleNamespace

import constants
from rules.core.base_rule import BaseRule
from rules.counterparty.counterparty_fan_in_rule import CounterpartyFanInRule
from rules.counterparty.counterparty_first_time_high_rule import CounterpartyFirstTimeHighRule
from rules.counterparty.counterparty_graph_risk_rule import CounterpartyGraphRiskRule
from rules.counterparty.counterparty_new_account_rule import CounterpartyNewAccountRule
from rules.limit.limit_night_amount_rule import LimitNightAmountRule
from rules.limit.limit_single_amount_rule import LimitSingleAmountRule
from rules.models.model_score_shadow_rule import load_score_model_rules
from rules.models.model_shadow_rule import load_model_rules
from rules.profile.profile_amount_robust_z_rule import ProfileAmountRobustZRule
from rules.profile.profile_geo_velocity_rule import ProfileGeoVelocityRule
from rules.profile.profile_new_device_rule import ProfileNewDeviceRule
from rules.profile.profile_new_source_account_rule import ProfileNewSourceAccountRule
from rules.typology.typology_account_takeover_rule import TypologyAccountTakeoverRule
from rules.typology.typology_mule_rule import TypologyMuleRule
from rules.velocity.velocity_device_sources_rule import VelocityDeviceSourcesRule
from rules.velocity.velocity_poisson_gamma_rule import VelocityPoissonGammaRule
from rules.velocity.velocity_source_count_rule import VelocitySourceCountRule

NON_NUMERIC = {"RULE_SET_VERSION", "RULE_MODEL_DIR"}
PARAMETERS = {
    name: getattr(constants, name) for name in dir(constants) if name.startswith("RULE_") and name not in NON_NUMERIC
}


def build_rules(overrides: dict[str, int] | None = None) -> list[BaseRule]:
    # Order here breaks ties between reasons of equal severity.
    overrides = overrides or {}
    unknown = sorted(set(overrides) - set(PARAMETERS))
    if unknown:
        raise ValueError(f"unknown rule parameters: {', '.join(unknown)}")
    p = SimpleNamespace(**{**PARAMETERS, **overrides})
    rules = [
        LimitNightAmountRule(p.RULE_NIGHT_START_HOUR, p.RULE_NIGHT_END_HOUR, p.RULE_LIMIT_NIGHT_AMOUNT_CENTS),
        LimitSingleAmountRule(p.RULE_LIMIT_SINGLE_AMOUNT_CENTS, p.RULE_LIMIT_SINGLE_AMOUNT_PJ_CENTS),
        VelocitySourceCountRule(p.RULE_VELOCITY_WINDOW_MINUTES, p.RULE_VELOCITY_2FA_COUNT, p.RULE_VELOCITY_REJECT_COUNT),
        VelocityDeviceSourcesRule(p.RULE_DEVICE_MAX_SOURCES_24H),
        ProfileNewDeviceRule(p.RULE_NEW_DEVICE_MIN_AMOUNT_CENTS),
        ProfileNewSourceAccountRule(p.RULE_SOURCE_MIN_AGE_DAYS, p.RULE_SOURCE_NEW_MAX_AMOUNT_CENTS),
        ProfileAmountRobustZRule(
            p.RULE_PROFILE_MIN_HISTORY, p.RULE_PROFILE_MIN_SCALE_PERCENT / 100, p.RULE_PROFILE_Z_2FA_TENTHS / 10
        ),
        ProfileGeoVelocityRule(p.RULE_GEO_MIN_DISTANCE_KM, p.RULE_GEO_MAX_SPEED_KMH),
        VelocityPoissonGammaRule(
            p.RULE_POISSON_WINDOW_MINUTES,
            p.RULE_POISSON_LOOKBACK_DAYS,
            p.RULE_POISSON_PRIOR_SHAPE,
            p.RULE_POISSON_PRIOR_RATE_HOURS,
            p.RULE_POISSON_TAIL_PPM / 1_000_000,
            p.RULE_POISSON_MIN_EXPOSURE_HOURS,
        ),
        CounterpartyNewAccountRule(
            p.RULE_DESTINATION_MIN_AGE_DAYS,
            p.RULE_DESTINATION_CRITICAL_AGE_DAYS,
            p.RULE_DESTINATION_NEW_MAX_AMOUNT_CENTS,
        ),
        CounterpartyFanInRule(p.RULE_DESTINATION_MAX_SOURCES_1H),
        CounterpartyFirstTimeHighRule(p.RULE_FIRST_TIME_MIN_AMOUNT_CENTS),
        CounterpartyGraphRiskRule(p.RULE_GRAPH_RISK_2FA_PERMILLE, p.RULE_GRAPH_RISK_REJECT_PERMILLE),
        TypologyAccountTakeoverRule(
            p.RULE_GEO_MIN_DISTANCE_KM,
            p.RULE_GEO_MAX_SPEED_KMH,
            p.RULE_PROFILE_MIN_HISTORY,
            p.RULE_PROFILE_MIN_SCALE_PERCENT / 100,
            p.RULE_ATO_Z_TENTHS / 10,
        ),
        TypologyMuleRule(p.RULE_DESTINATION_MIN_AGE_DAYS, p.RULE_MULE_MIN_SOURCES_1H),
    ]
    return rules + load_model_rules(constants.RULE_MODEL_DIR) + load_score_model_rules(constants.WORKER_MODEL_DIR)


ACTIVE_RULES = build_rules()
