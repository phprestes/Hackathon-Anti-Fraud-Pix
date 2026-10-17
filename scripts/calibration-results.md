# Calibration results

Simulator: `scripts/simulate.py`, seed 42, 200 payers, 14 days, 5062 Pix (4926 legitimate, 136 fraud in 22 sequences). Each experiment changes one parameter on top of the best previous configuration. Escape = fraud Pix approved.

| experiment | parameter=value | legit approved / 2FA / rejected % | fraud sequences barred | fraud escaped % (ATO / mule / splitting / night / device_farm) | P95 ms |
|---|---|---|---|---|---|
| 1 baseline (after TYPOLOGY_SPLITTING fix) | RULE_AMOUNT_DAILY_SUM_CENTS=1000000 | 89.8 / 10.0 / 0.2 | 22/22 | 0 / 0 / 21.1 / 0 / 23.8 | 56.9 |
| 2a | RULE_AMOUNT_DAILY_SUM_CENTS=2000000 | 93.9 / 6.1 / 0.0 | 22/22 | 0 / 0 / 31.6 / 0 / 23.8 | 56.3 |
| 2b | RULE_AMOUNT_DAILY_SUM_CENTS=3000000 | 94.3 / 5.7 / 0.0 | 22/22 | 0 / 0 / 31.6 / 0 / 23.8 | 56.5 |
| 3a | + RULE_POISSON_TAIL_PPM=100 | 96.2 / 3.8 / 0.0 | 22/22 | 0 / 0 / 39.5 / 0 / 23.8 | 56.0 |
| 3b | + RULE_POISSON_TAIL_PPM=10 | 97.0 / 3.0 / 0.0 | 22/22 | 0 / 0 / 57.9 / 0 / 23.8 | 55.9 |
| 4 | RULE_PROFILE_Z_2FA_TENTHS=35/45 | not run: 3a already meets the 2FA <= 5% goal | - | - | - |
| 5 splitting decoupled (RULE_SPLITTING_MIN_SUM_CENTS=500000) | + TYPOLOGY_SPLITTING no longer uses the daily cap | 95.7 / 3.8 / 0.5 | 22/22 | 0 / 0 / 31.6 / 0 / 23.8 | 54.9 |
| 6 splitting floor raised | RULE_SPLITTING_MIN_SUM_CENTS=1500000 | 0.0 rejected (2 of 4926, 0.04%) | 22/22 | 0 / 0 / 34.2 / 0 / 23.8 | 54.9 |
| 6a (alternative) | RULE_SPLITTING_MIN_SUM_CENTS=1000000 | 0.2 rejected (8) | 22/22 | splitting 31.6 | 55.5 |
| 6b (alternative) | RULE_SPLITTING_MIN_DESTINATIONS=5 with sum 500000 | 0.3 rejected (16) | 22/22 | splitting 31.6 | 55.3 |

Reference before the fix (rule_set 2026.10.17-f4): 90.4 / 8.3 / 1.3 legit, 66 TYPOLOGY_SPLITTING rejections on legitimate Pix.

## Chosen configuration

Final: RULE_AMOUNT_DAILY_SUM_CENTS=3000000, RULE_POISSON_TAIL_PPM=100, RULE_SPLITTING_MIN_SUM_CENTS=1500000, rule_set 2026.10.18-calib3.
Why: legitimate rejections fall to 2 of 4926 (0.04%) and all 22 fraud sequences are still barred; ATO, mule and night escape 0, splitting escapes 34.2%, device_farm 23.8%, P95 54.9 ms.
The data is synthetic, so no further tuning: more would overfit the simulator.
