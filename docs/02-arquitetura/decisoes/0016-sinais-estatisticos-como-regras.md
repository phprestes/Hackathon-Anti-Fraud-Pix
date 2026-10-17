---
title: "ADR 0016: Sinais estatísticos viram regras, em Python puro"
summary: z robusto (mediana/MAD de log do valor), velocity Poisson–Gamma e viagem impossível entram como regras comuns com corte explícito, sem biblioteca de ML.
related: [0004-motor-de-regras-em-codigo.md, 0017-ml-fora-do-prazo-e-do-hot-path.md, ../../05-motor/regras.md, ../../plano-de-implementacao.md]
sources: [Pesquisa QITech (M1), Bolton & Hand (2002), Desafio Antifraude Pix (seção 2.2 "Perfil", "Velocity")]
---

# ADR 0016: Sinais estatísticos viram regras, em Python puro

> [Índice](../../README.md) › [Decisões](README.md) › 0016

**Status:** proposta

## Contexto

Limites fixos ("mais de 5 Pix em 10 minutos") tratam igual quem faz 1 Pix por mês e quem faz 30 por dia. A pesquisa do time propõe perfis estatísticos por conta (Bolton & Hand, 2002). O histórico de cada pagador é pequeno e assimétrico, e o prazo não comporta treinar modelo.

## Decisão

- **Desvio de valor:** `z = (log(amount) − mediana(log)) / (1,4826 · MAD)` sobre o histórico do pagador. Mediana e MAD em vez de média e desvio padrão porque um Pix grande antigo não contamina o perfil. Só vale com histórico mínimo.
- **Velocity Poisson–Gamma:** taxa de Pix do pagador com prior `Gamma(α, β)`; o sinal é a probabilidade de cauda de ver a contagem da janela sob a preditiva (binomial negativa). Dá um número para quem tem pouco histórico, sem corte arbitrário por pessoa.
- **Viagem impossível:** haversine entre a última geolocalização e a atual, dividida pelo tempo entre os Pix; sem geolocalização, a regra não dispara.
- Cada sinal é uma regra comum ([ADR 0004](0004-motor-de-regras-em-codigo.md)) com corte em `src/constants.py` ([ADR 0008](0008-parametros-de-regra-por-ambiente.md)). O valor do sinal vai para `metadata.signals`.
- A matemática fica em `src/utils/statistics.py`, só com `math` e `statistics`.

## Alternativas descartadas

- **Média e desvio padrão.**
  - **Preço:** um único outlier antigo infla o desvio e esconde o próximo.
  - **Ganharia se** o histórico fosse grande e simétrico.
- **Só limites fixos.**
  - **Preço:** limite baixo trava o cliente intenso, limite alto deixa passar o cliente parado que de repente faz rajada.
  - **Ganharia se** os clientes fossem homogêneos.
- **numpy/scipy para as distribuições.**
  - **Preço:** dependência nova na imagem para três fórmulas fechadas.
  - **Ganharia se** houvesse dezenas de distribuições ou álgebra matricial.

## Consequências

- O primeiro Pix de um pagador não tem perfil: regras de payload puro (idade de conta, limites) cobrem esse caso.
- O `metadata` mostra o número que disparou ("z = 4,1"), o que explica a decisão.
