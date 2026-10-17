---
title: Camadas do serviço
summary: O que cada pasta de src/ pode e não pode fazer, incluindo a pasta nova rules/, e onde mexer para cada tipo de mudança.
related: [visao-geral.md, ../05-motor/motor-de-regras.md, ../contribuindo.md]
sources: [bootcamp-base-api/docs/como-o-projeto-e-organizado.md, Aula 1 tarde]
---

# Camadas do serviço

> [Índice](../README.md) › Arquitetura › Camadas
>
> **Responde a:** em qual pasta mora cada coisa? quem pode chamar quem? onde fica o commit? onde mora uma regra antifraude?

O guia completo herdado da base está em [como o projeto é organizado](../referencia/como-o-projeto-e-organizado.md). Aqui fica o resumo e o que muda para o motor.

## Caminho de uma requisição

```
requisição
  → middlewares/    request_context → request_logger → internal_token (403) → session_manager
  → resources/      schema valida o corpo (400) e chama um controller
  → controllers/    orquestra: idempotência, contexto, regras, decisão, commit
      → repositories/   consultas e agregados de histórico
      → rules/          regras puras: (pix, contexto) → disparo ou nada
  → dtos/           objeto do banco → JSON
resposta
```

A dependência anda num sentido só: `resources → controllers → (repositories | rules)`. `rules/` não conhece `repositories/` e vice-versa.

## O que cada pasta pode e não pode

| Pasta | Pode | Não pode |
|---|---|---|
| `resources/` | receber a requisição, validar o schema, chamar o controller, escolher o status de sucesso (201 ou 200) | SQL, regra, `raise` |
| `schemas/` | descrever o JSON aceito (`additionalProperties: false`) | consultar banco, decidir |
| `controllers/` | buscar idempotência, montar o `RuleContext`, rodar as regras, agregar a decisão, gravar, dar `commit` | escrever SQL, conhecer HTTP |
| `rules/` | decidir se **uma** regra dispara, com o Pix, o contexto e seus parâmetros; cálculos compartilhados em `signals.py` | tocar banco, chamar `datetime.now()`, ler ambiente, ler o resultado de outra regra |
| `repositories/` | buscar, inserir, calcular agregados por janela | decidir se é fraude |
| `models/` | descrever tabelas | ter regra |
| `dtos/` | montar `{key, status, metadata}` | serializar `id` ou FK |
| `errors/` | código, mensagem e status de cada recusa | ter regra |
| `middlewares/` | agir em toda requisição | conhecer uma rota |
| `connectors/` | (sem uso neste projeto, [ADR 0002](decisoes/0002-monolito-sincrono-sem-dependencia-externa.md)) | — |
| `worker/` | cold path: jobs periódicos que leem o histórico e gravam scores (grafo, GraphSAGE, HMM), cada um com o próprio commit | ser chamado pela api; decidir um Pix |
| `utils/` | logger, request id, validação de schema, documento, estatística pura (`statistics.py`) | virar depósito |

Exemplo: `if pix.amount > self.max_night_amount_cents: return RuleResult(...)` mora em `src/rules/limit_night_amount_rule.py`. A consulta "soma dos Pix desse documento nas últimas 24h" mora no `pix_transaction_repository.py`. Quem junta as duas coisas é o controller.

## Commit

Uma transação de banco por requisição. O `commit` é a última linha do controller antes do `return`: Pix, análise e motivos entram juntos ou nada entra. O `session_manager` faz rollback em exceção e nunca dá commit.

## Onde mexer

| Quero… | Mexo em | Depois |
|---|---|---|
| regra antifraude nova | `src/rules/` + `src/constants.py` | registrar em `src/rules/__init__.py`, [catálogo](../05-motor/regras.md), README; skill [nova-regra](../../.agents/skills/nova-regra/SKILL.md) |
| sinal novo de histórico | `src/repositories/` | campo novo no `RuleContext`, montado no controller |
| calibrar parâmetro | `src/constants.py` (padrão) | [catálogo](../05-motor/regras.md), README, [CHANGELOG](../../CHANGELOG.md) |
| campo novo na entrada | `src/schemas/post_pix_transaction.json` | `database.sql` e `models/` se for coluna |
| campo novo na saída | `src/dtos/` | [rotas](../03-api/rotas.md) |
| recusa nova da API | `src/errors/custom_errors.py` | [erros](../03-api/erros.md); skill [novo-erro](../../.agents/skills/novo-erro/SKILL.md) |
| tabela ou índice | `database/database.sql` | `src/models/`, `make reset`, [modelo](../04-dados/modelo.md) |

## Armadilhas herdadas

| Sintoma | Causa | Correção |
|---|---|---|
| `ModuleNotFoundError` num arquivo novo | falta a linha no `__init__.py` da pasta | acrescentar |
| `relation "…" does not exist` | `database.sql` só roda quando o banco nasce | `make reset` (apaga os dados) |
| teste quebra depois de mudar `requirements.txt` | a dependência mora na imagem | `make rebuild` |
| `ImportError … partially initialized module` | ordem do `src/models/__init__.py` | enumerador antes de quem depende dele |
