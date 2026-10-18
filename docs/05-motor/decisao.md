---
title: Como as regras viram decisão
summary: Severidade das três decisões, quando sai 2FA, quando sai reprovação, papel das tipologias, ordem dos motivos e exemplos.
related: [motor-de-regras.md, regras.md, ../02-arquitetura/decisoes/0006-pior-decisao-vence-e-todas-as-regras-rodam.md, ../02-arquitetura/decisoes/0018-regras-compostas-por-tipologia.md]
sources: [Desafio Antifraude Pix (seção 2.3 e seção 6 "Como as regras viram decisão"), código em src/controllers/pix_transaction_controller.py]
---

# Como as regras viram decisão

> [Índice](../README.md) › Motor › Decisão
>
> **Responde a:** em que ordem as regras rodam? quando sai 2FA? quando sai reprovação? o que vai no `metadata`?

**Estado:** implementado ([ADR 0006](../02-arquitetura/decisoes/0006-pior-decisao-vence-e-todas-as-regras-rodam.md), [ADR 0018](../02-arquitetura/decisoes/0018-regras-compostas-por-tipologia.md)).

## Regra de agregação

1. Todas as regras ativas rodam, sem curto-circuito.
2. Cada regra devolve nada (não disparou) ou um disparo com `two_factor_required` ou `rejected`.
3. A decisão final é a de maior severidade: `rejected` (2) > `two_factor_required` (1) > `approved` (0).
4. Sem nenhum disparo, a decisão é `approved` com `reasons` vazia.
5. `metadata.reasons` lista todos os disparos, ordenados por severidade e depois pela ordem de `ACTIVE_RULES` (limite → velocity → montante → perfil → contraparte → tipologia). `metadata.signals` traz os números de cada regra disparada.

A ordem das regras **não** muda a decisão, só a ordem dos motivos.

## Três camadas de severidade

| Camada | Regras | Decide | Por quê |
|---|---|---|---|
| **Sinal isolado de dúvida** | limites, velocity fixa, perfil (device novo, conta nova, z robusto, Poisson, viagem impossível), destino novo, primeira vez com valor alto, reputação de grafo ≥ 0,6 (`COUNTERPARTY_GRAPH_RISK`) | `two_factor_required` | Sozinho, o sinal acontece com cliente bom (viagem, compra grande, aparelho novo). O cliente legítimo resolve com um toque; o fraudador não tem o segundo fator |
| **Sinal isolado de risco claro** | conta de destino com menos de 3 dias + valor alto, velocity extrema (10 em 10 min), aparelho com mais de 3 pagadores, fan-in acima de 10, reputação de grafo ≥ 0,9 | `rejected` | Padrões que quase nunca são de cliente legítimo |
| **Tipologia** (combinação) | `TYPOLOGY_ACCOUNT_TAKEOVER`, `TYPOLOGY_MULE` | `rejected` | A combinação descreve um golpe conhecido. Dois 2FA não somam um `rejected`; só uma tipologia explícita reprova ([ADR 0018](../02-arquitetura/decisoes/0018-regras-compostas-por-tipologia.md)) |

## Exemplos (dos testes de cenário)

| Cenário | Disparos | Decisão |
|---|---|---|
| Aluguel para o destino de sempre, mesmo aparelho, 10h | — | `approved` |
| Pix para conta aberta há 7 dias | `COUNTERPARTY_NEW_ACCOUNT` (2FA) | `two_factor_required` |
| Pagador antigo, aparelho novo, 10 min depois de um Pix em São Paulo, agora no Rio, valor alto para destino novo | `TYPOLOGY_ACCOUNT_TAKEOVER` (rejected), `PROFILE_GEO_VELOCITY`, `PROFILE_NEW_DEVICE`, `COUNTERPARTY_FIRST_TIME_HIGH` (2FA) | `rejected`, quatro motivos |
| 5º pagador diferente em 1 h para conta aberta há 2 dias | `TYPOLOGY_MULE` (rejected), `COUNTERPARTY_NEW_ACCOUNT` | `rejected` |

`TYPOLOGY_SPLITTING`, `COUNTERPARTY_FLAGGED` e `AMOUNT_SOURCE_DAILY_SUM` foram descartadas ([ADR 0033](../02-arquitetura/decisoes/0033-regras-descartadas-pela-ablacao.md)).

Os parâmetros, as fontes e o efeito medido de cada regra no PixSim estão no [catálogo](regras.md).
