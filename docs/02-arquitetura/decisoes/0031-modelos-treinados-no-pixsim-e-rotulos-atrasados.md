---
title: "ADR 0031: Modelos treinados no PixSim e treino só com rótulos já reportados"
summary: LogReg, LightGBM e GraphSAGE são treinados num mundo do PixSim e testados em outro; o treino considera só as fraudes cujo desfecho no MED já chegou, com os atrasos de reporte do próprio simulador.
related: [0024-modelos-servidos-em-python-puro.md, 0026-graphsage-e-hmm-no-worker.md, 0029-pixsim-como-referencia.md]
sources: [Dal Pozzolo, Boracchi, Caelen, Alippi & Bontempi (2018), Credit card fraud detection: a realistic modeling and a novel learning strategy, IEEE Transactions on Neural Networks and Learning Systems 29(8), https://re.public.polimi.it/handle/11311/1044896, rótulos atrasados; PixSim (draw_report_delay); docs/05-motor/validacao-pixsim.md]
---

# ADR 0031: Modelos treinados no PixSim e treino só com rótulos já reportados

> [Índice](../../README.md) › [Decisões](README.md) › 0031

**Status:** aceita

## Contexto

O LightGBM treinado no nosso gerador teve AUC de 0,58 no PixSim; ele tinha aprendido o nosso simulador. Na vida real, o rótulo de fraude só chega quando a vítima contesta no MED, dias ou semanas depois (Dal Pozzolo et al., 2018).

## Decisão

- **Treino no PixSim.** LogReg + Platt e LightGBM treinam no mundo A e são instalados se forem melhores no mundo B: AUC 0,99 contra 0,58–0,77 dos treinados no nosso gerador. O GraphSAGE treina com o `is_mule` do próprio PixSim como rótulo de nó (AUC 0,92 contra 0,52). Todos seguem em shadow ([ADR 0022](0022-shadow-mode.md)). O Isolation Forest ficou como estava (recall de 8% no PixSim).
- **Rótulos atrasados.** O experimento usa o atraso de reporte do PixSim (mediana de 2,1 dias, p90 de 17,5 dias, 1,8% nunca reportado). Só com os rótulos já reportados, o LightGBM perde pouco (AUC 0,97 contra 0,99). Com um atraso fixo de 14 dias, despenca (0,66).

## Alternativas descartadas

- **Manter os modelos treinados no nosso gerador.**
  - **Preço:** AUC de 0,58 a 0,77 no PixSim.
  - **Ganharia se** o nosso gerador fosse a referência.
- **Treinar com todos os rótulos (oráculo).**
  - **Preço:** mede um modelo que nenhum banco consegue treinar.
  - **Ganharia se** os rótulos chegassem na hora.

## Consequências

- O 0,99 compara duas seeds do mesmo gerador. Mede generalização entre seeds, não independência; no nosso simulador, os modelos do PixSim caem, e as regras ganham deles.
- Retreinar com frequência pesa mais do que corrigir o prior; esperar os rótulos amadurecerem por muito tempo destrói o modelo.
- `make train-models` treina no PixSim; `make train-models-mock` treina no nosso gerador e avisa que sobrescreve.
