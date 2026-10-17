---
title: "ADR 0007: O relógio das regras é o transaction_date do Pix"
summary: Janelas de velocity, horário noturno e idade de conta são calculados a partir do transaction_date, nunca do now() do servidor.
related: [0005-regras-puras-com-contexto-carregado.md, ../../05-motor/regras.md, ../../07-testes/estrategia.md]
sources: [Desafio Antifraude Pix (seção 3.2 "transaction_date: data e hora, com fuso")]
---

# ADR 0007: O relógio das regras é o `transaction_date` do Pix

> [Índice](../../README.md) › [Decisões](README.md) › 0007

**Status:** aceita

## Contexto

O payload traz `transaction_date` com fuso. Regras perguntam "na última hora?", "é de madrugada?", "a conta tem quantos dias?". A banca vai mandar Pix com datas escolhidas por ela, provavelmente fora da hora real do servidor.

## Decisão

- "Agora" para as regras é o `transaction_date` do Pix em análise.
- Janela de velocity: Pix do mesmo sinal com `transaction_date` em `[agora − janela, agora)`.
- Horário local (regra noturna) usa o fuso que veio no payload. O banco grava `TIMESTAMPTZ`.
- `created_at` (hora do servidor) fica só para auditoria.

## Alternativas descartadas

- **`now()` do servidor.**
  - **Preço:** o mesmo Pix dá decisões diferentes conforme a hora em que roda; teste de velocity depende de `sleep`; a banca não consegue reproduzir a decisão do README.
  - **Ganharia se** quem chama não fosse confiável para informar a data.

## Consequências

- Testes montam histórico mandando Pix com datas escolhidas, sem esperar o relógio.
- Pix com `transaction_date` muito no futuro ou no passado é um sinal possível, e uma regra pode tratá-lo.
