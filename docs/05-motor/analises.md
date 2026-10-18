---
title: Análises estatísticas
summary: Quatro análises no PixSim, simulador de terceiros (log-normalidade do valor por pagador, dispersão das contagens, PSI entre os mundos A e B, sensibilidade de limiar com custo) que sustentam z robusto, Poisson-Gamma e os parâmetros.
related: [regras.md, calibracao.md, validacao-pixsim.md, motor-de-regras.md, ../../scripts/analysis/analyze.py]
sources: [scripts/analysis/analyze.py, scripts/calibration/calibrate.py, scripts/pixsim/pixsim_adapter.py, src/rules/core/features.py, Pesquisa QITech (análises 1, 2, 6 e 7)]
---

# Análises estatísticas

> [Índice](../README.md) › Motor › Análises
>
> **Responde a:** o valor do Pix por pagador é log-normal (vale o z robusto)? as contagens são Poisson ou super-dispersas (vale a Poisson–Gamma)? as features derivam entre janelas? o quanto cada limiar mexe em fricção e em fraude barrada?

**Métricas no PixSim, simulador de terceiros.** O PixSim ([validação](validacao-pixsim.md)) não é Pix real e foi gerado por quem não somos: as formas que ele sorteia (valores, chegadas) não foram escolhidas por nós para o motor passar. Os números provam o método e a sensibilidade dos parâmetros neste mundo; com dado real, a mesma rotina deve ser rerodada. O nosso simulador (`scripts/fixture/simulate.py`) é só fixture de CI e não entra nestas análises.

Gerado por `make analyze` ([scripts/analysis/analyze.py](../../scripts/analysis/analyze.py)), sem API e sem banco, em leitura por streaming: mundo A (131828 Pix de features, escolha) e mundo B (134353, confirmação), ambos de `scripts/out/pixsim/`. Pagadores com menos de 10 Pix ficam fora das análises 1 e 2.

## 1. `log(amount)` por pagador

**Medido.** No mundo A, só Pix legítimos (burn-in incluído) de 3192 pagadores com ao menos 10 Pix (246199 Pix; 3681 pagadores no total). Para cada um, assimetria e curtose em excesso de `log(amount)`; depois o QQ: os valores viram z-score dentro do pagador (média e desvio, e também mediana e MAD×1,4826, a escala da regra) e seus quantis são lidos contra os da normal.

| Medida | Valor |
|---|---|
| Assimetria mediana | 0,03 |
| Curtose em excesso mediana | -0,20 |
| Pagadores com \|assimetria\| < 0,5 | 2726 de 3192 (85,4%) |

QQ agregado (z dentro do pagador):

| Quantil | Normal teórico | Empírico (média/desvio) | Empírico (mediana/MAD) |
|---|---|---|---|
| 0,1 | -1,282 | -1,285 | -1,289 |
| 0,2 | -0,842 | -0,845 | -0,831 |
| 0,3 | -0,524 | -0,529 | -0,525 |
| 0,4 | -0,253 | -0,258 | -0,246 |
| 0,5 | 0,000 | -0,006 | 0,000 |
| 0,6 | 0,253 | 0,251 | 0,248 |
| 0,7 | 0,524 | 0,524 | 0,532 |
| 0,8 | 0,842 | 0,845 | 0,841 |
| 0,9 | 1,282 | 1,287 | 1,301 |

**Conclusão.** 85,4% dos pagadores têm `log(amount)` aproximadamente simétrico e o QQ fica a no máximo 0,01 da normal em z: o dado justifica o z robusto sobre `log(amount)` da regra `PROFILE_AMOUNT_ROBUST_Z`. Com poucos Pix por pagador a assimetria amostral é ruidosa; a mediana/MAD segue sem distorcer com um valor extremo no histórico, que é o caso que a regra precisa detectar.

## 2. Dispersão das contagens

**Medido.** No mundo A, contagem de Pix legítimos por pagador (3192 pagadores, burn-in incluído) em cada hora e em cada dia da janela, com zeros incluídos. Índice de dispersão = variância / média (1 para Poisson, > 1 para super-dispersão, que é o que a binomial negativa modela). A coluna de referência repete o cálculo com contagens Poisson sorteadas com a mesma média de cada pagador (seed 42), para mostrar quanto de ruído amostral cabe acima de 1,5 sem super-dispersão real.

| Janela | Intervalos | Média por intervalo | Índice mediano | Índice p90 | Pagadores com índice > 1,5 | Referência Poisson com índice > 1,5 |
|---|---|---|---|---|---|---|
| por hora | 1440 | 0,054 | 1,01 | 1,09 | 0 de 3192 (0,0%) | 0 de 3192 (0,0%) |
| por dia | 60 | 1,286 | 1,03 | 1,31 | 90 de 3192 (2,8%) | 38 de 3192 (1,2%) |

Distribuição do índice por hora (nº de pagadores):

```mermaid
xychart-beta
    title "Pagadores por faixa do índice de dispersão (hora)"
    x-axis ["0-0,5", "0,5-1", "1-1,5", "1,5-2", "2-3", "3+"]
    y-axis "pagadores"
    bar [0.00, 1432.00, 1760.00, 0.00, 0.00, 0.00]
```

**Conclusão.** Índice mediano 1,01 por hora e 1,03 por dia; 0,0% (hora) e 2,8% (dia) dos pagadores passam de 1,5, contra 0,0% e 1,2% na referência Poisson. Neste dado, a super-dispersão intra-pagador não passa do ruído de Poisson; a Poisson simples descreve cada pagador, e a Poisson–Gamma continua útil porque a taxa de cada pagador é incerta (prior + pouco histórico), o que dá cauda mais larga na preditiva.

## 3. PSI entre janelas

**Medido.** Population Stability Index de cada feature de `FEATURE_NAMES`, com 10 bins por quantil da amostra-base (bins repetidos por valores discretos são fundidos; o PSI usa piso de 0,0001 por bin). Leitura: < 0,1 estável, 0,1 a 0,25 atenção, > 0,25 drift. Três comparações: (a) primeira × segunda metade do mundo A, só legítimos (62759 × 62759 Pix), a deriva natural; (b) mundo A × mundo B, todos os Pix avaliados (131828 × 134353), mesma população gerada com outra semente; (c) o mesmo, só Pix de fraude (6310 × 6670).

| Feature | PSI metade × metade (legítimos) | Leitura | PSI A × B (todos) | PSI A × B (fraude) | Leitura (fraude) |
|---|---|---|---|---|---|
| hours_since_first_seen | 6,159 | drift | 0,000 | 0,017 | estável |
| source_history_size | 0,176 | atenção | 0,002 | 0,006 | estável |
| weekday | 0,039 | estável | 0,000 | 0,013 | estável |
| source_attempts_poisson_lookback | 0,003 | estável | 0,007 | 0,005 | estável |
| history_30d_median_cents | 0,003 | estável | 0,006 | 0,012 | estável |
| history_30d_size | 0,003 | estável | 0,006 | 0,006 | estável |
| local_hour | 0,003 | estável | 0,000 | 0,011 | estável |
| destination_rejected_by_others_last_window | 0,002 | estável | 0,000 | 0,000 | estável |
| poisson_tail_log10 | 0,002 | estável | 0,003 | 0,004 | estável |
| source_age_days | 0,001 | estável | 0,010 | 0,017 | estável |
| destination_age_days | 0,001 | estável | 0,012 | 0,169 | atenção |
| source_new_destinations_last_24h | 0,001 | estável | 0,000 | 0,004 | estável |
| source_small_attempts_last_24h | 0,001 | estável | 0,000 | 0,004 | estável |
| source_sum_last_24h_cents | 0,001 | estável | 0,002 | 0,008 | estável |
| amount_robust_z | 0,001 | estável | 0,000 | 0,004 | estável |
| source_attempts_last_velocity_window | 0,000 | estável | 0,000 | 0,000 | estável |
| source_attempts_poisson_window | 0,000 | estável | 0,000 | 0,002 | estável |
| amount | 0,000 | estável | 0,001 | 0,004 | estável |
| log_amount | 0,000 | estável | 0,001 | 0,004 | estável |
| destination_distinct_other_sources_last_1h | 0,000 | estável | 0,000 | 0,004 | estável |
| is_self_transfer | 0,000 | estável | 0,000 | 0,000 | estável |
| is_legal_entity_source | 0,000 | estável | 0,000 | 0,000 | estável |
| has_geolocation | 0,000 | estável | 0,000 | 0,000 | estável |
| device_seen_for_source | 0,000 | estável | 0,000 | 0,000 | estável |
| destination_seen_for_source | 0,000 | estável | 0,000 | 0,000 | estável |
| device_distinct_other_sources_last_24h | 0,000 | estável | 0,000 | 0,000 | estável |
| destination_used_before | 0,000 | estável | 0,000 | 0,000 | estável |
| km_since_last_geolocation | 0,000 | estável | 0,000 | 0,000 | estável |
| speed_kmh_since_last_geolocation | 0,000 | estável | 0,000 | 0,000 | estável |
| destination_graph_risk | 0,000 | estável | 0,000 | 0,000 | estável |
| destination_graph_risk_age_minutes | 0,000 | estável | 0,000 | 0,000 | estável |
| destination_graphsage_score | 0,000 | estável | 0,000 | 0,000 | estável |
| source_sequence_score | 0,000 | estável | 0,000 | 0,000 | estável |

**Conclusão.** Entre as metades do período, 2 de 33 features passam de 0,1 (source_history_size, hours_since_first_seen), todas efeito de aquecimento do histórico em memória (o histórico cresce com o tempo), não de mudança de comportamento. A × B: 0 features em drift considerando todos os Pix (a fraude é minoria) e 0 considerando só a fraude. Dois mundos da mesma população devem ficar estáveis; o PSI serve de alarme para recalibrar ou retreinar os modelos em shadow quando a população muda.

## 4. Sensibilidade de limiar

**Medido.** Passada em streaming pelo mundo A com um parâmetro por vez e os demais nos padrões atuais, a mesma avaliação da [calibração](calibracao.md). Em legítimos: % aprovado / 2FA / reprovado (fricção). Em fraude: % de Pix pagador→mula barrados (2FA ou reprovação). Custo: esperado por 1.000 Pix na visão do pagador, com a fraude ponderada pelo peso de importância do PixSim ([`scripts/backtest/cost-model.json`](../../scripts/backtest/cost-model.json)); a dispersão (lado da mula) não entra. Padrão de cada parâmetro marcado com `*`. Linha de base: legítimos 96,18% aprovados, fraude barrada 51,67% (1380 Pix pagador→mula), custo R$ 131,66 por 1.000 Pix.

### `RULE_AMOUNT_DAILY_SUM_CENTS`

| Valor | Legítimos aprovados % | Legítimos 2FA % | Legítimos reprovados % | Fraude barrada % | Custo R$/1.000 Pix |
|---|---|---|---|---|---|
| R$ 15.000 | 96,04 | 3,95 | 0,01 | 52,39 | 133,01 |
| R$ 22.500 | 96,14 | 3,85 | 0,01 | 51,88 | 132,52 |
| R$ 30.000 | 96,16 | 3,83 | 0,01 | 51,67 | 132,18 |
| R$ 45.000* | 96,18 | 3,81 | 0,01 | 51,67 | 131,66 |
| R$ 60.000 | 96,18 | 3,80 | 0,01 | 51,59 | 131,66 |

Linhas: fricção em legítimos (100 − aprovados) e fraude barrada, em %. Eixo x em reais.

```mermaid
xychart-beta
    title "RULE_AMOUNT_DAILY_SUM_CENTS"
    x-axis ["15000", "22500", "30000", "45000", "60000"]
    y-axis "%" 0 --> 100
    line [3.96, 3.86, 3.84, 3.82, 3.82]
    line [52.39, 51.88, 51.67, 51.67, 51.59]
```

Amplitude ao varrer o parâmetro: 0,15 p.p. de fricção, 0,80 p.p. de fraude barrada e R$ 1,35 de custo.

### `RULE_POISSON_TAIL_PPM`

| Valor | Legítimos aprovados % | Legítimos 2FA % | Legítimos reprovados % | Fraude barrada % | Custo R$/1.000 Pix |
|---|---|---|---|---|---|
| 10 | 96,25 | 3,74 | 0,01 | 50,43 | 131,77 |
| 30* | 96,18 | 3,81 | 0,01 | 51,67 | 131,66 |
| 100 | 95,98 | 4,00 | 0,01 | 54,13 | 133,27 |
| 300 | 95,58 | 4,41 | 0,01 | 56,23 | 137,74 |
| 1000 | 94,45 | 5,54 | 0,01 | 59,86 | 155,90 |

Linhas: fricção em legítimos (100 − aprovados) e fraude barrada, em %.

```mermaid
xychart-beta
    title "RULE_POISSON_TAIL_PPM"
    x-axis ["10", "30", "100", "300", "1000"]
    y-axis "%" 0 --> 100
    line [3.75, 3.82, 4.02, 4.42, 5.55]
    line [50.43, 51.67, 54.13, 56.23, 59.86]
```

Amplitude ao varrer o parâmetro: 1,79 p.p. de fricção, 9,42 p.p. de fraude barrada e R$ 24,24 de custo.

### `RULE_PROFILE_Z_2FA_TENTHS`

| Valor | Legítimos aprovados % | Legítimos 2FA % | Legítimos reprovados % | Fraude barrada % | Custo R$/1.000 Pix |
|---|---|---|---|---|---|
| 25 | 95,26 | 4,73 | 0,01 | 55,58 | 142,04 |
| 30 | 95,84 | 4,15 | 0,01 | 53,41 | 134,48 |
| 35 | 96,05 | 3,94 | 0,01 | 52,39 | 132,97 |
| 45* | 96,18 | 3,81 | 0,01 | 51,67 | 131,66 |
| 55 | 96,22 | 3,77 | 0,01 | 51,45 | 131,75 |

Linhas: fricção em legítimos (100 − aprovados) e fraude barrada, em %.

```mermaid
xychart-beta
    title "RULE_PROFILE_Z_2FA_TENTHS"
    x-axis ["25", "30", "35", "45", "55"]
    y-axis "%" 0 --> 100
    line [4.74, 4.16, 3.95, 3.82, 3.78]
    line [55.58, 53.41, 52.39, 51.67, 51.45]
```

Amplitude ao varrer o parâmetro: 0,96 p.p. de fricção, 4,13 p.p. de fraude barrada e R$ 10,38 de custo.

**Conclusão.** `RULE_POISSON_TAIL_PPM` é o parâmetro de maior efeito no custo (R$ 24,24 na faixa varrida; 1,79 p.p. de fricção, 9,42 p.p. de fraude) e `RULE_AMOUNT_DAILY_SUM_CENTS` o de menor (R$ 1,35; 0,15 e 0,80 p.p.). Onde a fraude barrada não muda com a fricção, o limiar está num platô e a escolha é por custo de falso positivo; onde as duas curvas sobem juntas, há troca real. Os padrões em uso foram escolhidos na [calibração](calibracao.md); esta tabela só mede o entorno deles, no mesmo mundo.
