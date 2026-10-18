---
title: "ADR 0001: Partir do bootcamp-base-api da Aula 1"
summary: O repositório nasce de uma cópia do bootcamp-base-api; camadas, middlewares, erros e testes black box são herdados sem reescrita.
related: [../visao-geral.md, ../camadas.md, ../../referencia/base-service-readme.md]
sources: [Desafio Antifraude Pix (seções 4 e 5), Aula 1 (bootcamp-base-api)]
---

# ADR 0001: Partir do bootcamp-base-api da Aula 1

> [Índice](../../README.md) › [Decisões](README.md) › 0001

**Status:** aceita

## Contexto

O enunciado diz "Ponto de partida: o Base Service" e avalia "alinhamento com o Base Service, camadas corretamente aplicadas" (critério 2). Existem três candidatos: o `bootcamp-base-api` da Aula 1, a `bootcamp-biblioteca-api` da Aula 3 e o banco digital da fase 1.

## Decisão

Copiar o `bootcamp-base-api` da Aula 1 para a raiz do repositório e construir em cima dele:

- Camadas, `app.py`, middlewares (`X-Request-ID`, log, `INTERNAL-TOKEN`, sessão), `SchemaHandler`, erros `QIT000xxx` e a checagem de código duplicado no boot ficam como estão.
- O exemplo `sample_entity` ficou no código até a primeira rota `/pix/transaction` substituí-lo, para a suíte herdada seguir verde e servir de referência; foi removido quando a rota do Pix entrou.
- O README original vai para [`docs/referencia/base-service-readme.md`](../../referencia/base-service-readme.md); o guia de pastas, para [`docs/referencia/como-o-projeto-e-organizado.md`](../../referencia/como-o-projeto-e-organizado.md).

## Alternativas descartadas

- **Partir do banco digital da fase 1.**
  - **Preço:** traz `customer`, `account`, saldo e MockServer, que o enunciado põe fora do escopo ("Onboarding e cadastro de contas", "Outras APIs"). Seria código para apagar antes de começar.
  - **Ganharia se** o desafio exigisse mover o saldo além de decidir.
- **Partir da biblioteca-api da Aula 3.**
  - **Preço:** é um domínio de exemplo, não o Base Service citado no enunciado.
  - **Ganharia se** a banca avaliasse aderência à Aula 3.
- **Projeto do zero.**
  - **Preço:** perde o critério 2 e as horas de infraestrutura já resolvidas.
  - **Ganharia se** o Base Service não tivesse a stack pedida.

## Consequências

- Mesma stack: Python 3.11, FastAPI, SQLAlchemy 2, PostgreSQL 16, jsonschema, Docker Compose.
- Remover o `sample_entity` foi registrado no [CHANGELOG](../../../CHANGELOG.md), junto com os códigos `QIT001xxx`.
