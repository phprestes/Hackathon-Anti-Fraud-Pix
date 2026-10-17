from constants import (
    RULE_AMOUNT_DAILY_SUM_CENTS,
    RULE_AMOUNT_DAILY_SUM_PJ_CENTS,
    RULE_DESTINATION_CRITICAL_AGE_DAYS,
    RULE_DESTINATION_MAX_SOURCES_1H,
    RULE_DESTINATION_MIN_AGE_DAYS,
    RULE_DESTINATION_NEW_MAX_AMOUNT_CENTS,
    RULE_DEVICE_MAX_SOURCES_24H,
    RULE_FIRST_TIME_MIN_AMOUNT_CENTS,
    RULE_LIMIT_NIGHT_AMOUNT_CENTS,
    RULE_LIMIT_SINGLE_AMOUNT_CENTS,
    RULE_LIMIT_SINGLE_AMOUNT_PJ_CENTS,
    RULE_NEW_DEVICE_MIN_AMOUNT_CENTS,
    RULE_NIGHT_END_HOUR,
    RULE_NIGHT_START_HOUR,
    RULE_SOURCE_MIN_AGE_DAYS,
    RULE_SOURCE_NEW_MAX_AMOUNT_CENTS,
    RULE_VELOCITY_2FA_COUNT,
    RULE_VELOCITY_REJECT_COUNT,
    RULE_VELOCITY_WINDOW_MINUTES,
)
from rules.amount_source_daily_sum_rule import AmountSourceDailySumRule
from rules.counterparty_fan_in_rule import CounterpartyFanInRule
from rules.counterparty_first_time_high_rule import CounterpartyFirstTimeHighRule
from rules.counterparty_new_account_rule import CounterpartyNewAccountRule
from rules.limit_night_amount_rule import LimitNightAmountRule
from rules.limit_single_amount_rule import LimitSingleAmountRule
from rules.profile_new_device_rule import ProfileNewDeviceRule
from rules.profile_new_source_account_rule import ProfileNewSourceAccountRule
from rules.velocity_device_sources_rule import VelocityDeviceSourcesRule
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
    CounterpartyNewAccountRule(
        RULE_DESTINATION_MIN_AGE_DAYS,
        RULE_DESTINATION_CRITICAL_AGE_DAYS,
        RULE_DESTINATION_NEW_MAX_AMOUNT_CENTS,
    ),
    CounterpartyFanInRule(RULE_DESTINATION_MAX_SOURCES_1H),
    CounterpartyFirstTimeHighRule(RULE_FIRST_TIME_MIN_AMOUNT_CENTS),
]
