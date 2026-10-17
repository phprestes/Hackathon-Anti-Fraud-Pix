---
title: "ADR 0022: Shadow mode — regras e modelos que calculam sem decidir"
summary: Regras com shadow = True rodam em todo Pix e aparecem em metadata.shadow, mas nunca entram no status, nos motivos nem em pix_analysis_reason.
related: [0006-pior-decisao-vence-e-todas-as-regras-rodam.md, 0017-ml-fora-do-prazo-e-do-hot-path.md]
sources: [Plano de implementação 2 (G1, G4), prática de mercado (shadow/champion-challenger)]
---

# ADR 0022: Shadow mode — regras e modelos que calculam sem decidir

> [Índice](../../README.md) › [Decisões](README.md) › 0022

**Status:** aceita

## Contexto

Queremos colocar modelos treinados com dados sintéticos no caminho do Pix para mostrar que o desenho comporta ML, sem que um modelo sem rótulo real mude a decisão de alguém. Também queremos testar regras candidatas sem mudar as respostas.

## Decisão

- `BaseRule.shadow` (padrão `False`). O `engine.evaluate` roda as regras shadow junto com as outras, mas os resultados delas vão só para `metadata.shadow = [{rule, would_decide, reason, signals}]`.
- Regra shadow nunca afeta `status`, `metadata.reasons` nem `pix_analysis_reason`.
- O simulador e o backtest comparam o que as regras shadow teriam decidido com os rótulos, como se fosse um champion/challenger offline.

## Alternativas descartadas

- **Modelo decidindo direto.**
  - **Preço:** decisões guiadas por rótulo sintético; erro do modelo vira cliente bloqueado.
  - **Ganharia se** houvesse rótulo real e avaliação em produção.
- **Modelo só fora da API (relatório offline).**
  - **Preço:** não prova que o modelo cabe no hot path (latência, dependências, serialização).
  - **Ganharia se** o objetivo fosse só pesquisa.

## Consequências

- Promover uma regra ou modelo de shadow para valer é trocar um atributo, registrar no CHANGELOG e mudar o `RULE_SET_VERSION`.
- `metadata.shadow` é sempre uma lista (vazia quando não há regra shadow).
