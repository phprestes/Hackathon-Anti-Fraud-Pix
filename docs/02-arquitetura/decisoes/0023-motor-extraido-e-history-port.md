---
title: "ADR 0023: Motor extraído do controller, com HistoryPort e vetor de features"
summary: Montagem do contexto, avaliação e decisão moram em src/rules/engine.py e dependem só de um HistoryPort; o mesmo motor roda na API (SQL) e no backtest (memória), e um vetor único de features sai em metadata.features.
related: [0005-regras-puras-com-contexto-carregado.md, ../c4.md, 0020-simulador-para-calibracao.md]
sources: [Plano de implementação 2 (G1, G2), C4 seção 5]
---

# ADR 0023: Motor extraído do controller, com HistoryPort e vetor de features

> [Índice](../../README.md) › [Decisões](README.md) › 0023

**Status:** aceita

## Contexto

O backtest pela API leva cerca de 3 minutos para 5 mil Pix, e cada Pix paga HTTP e cerca de 15 consultas. Para reprocessar em lote, treinar modelos e varrer parâmetros, o motor precisa rodar fora da API. Ao mesmo tempo, não pode existir uma segunda versão das regras, nem da montagem do contexto.

## Decisão

- `src/rules/engine.py`: `build_context(snapshot, history)`, `evaluate(snapshot, context, rules)` e `metadata_from(result)`. O controller faz só idempotência, gravação e commit.
- `src/rules/history_port.py`: `HistoryPort` (Protocol) com os agregados de que o contexto precisa. O `PixTransactionRepository` (SQL) o implementa na API; o `InMemoryHistory` (scripts/) o implementa no backtest.
- `src/rules/features.py`: um único vetor de features (29 campos, nada identificável), montado do mesmo contexto que as regras veem e devolvido em `metadata.features`. É a fonte das features de treino.
- **Paridade:** o mesmo arquivo de eventos passa pela API e pelo backtest; status, regras disparadas e o vetor inteiro de features precisam ser idênticos Pix a Pix (`make parity`). Como o vetor cobre todos os agregados, a comparação prova que as duas implementações do `HistoryPort` contam igual, sem que os testes importem `src/` (R1).

## Alternativas descartadas

- **Backtest só pela API.**
  - **Preço:** minutos por rodada; grid e geração de treino viram horas.
  - **Ganharia se** o volume fosse sempre pequeno.
- **Agregados em memória sem verificação.**
  - **Preço:** a segunda implementação diverge em silêncio, e a calibração mede uma cópia do motor (*training-serving skew*).
  - **Ganharia se** existisse uma feature store compartilhada.

## Consequências

- Qualquer agregado novo entra no `HistoryPort`, nos dois adaptadores e no vetor de features; a paridade acusa se faltar um lado.
- As respostas da API ganharam `metadata.features` e `metadata.shadow`.
