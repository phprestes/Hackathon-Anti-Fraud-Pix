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

```json
{
  "key": "b3f1c2e0-7d4a-4c1e-9a52-1f0e6c9d2a77",
  "status": "two_factor_required",
  "metadata": {
    "rule_set_version": "2026.10.17-f2",
    "signals": {"COUNTERPARTY_NEW_ACCOUNT": {"destination_age_days": 7}},
    "reasons": [
      {
        "rule": "COUNTERPARTY_NEW_ACCOUNT",
        "decision": "two_factor_required",
        "reason": "Conta de destino aberta há 7 dias."
      }
    ]
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
| `rule_set_version` | string | Versão do conjunto de regras que decidiu ([ADR 0021](../02-arquitetura/decisoes/0021-o-que-cada-janela-conta-e-versao-das-regras.md)) |

O enunciado deixa o `metadata` livre; campos novos entram aqui primeiro.

## `GET /pix/transaction/{id}`

`{id}` é o `id` do Pix enviado no POST, não a `key`. Devolve o mesmo corpo que o POST devolveu, lido do banco sem recalcular.
