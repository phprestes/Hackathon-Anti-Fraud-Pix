---
title: "ADR 0020: Simulador de tráfego para calibrar parâmetros e medir latência"
summary: scripts/simulate.py gera população legítima e fraudes injetadas por tipologia, manda pela API e mede a distribuição das decisões e o P95.
related: [0008-parametros-de-regra-por-ambiente.md, 0018-regras-compostas-por-tipologia.md, ../../05-motor/regras.md]
sources: [Pesquisa QITech (análise 7, PixSim), Desafio Antifraude Pix ("Expliquem o porquê de cada parâmetro")]
---

# ADR 0020: Simulador de tráfego para calibrar parâmetros e medir latência

> [Índice](../../README.md) › [Decisões](README.md) › 0020

**Status:** aceita

## Contexto

A banca pergunta o porquê de cada parâmetro e quanta fricção o motor gera. Não temos dado real. A pesquisa cita o PixSim e pede a análise de sensibilidade de limiar e o P95 do endpoint.

## Decisão

- `scripts/simulate.py`, fora de `src/` e dos testes, usa só `requests`. Gera pagadores legítimos com perfis variados (frequência, valor típico, aparelho fixo) e injeta cenários de fraude por tipologia (conta tomada, mula, fracionamento, golpe noturno).
- Manda tudo pela API (como a banca faria) e imprime: % de `approved`/`two_factor_required`/`rejected` entre legítimos (fricção) e entre fraudes (captura), matriz por tipologia e P50/P95 de latência.
- O resultado entra em `docs/05-motor/calibracao.md` e justifica os padrões de `src/constants.py`.

- **O simulador é um backtest com dados fabricados.** Cada Pix nasce com um rótulo (`legit`, `mule`, `account_takeover`…) que fica só no script; a API decide sem vê-lo, e o simulador compara a decisão com o rótulo para medir fricção e captura. Trocar o gerador por um histórico real rotulado (desfecho do MED, contestações) transforma o mesmo processo em backtest real.
- **O backtest roda pela API**, não offline: mede exatamente o motor entregue (schema, idempotência, consultas SQL, latência) e não exige uma segunda implementação dos agregados.

## Alternativas descartadas

- **PixSim ou PaySim.**
  - **Preço:** formato diferente do payload, conversão e dependências; o PixSim pode nem estar disponível.
  - **Ganharia se** o time tivesse tempo para adaptar e quisesse comparar com dado calibrado pelo BCB.
- **Calibrar no olho.**
  - **Preço:** o "porquê" do parâmetro vira opinião.
  - **Ganharia se** houvesse dado real.

- **Backtest offline em lote (motor sem HTTP ou agregados em SQL de janela sobre a base inteira).**
  - **Preço:** ou ganha pouco (o gargalo são as consultas, não o HTTP), ou exige reimplementar os agregados fora do repository, e a calibração passa a medir uma cópia do motor.
  - **Ganharia se** houvesse milhões de Pix reais para reprocessar, com uma camada de features compartilhada entre serviço e backtest.

## Consequências

- A calibração é circular (as fraudes injetadas foram desenhadas por nós); isso é dito explicitamente no README e na apresentação.
- O simulador também é um teste de carga barato.
