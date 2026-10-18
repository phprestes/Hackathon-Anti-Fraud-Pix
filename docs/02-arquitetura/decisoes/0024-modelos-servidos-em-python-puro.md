---
title: "ADR 0024: Modelos treinados fora da API e servidos em Python puro a partir de JSON"
summary: LogReg (com Platt), LightGBM e Isolation Forest são treinados em scripts/ com bibliotecas de desenvolvimento, exportados para JSON e avaliados na API só com math, em shadow; a fidelidade é provada contra a biblioteca.
related: [0022-shadow-mode.md, 0023-motor-extraido-e-history-port.md, 0017-ml-fora-do-prazo-e-do-hot-path.md]
sources: [Pesquisa QITech (M2, M3, tabela de latências), Dal Pozzolo, Caelen, Johnson & Bontempi (2015), Calibrating probability with undersampling for unbalanced classification, IEEE SSCI 2015, https://ieeexplore.ieee.org/document/7376606, Platt (1999), Probabilistic outputs for support vector machines and comparisons to regularized likelihood methods, Advances in Large Margin Classifiers, p. 61-74, https://www.csie.ntu.edu.tw/~cjlin/papers/plattprob.pdf, Ke et al. (2017), LightGBM, NeurIPS 30, p. 3146-3154, https://proceedings.neurips.cc/paper/2017/file/6449f44a102fde848669bdd9eb6b76fa-Paper.pdf, Liu, Ting & Zhou (2008), Isolation Forest, IEEE ICDM, p. 413-422, https://doi.org/10.1109/ICDM.2008.17, scripts/model-results.md]
---

# ADR 0024: Modelos treinados fora da API e servidos em Python puro a partir de JSON

> [Índice](../../README.md) › [Decisões](README.md) › 0024

**Status:** aceita

## Contexto

A pesquisa coloca gradient boosting no hot path (2–8 ms) e Isolation Forest como pré-filtro. Queremos mostrar que isso cabe no nosso motor sem inflar a imagem da `api` (lightgbm, scikit-learn e numpy somam centenas de MB) e sem criar um caminho de inferência diferente do de treino.

## Decisão

- **Treino** em `scripts/train_models.py`, com `numpy`, `scikit-learn` e `lightgbm` só em `requirements-dev.txt`. Os dados vêm de `make datasets`: simulador → backtest em lote → `metadata.features` + rótulo. Treino com seed 42, teste com seed 7 e com o gerador perturbado.
  - LogReg com `class_weight` balanceado e calibração de Platt (a base tem cerca de 2,5% de fraude; Dal Pozzolo, 2015).
  - LightGBM com 100 árvores, 15 folhas e `scale_pos_weight`.
  - Isolation Forest treinado só com legítimos, sem rótulo.
- **Exportação** para `src/rules/model/*.json`: pesos e Platt; árvores como listas aninhadas; tamanho das folhas e `n_samples` do Isolation Forest. Cada arquivo traz `warning: "mock: synthetic labels"`.
- **Inferência** em `src/rules/models/` só com `math`. O `make model-parity` compara com `predict_proba`/`decision_function` da biblioteca sobre 14.202 Pix do nosso simulador (seed 7, normal e perturbado), medido com os modelos instalados em 2026-10-18: diferença máxima de 1,1e-15 na regressão logística, 1,1e-16 no LightGBM e 1,7e-16 no score do Isolation Forest (5,3e-15 no comprimento de caminho). Tolerância do script: 1e-6.
- As regras `MODEL_LOGREG`, `MODEL_LIGHTGBM` e `MODEL_IFOREST` são **shadow** ([ADR 0022](0022-shadow-mode.md)). Os arquivos são lidos uma vez, em `build_rules()`; se um faltar, a regra não é registrada e a API sobe.

## Resultados (dados sintéticos)

Resultado no fixture do CI (sem valor estatístico; os números com valor estatístico, treinados e testados no PixSim, estão na [ADR 0031](0031-modelos-treinados-no-pixsim-e-rotulos-atrasados.md)):

| | AUC teste (perturbado) | Fraudes barradas | Fricção em legítimos |
|---|---|---|---|
| Regras | — | 81% (89%) | 3,3% |
| LightGBM | 0,990 (0,985) | 84% (86%) | 0,1% |
| Regras + LightGBM | — | 89% (92%) | 3,4% |
| LogReg + Platt | 0,978 (0,969) | — | — |
| Isolation Forest | 0,866 (0,904) | 26% (34%) | 1,0% |

Latência no backtest: +149 µs por Pix para os três modelos juntos. Treino: menos de 1 s cada. Detalhe em [`scripts/model-results.md`](../../../scripts/model-results.md).

## Alternativas descartadas

- **Servir com a biblioteca na imagem.**
  - **Preço:** imagem centenas de MB maior, `make all` mais lento na máquina da banca (R2) e mais superfície de dependência.
  - **Ganharia se** o modelo fosse uma rede neural ou se houvesse um serviço de inferência dedicado.
- **Serviço de modelo separado (HTTP).**
  - **Preço:** chamada externa no caminho do Pix ([ADR 0002](0002-monolito-sincrono-sem-dependencia-externa.md)).
  - **Ganharia se** vários motores compartilhassem o mesmo modelo.

## Consequências

- Os números medem o gerador que escrevemos: o LightGBM bate as regras no sintético, e isso **não** prova eficácia real. Por isso ele fica em shadow.
- Retreinar é `make train-models`; promover é tirar o `shadow` e mudar o `RULE_SET_VERSION`.
