---
title: Catálogo de regras antifraude
summary: Toda regra do motor com família, lógica, parâmetros, decisão, porquê e estado; fonte da tabela "Regras" do README.
related: [motor-de-regras.md, decisao.md, ../01-contexto/requisitos.md]
sources: [Desafio Antifraude Pix (seção 2.2 "Exemplos de regras"), Resolução BCB nº 142/2021 (limite noturno do Pix)]
---

# Catálogo de regras

> [Índice](../README.md) › Motor › Regras
>
> **Responde a:** quais regras existem? o que cada uma olha? por que esse parâmetro? qual decisão ela dá?

Esta é a fonte da tabela "Regras" do [README](../../README.md). Mudou uma linha aqui, muda lá e entra no [CHANGELOG](../../CHANGELOG.md).

**Estados:** `candidata` = ideia para o time discutir; `aceita` = vai ser implementada com esses parâmetros; `ativa` = em `ACTIVE_RULES`, com teste; `descartada` = fica aqui com o motivo.

**Os parâmetros abaixo são pontos de partida para discussão**, não valores calibrados. Calibrar é trabalho do time: cada valor final precisa de um porquê próprio na coluna "Por quê".

## Regras

| Código | Família | Lógica | Parâmetros (sugestão inicial) | Decisão | Por quê | Estado |
|---|---|---|---|---|---|---|
| `LIMIT_NIGHT_AMOUNT` | Limite | Pix entre 20h e 6h (fuso do payload) acima do teto noturno | `RULE_LIMIT_NIGHT_AMOUNT_CENTS` = 100000; `RULE_NIGHT_START_HOUR` = 20; `RULE_NIGHT_END_HOUR` = 6 | 2FA | Golpes de sequestro relâmpago concentram-se à noite; o BC fixou R$ 1.000 como limite noturno padrão para pessoa física. 2FA e não reprovar: o cliente pode ter ampliado o limite | candidata |
| `LIMIT_SINGLE_AMOUNT` | Limite | Valor de um único Pix acima do teto absoluto | `RULE_LIMIT_SINGLE_AMOUNT_CENTS` = 5000000 | 2FA | Teto de exposição de um Pix só, independente do perfil | candidata |
| `VELOCITY_SOURCE_COUNT` | Velocity | Número de Pix do pagador nos últimos N minutos | `RULE_VELOCITY_WINDOW_MINUTES` = 10; 2FA a partir de 5; reprova a partir de 10 | 2FA / reprova | Conta tomada costuma ser esvaziada em rajada antes que o dono perceba | candidata |
| `VELOCITY_DEVICE_SOURCES` | Velocity | Pagadores distintos usando o mesmo `device_id` em 24h | `RULE_DEVICE_MAX_SOURCES_24H` = 3 | reprova | Um aparelho operando várias contas é sinal de fazenda de contas ou de golpista com credenciais de vítimas | candidata |
| `AMOUNT_SOURCE_DAILY_SUM` | Montante | Soma do pagador em 24h + este Pix acima do teto diário | `RULE_AMOUNT_DAILY_SUM_CENTS` = 1000000 | 2FA | Fracionar em Pix pequenos para fugir do limite por Pix | candidata |
| `PROFILE_AMOUNT_OUTLIER` | Perfil | Valor acima de K vezes a média de 30 dias do pagador, com histórico mínimo | `RULE_PROFILE_RATIO_PERCENT` = 500; `RULE_PROFILE_MIN_HISTORY` = 5 | 2FA | Fora do padrão do cliente; sem histórico mínimo a média não diz nada e a regra fica muda | candidata |
| `PROFILE_NEW_DEVICE` | Perfil | Pagador com histórico usando aparelho nunca visto, acima de um valor mínimo | `RULE_NEW_DEVICE_MIN_AMOUNT_CENTS` = 50000 | 2FA | Troca de aparelho é o primeiro passo de tomada de conta; valor mínimo evita fricção no Pix de cafezinho | candidata |
| `PROFILE_NEW_SOURCE_ACCOUNT` | Perfil | Conta de origem aberta há menos de N dias e valor alto | `RULE_SOURCE_MIN_AGE_DAYS` = 7; `RULE_SOURCE_NEW_MAX_AMOUNT_CENTS` = 200000 | 2FA | Conta recém-aberta com fraude de identidade costuma ser usada logo | candidata |
| `PROFILE_GEO_VELOCITY` | Perfil | Velocidade implícita entre a geolocalização anterior e a atual | `RULE_GEO_MAX_SPEED_KMH` = 900 | 2FA | Deslocamento impossível sugere sessão em outro aparelho ou localização falsa. Sem geolocalização, não dispara | candidata |
| `COUNTERPARTY_NEW_ACCOUNT` | Contraparte | Conta de destino aberta há menos de N dias | `RULE_DESTINATION_MIN_AGE_DAYS` = 30; reprova abaixo de 3 dias com valor acima de `RULE_DESTINATION_NEW_MAX_AMOUNT_CENTS` = 100000 | 2FA / reprova | Contas laranja são abertas para receber o golpe e esvaziadas em poucos dias | candidata |
| `COUNTERPARTY_FIRST_TIME_HIGH` | Contraparte | Primeiro Pix do pagador para esse destino, acima de um valor | `RULE_FIRST_TIME_MIN_AMOUNT_CENTS` = 300000 | 2FA | Golpe do falso parente e do falso boleto mandam para destino novo; o aluguel vai sempre para o mesmo | candidata |
| `COUNTERPARTY_FAN_IN` | Contraparte | Pagadores distintos mandando para o mesmo destino em 1h | `RULE_DESTINATION_MAX_SOURCES_1H` = 10 | reprova | Conta de passagem recebendo de muitas vítimas ao mesmo tempo | candidata |

Ideias ainda sem linha: `transaction_date` muito distante do `created_at`; CNPJ pagando CPF fora do horário comercial; IP compartilhado por muitos pagadores; Pix para o próprio documento (sinal de risco **menor**, que exigiria uma regra de exceção, [ADR 0006](../02-arquitetura/decisoes/0006-pior-decisao-vence-e-todas-as-regras-rodam.md)).

## Como uma regra entra aqui

Siga a [skill nova-regra](../../.agents/skills/nova-regra/SKILL.md): linha neste catálogo → teste que dispara e teste que não dispara → classe em `src/rules/` → constante em `src/constants.py` → `ACTIVE_RULES` → README → CHANGELOG.
