---
title: "ADR 0021: O que cada janela conta, redutores de fricção e versão do conjunto de regras"
summary: Velocity conta todas as tentativas; montante só as não reprovadas; Pix para o próprio documento não dispara contraparte; CPF e CNPJ têm tetos diferentes; cada análise grava rule_set_version.
related: [0005-regras-puras-com-contexto-carregado.md, 0009-historico-append-only.md, ../../04-dados/modelo.md]
sources: [Plano de implementação (N4, N5, N6), Desafio Antifraude Pix (seção 2.1 "Fricção")]
---

# ADR 0021: O que cada janela conta, redutores de fricção e versão do conjunto de regras

> [Índice](../../README.md) › [Decisões](README.md) › 0021

**Status:** proposta

## Contexto

Todo Pix recebido é gravado, inclusive os reprovados ([ADR 0009](0009-historico-append-only.md)). Isso muda o significado de cada agregado. E "bloquear cliente bom também é prejuízo".

## Decisão

- **Velocity** conta todas as tentativas, inclusive as reprovadas: insistir depois de um bloqueio é sinal.
- **Montante** soma só os Pix não reprovados: o dinheiro reprovado não saiu.
- **Self-transfer** (mesmo documento na origem e no destino) não dispara regras de contraparte.
- **CPF e CNPJ** têm tetos de valor separados (`RULE_*_CENTS` e `RULE_*_PJ_CENTS`): empresa movimenta mais.
- **`rule_set_version`** (constante `RULE_SET_VERSION`) é gravada em `pix_analysis` e devolvida no `metadata`.

## Alternativas descartadas

- **Mesma contagem para tudo.**
  - **Preço:** um fraudador reprovado dez vezes "gastaria" o teto diário da vítima sem ter levado nada, e a vítima seria bloqueada depois.
  - **Ganharia se** só os aprovados fossem gravados.
- **Sem versão.**
  - **Preço:** depois de uma calibragem, não dá para saber com qual regra uma análise antiga foi decidida.
  - **Ganharia se** as regras nunca mudassem.

## Consequências

- Mudar parâmetro ou regra muda `RULE_SET_VERSION` no mesmo commit e entra no CHANGELOG.
