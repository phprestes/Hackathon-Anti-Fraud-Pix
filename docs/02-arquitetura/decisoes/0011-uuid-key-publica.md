---
title: "ADR 0011: id interno, analysis_key UUID na saída e o id do Pix como chave de consulta"
summary: O SERIAL do banco nunca sai; a resposta expõe key (UUID da análise); o GET usa o id do Pix, que é de quem chama.
related: [../../03-api/rotas.md, ../../04-dados/modelo.md]
sources: [Desafio Antifraude Pix (seções 3.3 e 3.4), Autoestudo Aula 2 (R5), bootcamp-base-api (sample_entity_key)]
---

# ADR 0011: `id` interno, `analysis_key` UUID na saída e o `id` do Pix como chave de consulta

> [Índice](../../README.md) › [Decisões](README.md) › 0011

**Status:** aceita

## Contexto

O contrato tem dois identificadores: `key` ("identificador da análise", na saída) e `id` do Pix (na entrada e no `GET /pix/transaction/{id}`). R5 proíbe expor o número gerado pelo banco.

## Decisão

- Toda tabela tem `id SERIAL` interno, que nunca sai da API.
- `pix_analysis.analysis_key CHAR(36)` é gerado no repository com `uuid4` e sai como `key`.
- O `id` do Pix é guardado em `pix_transaction.pix_id` com `UNIQUE`. Ele não viola R5: quem gerou foi quem chamou, não o nosso banco.
- `GET /pix/transaction/{id}` busca por `pix_id`, como pede o enunciado.

## Alternativas descartadas

- **Usar o `id` do Pix também como `key`.**
  - **Preço:** junta dois conceitos: se um dia houver reanálise, um Pix terá duas análises.
  - **Ganharia se** o contrato tivesse um campo só.
- **`key` sequencial.**
  - **Preço:** revela volume e permite enumerar análises (R5).
  - **Ganharia se** a API fosse só interna e sem auditoria.

## Consequências

- O DTO serializa `key`, `status` e `metadata`; nunca `id` nem FKs.
