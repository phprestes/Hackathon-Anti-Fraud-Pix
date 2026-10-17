---
title: Motor de regras
summary: Como o motor transforma um Pix em decisão — contrato de uma regra, RuleContext, ordem de execução e onde cada peça mora.
related: [regras.md, decisao.md, ../02-arquitetura/decisoes/0004-motor-de-regras-em-codigo.md, ../02-arquitetura/decisoes/0005-regras-puras-com-contexto-carregado.md]
sources: [Desafio Antifraude Pix (seções 1 e 2), slides do hackathon ("Como o motor decide")]
---

# Motor de regras

> [Índice](../README.md) › Motor › Motor de regras
>
> **Responde a:** como o motor está estruturado? o que é uma regra no código? de onde vem o histórico?

**Estado:** proposta ([ADR 0004](../02-arquitetura/decisoes/0004-motor-de-regras-em-codigo.md) a [ADR 0008](../02-arquitetura/decisoes/0008-parametros-de-regra-por-ambiente.md)).

## Em uma frase

O controller carrega o histórico relevante uma vez, passa o Pix e esse contexto por **todas** as regras, e a decisão final é a mais severa entre as que dispararam, com todos os motivos no `metadata`.

## As peças

| Peça | Onde | Faz |
|---|---|---|
| `PixTransactionController.analyze` | `src/controllers/pix_transaction_controller.py` | Orquestra os passos abaixo e dá o `commit` |
| `PixTransactionRepository` | `src/repositories/pix_transaction_repository.py` | Busca por `pix_id`; agregados por janela; insere Pix, análise e motivos |
| `RuleContext` | `src/rules/rule_context.py` | Dataclass imutável com os agregados de histórico |
| `BaseRule` e `RuleResult` | `src/rules/base_rule.py` | Contrato de toda regra |
| Uma regra | `src/rules/<familia>_<sinal>_rule.py` | `evaluate(pix, context) -> RuleResult | None` |
| `ACTIVE_RULES` | `src/rules/__init__.py` | Lista única das regras ligadas, com os parâmetros de `src/constants.py` |

## Contrato de uma regra

```python
class CounterpartyNewAccountRule(BaseRule):
    code = "COUNTERPARTY_NEW_ACCOUNT"
    family = "counterparty"

    def __init__(self, min_age_days: int) -> None:
        self.min_age_days = min_age_days

    def evaluate(self, pix, context) -> RuleResult | None:
        age_days = (pix.transaction_date - pix.destination_opening_date).days
        if age_days >= self.min_age_days:
            return None
        return RuleResult(self.code, TWO_FACTOR_REQUIRED, f"Conta de destino aberta há {age_days} dias.")
```

Regras não leem banco, ambiente nem relógio ([ADR 0005](../02-arquitetura/decisoes/0005-regras-puras-com-contexto-carregado.md), [ADR 0007](../02-arquitetura/decisoes/0007-relogio-da-transacao.md)).

## Passo a passo do `POST`

1. **Schema** valida o formato (400 se torto).
2. **Idempotência:** busca por `pix_id`. Mesmo corpo → 200 com a análise original. Corpo diferente → 409 ([ADR 0012](../02-arquitetura/decisoes/0012-idempotencia-pelo-id-do-pix.md)).
3. **Contexto:** o repository calcula os agregados que as regras ativas usam, relativos ao `transaction_date` e excluindo o próprio Pix.
4. **Regras:** todas rodam; cada uma devolve um disparo ou nada.
5. **Decisão:** a mais severa vence ([decisão](decisao.md)).
6. **Gravação:** `pix_transaction`, `pix_analysis` e `pix_analysis_reason` no mesmo commit.
7. **Resposta:** 201 com `{key, status, metadata}`.

## Sinais disponíveis

Do payload: valor, data/hora com fuso, idade das duas contas, documentos (CPF ou CNPJ), ISPB de destino, aparelho, canal, IP, geolocalização.

Do histórico (agregados candidatos para o `RuleContext`):

| Agregado | Pergunta |
|---|---|
| `source_count_last_<janela>` | Quantos Pix esse pagador fez na janela? |
| `source_sum_last_24h_cents` | Quanto esse pagador já mandou hoje? |
| `source_avg_amount_last_30d_cents`, `source_history_size` | Qual o padrão de valor do pagador, e há histórico suficiente para ter padrão? |
| `device_seen_for_source` | Esse aparelho já foi usado por esse pagador? |
| `device_distinct_sources_last_24h` | Quantos pagadores diferentes usaram esse aparelho? |
| `destination_seen_for_source` | O pagador já mandou para esse destino? |
| `destination_distinct_sources_last_1h` | Quantos pagadores diferentes mandaram para esse destino? |
| `last_geolocation`, `last_transaction_date` | Onde e quando foi o Pix anterior do pagador? |

As regras e os parâmetros estão no [catálogo](regras.md).
