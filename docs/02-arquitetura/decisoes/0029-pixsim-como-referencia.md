---
title: "ADR 0029: PixSim como referência das métricas; o nosso simulador só para CI"
summary: Fricção, captura, custo, P@k, calibração e treino dos modelos são medidos num simulador de terceiros calibrado com dados do BCB (PixSim); o gerador próprio fica restrito a testes, paridade e trava de regressão.
related: [0020-simulador-para-calibracao.md, 0027-pipeline-de-calibracao-e-ci.md, ../../05-motor/validacao-pixsim.md, ../../plano-de-implementacao-4.md]
sources: [Zeimarani, Khatib, Mousavinasr, Figueiredo (2026), PixSim, github.com/BashirZeimarani/pixsim_public (Apache-2.0, commit 7fdfc90)]
---

# ADR 0029: PixSim como referência das métricas; o nosso simulador só para CI

> [Índice](../../README.md) › [Decisões](README.md) › 0029

**Status:** aceita

## Contexto

O nosso simulador gera as fraudes que nós desenhamos, e as regras procuram exatamente esses padrões. Sobre ele, a captura chegava a cerca de 92%. No PixSim, um simulador de Pix de terceiros, open source e calibrado com dados abertos do BCB, o mesmo motor barrou cerca de 36% dos Pix de vítima. Lá as mulas são contas antigas, e a engenharia social vem do aparelho e do padrão da própria vítima ([validação](../../05-motor/validacao-pixsim.md)).

## Decisão

- **Referência:** todo número de resultado (README, calibração, modelos, apresentação) vem do PixSim. A calibração escolhe os parâmetros no mundo A e confirma no mundo B; os modelos treinam no A e testam no B.
- **Ambiente isolado:** o PixSim roda em `scripts/out/pixsim/`, fora do Git, com venv próprio (Python 3.13) e versão fixa (commit `7fdfc90`). É código de terceiro: lido antes de executar, sem instaladores nem privilégio.
- **Escala reduzida:** 5 mil contas e 30 dias por mundo. A escala do artigo pede 19 GB por parte.
- **Nosso simulador:** fica só para CI/CD (testes, paridade e trava de regressão). É rápido, determinístico e roda em máquina limpa.
- **Vocabulário:** os documentos dizem "no PixSim", nunca "dado real". Ele também é simulado.

## Alternativas descartadas

- **Continuar medindo no nosso simulador.**
  - **Preço:** avaliação circular; o motor parecia três vezes melhor do que é fora dele.
  - **Ganharia se** não houvesse gerador independente disponível.
- **PixSim também no CI.**
  - **Preço:** Python 3.13, venv separado e minutos de geração em cada build; CI lento e frágil.
  - **Ganharia se** houvesse um conjunto congelado e pequeno do PixSim versionável.
- **Elliptic (Bitcoin, rótulos reais).**
  - **Preço:** outra dinâmica (sem contas bancárias, sem MED), e o artigo original já publica GCN e Random Forest nele.
  - **Ganharia se** o foco fosse validar a implementação do GraphSAGE, não o motor de Pix.

## Consequências

- A queda de captura no PixSim é um resultado, não uma falha a esconder; ela orienta as próximas regras de destino.
- `make pixsim`, `make validate-pixsim` e `make pixsim-datasets` reproduzem tudo a partir do clone.
