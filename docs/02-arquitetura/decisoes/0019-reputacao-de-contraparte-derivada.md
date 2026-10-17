---
title: "ADR 0019: Reputação de contraparte derivada do nosso próprio histórico"
summary: Destino que recebeu Pix reprovado nos últimos N dias exige 2FA de outros pagadores; sem lista externa e sem lista em memória.
related: [0009-historico-append-only.md, 0017-ml-fora-do-prazo-e-do-hot-path.md, ../../05-motor/regras.md]
sources: [Pesquisa QITech (listas, reputação de rede por GNN), Desafio Antifraude Pix ("Contraparte: quem recebe é confiável?")]
---

# ADR 0019: Reputação de contraparte derivada do nosso próprio histórico

> [Índice](../../README.md) › [Decisões](README.md) › 0019

**Status:** proposta

## Contexto

"Quem recebe é confiável?" é uma das cinco perguntas do enunciado. A pesquisa responde com listas restritivas (DICT) e reputação de rede calculada por GNN. Não temos lista externa ([ADR 0002](0002-monolito-sincrono-sem-dependencia-externa.md)), e uma lista em memória some no restart.

## Decisão

- Regra `COUNTERPARTY_FLAGGED`: se o documento de destino recebeu algum Pix com análise `rejected` nos últimos `RULE_FLAGGED_WINDOW_DAYS` (padrão 7) por **outro** pagador, o Pix pede 2FA.
- O sinal sai de `pix_analysis` + `pix_transaction` com o índice de destino que já existe ([ADR 0009](0009-historico-append-only.md)).

## Alternativas descartadas

- **Lista de bloqueio em memória ou em tabela seed.**
  - **Preço:** sem fonte de dados real; some no restart ou fica estática.
  - **Ganharia se** houvesse integração com o DICT.
- **Reprovar direto.**
  - **Preço:** um falso positivo antigo contamina para sempre quem recebe; vira efeito cascata.
  - **Ganharia se** o `rejected` original fosse confirmado como fraude (MED).

## Consequências

- O motor aprende com as próprias decisões, um passo de grau 1 do que a GNN faria em grafo inteiro.
- O risco de laço (2FA nunca vira `rejected` por esta regra) fica contido porque a regra só pede 2FA.
