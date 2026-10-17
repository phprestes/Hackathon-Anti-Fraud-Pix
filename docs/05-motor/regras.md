---
title: Catálogo de regras antifraude
summary: As 17 regras ativas do motor com família, lógica, parâmetros, decisão e porquê; fonte da tabela "Regras" do README.
related: [motor-de-regras.md, decisao.md, calibracao.md, ../01-contexto/requisitos.md]
sources: [Desafio Antifraude Pix (seção 2.2), Pesquisa QITech, Resolução BCB nº 142/2021 (limite noturno), Pizzolato et al. (2025), Bolton & Hand (2002), src/rules/, src/constants.py]
---

# Catálogo de regras

> [Índice](../README.md) › Motor › Regras
>
> **Responde a:** quais regras existem? o que cada uma olha? por que esse parâmetro? qual decisão ela dá?

Fonte da tabela "Regras" do [README](../../README.md). Versão do conjunto: `2026.10.18-calib3`. Todos os parâmetros são variáveis `RULE_*` em `src/constants.py`, lidas do ambiente ([ADR 0008](../02-arquitetura/decisoes/0008-parametros-de-regra-por-ambiente.md)); os três marcados com ★ foram ajustados pelo simulador ([calibração](calibracao.md)). As janelas são `[t − N, t)`, com `t = transaction_date` ([ADR 0007](../02-arquitetura/decisoes/0007-relogio-da-transacao.md)).

## Limite: "passou do teto?"

| Código | Lógica | Parâmetros | Decisão | Por quê |
|---|---|---|---|---|
| `LIMIT_NIGHT_AMOUNT` | Pix entre 20h e 6h (hora local do payload) acima do teto; não vale para CNPJ | R$ 1.000; 20h–6h | 2FA | O BC fixou R$ 1.000 como limite noturno padrão de pessoa física (Res. 142/2021): é o valor que o próprio regulador associa ao risco de sequestro relâmpago. 2FA, não reprovação, porque o cliente pode ter ampliado o limite |
| `LIMIT_SINGLE_AMOUNT` | Valor de um Pix acima do teto absoluto | R$ 50.000 (CPF), R$ 200.000 (CNPJ) | 2FA | Teto de exposição de um único Pix, independente do perfil; empresa movimenta mais ([ADR 0021](../02-arquitetura/decisoes/0021-o-que-cada-janela-conta-e-versao-das-regras.md)) |

## Velocity: "rápido demais?"

| Código | Lógica | Parâmetros | Decisão | Por quê |
|---|---|---|---|---|
| `VELOCITY_SOURCE_COUNT` | Tentativas do pagador em 10 min, contando reprovadas | 2FA a partir de 5; reprova a partir de 10 | 2FA / reprova | Conta tomada é esvaziada em rajada. Insistir depois de reprovado também conta. É a regra que protege o pagador sem histórico |
| `VELOCITY_DEVICE_SOURCES` | Pagadores distintos no mesmo aparelho em 24 h | reprova acima de 3 | reprova | Um aparelho operando várias contas é fazenda de contas ou golpista com credenciais de vítimas; família usando o mesmo celular raramente passa de 3 |
| `VELOCITY_POISSON_GAMMA` | Probabilidade da rajada da última hora sob a taxa histórica do pagador (Poisson–Gamma), com 24 h de histórico no mínimo | ★ cauda < 0,0001; prior de 1 Pix/dia | 2FA | Adapta o "rápido demais" ao ritmo de cada um: 4 Pix numa hora é normal para quem faz 1 por hora e improvável para quem faz 1 por semana ([ADR 0016](../02-arquitetura/decisoes/0016-sinais-estatisticos-como-regras.md)) |

## Montante: "somou demais?"

| Código | Lógica | Parâmetros | Decisão | Por quê |
|---|---|---|---|---|
| `AMOUNT_SOURCE_DAILY_SUM` | Soma do pagador em 24 h (só não reprovados) + este Pix | ★ R$ 30.000 (CPF), R$ 50.000 (CNPJ) | 2FA | Fracionar para fugir do teto por Pix. R$ 10 mil gerava 266 casos de 2FA em legítimos no simulador; R$ 30 mil mantém o sinal sem travar o pagador intenso |

## Perfil: "está no padrão do cliente?"

| Código | Lógica | Parâmetros | Decisão | Por quê |
|---|---|---|---|---|
| `PROFILE_NEW_DEVICE` | Pagador com histórico, aparelho nunca visto, valor alto | a partir de R$ 500 | 2FA | Troca de aparelho é o primeiro passo da tomada de conta; o piso de valor evita fricção no Pix do cafezinho |
| `PROFILE_NEW_SOURCE_ACCOUNT` | Conta de origem com menos de 7 dias e valor alto | < 7 dias e > R$ 2.000 | 2FA | Conta aberta com identidade falsa costuma ser usada logo; idade de conta é fator citado no art. 39-B do Regulamento do Pix |
| `PROFILE_AMOUNT_ROBUST_Z` | z robusto de `log(valor)` sobre os últimos 30 dias do pagador (mediana/MAD), com 5 Pix no mínimo | z > 3,5; piso de escala 25% | 2FA | Fora do padrão do próprio cliente (Bolton & Hand). Mediana e MAD porque o histórico é pequeno e um Pix grande antigo não deve esconder o próximo |
| `PROFILE_GEO_VELOCITY` | Distância ao último Pix com GPS ÷ tempo decorrido | > 50 km e > 900 km/h | 2FA | Viagem impossível: sessão em outro aparelho ou localização falsa. 900 km/h é a velocidade de um avião comercial |

## Contraparte: "quem recebe é confiável?"

| Código | Lógica | Parâmetros | Decisão | Por quê |
|---|---|---|---|---|
| `COUNTERPARTY_NEW_ACCOUNT` | Idade da conta de destino; self-transfer não conta | 2FA < 30 dias; reprova < 3 dias e > R$ 1.000 | 2FA / reprova | Contas laranja são abertas para receber o golpe e esvaziadas em dias. A pesquisa insiste: com vítima coagida, só o destino denuncia |
| `COUNTERPARTY_FAN_IN` | Pagadores distintos para o mesmo destino em 1 h | reprova acima de 10 | reprova | Conta de passagem recebendo de muitas vítimas ao mesmo tempo (padrão funil) |
| `COUNTERPARTY_FIRST_TIME_HIGH` | Primeiro Pix (não reprovado) do pagador para esse destino, valor alto | > R$ 3.000 | 2FA | Golpes do falso parente e do falso boleto mandam para destino novo; o aluguel vai sempre para o mesmo (recorrência do par, art. 39-B) |
| `COUNTERPARTY_FLAGGED` | Destino recebeu Pix reprovado de **outro** pagador em 7 dias | 7 dias | 2FA | Reputação derivada do próprio histórico, sem lista externa ([ADR 0019](../02-arquitetura/decisoes/0019-reputacao-de-contraparte-derivada.md)) |

## Tipologia: combinações que descrevem um golpe

| Código | Lógica | Parâmetros | Decisão | Por quê |
|---|---|---|---|---|
| `TYPOLOGY_ACCOUNT_TAKEOVER` | Pagador com histórico + aparelho novo + (viagem impossível ou z > 3,0) | z > 3,0 | reprova | Tomada de conta (Pizzolato et al.): cada sinal sozinho pede 2FA; juntos, o risco é claro ([ADR 0018](../02-arquitetura/decisoes/0018-regras-compostas-por-tipologia.md)) |
| `TYPOLOGY_MULE` | Destino com menos de 30 dias + 5 ou mais pagadores distintos em 1 h | 5 pagadores | reprova | Conta laranja: barra no 5º pagador, antes do fan-in genérico (11º) |
| `TYPOLOGY_SPLITTING` | 6 ou mais Pix pequenos (≤ R$ 2.000) para 4 ou mais destinos **novos** em 24 h, somando acima do corte | ★ R$ 15.000 | reprova | Fracionamento espalha para contas novas; contar só destinos novos tirou os 66 legítimos reprovados da linha de base |

## Ideias que não viraram regra

- **Horário atípico por conta:** a pesquisa indica que golpes de engenharia social acontecem em horário comercial; um corte fixo de horário não ajudaria.
- **`transaction_date` distante do recebimento:** depende de saber a hora real em que o Pix chegou.
- **IP compartilhado por muitos pagadores:** sinal fraco com NAT de operadora móvel.

Regra nova: siga a [skill nova-regra](../../.agents/skills/nova-regra/SKILL.md).
