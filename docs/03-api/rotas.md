---
title: Rotas
summary: Contrato completo da API: entrada, saídas com status e código QIT, idempotência e formato do metadata.
related: [erros.md, ../01-contexto/enunciado.md, ../02-arquitetura/decisoes/0003-decisao-antifraude-e-dado-nao-erro-http.md]
sources: [Desafio Antifraude Pix (seção 3), bootcamp-base-api (rotas herdadas)]
---

# Rotas

> [Índice](../README.md) › API › Rotas
>
> **Responde a:** quais rotas existem? o que entra, o que sai, com que status? o que acontece se repetir?

Toda rota, exceto `/` e `/health_check`, exige o header `INTERNAL-TOKEN` (403 `QIT000002` sem ele). Erros seguem `{title, description, translation, code}` ([erros](erros.md)).

## Tabela

| Método e rota | Faz | Sucesso | Recusas | Idempotência | Estado |
|---|---|---|---|---|---|
| `GET /` | identifica o serviço | 200 | — | sim | herdada |
| `GET /health_check` | diz se a API está de pé | 204 | — | sim | herdada |
| `POST /pix/transaction` | analisa e grava um Pix | 201 `{key, status, metadata}`; 200 se o `id` já foi analisado com o mesmo corpo | 400 `QIT000001`; 409 `QIT002002` | pelo `id` do Pix ([ADR 0012](../02-arquitetura/decisoes/0012-idempotencia-pelo-id-do-pix.md)) | implementada |
| `GET /pix/transaction/{id}` | devolve a análise gravada | 200 `{key, status, metadata}` | 404 `QIT002001` | sim | implementada |

As rotas `/sample_entity*` do Base Service foram removidas quando a rota do Pix entrou ([ADR 0001](../02-arquitetura/decisoes/0001-partir-do-base-service.md)).

## `POST /pix/transaction`

Entrada: o payload da [seção 3.1 do enunciado](../01-contexto/enunciado.md#31-entrada), validado por `src/schemas/post_pix_transaction.json` ([ADR 0013](../02-arquitetura/decisoes/0013-contrato-em-json-schema.md)).

As três decisões saem com o mesmo status HTTP; o que muda é o campo `status` ([ADR 0003](../02-arquitetura/decisoes/0003-decisao-antifraude-e-dado-nao-erro-http.md)).

Resposta real para o payload de [`exemplo-pix.json`](exemplo-pix.json) (Pix noturno de R$ 1.500 para uma conta de 7 dias), lida pelo `GET`, com a API no conjunto `2026.10.18-pixsim`:

```json
{
  "key": "4f26213a-9939-4b05-ab03-8edd2349a94f",
  "status": "two_factor_required",
  "metadata": {
    "shadow": [
      {
        "rule": "MODEL_LOGREG",
        "reason": "Modelo logreg deu score 0.6379 (limiar 0.1899); só observação.",
        "signals": {
          "score": 0.637872,
          "threshold": 0.18993193264537966
        },
        "would_decide": "two_factor_required"
      },
      {
        "rule": "MODEL_LIGHTGBM",
        "reason": "Modelo gbdt deu score 0.0043 (limiar 0.9404); só observação.",
        "signals": {
          "score": 0.004325,
          "threshold": 0.9403942827735305
        },
        "would_decide": "approved"
      },
      {
        "rule": "MODEL_IFOREST",
        "reason": "Modelo iforest deu score 0.5511 (limiar 0.5895); só observação.",
        "signals": {
          "score": 0.551135,
          "threshold": 0.5894942881464827
        },
        "would_decide": "approved"
      }
    ],
    "reasons": [
      {
        "rule": "LIMIT_NIGHT_AMOUNT",
        "reason": "Pix de R$ 1500.00 às 22h acima do limite noturno de R$ 1000.00.",
        "decision": "two_factor_required"
      },
      {
        "rule": "COUNTERPARTY_NEW_ACCOUNT",
        "reason": "Conta de destino aberta há 7 dias.",
        "decision": "two_factor_required"
      }
    ],
    "signals": {
      "LIMIT_NIGHT_AMOUNT": {
        "local_hour": 22,
        "limit_cents": 100000,
        "amount_cents": 150000
      },
      "COUNTERPARTY_NEW_ACCOUNT": {
        "destination_age_days": 7
      }
    },
    "features": {
      "amount": 150000,
      "weekday": 5,
      "local_hour": 22,
      "log_amount": 11.918391,
      "amount_robust_z": 0.0,
      "has_geolocation": 1,
      "source_age_days": 594,
      "history_30d_size": 0,
      "is_self_transfer": 0,
      "poisson_tail_log10": 0.0,
      "source_history_size": 0,
      "destination_age_days": 7,
      "source_sequence_score": -1,
      "destination_graph_risk": -1,
      "device_seen_for_source": 0,
      "hours_since_first_seen": -1,
      "is_legal_entity_source": 0,
      "destination_used_before": 0,
      "history_30d_median_cents": 0,
      "km_since_last_geolocation": -1,
      "source_sum_last_24h_cents": 0,
      "destination_graphsage_score": -1,
      "destination_seen_for_source": 0,
      "source_attempts_poisson_window": 0,
      "source_small_attempts_last_24h": 0,
      "source_attempts_poisson_lookback": 0,
      "source_new_destinations_last_24h": 0,
      "speed_kmh_since_last_geolocation": -1,
      "destination_graph_risk_age_minutes": -1,
      "source_attempts_last_velocity_window": 0,
      "device_distinct_other_sources_last_24h": 0,
      "destination_distinct_other_sources_last_1h": 0,
      "destination_rejected_by_others_last_window": 0
    },
    "rule_set_version": "2026.10.18-pixsim"
  }
}
```

### Formato do `metadata`

| Campo | Tipo | Conteúdo |
|---|---|---|
| `reasons` | lista | Um item por regra disparada, do mais severo ao menos severo. Vazia em `approved` |
| `reasons[].rule` | string | Código estável da regra ([catálogo](../05-motor/regras.md)) |
| `reasons[].decision` | string | `two_factor_required` ou `rejected` |
| `reasons[].reason` | string | Frase em português para quem atende o cliente |
| `signals` | objeto | Por código de regra disparada, os números que ela usou (idade da conta, contagem na janela, z, km/h…) |
| `features` | objeto | O vetor de 33 features numéricas do Pix, montado do mesmo contexto das regras (nada identificável); é a fonte dos dados de treino ([ADR 0023](../02-arquitetura/decisoes/0023-motor-extraido-e-history-port.md)). Valor `-1` quer dizer "sem dado" (sem geolocalização anterior, sem score do worker) |
| `shadow` | lista | Um item por modelo em shadow que rodou (`MODEL_LOGREG`, `MODEL_LIGHTGBM`, `MODEL_IFOREST`, e `MODEL_GRAPHSAGE` e `MODEL_SEQUENCE_HMM` quando há score do worker): `rule`, `would_decide` (o que decidiria), `reason` e `signals` (`score` e `threshold`). Nunca muda o `status` ([ADR 0022](../02-arquitetura/decisoes/0022-shadow-mode.md)) |
| `rule_set_version` | string | Versão do conjunto de regras que decidiu ([ADR 0021](../02-arquitetura/decisoes/0021-o-que-cada-janela-conta-e-versao-das-regras.md)) |

O enunciado deixa o `metadata` livre; campos novos entram aqui primeiro.

## `GET /pix/transaction/{id}`

`{id}` é o `id` do Pix enviado no POST, não a `key`. Devolve o mesmo corpo que o POST devolveu, lido do banco sem recalcular.
