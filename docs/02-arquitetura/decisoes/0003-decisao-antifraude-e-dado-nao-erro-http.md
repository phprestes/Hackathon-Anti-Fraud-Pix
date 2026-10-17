---
title: "ADR 0003: A decisão antifraude é dado da resposta, não erro HTTP"
summary: approved, rejected e two_factor_required saem todas com 201 e o mesmo corpo; os erros QIT ficam para pedido inválido ou conflito.
related: [../../03-api/rotas.md, ../../03-api/erros.md, ../../05-motor/decisao.md]
sources: [Desafio Antifraude Pix (seções 3.3 e 3.4)]
---

# ADR 0003: A decisão antifraude é dado da resposta, não erro HTTP

> [Índice](../../README.md) › [Decisões](README.md) › 0003

**Status:** aceita

## Contexto

O contrato tem um único formato de saída: `{key, status, metadata}`. Um Pix reprovado foi analisado e gravado com sucesso; o que foi recusado é o Pix, não a requisição. O Base Service tem erros com código `QIT`, e a tentação é devolver `rejected` como 422.

## Decisão

- `POST /pix/transaction` devolve **201** com `{key, status, metadata}` para as três decisões.
- Erros `QIT` (R3) ficam para o que impede a análise: corpo fora do schema (400), token ausente (403), `id` repetido com corpo diferente (409), `id` inexistente no GET (404).
- `status` é o campo que quem chama lê para seguir, pedir 2FA ou bloquear.

## Alternativas descartadas

- **`rejected` como 422 e `two_factor_required` como 428 ou 401.**
  - **Preço:** dois formatos de corpo para a mesma coisa (análise), e o `rejected` some do `GET` se for tratado como erro. Quem chama precisa de dois caminhos de parsing.
  - **Ganharia se** a API estivesse no caminho da liquidação e um não-2xx precisasse abortar a transferência sozinho.
- **200 em vez de 201.**
  - **Preço:** perde a distinção entre "analisei agora" (201) e "devolvi a análise que já existia" (200, [ADR 0012](0012-idempotencia-pelo-id-do-pix.md)).
  - **Ganharia se** não houvesse idempotência.

## Consequências

- O teste de cada regra confere `status` e `metadata`, não o código HTTP.
- O `GET` devolve exatamente o mesmo corpo do `POST`.
