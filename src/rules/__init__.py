from constants import (
    RULE_AMOUNT_DAILY_SUM_CENTS,
    RULE_AMOUNT_DAILY_SUM_PJ_CENTS,
    RULE_DESTINATION_CRITICAL_AGE_DAYS,
    RULE_DESTINATION_MIN_AGE_DAYS,
    RULE_DESTINATION_NEW_MAX_AMOUNT_CENTS,
    RULE_VELOCITY_2FA_COUNT,
    RULE_VELOCITY_REJECT_COUNT,
    RULE_VELOCITY_WINDOW_MINUTES,
)
from rules.amount_source_daily_sum_rule import AmountSourceDailySumRule
from rules.counterparty_new_account_rule import CounterpartyNewAccountRule
from rules.velocity_source_count_rule import VelocitySourceCountRule

# Order here breaks ties between reasons of equal severity.
ACTIVE_RULES = [
    CounterpartyNewAccountRule(
        RULE_DESTINATION_MIN_AGE_DAYS,
        RULE_DESTINATION_CRITICAL_AGE_DAYS,
        RULE_DESTINATION_NEW_MAX_AMOUNT_CENTS,
    ),
    VelocitySourceCountRule(RULE_VELOCITY_WINDOW_MINUTES, RULE_VELOCITY_2FA_COUNT, RULE_VELOCITY_REJECT_COUNT),
    AmountSourceDailySumRule(RULE_AMOUNT_DAILY_SUM_CENTS, RULE_AMOUNT_DAILY_SUM_PJ_CENTS),
]
