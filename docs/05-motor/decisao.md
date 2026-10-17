---
title: Como as regras viram decisão
summary: Severidade das três decisões, quando sai 2FA, como os motivos são ordenados e exemplos de agregação.
related: [motor-de-regras.md, regras.md, ../02-arquitetura/decisoes/0006-pior-decisao-vence-e-todas-as-regras-rodam.md]
sources: [Desafio Antifraude Pix (seção 2.3 e seção 6 "Como as regras viram decisão")]
---

# Como as regras viram decisão

> [Índice](../README.md) › Motor › Decisão
>
> **Responde a:** em que ordem as regras rodam? quando sai 2FA? quando sai reprovação? o que vai no `metadata`?

**Estado:** proposta ([ADR 0006](../02-arquitetura/decisoes/0006-pior-decisao-vence-e-todas-as-regras-rodam.md)).

## Regra de agregação

1. Todas as regras ativas rodam, sem curto-circuito.
2. Cada regra devolve nada (não disparou) ou um disparo com `two_factor_required` ou `rejected`.
3. A decisão final é a de maior severidade: `rejected` (2) > `two_factor_required` (1) > `approved` (0).
4. Sem nenhum disparo, a decisão é `approved` com `reasons` vazia.
5. `metadata.reasons` lista todos os disparos, ordenados por severidade e depois pela ordem de `ACTIVE_RULES`.

## Quando cada decisão sai

| Decisão | Quando | Intenção |
|---|---|---|
| `approved` | Nenhuma regra disparou | Zero fricção para o comportamento habitual |
| `two_factor_required` | Pelo menos uma regra de dúvida disparou e nenhuma de risco claro | O sinal sozinho não prova fraude, mas o cliente legítimo resolve com um toque |
| `rejected` | Pelo menos uma regra de risco claro disparou | Padrões que quase nunca são de cliente legítimo (aparelho com muitas contas, conta de passagem) |

Uma regra pode ter dois degraus (ex.: velocity 2FA a partir de 5, reprova a partir de 10): ela devolve um disparo só, o do degrau mais alto atingido.

## Exemplos

| Cenário | Disparos | Decisão |
|---|---|---|
| Aluguel de R$ 1.500 às 10h para o destino de sempre | — | `approved` |
| R$ 1.500 às 22h15 para conta aberta há 7 dias | `LIMIT_NIGHT_AMOUNT` (2FA), `COUNTERPARTY_NEW_ACCOUNT` (2FA) | `two_factor_required`, dois motivos |
| Quarto pagador diferente no mesmo aparelho hoje, R$ 50 | `VELOCITY_DEVICE_SOURCES` (reprova) | `rejected` |

Os parâmetros dos exemplos são os sugeridos no [catálogo](regras.md) e mudam com a calibragem.
