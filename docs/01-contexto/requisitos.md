---
title: Requisitos e critérios de avaliação
summary: O que o enunciado exige, as regras herdadas do bootcamp que continuam valendo e onde o projeto atende cada critério da banca.
related: [enunciado.md, problema.md, ../07-testes/estrategia.md]
sources: [Desafio Antifraude Pix (seções 3 a 7), Projeto da fase 1 (R1–R8)]
---

# Requisitos

> [Índice](../README.md) › Contexto › Requisitos
>
> **Responde a:** o que o enunciado exige? o que a banca observa? quais regras do bootcamp continuam valendo?

## Exigências do enunciado (E1–E8)

| # | Exigência | Onde o projeto atende |
|---|---|---|
| E1 | `POST /pix/transaction` recebe o payload da seção 3.1 do [enunciado](enunciado.md) | [rotas](../03-api/rotas.md) |
| E2 | A saída tem `key`, `status` (`approved`, `rejected`, `two_factor_required`) e `metadata` livre | [rotas](../03-api/rotas.md), [ADR 0003](../02-arquitetura/decisoes/0003-decisao-antifraude-e-dado-nao-erro-http.md) |
| E3 | `GET /pix/transaction/{id}` devolve a análise gravada | [rotas](../03-api/rotas.md) |
| E4 | Banco próprio com o histórico de tudo que chegou | [modelo](../04-dados/modelo.md), [ADR 0009](../02-arquitetura/decisoes/0009-historico-append-only.md) |
| E5 | Regras antifraude e testes | [regras](../05-motor/regras.md), [estratégia de testes](../07-testes/estrategia.md) |
| E6 | Toda decisão sai com um motivo explicável | [decisão](../05-motor/decisao.md) |
| E7 | Repositório a partir do Base Service, nos padrões do bootcamp | [ADR 0001](../02-arquitetura/decisoes/0001-partir-do-base-service.md), [camadas](../02-arquitetura/camadas.md) |
| E8 | README no modelo da seção 6 do enunciado, com o porquê de cada parâmetro | [README](../../README.md) |

## Regras herdadas do bootcamp (R1–R6)

Vieram da fase 1 e do Base Service. Continuam valendo porque a banca avalia "alinhamento com o Base Service" (critério 2).

| # | Regra | Como o projeto atende |
|---|---|---|
| R1 | Teste nunca importa de `src/` nem lê o banco; o cenário nasce pela API | Testes black box por HTTP ([estratégia](../07-testes/estrategia.md)) |
| R2 | Um comando sobe tudo numa máquina Linux limpa | `make all` ([rodando localmente](../06-operacao/rodando-localmente.md)) |
| R3 | Toda recusa tem corpo `{title, description, translation, code}` com código `QIT` único | [erros](../03-api/erros.md) |
| R4 | Nada que entrou deixa de existir (append-only) | [ADR 0009](../02-arquitetura/decisoes/0009-historico-append-only.md) |
| R5 | Nenhum identificador gerado pelo banco sai da API | [ADR 0011](../02-arquitetura/decisoes/0011-uuid-key-publica.md) |
| R6 | Dinheiro é `BIGINT` em centavos, nunca float | [ADR 0010](../02-arquitetura/decisoes/0010-dinheiro-em-centavos.md) |

## Critérios da banca → onde mostrar

| # | Critério | Evidência no repositório |
|---|---|---|
| 1 | Profundidade antifraude | [regras.md](../05-motor/regras.md): cada regra com sinal, parâmetro e porquê; tabela "Por quê" do README |
| 2 | Padrão de código | [camadas](../02-arquitetura/camadas.md), `make lint`, testes black box com os dois caminhos de cada `if` |
| 3 | Modelagem de dados | [modelo](../04-dados/modelo.md) e `database/database.sql` |
| 4 | Solução funcional | `make all` do clone ao verde; teste que grava e consulta cada Pix; teste por regra descrita |
| 5 | Documentação | README no modelo + `docs/` + [ADRs](../02-arquitetura/decisoes/README.md) + [CHANGELOG](../../CHANGELOG.md) |
| 6 | Apresentação | ADRs com alternativas descartadas e preço de cada uma |

## Matriz regra → teste

Uma linha por regra que decide (15). Cada `if` tem pelo menos um teste que passa pela regra e um que é barrado por ela.

| Regra | Teste que passa (approved) | Teste que dispara | Arquivo |
|---|---|---|---|
| `COUNTERPARTY_FAN_IN` | `test_post_tenth_distinct_payer_returns_approved` | `test_post_eleventh_distinct_payer_returns_rejected` | [`test_counterparty_fan_in_rule.py`](../../tests/integration/pix/rules/test_counterparty_fan_in_rule.py) |
| `COUNTERPARTY_FIRST_TIME_HIGH` | `test_post_new_destination_at_limit_returns_approved` | `test_post_new_destination_above_limit_returns_two_factor_required` | [`test_counterparty_first_time_high_rule.py`](../../tests/integration/pix/rules/test_counterparty_first_time_high_rule.py) |
| `COUNTERPARTY_GRAPH_RISK` | `test_post_ordinary_destination_returns_approved_without_graph_risk` | `test_post_funnel_then_dispersion_destination_returns_two_factor_required` | [`test_counterparty_graph_risk_rule.py`](../../tests/integration/pix/rules/test_counterparty_graph_risk_rule.py) |
| `COUNTERPARTY_NEW_ACCOUNT` | `test_post_destination_30_days_old_returns_approved` | `test_post_destination_29_days_old_returns_two_factor_required` | [`test_counterparty_new_account_rule.py`](../../tests/integration/pix/rules/test_counterparty_new_account_rule.py) |
| `LIMIT_NIGHT_AMOUNT` | `test_post_evening_before_night_returns_approved` | `test_post_night_start_returns_two_factor_required` | [`test_limit_night_amount_rule.py`](../../tests/integration/pix/rules/test_limit_night_amount_rule.py) |
| `LIMIT_SINGLE_AMOUNT` | `test_post_individual_at_ceiling_returns_approved` | `test_post_individual_above_ceiling_returns_two_factor_required` | [`test_limit_single_amount_rule.py`](../../tests/integration/pix/rules/test_limit_single_amount_rule.py) |
| `PROFILE_AMOUNT_ROBUST_Z` | `test_post_amount_near_profile_returns_approved` | `test_post_amount_far_above_profile_returns_two_factor_required` | [`test_profile_amount_robust_z_rule.py`](../../tests/integration/pix/rules/test_profile_amount_robust_z_rule.py) |
| `PROFILE_GEO_VELOCITY` | `test_post_same_trip_after_six_hours_returns_approved` | `test_post_impossible_travel_returns_two_factor_required` | [`test_profile_geo_velocity_rule.py`](../../tests/integration/pix/rules/test_profile_geo_velocity_rule.py) |
| `PROFILE_NEW_DEVICE` | `test_post_first_pix_of_payer_returns_approved` | `test_post_new_device_at_minimum_amount_returns_two_factor_required` | [`test_profile_new_device_rule.py`](../../tests/integration/pix/rules/test_profile_new_device_rule.py) |
| `PROFILE_NEW_SOURCE_ACCOUNT` | `test_post_source_7_days_old_returns_approved` | `test_post_source_6_days_old_above_limit_returns_two_factor_required` | [`test_profile_new_source_account_rule.py`](../../tests/integration/pix/rules/test_profile_new_source_account_rule.py) |
| `TYPOLOGY_ACCOUNT_TAKEOVER` | `test_post_new_device_without_travel_or_unusual_amount_returns_approved` | `test_post_new_device_and_impossible_travel_returns_rejected` | [`test_typology_account_takeover_rule.py`](../../tests/integration/pix/rules/test_typology_account_takeover_rule.py) |
| `TYPOLOGY_MULE` | `test_post_fifth_payer_to_old_account_returns_approved` | `test_post_fifth_payer_to_new_account_returns_rejected` | [`test_typology_mule_rule.py`](../../tests/integration/pix/rules/test_typology_mule_rule.py) |
| `VELOCITY_DEVICE_SOURCES` | `test_post_third_distinct_payer_on_device_returns_approved` | `test_post_fourth_distinct_payer_on_device_returns_rejected` | [`test_velocity_device_sources_rule.py`](../../tests/integration/pix/rules/test_velocity_device_sources_rule.py) |
| `VELOCITY_POISSON_GAMMA` | `test_post_burst_from_intense_payer_returns_approved` | `test_post_burst_from_light_payer_returns_two_factor_required` | [`test_velocity_poisson_gamma_rule.py`](../../tests/integration/pix/rules/test_velocity_poisson_gamma_rule.py) |
| `VELOCITY_SOURCE_COUNT` | `test_post_fourth_pix_in_window_returns_approved` | `test_post_fifth_pix_in_window_returns_two_factor_required` | [`test_velocity_source_count_rule.py`](../../tests/integration/pix/rules/test_velocity_source_count_rule.py) |
