# Model results (mock: synthetic labels)

**Fixture do CI, sem valor estatístico.** Rótulos e gerador são nossos; os resultados com valor estatístico estão em docs/05-motor/validacao-pixsim.md.

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

<!-- pixsim_models:start -->
## Modelos treinados no PixSim

Treino no mundo A do PixSim (seed 20260910), teste no mundo B (seed 20261017) e no nosso simulador (seed 7). Mesmos hiperparâmetros fixos de `scripts/models/train_models.py`; fatia de ajuste = primeiros 75% do mundo A no tempo, validação = 25% finais (limiar por F1 máximo; Platt na validação). Linhas: 95173 de ajuste, 31725 de validação. Limiares: {"logreg": 0.1933, "lightgbm": 0.8558, "iforest": 0.6035}.

Positivo = Pix de vítima (`victim_to_mule`); legítimo = tráfego legítimo. A dispersão (`mule_forward`, `cash_out`) e a semente do Pix errado ficam fora do treino e da avaliação: o banco só a veria se a mula fosse cliente, e misturá-la como positivo ensinaria o modelo a pontuar o comportamento da mula, não o da vítima. Burn-in só alimenta o histórico. Custos e precisão usam o peso de importância do PixSim; AUC, recall e P@k são brutos.

| Conjunto | Pix avaliados | Legítimos | Fraude pagador→mula | Peso médio da fraude |
|---|---|---|---|---|
| PixSim A (treino) | 126898 | 125518 | 1380 | 0,0071 |
| PixSim B (teste) | 129121 | 127683 | 1438 | 0,0072 |
| Nosso simulador (seed 7, teste) | 7100 | 6920 | 180 | 1,0000 |

**AUC**

| decisor | nosso → PixSim B | PixSim A → PixSim B | PixSim A → nosso | nosso → nosso (referência) |
|---|---|---|---|---|
| logreg | 0,770 | 0,990 | 0,919 | 0,978 |
| lightgbm | 0,580 | 0,989 | 0,775 | 0,990 |
| iforest | 0,788 | 0,850 | 0,911 | 0,866 |
| rules | 0,740 | 0,740 | 0,965 | 0,965 |
| rules+lightgbm | 0,718 | 0,987 | 0,958 | 0,992 |

**Recall no limiar**

| decisor | nosso → PixSim B | PixSim A → PixSim B | PixSim A → nosso | nosso → nosso (referência) |
|---|---|---|---|---|
| logreg | 8,0% | 64,7% | 68,9% | 68,3% |
| lightgbm | 27,5% | 73,0% | 22,2% | 83,9% |
| iforest | 38,9% | 8,0% | 54,4% | 25,6% |
| rules | 51,1% | 51,1% | 96,7% | 96,7% |
| rules+lightgbm | 60,2% | 80,9% | 97,8% | 98,3% |

**Precisão ponderada**

| decisor | nosso → PixSim B | PixSim A → PixSim B | PixSim A → nosso | nosso → nosso (referência) |
|---|---|---|---|---|
| logreg | 0,1% | 0,7% | 30,9% | 93,2% |
| lightgbm | 0,0% | 0,6% | 13,1% | 95,0% |
| iforest | 0,0% | 0,0% | 28,5% | 39,7% |
| rules | 0,1% | 0,1% | 27,4% | 27,4% |
| rules+lightgbm | 0,1% | 0,2% | 24,0% | 27,5% |

**Fricção em legítimos**

| decisor | nosso → PixSim B | PixSim A → PixSim B | PixSim A → nosso | nosso → nosso (referência) |
|---|---|---|---|---|
| logreg | 0,8% | 0,8% | 4,0% | 0,1% |
| lightgbm | 7,3% | 1,0% | 3,8% | 0,1% |
| iforest | 8,9% | 1,4% | 3,6% | 1,0% |
| rules | 3,1% | 3,1% | 6,7% | 6,7% |
| rules+lightgbm | 9,5% | 3,6% | 8,0% | 6,7% |

**Custo ponderado por 1.000 Pix**

| decisor | nosso → PixSim B | PixSim A → PixSim B | PixSim A → nosso | nosso → nosso (referência) |
|---|---|---|---|---|
| logreg | R$ 155,96 | R$ 53,39 | R$ 23.441,61 | R$ 29.799,46 |
| lightgbm | R$ 254,61 | R$ 59,12 | R$ 44.766,59 | R$ 10.228,05 |
| iforest | R$ 253,14 | R$ 157,88 | R$ 19.900,85 | R$ 33.790,64 |
| rules | R$ 118,82 | R$ 118,82 | R$ 3.851,57 | R$ 3.851,57 |
| rules+lightgbm | R$ 237,81 | R$ 99,42 | R$ 3.644,71 | R$ 3.497,64 |

**P@k diário** (fraude superamostrada: a precisão do PixSim é inflada na proporção do peso)

| cenário | decisor | P@5 | P@10 | P@25 | P@50 |
|---|---|---|---|---|---|
| nosso → PixSim B | logreg | 11,3% | 12,3% | 11,7% | 9,3% |
| nosso → PixSim B | lightgbm | 27,3% | 16,0% | 7,2% | 3,7% |
| nosso → PixSim B | iforest | 6,0% | 6,7% | 9,9% | 8,0% |
| nosso → PixSim B | rules | 15,3% | 13,3% | 21,2% | 21,3% |
| nosso → PixSim B | rules+lightgbm | 34,7% | 19,7% | 8,9% | 4,6% |
| PixSim A → PixSim B | logreg | 81,3% | 78,3% | 65,6% | 52,5% |
| PixSim A → PixSim B | lightgbm | 98,0% | 96,3% | 77,5% | 58,1% |
| PixSim A → PixSim B | iforest | 2,0% | 3,0% | 5,3% | 5,8% |
| PixSim A → PixSim B | rules | 15,3% | 13,3% | 21,2% | 21,3% |
| PixSim A → PixSim B | rules+lightgbm | 96,7% | 96,0% | 77,2% | 57,9% |
| PixSim A → nosso | logreg | 52,9% | 49,3% | 34,6% | 20,6% |
| PixSim A → nosso | lightgbm | 25,7% | 19,3% | 11,4% | 10,4% |
| PixSim A → nosso | iforest | 54,3% | 44,3% | 28,9% | 19,0% |
| PixSim A → nosso | rules | 61,4% | 48,6% | 30,6% | 22,4% |
| PixSim A → nosso | rules+lightgbm | 55,7% | 48,6% | 32,0% | 19,7% |

**Captura por tipologia do PixSim em PixSim B** (Pix de vítima acima do limiar do modelo, ou fora de `approved` nas regras)

| tipologia | logreg (nosso) | lightgbm (nosso) | iforest (nosso) | logreg (PixSim A) | lightgbm (PixSim A) | iforest (PixSim A) | regras |
|---|---|---|---|---|---|---|---|
| account_takeover | 11,5% | 45,5% | 63,1% | 91,9% | 84,6% | 9,5% | 71,8% |
| pix_errado | 3,7% | 1,9% | 14,8% | 16,7% | 27,8% | 3,7% | 9,3% |
| qr_substitution | 2,5% | 10,0% | 15,0% | 28,7% | 38,8% | 1,2% | 30,0% |
| social_engineering | 7,4% | 23,6% | 33,1% | 60,3% | 74,1% | 8,2% | 47,5% |

**Captura por tipologia do nosso simulador (modelos do PixSim A)**

| tipologia | logreg | lightgbm | iforest | rules | rules+lightgbm |
|---|---|---|---|---|---|
| account_takeover | 43,8% | 25,0% | 50,0% | 100,0% | 100,0% |
| device_farm | 40,7% | 7,4% | 0,0% | 96,3% | 96,3% |
| mule | 77,3% | 0,0% | 50,7% | 100,0% | 100,0% |
| night_kidnapping | 66,7% | 0,0% | 33,3% | 100,0% | 100,0% |
| splitting | 78,6% | 60,7% | 89,3% | 91,1% | 94,6% |

<!-- pixsim_models:end -->

<!-- graphsage_pixsim:start -->
## GraphSAGE treinado no PixSim

Grafo pagador→destino em janelas de 72 h (passo de 24 h) só do período avaliado; o burn-in alimenta apenas o primeiro pagamento das arestas. Rótulo de nó = `is_mule` da conta no PixSim (rótulo do simulador de terceiros, não o nosso); mulas: 1366 no mundo A, 1321 no B. Arquitetura e taxa de aprendizado do GraphSAGE do nosso simulador; épocas e lote mudados (200 e 64 no nosso) para caber no prazo, o grafo do PixSim tem muito mais nós alvo (100 épocas, lr 0.01, lote 256, oculta 16); limiar 0.73864 (F1 máximo nos nós de treino, dentro da amostra). Treino em 404 s. Só entram como nó alvo as contas que recebem ao menos um Pix na janela.

| modelo | avaliado em | nós alvo | nós mula | AUC | precisão | recall | fricção em destinos legítimos |
|---|---|---|---|---|---|---|---|
| treinado no PixSim A | treino (dentro da amostra) | 80709 | 9143 | 0,912 | 0,777 | 0,754 | 2,8% |
| treinado no PixSim A | PixSim B | 82682 | 8688 | 0,919 | 0,786 | 0,787 | 2,5% |
| treinado no nosso simulador | PixSim B | 82682 | 8688 | 0,518 | 0,241 | 0,005 | 0,2% |

<!-- graphsage_pixsim:end -->
