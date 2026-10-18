---
title: "ADR 0030: Custo assimétrico em R$ e P@k como métricas de decisão"
summary: A calibração e os relatórios medem o prejuízo esperado (fraude aprovada custa o valor; 2FA e bloqueio de cliente bom custam atrito) e a precisão nos k alertas diários de uma mesa de analistas.
related: [0027-pipeline-de-calibracao-e-ci.md, 0029-pixsim-como-referencia.md, ../../05-motor/calibracao.md]
sources: [Pesquisa QITech (custo assimétrico, capacidade da mesa e P@k), PixSim (valor perdido sob capacidade de analistas), scripts/backtest/cost-model.json]
---

# ADR 0030: Custo assimétrico em R$ e P@k como métricas de decisão

> [Índice](../../README.md) › [Decisões](README.md) › 0030

**Status:** aceita

## Contexto

A função objetivo original ordenava critérios: menos legítimos reprovados, depois mais fraudes barradas, depois menos 2FA. Isso não diz quanto custa cada erro. A pesquisa insiste em otimizar custo, não acurácia, e em medir a mesa de analistas pelos k primeiros alertas. A métrica central do PixSim é o valor perdido sob capacidade limitada de analistas.

## Decisão

- **`scripts/backtest/cost-model.json`**, com o porquê de cada valor:
  - fraude aprovada custa o valor do Pix;
  - fraude com 2FA custa 10% do valor (a vítima coagida confirma);
  - 2FA em cliente bom custa R$ 2;
  - bloqueio de cliente bom custa R$ 50 mais 2% do valor (a premissa A3.5 do PixSim, ASSUMED; antes era R$ 50 fixos).
- **`calibrate.py --objective cost`** escolhe a configuração pelo custo esperado, ponderado no PixSim pelo peso de importância do próprio simulador. A ordem lexicográfica continua disponível.
- **P@k diário** (k = 5, 10, 25, 50): precisão nos k Pix mais suspeitos do dia. Fica no relatório para regras sozinhas e para regras + LightGBM.

## Relação com a cascata de valor do PixSim

O custo de fraude daqui trata toda fraude aprovada como perda total do valor, sem crédito de recuperação. O PixSim mede a cascata do valor da vítima (barrado antes da liquidação, retido num salto, recuperado pelo MED, recuperado por bloqueio cautelar, perdido; as linhas somam 1). A cascata roda o relógio do MED do PixSim sobre as decisões do motor em [Alinhamento com a metodologia do PixSim](../../05-motor/validacao-pixsim.md#alinhamento-com-a-metodologia-do-pixsim) e serve de leitura de perda realista; o custo em R$ continua sendo o critério de calibração porque é uma única conta, barata e que cabe na grade. O custo, portanto, é um limite superior da perda de fraude; o falso bloqueio já está na mesma definição do PixSim.

## Alternativas descartadas

- **Só a ordem lexicográfica.**
  - **Preço:** não compara "2 bloqueios a mais" com "R$ 10 mil de fraude a menos".
  - **Ganharia se** o banco não aceitasse nenhum bloqueio de cliente bom, a qualquer preço.
- **AUC como métrica de escolha.**
  - **Preço:** ignora o limiar e o valor de cada Pix; um modelo com AUC alta pode perder mais dinheiro.
  - **Ganharia se** só se quisesse ranquear, sem decidir.

## Consequências

- Os parâmetros do custo são hipóteses de negócio, não medidas; mudá-los muda a configuração vencedora. Por isso cada um tem o porquê ao lado.
- Com a taxa real de fraude, a precisão ponderada dos alertas é baixa (cerca de 1%), e o P@k mostra isso sem maquiagem.
