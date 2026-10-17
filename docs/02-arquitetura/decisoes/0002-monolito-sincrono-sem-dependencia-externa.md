---
title: "ADR 0002: Uma API síncrona, sem dependência externa no caminho da decisão"
summary: A decisão sai na própria resposta do POST, calculada só com o payload e o banco local; nenhum serviço externo nem fila.
related: [../visao-geral.md, ../../06-operacao/rodando-localmente.md]
sources: [Desafio Antifraude Pix (seção 2.1 "Tempo", seção 4 "Outras APIs")]
---

# ADR 0002: Uma API síncrona, sem dependência externa no caminho da decisão

> [Índice](../../README.md) › [Decisões](README.md) › 0002

**Status:** proposta

## Contexto

"A decisão sai antes do dinheiro sair, em poucos segundos. Não dá para esperar uma consulta externa pesada nem um analista." E "Outras APIs" estão fora do escopo. A banca roda o projeto numa máquina limpa.

## Decisão

- Dois containers: `api` e `db`. Nada de `mock`, fila ou worker.
- O `POST /pix/transaction` grava o Pix, roda as regras e devolve a decisão na mesma requisição.
- Toda regra usa só o payload e o histórico do nosso banco. A pasta `src/connectors/` herdada fica sem uso.

## Alternativas descartadas

- **Decisão assíncrona (fila + worker, cliente consulta depois).**
  - **Preço:** o cliente do Pix espera de qualquer jeito; vira mais infraestrutura e um estado "em análise" que o enunciado não prevê.
  - **Ganharia se** existisse análise manual ou modelo pesado no fluxo.
- **Consultar serviço externo (DICT, lista restritiva, birô) com MockServer.**
  - **Preço:** latência e um modo de falha a mais (timeout vira decisão do quê?) para um sinal que o enunciado não fornece.
  - **Ganharia se** o desafio trouxesse uma base externa de contas suspeitas.

## Consequências

- Latência é dominada pelas consultas de histórico; elas precisam de índice ([ADR 0009](0009-historico-append-only.md)).
- Uma transação de banco por requisição: o Pix, a análise e os motivos entram juntos ou nada entra.
