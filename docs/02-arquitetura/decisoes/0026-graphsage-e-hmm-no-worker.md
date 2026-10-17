---
title: "ADR 0026: GraphSAGE e HMM enxutos em numpy, restritos ao worker"
summary: GraphSAGE de 2 camadas (até 10 vizinhos) e HMM discreto de 3 estados, treinados em scripts/ com rótulos do simulador, servidos pelo worker em numpy e lidos em shadow pelo hot path; a imagem da api não ganha numpy.
related: [0025-cold-path-worker.md, 0022-shadow-mode.md, 0024-modelos-servidos-em-python-puro.md]
sources: [Pesquisa QITech (GNN: GraphSAGE grau 1–2, até 10 vizinhos; HMM de Lucas et al., 2019), scripts/model-results.md]
---

# ADR 0026: GraphSAGE e HMM enxutos em numpy, restritos ao worker

> [Índice](../../README.md) › [Decisões](README.md) › 0026

**Status:** aceita

## Contexto

A pesquisa coloca GNN e modelos de sequência fora do caminho síncrono: rodam em lote e deixam um score pronto para o motor consultar. Queremos mostrar esse padrão com modelos aprendidos de verdade, sem PyTorch nem DGL, que pesam centenas de MB, e sem mudar a imagem da `api`.

## Decisão

- **GraphSAGE**:
  - **Arquitetura:** 2 camadas com agregação por média e até 10 vizinhos amostrados (como na pesquisa), hidden 16.
  - **Treino:** em `scripts/train_graphsage.py`, com backprop escrito à mão e conferido contra gradiente numérico.
  - **Grafo:** pagador → destino, em janelas de 72 h, com 7 features de nó (graus, valores, idade, fração de pagadores novos, dispersão). O rótulo de nó é "foi destino de fraude no simulador".
  - **Serviço:** a cada ciclo, o worker monta o subgrafo da janela via SQL, roda o forward e grava `account_risk_score` com `model='graphsage'`.
- **HMM**:
  - **Modelo:** discreto, de 3 estados, com 12 símbolos por Pix (faixa de valor relativa ao próprio pagador × destino novo × noite).
  - **Treino:** Baum-Welch, só com pagadores legítimos, em `scripts/train_hmm.py`.
  - **Score:** a anomalia é a CDF empírica da log-verossimilhança média dos últimos Pix. Vira a `seq_anomaly_likelihood` da pesquisa, em `payer_sequence_score`.
- **Imagens:** numpy só no target `worker` do Dockerfile (`requirements-worker.txt`). A `api` lê do JSON apenas o threshold.
- **Shadow:** `MODEL_GRAPHSAGE` e `MODEL_SEQUENCE_HMM` leem o score mais recente e entram em `metadata.shadow` ([ADR 0022](0022-shadow-mode.md)); nunca decidem.

## Resultados (dados sintéticos, sem busca de hiperparâmetros)

| Modelo | AUC teste (perturbado) | Leitura |
|---|---|---|
| GraphSAGE | 1,000 (0,999) | Otimista: o grafo do simulador é fácil de separar e a avaliação vê a janela que contém a fraude. No hot path só existe o score do ciclo anterior |
| HMM, com o Pix atual | 0,652 (0,683) | Fraco |
| HMM, só o que o hot path vê | 0,509 (0,578) | Praticamente aleatório: a sequência de Pix do payload diz pouco sem eventos de sessão |

Ciclo do worker no cenário padrão: 0,31 s para os três jobs (619 destinos, 179 pagadores). A imagem do worker tem 546 MB, contra 404 MB da `api`.

## Alternativas descartadas

- **PyTorch Geometric ou DGL.**
  - **Preço:** dependências de centenas de MB e um treino que exige mais infraestrutura do que o próprio motor.
  - **Ganharia se** o grafo tivesse milhões de nós e o time mantivesse modelos de grafo em produção.
- **RNN/LSTM no lugar do HMM.**
  - **Preço:** mais parâmetros para aprender a mesma sequência pobre; o payload não tem os eventos de sessão que justificariam uma rede recorrente.
  - **Ganharia se** o contrato trouxesse eventos do app (login, troca de limite, cadastro de chave).

## Consequências

- O resultado ruim do HMM é um achado e fica registrado assim. O sinal de sequência só vale com dados que o enunciado não fornece.
- No backtest em lote, os scores do cold path são `None` (o `InMemoryHistory` não roda o worker), o que mantém a paridade exata.
