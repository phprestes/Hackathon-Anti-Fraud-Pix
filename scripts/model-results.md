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

<!-- graphsage:start -->
## GraphSAGE (cold path, numpy)

Two layers, mean aggregation over at most 10 neighbors (in and out united), hidden 16, ReLU, sigmoid; 200 epochs of mini-batch gradient descent (lr 0.01, batch 64), balanced class weights, seed 42, no search. Node label: destination of a mule, account_takeover, splitting or night_kidnapping Pix inside the window (device_farm is not a destination fraud). Windows: 72 h, stride 24 h. Threshold 0.96812 (max F1 on the training nodes). Training took 317.6 s. The window contains the fraud Pix being scored, so recall is optimistic for the hot path, which only sees the score of the previous cycle.

### Test (seed 7, default frauds)

9898 destination nodes over the 72 h windows (202 fraud destinations).

| AUC | precision | recall | friction on legitimate destinations |
|---|---|---|---|
| 1.000 | 0.913 | 0.990 | 0.2% |

Fraud destinations flagged per typology (nodes, sequences with at least one destination flagged):

| typology | nodes flagged | sequences caught |
|---|---|---|
| account_takeover | 100.0% (14/14) | 6/6 |
| mule | 100.0% (20/20) | 7/7 |
| night_kidnapping | 100.0% (16/16) | 6/6 |
| splitting | 98.7% (150/152) | 6/6 |

### Perturbed test (seed 7, perturbed fraud ranges)

9969 destination nodes over the 72 h windows (289 fraud destinations).

| AUC | precision | recall | friction on legitimate destinations |
|---|---|---|---|
| 0.999 | 0.897 | 0.969 | 0.3% |

Fraud destinations flagged per typology (nodes, sequences with at least one destination flagged):

| typology | nodes flagged | sequences caught |
|---|---|---|
| account_takeover | 100.0% (22/22) | 8/8 |
| mule | 100.0% (24/24) | 8/8 |
| night_kidnapping | 85.0% (17/20) | 7/7 |
| splitting | 97.3% (217/223) | 8/8 |

<!-- graphsage:end -->

<!-- hmm:start -->
## HMM de sequência (cold path, numpy)

Discrete HMM, 3 states, 12 symbols (value band vs the payer's own median x new destination x night), Baum-Welch with scaling, 30 iterations, seed 42, trained only on the 186 payers with no fraud Pix (log-likelihood -10804 -> -6595). Score: mean log-likelihood per symbol of the last 10 Pix mapped to [0, 1] by the empirical CDF of the legitimate windows; threshold = p99 (0.99). Training took 2.4 s.

### Test (seed 7, default frauds)

Score including the current Pix: 7100 Pix, 180 fraud.

| AUC | precision | recall | friction on legitimate Pix |
|---|---|---|---|
| 0.652 | 0.171 | 0.239 | 3.0% |

| typology | Pix flagged | sequences caught |
|---|---|---|
| account_takeover | 18.8% (3/16) | 3/7 |
| device_farm | 14.8% (4/27) | 4/6 |
| mule | 16.0% (12/75) | 5/7 |
| night_kidnapping | 0.0% (0/6) | 0/6 |
| splitting | 42.9% (24/56) | 3/6 |

Score before the current Pix (what the hot path sees): 7100 Pix, 180 fraud.

| AUC | precision | recall | friction on legitimate Pix |
|---|---|---|---|
| 0.509 | 0.120 | 0.156 | 3.0% |

| typology | Pix flagged | sequences caught |
|---|---|---|
| account_takeover | 6.2% (1/16) | 1/7 |
| device_farm | 3.7% (1/27) | 1/6 |
| mule | 5.3% (4/75) | 3/7 |
| night_kidnapping | 0.0% (0/6) | 0/6 |
| splitting | 39.3% (22/56) | 3/6 |

### Perturbed test (seed 7, perturbed fraud ranges)

Score including the current Pix: 7102 Pix, 182 fraud.

| AUC | precision | recall | friction on legitimate Pix |
|---|---|---|---|
| 0.683 | 0.169 | 0.247 | 3.2% |

| typology | Pix flagged | sequences caught |
|---|---|---|
| account_takeover | 40.0% (10/25) | 4/8 |
| device_farm | 12.0% (3/25) | 3/7 |
| mule | 9.1% (4/44) | 2/8 |
| night_kidnapping | 14.3% (1/7) | 1/7 |
| splitting | 33.3% (27/81) | 4/8 |

Score before the current Pix (what the hot path sees): 7102 Pix, 182 fraud.

| AUC | precision | recall | friction on legitimate Pix |
|---|---|---|---|
| 0.578 | 0.124 | 0.170 | 3.2% |

| typology | Pix flagged | sequences caught |
|---|---|---|
| account_takeover | 24.0% (6/25) | 4/8 |
| device_farm | 0.0% (0/25) | 0/7 |
| mule | 0.0% (0/44) | 0/8 |
| night_kidnapping | 14.3% (1/7) | 1/7 |
| splitting | 29.6% (24/81) | 4/8 |

<!-- hmm:end -->

<!-- worker-cycle:start -->
## Worker cycle (cold path)

Default scenario: scripts/out/events-default.jsonl (seed 42, 200 payers, 14 days, 5062 Pix) replayed through the API, then `python -m worker --once`. The cycle scores 619 destinations (GraphRiskJob and GraphSageJob) and 179 payers (SequenceJob) over the 72 h window.

| job | time |
|---|---|
| graph_sql (SQL CTEs) | 0.11 s |
| graphsage (SQL features + numpy forward) | 0.12 s |
| hmm (history query + forward algorithm) | 0.08 s |
| full cycle | 0.31 s |

One-off `docker compose run --rm worker ... --once` takes about 2.3 s wall clock, almost all container startup. Image sizes (docker images): api target 404 MB on disk (106 MB content), worker target 546 MB (147 MB content); numpy is the only addition.
<!-- worker-cycle:end -->
