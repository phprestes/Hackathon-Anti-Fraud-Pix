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

Treino no mundo A do PixSim (seed 20260910), teste no mundo B (seed 20261017) e no nosso simulador (seed 7). Mesmos hiperparâmetros fixos de `scripts/train_models.py`; fatia de ajuste = primeiros 75% do mundo A no tempo, validação = 25% finais (limiar por F1 máximo; Platt na validação). Linhas: 95173 de ajuste, 31725 de validação. Limiares: {"logreg": 0.1899, "lightgbm": 0.9404, "iforest": 0.5942}.

Positivo = Pix de vítima (`victim_to_mule`); legítimo = tráfego legítimo. A dispersão (`mule_forward`, `cash_out`) e a semente do Pix errado ficam fora do treino e da avaliação: o banco só a veria se a mula fosse cliente, e misturá-la como positivo ensinaria o modelo a pontuar o comportamento da mula, não o da vítima. Burn-in só alimenta o histórico. Custos e precisão usam o peso de importância do PixSim; AUC, recall e P@k são brutos.

| Conjunto | Pix avaliados | Legítimos | Fraude pagador→mula | Peso médio da fraude |
|---|---|---|---|---|
| PixSim A (treino) | 126898 | 125518 | 1380 | 0,0071 |
| PixSim B (teste) | 129121 | 127683 | 1438 | 0,0072 |
| Nosso simulador (seed 7, teste) | 7100 | 6920 | 180 | 1,0000 |

**AUC**

| decisor | nosso → PixSim B | PixSim A → PixSim B | PixSim A → nosso | nosso → nosso (referência) |
|---|---|---|---|---|
| logreg | 0,770 | 0,990 | 0,901 | 0,978 |
| lightgbm | 0,580 | 0,990 | 0,674 | 0,990 |
| iforest | 0,788 | 0,846 | 0,926 | 0,866 |
| rules | 0,673 | 0,673 | 0,896 | 0,896 |
| rules+lightgbm | 0,654 | 0,987 | 0,910 | 0,993 |

**Recall no limiar**

| decisor | nosso → PixSim B | PixSim A → PixSim B | PixSim A → nosso | nosso → nosso (referência) |
|---|---|---|---|---|
| logreg | 8,0% | 65,0% | 62,8% | 68,3% |
| lightgbm | 27,5% | 63,6% | 14,4% | 83,9% |
| iforest | 38,9% | 8,5% | 67,8% | 25,6% |
| rules | 38,4% | 38,4% | 81,1% | 81,1% |
| rules+lightgbm | 51,5% | 70,8% | 85,6% | 89,4% |

**Precisão ponderada**

| decisor | nosso → PixSim B | PixSim A → PixSim B | PixSim A → nosso | nosso → nosso (referência) |
|---|---|---|---|---|
| logreg | 0,1% | 0,6% | 28,3% | 93,2% |
| lightgbm | 0,0% | 1,1% | 14,2% | 95,0% |
| iforest | 0,0% | 0,1% | 34,0% | 39,7% |
| rules | 0,1% | 0,1% | 38,7% | 38,7% |
| rules+lightgbm | 0,0% | 0,1% | 30,6% | 40,7% |

**Fricção em legítimos**

| decisor | nosso → PixSim B | PixSim A → PixSim B | PixSim A → nosso | nosso → nosso (referência) |
|---|---|---|---|---|
| logreg | 0,8% | 0,8% | 4,1% | 0,1% |
| lightgbm | 7,3% | 0,5% | 2,3% | 0,1% |
| iforest | 8,9% | 1,4% | 3,4% | 1,0% |
| rules | 3,8% | 3,8% | 3,3% | 3,3% |
| rules+lightgbm | 10,3% | 4,1% | 5,0% | 3,4% |

**Custo ponderado por 1.000 Pix**

| decisor | nosso → PixSim B | PixSim A → PixSim B | PixSim A → nosso | nosso → nosso (referência) |
|---|---|---|---|---|
| logreg | R$ 156,12 | R$ 53,44 | R$ 24.872,61 | R$ 29.799,46 |
| lightgbm | R$ 254,61 | R$ 58,68 | R$ 50.786,57 | R$ 10.228,05 |
| iforest | R$ 253,11 | R$ 158,33 | R$ 15.725,87 | R$ 33.790,64 |
| rules | R$ 157,60 | R$ 157,60 | R$ 8.000,14 | R$ 8.000,14 |
| rules+lightgbm | R$ 274,15 | R$ 128,79 | R$ 6.720,78 | R$ 6.124,20 |

**P@k diário** (fraude superamostrada: a precisão do PixSim é inflada na proporção do peso)

| cenário | decisor | P@5 | P@10 | P@25 | P@50 |
|---|---|---|---|---|---|
| nosso → PixSim B | logreg | 11,3% | 12,3% | 11,6% | 9,3% |
| nosso → PixSim B | lightgbm | 27,3% | 16,0% | 7,2% | 3,7% |
| nosso → PixSim B | iforest | 6,0% | 6,7% | 9,9% | 8,0% |
| nosso → PixSim B | rules | 12,0% | 9,7% | 14,4% | 18,3% |
| nosso → PixSim B | rules+lightgbm | 30,0% | 18,7% | 9,1% | 4,7% |
| PixSim A → PixSim B | logreg | 88,7% | 83,3% | 67,2% | 52,6% |
| PixSim A → PixSim B | lightgbm | 100,0% | 97,7% | 80,1% | 59,7% |
| PixSim A → PixSim B | iforest | 2,7% | 3,0% | 5,6% | 6,3% |
| PixSim A → PixSim B | rules | 12,0% | 9,7% | 14,4% | 18,3% |
| PixSim A → PixSim B | rules+lightgbm | 80,7% | 85,7% | 76,8% | 58,9% |
| PixSim A → nosso | logreg | 52,9% | 46,4% | 30,6% | 19,3% |
| PixSim A → nosso | lightgbm | 21,4% | 15,7% | 11,4% | 7,7% |
| PixSim A → nosso | iforest | 57,1% | 48,6% | 33,4% | 20,3% |
| PixSim A → nosso | rules | 61,4% | 49,3% | 35,1% | 21,1% |
| PixSim A → nosso | rules+lightgbm | 55,7% | 47,9% | 31,4% | 18,3% |

**Captura por tipologia do PixSim em PixSim B** (Pix de vítima acima do limiar do modelo, ou fora de `approved` nas regras)

| tipologia | logreg (nosso) | lightgbm (nosso) | iforest (nosso) | logreg (PixSim A) | lightgbm (PixSim A) | iforest (PixSim A) | regras |
|---|---|---|---|---|---|---|---|
| account_takeover | 11,5% | 45,5% | 63,1% | 91,9% | 84,9% | 11,2% | 63,7% |
| pix_errado | 3,7% | 1,9% | 14,8% | 16,7% | 11,1% | 3,7% | 7,4% |
| qr_substitution | 2,5% | 10,0% | 15,0% | 28,7% | 25,0% | 2,5% | 11,2% |
| social_engineering | 7,4% | 23,6% | 33,1% | 60,7% | 61,7% | 8,2% | 32,9% |

**Captura por tipologia do nosso simulador (modelos do PixSim A)**

| tipologia | logreg | lightgbm | iforest | rules | rules+lightgbm |
|---|---|---|---|---|---|
| account_takeover | 43,8% | 6,2% | 43,8% | 100,0% | 100,0% |
| device_farm | 40,7% | 0,0% | 0,0% | 70,4% | 70,4% |
| mule | 62,7% | 0,0% | 84,0% | 100,0% | 100,0% |
| night_kidnapping | 66,7% | 0,0% | 33,3% | 100,0% | 100,0% |
| splitting | 78,6% | 44,6% | 89,3% | 53,6% | 67,9% |

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
