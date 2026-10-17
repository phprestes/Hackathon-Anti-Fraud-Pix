---
title: "ADR 0017: Machine learning, grafos e LLM ficam fora desta entrega"
summary: Isolation Forest, LightGBM, GNN, RNN/HMM e avaliação semântica por LLM viram roadmap; nada disso roda no caminho síncrono do Pix neste hackathon.
related: [0016-sinais-estatisticos-como-regras.md, 0002-monolito-sincrono-sem-dependencia-externa.md, ../../plano-de-implementacao.md]
sources: [Pesquisa QITech (M2, M3, GNN, RNN, JEV), Dal Pozzolo et al. (2015, 2018), Pizzolato et al. (2025)]
---

# ADR 0017: Machine learning, grafos e LLM ficam fora desta entrega

> [Índice](../../README.md) › [Decisões](README.md) › 0017

**Status:** aceita

## Contexto

A pesquisa descreve a arquitetura de produção: regras e listas na primeira linha, gradient boosting no hot path, RNN e GNN gerando embeddings e reputação fora do caminho síncrono, LLM na zona cinzenta. O enunciado não traz rótulo de fraude e o prazo é de 26 horas.

## Decisão

- Nenhum modelo treinado nesta entrega. O motor é regra explícita + estatística sobre o próprio histórico ([ADR 0016](0016-sinais-estatisticos-como-regras.md)).
- O que a pesquisa mostra vira o roadmap da apresentação, cada item com o sinal que já gravamos para alimentá-lo:

| Técnica | Papel em produção | O que já deixamos pronto |
|---|---|---|
| LightGBM/XGBoost calibrado | decisão síncrona | `metadata.signals` gravado por análise = features prontas |
| Isolation Forest | pré-filtro não supervisionado | mesmas features |
| GNN (funil, dispersão) | reputação de conta, assíncrona | [reputação derivada](0019-reputacao-de-contraparte-derivada.md) como versão SQL |
| RNN/HMM | embedding de sequência | `pix_transaction` ordenada por `transaction_date` |
| LLM de passagem única | zona cinzenta semântica | `two_factor_required` marca exatamente essa zona |

## Alternativas descartadas

- **Treinar com dado sintético (PaySim, gerador próprio).**
  - **Preço:** os rótulos saem das próprias regras, e o modelo aprende a copiá-las (circularidade que a pesquisa admite); sklearn e o arquivo do modelo entram na imagem.
  - **Ganharia se** houvesse rótulos reais, mesmo que atrasados como os do MED (Dal Pozzolo, 2018).
- **LLM na decisão.**
  - **Preço:** latência e custo por Pix, risco de quebrar o schema da resposta, decisão não reproduzível.
  - **Ganharia se** existissem sinais textuais ou de sessão que o payload não tem.

## Consequências

- O motor roda em milissegundos, sem GPU e sem chamada externa.
- A apresentação mostra o caminho de evolução sem prometer o que não foi medido.
