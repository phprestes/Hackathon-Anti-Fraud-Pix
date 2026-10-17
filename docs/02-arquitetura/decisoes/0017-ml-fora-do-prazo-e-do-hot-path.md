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

- **Fora do escopo: backtest e pipeline de dados para treinar modelos.** O desafio e as aulas são sobre construir uma API (camadas, contrato, banco, testes); montar uma base de treino, rotular e treinar é trabalho de ciência de dados. O simulador ([ADR 0020](0020-simulador-para-calibracao.md)) serve para calibrar e medir a API, não para treinar modelo.
- **Caminho previsto para quando houver rótulo:**
  1. As regras resolvem o *cold start* e cada análise já grava as features (`metadata.signals`), a decisão e o `rule_set_version`.
  2. Os desfechos viram rótulo: MED e contestações (fraude confirmada, com dias ou semanas de atraso) e o resultado do 2FA (rótulo fraco e imediato, que exigiria uma rota de retorno, hoje fora do escopo).
  3. Pix `rejected` nunca tem desfecho (viés de seleção): uma fração controlada de tráfego ou a documentação do viés é necessária.
  4. Modelo supervisionado calibrado (Dal Pozzolo, 2015) entra como mais uma regra (`MODEL_RISK_SCORE`), primeiro em shadow mode (calcula e registra sem decidir), depois valendo.

## Alternativas descartadas

- **Treinar com dado sintético (PaySim, gerador próprio).**
  - **Preço:** os rótulos saem das próprias regras, e o modelo aprende a copiá-las (circularidade que a pesquisa admite); sklearn e o arquivo do modelo entram na imagem.
  - **Ganharia se** houvesse rótulos reais, mesmo que atrasados como os do MED (Dal Pozzolo, 2018).
- **Treinar com as decisões das próprias regras como rótulo.**
  - **Preço:** o modelo só aprende a imitar as regras; não descobre fraude nova.
  - **Ganharia se** o objetivo fosse só suavizar cortes, não detectar mais.
- **LLM na decisão.**
  - **Preço:** latência e custo por Pix, risco de quebrar o schema da resposta, decisão não reproduzível.
  - **Ganharia se** existissem sinais textuais ou de sessão que o payload não tem.

## Consequências

- O motor roda em milissegundos, sem GPU e sem chamada externa.
- A apresentação mostra o caminho de evolução sem prometer o que não foi medido.
