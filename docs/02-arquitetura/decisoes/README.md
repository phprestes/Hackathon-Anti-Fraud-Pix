---
title: Registro de decisões (ADRs)
summary: Índice das decisões de arquitetura, uma por arquivo, cada uma com alternativas descartadas e o preço de cada uma.
related: [../visao-geral.md, ../../../CHANGELOG.md]
sources: [Modelo de RFC (Aula 2), Desafio Antifraude Pix (seção 5)]
---

# Decisões de arquitetura

> [Índice](../../README.md) › Arquitetura › Decisões
>
> **Responde a:** por que o sistema é assim? o que foi descartado e quanto custava?

Uma decisão por arquivo, sempre no mesmo formato: **Contexto → Decisão → Alternativas descartadas** (cada uma com *Preço* e *Ganharia se*) **→ Consequências**. Escritas no presente. Este registro substitui a RFC ([ADR 0015](0015-changelog-e-adrs-no-lugar-da-rfc.md)).

**Status:** `proposta` = combinada, ainda sem código; `aceita` = em vigor no código; `substituída por NNNN` = não vale mais (o arquivo fica, R4).

| ADR | Decisão | Tema | Status |
|---|---|---|---|
| [0001](0001-partir-do-base-service.md) | Partir do `bootcamp-base-api` da Aula 1 | Base | aceita |
| [0002](0002-monolito-sincrono-sem-dependencia-externa.md) | Uma API síncrona (`api` + `db`), sem dependência externa no caminho da decisão | Ecossistema | aceita |
| [0003](0003-decisao-antifraude-e-dado-nao-erro-http.md) | A decisão é dado da resposta (201 para as três), não erro HTTP | API | aceita |
| [0004](0004-motor-de-regras-em-codigo.md) | Regras em código, uma classe por regra em `src/rules/` | Motor | aceita |
| [0005](0005-regras-puras-com-contexto-carregado.md) | Regra pura; o controller carrega o `RuleContext` uma vez | Motor | aceita |
| [0006](0006-pior-decisao-vence-e-todas-as-regras-rodam.md) | Todas as regras rodam; a decisão mais severa vence | Motor | aceita |
| [0007](0007-relogio-da-transacao.md) | O relógio das regras é o `transaction_date` | Motor | aceita |
| [0008](0008-parametros-de-regra-por-ambiente.md) | Parâmetros de regra em `src/constants.py`, lidos do ambiente | Motor | aceita |
| [0009](0009-historico-append-only.md) | Histórico append-only: colunas tipadas + payload JSONB | Dados | aceita |
| [0010](0010-dinheiro-em-centavos.md) | Dinheiro em `BIGINT` de centavos | Dados | aceita |
| [0011](0011-uuid-key-publica.md) | `id` interno, `key` UUID na saída, `id` do Pix na consulta | Dados | aceita |
| [0012](0012-idempotencia-pelo-id-do-pix.md) | Idempotência pelo `id` do Pix (200 replay, 409 conflito) | API | aceita |
| [0013](0013-contrato-em-json-schema.md) | Contrato de entrada em JSON Schema fechado | API | aceita (herdada) |
| [0014](0014-repositorio-ai-friendly.md) | `AGENTS.md` + `.agents/skills/` + `llms.txt` | Processo | aceita |
| [0015](0015-changelog-e-adrs-no-lugar-da-rfc.md) | `CHANGELOG.md` + ADRs no lugar da RFC | Processo | aceita |
| [0016](0016-sinais-estatisticos-como-regras.md) | Sinais estatísticos (z robusto, Poisson–Gamma, viagem impossível) como regras, em Python puro | Motor | aceita |
| [0017](0017-ml-fora-do-prazo-e-do-hot-path.md) | ML, grafos e LLM fora desta entrega; viram roadmap | Motor | aceita |
| [0018](0018-regras-compostas-por-tipologia.md) | Regras compostas por tipologia de golpe no lugar de score ponderado | Motor | aceita |
| [0019](0019-reputacao-de-contraparte-derivada.md) | Reputação de contraparte derivada do próprio histórico | Motor | aceita |
| [0020](0020-simulador-para-calibracao.md) | Simulador de tráfego para calibrar parâmetros e medir P95 | Processo | aceita |
| [0021](0021-o-que-cada-janela-conta-e-versao-das-regras.md) | O que cada janela conta, redutores de fricção e `rule_set_version` | Motor | aceita |

Decisão nova: siga a [skill nova-decisao](../../../.agents/skills/nova-decisao/SKILL.md). Ela adiciona a linha aqui, no [`llms.txt`](../../../llms.txt) e no [CHANGELOG](../../../CHANGELOG.md).
