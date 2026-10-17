---
title: "ADR 0005: Regras puras; o controller carrega o contexto de histórico uma vez"
summary: Regra não toca banco nem relógio; recebe o Pix e um RuleContext montado pelo controller com consultas agregadas do repository.
related: [0004-motor-de-regras-em-codigo.md, 0007-relogio-da-transacao.md, ../camadas.md]
sources: [bootcamp-base-api (camadas), Desafio Antifraude Pix (seção 2.1 "Histórico")]
---

# ADR 0005: Regras puras; o controller carrega o contexto de histórico uma vez

> [Índice](../../README.md) › [Decisões](README.md) › 0005

**Status:** proposta

## Contexto

Regras de velocity e montante precisam do passado ("quantos Pix esse aparelho fez na última hora?"). No Base Service, só `repositories/` fala com o banco e só o controller decide. Se cada regra consultar o banco, são N consultas por Pix e a camada fica furada.

## Decisão

- O `PixTransactionController` pede ao `PixTransactionRepository` os agregados de que as regras precisam (contagens e somas por janela, primeira vez de destino e aparelho, média do pagador) e monta um `RuleContext` imutável.
- Regra recebe `(pix, context)` e devolve resultado. Não importa `repositories`, `database` nem `datetime.now()`.
- O histórico consultado exclui o próprio Pix em análise.

## Alternativas descartadas

- **Cada regra consulta o repository que precisa.**
  - **Preço:** consultas repetidas por Pix, regra acoplada ao banco, e a regra deixa de ser testável só olhando entrada e saída.
  - **Ganharia se** cada regra precisasse de um dado muito diferente e caro, que só ela usa.
- **Carregar o histórico inteiro do pagador em memória.**
  - **Preço:** cresce sem limite com o cliente e repete no Python o que o Postgres faz com índice.
  - **Ganharia se** o histórico fosse curto por natureza.

## Consequências

- Regra nova que precisa de sinal novo acrescenta um campo ao `RuleContext` e uma consulta ao repository. A [skill nova-regra](../../../.agents/skills/nova-regra/SKILL.md) guia isso.
- O `metadata` pode expor o contexto usado, o que explica a decisão com números.
