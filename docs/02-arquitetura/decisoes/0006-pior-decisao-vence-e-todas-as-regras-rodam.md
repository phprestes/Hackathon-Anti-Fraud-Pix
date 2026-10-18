---
title: "ADR 0006: Todas as regras rodam e a decisão mais severa vence"
summary: Sem curto-circuito; severidade rejected > two_factor_required > approved; todos os disparos vão para metadata.reasons.
related: [../../05-motor/decisao.md, 0004-motor-de-regras-em-codigo.md]
sources: [Desafio Antifraude Pix (seção 2.3 e "Toda decisão sai com um motivo explicável")]
---

# ADR 0006: Todas as regras rodam e a decisão mais severa vence

> [Índice](../../README.md) › [Decisões](README.md) › 0006

**Status:** aceita; quem roda as regras hoje é `engine.evaluate`, chamado pelo controller ([ADR 0023](0023-motor-extraido-e-history-port.md))

## Contexto

Várias regras podem disparar no mesmo Pix com decisões diferentes. O enunciado pede "ordem, quando pede 2FA" no README e exige motivo explicável.

## Decisão

- O controller roda **todas** as regras ativas, sem parar na primeira.
- Severidade: `rejected` > `two_factor_required` > `approved`. A decisão final é a mais severa entre os disparos; sem disparo, `approved`.
- `metadata.reasons` lista todos os disparos (`rule`, `decision`, `reason`), do mais severo ao menos severo. Cada disparo também é gravado no banco ([modelo](../../04-dados/modelo.md)).

## Alternativas descartadas

- **Parar na primeira regra que reprova.**
  - **Preço:** o motivo fica incompleto e a análise gravada não serve para calibrar as outras regras.
  - **Ganharia se** alguma regra fosse cara a ponto de pesar na latência.
- **Dois 2FA somam um `rejected`.**
  - **Preço:** a fricção cresce sem que nenhuma regra tenha dito que o risco é claro; vira score escondido.
  - **Ganharia se** o time calibrasse combinações com dado real. Pode virar regra explícita depois ([ADR 0004](0004-motor-de-regras-em-codigo.md)).

## Consequências

- A ordem das regras não muda a decisão, só a ordem dos motivos. Quem lê o README entende a decisão sem saber a ordem do código.
- Uma regra de "permitir" (lista branca) não cabe nesse modelo; se precisar, é decisão nova.
