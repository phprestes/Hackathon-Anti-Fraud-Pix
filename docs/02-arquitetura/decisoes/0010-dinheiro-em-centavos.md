---
title: "ADR 0010: Dinheiro em BIGINT de centavos"
summary: amount chega inteiro em centavos, é validado como inteiro positivo pelo schema e guardado como BIGINT; somas de montante nunca usam float.
related: [../../04-dados/modelo.md, ../../05-motor/regras.md]
sources: [Desafio Antifraude Pix (seção 3.2 "amount: valor em centavos"), Autoestudo Aula 2 (R6)]
---

# ADR 0010: Dinheiro em `BIGINT` de centavos

> [Índice](../../README.md) › [Decisões](README.md) › 0010

**Status:** proposta

## Contexto

O contrato já manda `amount` em centavos. Regras de montante somam muitos Pix e comparam com limites.

## Decisão

- Schema: `amount` é `integer` com `minimum: 1`. `150000.5` ou `"150000"` são 400.
- Banco: `BIGINT` com `CHECK (amount > 0)`.
- Parâmetros de valor terminam em `_CENTS` e são inteiros.
- Razões de proporção ("5× a média") comparam com multiplicação inteira (`amount * 100 > avg * RATIO_PERCENT`), sem dividir em float.

## Alternativas descartadas

- **`NUMERIC(15,2)` em reais.**
  - **Preço:** converte na entrada e na saída um contrato que já é inteiro.
  - **Ganharia se** o contrato viesse em reais com casas decimais.
- **`INTEGER`.**
  - **Preço:** estoura em R$ 21 milhões; uma soma de janela chega lá com poucos Pix grandes.
  - **Ganharia se** nunca houvesse soma.

## Consequências

- `float` não aparece em `src/` para dinheiro; a [skill revisar-mudanca](../../../.agents/skills/revisar-mudanca/SKILL.md) confere com `grep`.
