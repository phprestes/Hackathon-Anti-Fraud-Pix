# Model results (mock: synthetic labels)

Fixed simple hyperparameters, no search. Labels come from the simulator, so these numbers prove the pipeline fits the hot path; they say nothing about real fraud. Regenerate with `make train-models`.

Train: 7995 Pix (201 fraud); fit slice 5996, validation slice 1999 (39 fraud), split by time. Thresholds: {"logreg": 0.5782, "lightgbm": 0.0071, "iforest": 0.5895}.

Training time: logreg 0.35 s, lightgbm 0.14 s, iforest 0.14 s.

## Test (seed 7, default frauds)

| model | AUC | precision | recall | Brier |
|---|---|---|---|---|
| logreg | 0.978 | 0.932 | 0.683 | 0.0081 |
| lightgbm | 0.990 | 0.950 | 0.839 | 0.0055 |
| iforest | 0.866 | 0.397 | 0.256 | n/a (score is not a probability) |

Fraud captured per typology (Pix barred / Pix, sequences with at least one Pix barred):

| typology | logreg | lightgbm | iforest | rules | rules+lightgbm |
|---|---|---|---|---|---|
| account_takeover | 31.2% (3/7 seq) | 93.8% (7/7 seq) | 43.8% (4/7 seq) | 100.0% (7/7 seq) | 100.0% (7/7 seq) |
| device_farm | 77.8% (6/6 seq) | 70.4% (6/6 seq) | 0.0% (0/6 seq) | 70.4% (6/6 seq) | 92.6% (6/6 seq) |
| mule | 94.7% (7/7 seq) | 100.0% (7/7 seq) | 0.0% (0/7 seq) | 100.0% (7/7 seq) | 100.0% (7/7 seq) |
| night_kidnapping | 66.7% (4/6 seq) | 83.3% (5/6 seq) | 0.0% (0/6 seq) | 100.0% (6/6 seq) | 100.0% (6/6 seq) |
| splitting | 39.3% (4/6 seq) | 66.1% (5/6 seq) | 69.6% (6/6 seq) | 53.6% (5/6 seq) | 69.6% (5/6 seq) |

Rules x models (barred = status other than approved for rules, score >= threshold for models):

| decider | frauds barred | friction on legitimate |
|---|---|---|
| logreg | 68.3% | 0.1% |
| lightgbm | 83.9% | 0.1% |
| iforest | 25.6% | 1.0% |
| rules | 81.1% | 3.3% |
| rules+lightgbm | 89.4% | 3.4% |

## Perturbed test (seed 7, perturbed fraud ranges)

| model | AUC | precision | recall | Brier |
|---|---|---|---|---|
| logreg | 0.969 | 0.925 | 0.676 | 0.0088 |
| lightgbm | 0.985 | 0.951 | 0.857 | 0.0092 |
| iforest | 0.904 | 0.470 | 0.341 | n/a (score is not a probability) |

Fraud captured per typology (Pix barred / Pix, sequences with at least one Pix barred):

| typology | logreg | lightgbm | iforest | rules | rules+lightgbm |
|---|---|---|---|---|---|
| account_takeover | 76.0% (8/8 seq) | 100.0% (8/8 seq) | 48.0% (6/8 seq) | 100.0% (8/8 seq) | 100.0% (8/8 seq) |
| device_farm | 68.0% (7/7 seq) | 52.0% (6/7 seq) | 0.0% (0/7 seq) | 68.0% (7/7 seq) | 68.0% (7/7 seq) |
| mule | 81.8% (8/8 seq) | 97.7% (8/8 seq) | 0.0% (0/8 seq) | 100.0% (8/8 seq) | 100.0% (8/8 seq) |
| night_kidnapping | 57.1% (4/7 seq) | 100.0% (7/7 seq) | 14.3% (1/7 seq) | 100.0% (7/7 seq) | 100.0% (7/7 seq) |
| splitting | 58.0% (7/8 seq) | 84.0% (8/8 seq) | 60.5% (8/8 seq) | 85.2% (8/8 seq) | 91.4% (8/8 seq) |

Rules x models (barred = status other than approved for rules, score >= threshold for models):

| decider | frauds barred | friction on legitimate |
|---|---|---|
| logreg | 67.6% | 0.1% |
| lightgbm | 85.7% | 0.1% |
| iforest | 34.1% | 1.0% |
| rules | 89.0% | 3.5% |
| rules+lightgbm | 91.8% | 3.5% |
