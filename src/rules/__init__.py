from constants import (
    RULE_ATO_Z_TENTHS,
    RULE_AMOUNT_DAILY_SUM_CENTS,
    RULE_AMOUNT_DAILY_SUM_PJ_CENTS,
    RULE_DESTINATION_CRITICAL_AGE_DAYS,
    RULE_DESTINATION_MAX_SOURCES_1H,
    RULE_DESTINATION_MIN_AGE_DAYS,
    RULE_DESTINATION_NEW_MAX_AMOUNT_CENTS,
    RULE_DEVICE_MAX_SOURCES_24H,
    RULE_FLAGGED_WINDOW_DAYS,
    RULE_FIRST_TIME_MIN_AMOUNT_CENTS,
    RULE_GEO_MAX_SPEED_KMH,
    RULE_GEO_MIN_DISTANCE_KM,
    RULE_LIMIT_NIGHT_AMOUNT_CENTS,
    RULE_LIMIT_SINGLE_AMOUNT_CENTS,
    RULE_LIMIT_SINGLE_AMOUNT_PJ_CENTS,
    RULE_MULE_MIN_SOURCES_1H,
    RULE_NEW_DEVICE_MIN_AMOUNT_CENTS,
    RULE_NIGHT_END_HOUR,
    RULE_NIGHT_START_HOUR,
    RULE_POISSON_LOOKBACK_DAYS,
    RULE_POISSON_MIN_EXPOSURE_HOURS,
    RULE_POISSON_PRIOR_RATE_HOURS,
    RULE_POISSON_PRIOR_SHAPE,
    RULE_POISSON_TAIL_PPM,
    RULE_POISSON_WINDOW_MINUTES,
    RULE_PROFILE_MIN_HISTORY,
    RULE_PROFILE_MIN_SCALE_PERCENT,
    RULE_PROFILE_Z_2FA_TENTHS,
    RULE_SOURCE_MIN_AGE_DAYS,
    RULE_SPLITTING_MAX_AMOUNT_CENTS,
    RULE_SPLITTING_MIN_COUNT,
    RULE_SPLITTING_MIN_DESTINATIONS,
    RULE_SPLITTING_MIN_SUM_CENTS,
    RULE_SOURCE_NEW_MAX_AMOUNT_CENTS,
    RULE_VELOCITY_2FA_COUNT,
    RULE_VELOCITY_REJECT_COUNT,
    RULE_VELOCITY_WINDOW_MINUTES,
)
from rules.amount_source_daily_sum_rule import AmountSourceDailySumRule
from rules.counterparty_fan_in_rule import CounterpartyFanInRule
from rules.counterparty_flagged_rule import CounterpartyFlaggedRule
from rules.counterparty_first_time_high_rule import CounterpartyFirstTimeHighRule
from rules.counterparty_new_account_rule import CounterpartyNewAccountRule
from rules.limit_night_amount_rule import LimitNightAmountRule
from rules.limit_single_amount_rule import LimitSingleAmountRule
from rules.profile_amount_robust_z_rule import ProfileAmountRobustZRule
from rules.profile_geo_velocity_rule import ProfileGeoVelocityRule
from rules.profile_new_device_rule import ProfileNewDeviceRule
from rules.profile_new_source_account_rule import ProfileNewSourceAccountRule
from rules.typology_account_takeover_rule import TypologyAccountTakeoverRule
from rules.typology_mule_rule import TypologyMuleRule
from rules.typology_splitting_rule import TypologySplittingRule
from rules.velocity_device_sources_rule import VelocityDeviceSourcesRule
from rules.velocity_poisson_gamma_rule import VelocityPoissonGammaRule
from rules.velocity_source_count_rule import VelocitySourceCountRule

# Order here breaks ties between reasons of equal severity.
ACTIVE_RULES = [
    LimitNightAmountRule(RULE_NIGHT_START_HOUR, RULE_NIGHT_END_HOUR, RULE_LIMIT_NIGHT_AMOUNT_CENTS),
    LimitSingleAmountRule(RULE_LIMIT_SINGLE_AMOUNT_CENTS, RULE_LIMIT_SINGLE_AMOUNT_PJ_CENTS),
    VelocitySourceCountRule(RULE_VELOCITY_WINDOW_MINUTES, RULE_VELOCITY_2FA_COUNT, RULE_VELOCITY_REJECT_COUNT),
    VelocityDeviceSourcesRule(RULE_DEVICE_MAX_SOURCES_24H),
    AmountSourceDailySumRule(RULE_AMOUNT_DAILY_SUM_CENTS, RULE_AMOUNT_DAILY_SUM_PJ_CENTS),
    ProfileNewDeviceRule(RULE_NEW_DEVICE_MIN_AMOUNT_CENTS),
    ProfileNewSourceAccountRule(RULE_SOURCE_MIN_AGE_DAYS, RULE_SOURCE_NEW_MAX_AMOUNT_CENTS),
    ProfileAmountRobustZRule(
        RULE_PROFILE_MIN_HISTORY, RULE_PROFILE_MIN_SCALE_PERCENT / 100, RULE_PROFILE_Z_2FA_TENTHS / 10
    ),
    ProfileGeoVelocityRule(RULE_GEO_MIN_DISTANCE_KM, RULE_GEO_MAX_SPEED_KMH),
    VelocityPoissonGammaRule(
        RULE_POISSON_WINDOW_MINUTES,
        RULE_POISSON_LOOKBACK_DAYS,
        RULE_POISSON_PRIOR_SHAPE,
        RULE_POISSON_PRIOR_RATE_HOURS,
        RULE_POISSON_TAIL_PPM / 1_000_000,
        RULE_POISSON_MIN_EXPOSURE_HOURS,
    ),
    CounterpartyNewAccountRule(
        RULE_DESTINATION_MIN_AGE_DAYS,
        RULE_DESTINATION_CRITICAL_AGE_DAYS,
        RULE_DESTINATION_NEW_MAX_AMOUNT_CENTS,
    ),
    CounterpartyFanInRule(RULE_DESTINATION_MAX_SOURCES_1H),
    CounterpartyFirstTimeHighRule(RULE_FIRST_TIME_MIN_AMOUNT_CENTS),
    CounterpartyFlaggedRule(RULE_FLAGGED_WINDOW_DAYS),
    TypologyAccountTakeoverRule(
        RULE_GEO_MIN_DISTANCE_KM,
        RULE_GEO_MAX_SPEED_KMH,
        RULE_PROFILE_MIN_HISTORY,
        RULE_PROFILE_MIN_SCALE_PERCENT / 100,
        RULE_ATO_Z_TENTHS / 10,
    ),
    TypologyMuleRule(RULE_DESTINATION_MIN_AGE_DAYS, RULE_MULE_MIN_SOURCES_1H),
    TypologySplittingRule(
        RULE_SPLITTING_MAX_AMOUNT_CENTS,
        RULE_SPLITTING_MIN_COUNT,
        RULE_SPLITTING_MIN_DESTINATIONS,
        RULE_SPLITTING_MIN_SUM_CENTS,
        RULE_SPLITTING_MIN_SUM_CENTS * 5,
    ),
]
