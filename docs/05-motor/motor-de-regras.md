---
title: Motor de regras
summary: Como o motor transforma um Pix em decisão — peças no código, contrato de uma regra, passo a passo do POST e cada agregado de histórico que as regras recebem.
related: [regras.md, decisao.md, calibracao.md, ../02-arquitetura/decisoes/0004-motor-de-regras-em-codigo.md, ../02-arquitetura/decisoes/0005-regras-puras-com-contexto-carregado.md]
sources: [Desafio Antifraude Pix (seções 1 e 2), slides do hackathon ("Como o motor decide"), código em src/rules/]
---

# Motor de regras

> [Índice](../README.md) › Motor › Motor de regras
>
> **Responde a:** como o motor está estruturado? o que é uma regra no código? de onde vem o histórico?

**Estado:** implementado (fases F0–F4 do [plano](../plano-de-implementacao.md)).

## Em uma frase

O controller carrega o histórico relevante uma vez, passa o Pix e esse contexto por **todas** as 15 regras que decidem (e os 5 modelos em shadow, que só calculam), e a decisão final é a mais severa entre as que dispararam, com todos os motivos e os números de cada sinal no `metadata`.

## As peças

| Peça | Onde | Faz |
|---|---|---|
| `PixTransactionController.analyze` | `src/controllers/pix_transaction_controller.py` | Idempotência → `_build_snapshot` → `_build_context` → roda as regras → `_decide` → grava e dá o `commit` |
| `PixTransactionRepository` | `src/repositories/pix_transaction_repository.py` | Busca por `pix_id`; um método por agregado de janela; insere Pix, análise e motivos |
| `PixSnapshot` | `src/rules/pix_snapshot.py` | O Pix já parseado (datas com fuso), com `is_self_transfer` e `is_legal_entity_source` |
| `RuleContext` | `src/rules/rule_context.py` | Dataclass imutável com os agregados de histórico (tabela abaixo) |
| `BaseRule`, `RuleResult` | `src/rules/base_rule.py` | Contrato de toda regra |
| Severidade | `src/rules/decision.py` | `approved` 0, `two_factor_required` 1, `rejected` 2 |
| Sinais compartilhados | `src/rules/signals.py` | `amount_z` e `geo_speed_kmh`, usados pelas regras de perfil e pela tipologia de conta tomada |
| Estatística | `src/utils/statistics.py` | z robusto, cauda da binomial negativa, haversine; Python puro ([ADR 0016](../02-arquitetura/decisoes/0016-sinais-estatisticos-como-regras.md)) |
| `ACTIVE_RULES` | `src/rules/__init__.py` | Lista única das regras ligadas, já com os parâmetros de `src/constants.py` |

## Contrato de uma regra

```python
class CounterpartyNewAccountRule(BaseRule):
    code = "COUNTERPARTY_NEW_ACCOUNT"
    family = "counterparty"

    def evaluate(self, pix, context) -> RuleResult | None:
        if pix.is_self_transfer:
            return None
        age_days = (pix.transaction_date - pix.destination_opening_date).days
        if age_days >= self.min_age_days:
            return None
        ...
        return RuleResult(self.code, decision, f"Conta de destino aberta há {age_days} dias.", {"destination_age_days": age_days})
```

Regras não leem banco, ambiente nem relógio, e não leem o resultado de outra regra ([ADR 0005](../02-arquitetura/decisoes/0005-regras-puras-com-contexto-carregado.md), [ADR 0007](../02-arquitetura/decisoes/0007-relogio-da-transacao.md)).

## Passo a passo do `POST`

1. **Schema** valida o formato (400 se torto). Data impossível (`2026-02-30`) também é 400.
2. **Idempotência:** busca por `pix_id`. Mesmo corpo → 200 com a análise original. Corpo diferente → 409 ([ADR 0012](../02-arquitetura/decisoes/0012-idempotencia-pelo-id-do-pix.md)).
3. **Snapshot e contexto:** o repository calcula os agregados relativos ao `transaction_date`, sempre sobre Pix **anteriores** e excluindo o próprio.
4. **Regras:** as 15 que decidem rodam, mais os 5 modelos em shadow; cada uma devolve um disparo ou nada.
5. **Decisão:** a mais severa vence ([decisão](decisao.md)).
6. **Gravação:** `pix_transaction`, `pix_analysis` (com `rule_set_version`) e `pix_analysis_reason` no mesmo commit.
7. **Resposta:** 201 com `{key, status, metadata}`.

## Agregados do `RuleContext`

Janelas são `[t − N, t)` com `t = transaction_date`. "Tentativas" contam todos os status; somas e "conhecido" ignoram reprovados ([ADR 0021](../02-arquitetura/decisoes/0021-o-que-cada-janela-conta-e-versao-das-regras.md)).

| Agregado | Pergunta | Usado por |
|---|---|---|
| `source_attempts_last_velocity_window` | Quantas tentativas o pagador fez em 10 min? | `VELOCITY_SOURCE_COUNT` |
| `source_sum_last_24h_cents` | Quanto saiu (não reprovado) em 24 h? | modelos em shadow |
| `source_history_size` | O pagador tem histórico? | perfil, `COUNTERPARTY_FIRST_TIME_HIGH`, conta tomada |
| `device_seen_for_source` | Esse aparelho já foi usado por ele? | `PROFILE_NEW_DEVICE`, conta tomada |
| `destination_seen_for_source` | Ele já pagou esse destino (sem reprovação)? | `COUNTERPARTY_FIRST_TIME_HIGH` |
| `device_distinct_other_sources_last_24h` | Quantos outros pagadores usaram o aparelho em 24 h? | `VELOCITY_DEVICE_SOURCES` |
| `destination_distinct_other_sources_last_1h` | Quantos outros pagadores mandaram para o destino em 1 h? | `COUNTERPARTY_FAN_IN`, `TYPOLOGY_MULE` |
| `source_amounts_last_30d_cents` | Qual o perfil de valor do pagador? | `PROFILE_AMOUNT_ROBUST_Z`, conta tomada |
| `source_attempts_poisson_window`, `source_attempts_poisson_lookback`, `source_first_seen` | A rajada atual é improvável para o ritmo dele? | `VELOCITY_POISSON_GAMMA` |
| `source_last_geolocation` | Onde e quando foi o Pix anterior com GPS? | `PROFILE_GEO_VELOCITY`, conta tomada |
| destinos novos e tentativas pequenas em 24 h | Está fracionando para contas novas? | modelos em shadow |
| `destination_rejected_by_others_last_window` | O destino recebeu Pix reprovado de outros em 7 dias? | modelos em shadow |
| `destination_graph_risk` (e idade do score) | Qual a reputação do destino no grafo, calculada pelo worker nos últimos 120 min? | `COUNTERPARTY_GRAPH_RISK` |
| `destination_graphsage_score`, `source_sequence_score` | O que o GraphSAGE e o HMM do worker dizem do destino e da sequência do pagador? | modelos em shadow |

As regras, os parâmetros e o porquê de cada um estão no [catálogo](regras.md); a calibração, em [calibracao.md](calibracao.md).
