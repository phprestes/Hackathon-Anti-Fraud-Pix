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
| `rules/` | decidir se **uma** regra dispara, com o Pix, o contexto e seus parâmetros; cálculos compartilhados em `core/signals.py` | tocar banco, chamar `datetime.now()`, ler ambiente, ler o resultado de outra regra |
| `repositories/` | buscar, inserir, calcular agregados por janela | decidir se é fraude |
| `models/` | descrever tabelas | ter regra |
| `dtos/` | montar `{key, status, metadata}` | serializar `id` ou FK |
| `errors/` | código, mensagem e status de cada recusa | ter regra |
| `middlewares/` | agir em toda requisição | conhecer uma rota |
| `connectors/` | (sem uso neste projeto, [ADR 0002](decisoes/0002-monolito-sincrono-sem-dependencia-externa.md)) | — |
| `worker/` | cold path: jobs periódicos que leem o histórico e gravam scores (grafo, GraphSAGE, HMM), cada um com o próprio commit | ser chamado pela api; decidir um Pix |
| `utils/` | logger, request id, validação de schema, documento, estatística pura (`statistics.py`) | virar depósito |

Exemplo: `if pix.amount > self.max_night_amount_cents: return RuleResult(...)` mora em `src/rules/limit/limit_night_amount_rule.py`. A consulta "soma dos Pix desse documento nas últimas 24h" mora no `pix_transaction_repository.py`. Quem junta as duas coisas é o controller.

## Commit

Uma transação de banco por requisição. O `commit` é a última linha do controller antes do `return`: Pix, análise e motivos entram juntos ou nada entra. O `session_manager` faz rollback em exceção e nunca dá commit.

## Onde mexer

| Quero… | Mexo em | Depois |
|---|---|---|
| regra antifraude nova | `src/rules/<familia>/` + `src/constants.py` | registrar em `src/rules/__init__.py`, [catálogo](../05-motor/regras.md), README; skill [nova-regra](../../.agents/skills/nova-regra/SKILL.md) |
| sinal novo de histórico | `src/repositories/` | campo novo no `RuleContext`, montado no controller |
| calibrar parâmetro | `src/constants.py` (padrão) | [catálogo](../05-motor/regras.md), README, [CHANGELOG](../../CHANGELOG.md) |
| campo novo na entrada | `src/schemas/post_pix_transaction.json` | `database.sql` e `models/` se for coluna |
| campo novo na saída | `src/dtos/` | [rotas](../03-api/rotas.md) |
| recusa nova da API | `src/errors/custom_errors.py` | [erros](../03-api/erros.md); skill [novo-erro](../../.agents/skills/novo-erro/SKILL.md) |
| tabela ou índice | `database/database.sql` | `src/models/`, `make reset`, [modelo](../04-dados/modelo.md) |

## Onde fica o quê

| Caminho | O quê |
|---|---|
| `src/rules/__init__.py` | `build_rules`, `ACTIVE_RULES` e `PARAMETERS`: a ordem da lista desempata motivos de mesma severidade |
| `src/rules/core/` | motor (`engine.py`), `BaseRule`, decisão, `PixSnapshot`, `RuleContext`, `HistoryPort`, features dos modelos e sinais compartilhados (`signals.py`) |
| `src/rules/limit/`, `velocity/`, `profile/`, `counterparty/`, `typology/` | uma regra por arquivo, `<familia>_<sinal>_rule.py` |
| `src/rules/models/` | avaliadores em Python puro (`logreg`, `gbdt`, `iforest`), regras shadow e `artifacts/*.json` |
| `src/utils/statistics.py` | estatística pura (z robusto, cauda Poisson-Gama, haversine); fica em `utils/` porque os scripts de análise também a usam |
| `src/worker/jobs/` | os três jobs do cold path (grafo, GraphSAGE, HMM) |
| `src/worker/models/` | GraphSAGE, HMM e score de grafo em numpy, leitura dos artefatos e `artifacts/*.json` |
| `scripts/fixture/` | simulador do CI, replay pela API, relatório e cliente HTTP |
| `scripts/backtest/` | backtest em memória, `InMemoryHistory`, paridade API x backtest, modelo de custo |
| `scripts/calibration/` | grid de parâmetros, trava do CI (`calibration-gate.json`) e ablação por regra |
| `scripts/pixsim/` | setup, exportação, adaptador, relatório, scores e waterfall do PixSim |
| `scripts/models/` | features, treino e paridade dos modelos, rótulos atrasados |
| `scripts/feedback/`, `scripts/analysis/` | retroalimentação pelo MED e análises estatísticas |

Os scripts se importam pelo nome do módulo: cada um começa importando `scripts/_paths.py`, que põe `src/` e as pastas de `scripts/` no `sys.path`. A saída continua em `scripts/out/`.

## Ordem dos middlewares

O último middleware registrado em `src/app.py` é o primeiro a rodar, então as quatro linhas de registro são o diagrama acima de trás para frente. Cada posição tem um porquê, e nenhum teste guarda esta ordem:

- o identificador (`request_context`) vem antes do log, senão as linhas da requisição saem com `[-]` no lugar do id;
- o log vem antes do token, para que a tentativa recusada com 403 também apareça (mil delas seguidas é alguém adivinhando o token);
- a sessão de banco é a mais interna: quem leva 403 não chega a ter sessão.

Para ver: troque as duas últimas linhas de lugar, chame uma rota e rode `docker compose logs api | grep request_logger | tail -2`.

## Sessão por requisição

- O middleware `session_manager` abre um contexto vazio (`contextvars`), faz `rollback` em exceção, `close` sempre e **nunca** `commit`: quem sabe se o trabalho terminou é o controller.
- A sessão é preguiçosa: nasce quando um controller é construído. `/` e `/health_check` não constroem controller, então não dependem do banco. Por isso todo `rollback`/`close` pergunta antes se a sessão existe.
- O contexto guarda um objeto mutável, não a sessão direto: a task filha só vê uma cópia do `ContextVar`, e um `.set()` feito na rota seria invisível para o `finally` do middleware (uma conexão vazada por requisição).
- Custo: a sessão virou ambiente. O combinado é que só controllers chamam `get_context()`. Uma rota que devolvesse um fluxo lendo do banco aos poucos acharia a sessão já fechada.
- `SessionLocal()` não conecta; a conexão sai do pool no primeiro SQL.

O desenho veio do Base Service, que trocou a dependency `get_db` do FastAPI por middleware e depois por contexto.

## Outras escolhas herdadas

- **JSON Schema, não Pydantic:** o contrato de entrada é um arquivo `.json` que quem integra lê sem abrir o código; o custo é o corpo chegar como `dict` cru.
- **Request id:** `X-Request-ID` é a convenção que proxies já leem; o id recebido só é aceito por `fullmatch` em `[A-Za-z0-9_-]{1,64}` (log injection) e volta no cabeçalho da resposta. Mora em `utils/` porque o logger precisa dele e importar `middlewares/` fecharia um ciclo.
- **Log:** nunca o corpo (dado sensível); a query string entra, então segredo viaja em cabeçalho.
- **Token:** o middleware devolve o 403 em vez de levantar, porque os exception handlers rodam mais para dentro.

## Armadilhas herdadas

| Sintoma | Causa | Correção |
|---|---|---|
| `ModuleNotFoundError` num arquivo novo | falta a linha no `__init__.py` da pasta | acrescentar |
| `relation "…" does not exist` | `database.sql` só roda quando o banco nasce | `make reset` (apaga os dados) |
| teste quebra depois de mudar `requirements.txt` | a dependência mora na imagem | `make rebuild` |
| `ImportError … partially initialized module` | ordem do `src/models/__init__.py` | enumerador antes de quem depende dele |
