---
title: "ADR 0013: Contrato de entrada em JSON Schema fechado"
summary: post_pix_transaction.json valida o formato com additionalProperties false em todos os níveis; regra de negócio não mora no schema.
related: [../camadas.md, ../../03-api/rotas.md]
sources: [bootcamp-base-api (SchemaHandler, jsonschema 4.17.3), Projeto fase 1 (ADR de contrato)]
---

# ADR 0013: Contrato de entrada em JSON Schema fechado

> [Índice](../../README.md) › [Decisões](README.md) › 0013

**Status:** aceita (herdada do Base Service)

## Contexto

O payload do Pix tem três níveis de objetos aninhados. O Base Service valida corpo e query com `@SchemaHandler.validate("<arquivo>.json")` e `jsonschema`, antes de a rota rodar.

## Decisão

- `src/schemas/post_pix_transaction.json` descreve o payload da seção 3.1 do [enunciado](../../01-contexto/enunciado.md), com `additionalProperties: false` em cada objeto.
- Obrigatórios: tudo, menos `source.geolocation`. `amount` inteiro `>= 1`; datas com `format: date-time`; documento com padrão de CPF ou CNPJ mascarado; latitude e longitude com faixa.
- Formato inválido é 400 `QIT000001`. Dígito verificador de CPF/CNPJ, se o time quiser checar, é regra (sinal de fraude), não schema.

## Alternativas descartadas

- **Pydantic, que o FastAPI já traz.**
  - **Preço:** foge do padrão do Base Service (critério 2) e dos serviços da QI.
  - **Ganharia se** o projeto não tivesse base nenhuma.

## Consequências

- Campo novo no payload muda o schema primeiro; o teste de "campo desconhecido devolve 400" protege o contrato.
