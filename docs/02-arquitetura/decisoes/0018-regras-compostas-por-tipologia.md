---
title: "ADR 0018: Regras compostas por tipologia de golpe, no lugar de score ponderado"
summary: Combinações de sinais que caracterizam um golpe conhecido (conta tomada, mula, fracionamento) viram regras próprias com nome de tipologia e decisão rejected.
related: [0006-pior-decisao-vence-e-todas-as-regras-rodam.md, 0004-motor-de-regras-em-codigo.md, ../../05-motor/regras.md]
sources: [Pizzolato, Lopes, Schepke & Kreutz (2025), A Taxonomy of Pix Fraud in Brazil, arXiv:2511.20902, https://arxiv.org/abs/2511.20902; Pesquisa QITech (M4)]
---

# ADR 0018: Regras compostas por tipologia de golpe, no lugar de score ponderado

> [Índice](../../README.md) › [Decisões](README.md) › 0018

**Status:** aceita; `TYPOLOGY_SPLITTING` descartada por [0033](0033-regras-descartadas-pela-ablacao.md)

## Contexto

Sinais fracos isolados pedem 2FA. Juntos, alguns descrevem um golpe conhecido: aparelho novo + lugar distante + valor fora do perfil é conta tomada. A pesquisa propõe somar os escores (M4); a [ADR 0006](0006-pior-decisao-vence-e-todas-as-regras-rodam.md) descartou que dois 2FA virem `rejected` sem uma regra explícita.

## Decisão

- Regras `TYPOLOGY_<NOME>` leem os sinais que as outras regras já calcularam no `RuleContext` e disparam `rejected` quando a combinação completa aparece:
  - `TYPOLOGY_ACCOUNT_TAKEOVER`: aparelho novo para o pagador + (viagem impossível ou valor fora do perfil).
  - `TYPOLOGY_MULE`: destino aberto recentemente + fan-in alto.
  - `TYPOLOGY_SPLITTING`: vários Pix pequenos na janela cuja soma passa o teto diário.
- A tipologia aparece no motivo ("Padrão de conta tomada: …"), na língua de quem atende o cliente.

## Alternativas descartadas

- **Score ponderado com dois cortes (M4 da pesquisa).**
  - **Preço:** "rejeitado porque deu 0,72" não explica; pesos sem rótulo são chute.
  - **Ganharia se** houvesse dado rotulado para ajustar os pesos.
- **Contar disparos (dois 2FA = rejected).**
  - **Preço:** combina sinais sem relação (noite + conta nova) e reprova cliente bom.
  - **Ganharia se** os sinais fossem independentes e igualmente fortes.

## Consequências

- Cada tipologia tem teste de cenário próprio, e os três cenários da pesquisa (normal, mula, conta tomada) viram testes de aceitação.
- Tipologia nova é uma regra nova, sem mexer na agregação.
