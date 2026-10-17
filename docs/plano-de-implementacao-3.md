---
title: Plano de implementação 3 (v3)
summary: Validação externa do motor no PixSim (simulador de terceiros calibrado com dados do BCB), com custo assimétrico e P@k, peer group, rótulos atrasados e cold path no backtest com stacking; Elliptic, Redis, CUSUM e drift como job ficam fora.
related: [plano-de-implementacao-2.md, 05-motor/calibracao.md, 02-arquitetura/decisoes/0017-ml-fora-do-prazo-e-do-hot-path.md]
sources: [Pesquisa QITech (PixSim, cost-sensitive, P@k, Bolton & Hand nível 2, Dal Pozzolo 2018, embeddings assíncronos), github.com/BashirZeimarani/pixsim_public]
---

# Plano de implementação 3 (v3)

> [Índice](README.md) › Plano de implementação 3
>
> **Responde a:** como validar o motor fora do nosso próprio simulador? o que entra nesta rodada, em que ordem e o que fica fora?

**Estado:** aprovado pelo time. Substitui a primeira versão do plano 3, cancelada antes de qualquer código entrar.

## Por que esta rodada

Tudo o que o motor mede hoje vem do nosso simulador: fomos nós que desenhamos as fraudes, e a avaliação é circular ([calibração](05-motor/calibracao.md)). O **PixSim** (Zeimarani et al., 2026) é um simulador de Pix de terceiros, open source (Apache-2.0), calibrado com dados abertos do Banco Central. Ele tem tipologias que não desenhamos: engenharia social, conta tomada, Pix errado e QR adulterado, com cadeias de dispersão por mulas e atraso de reporte ao MED. Rodar o motor sobre ele é a validação externa possível no prazo. Continua sintético, mas não é nosso.

## Itens

| Fase | Entrega | Por quê |
|---|---|---|
| **V1** Custo assimétrico + P@k | Custo esperado em R$ (fraude que passa, 2FA e bloqueio de cliente bom) e precisão nos k alertas do dia | É a métrica do próprio PixSim (valor perdido sob capacidade de analistas); sem ela não há comparação |
| **V2** PixSim: ambiente e geração | Clone isolado, venv próprio (Python 3.13), geração em escala reduzida e seed fixa | A escala do artigo pede 19 GB por parte; a demo reduzida cabe na máquina |
| **V3** PixSim: adaptador e validação | Conversão para o contrato do enunciado, backtest do motor, relatório em `docs/05-motor/validacao-pixsim.md` | Mostrar o que se mantém e o que cai fora do nosso simulador, incluindo os modelos treinados no nosso gerador |
| **V4** Peer group | Regra que compara o pagador sem histórico com pares (PF/PJ × idade da conta) | Bolton & Hand, nível 2; o PixSim tem exatamente esses atributos |
| **V5** Rótulos atrasados | Treino só com rótulos já reportados, usando o atraso de reporte do PixSim | Dal Pozzolo et al. (2018): na vida real o rótulo chega dias depois (MED) |
| **V6** Cold path no backtest + stacking | Ciclos do worker simulados em lote; scores de grafo e sequência como features do LightGBM | Avaliação honesta do GraphSAGE e do HMM (score do ciclo anterior); "embedding assíncrono → árvore" da pesquisa. Primeiro corte se o tempo apertar |
| **V7** Entrega | ADRs, README (validação externa), C4, CHANGELOG | — |

As fases rodam em sequência, um agente por vez: a máquina tem pouca RAM e a rodada anterior caiu ao rodar quatro em paralelo.

## Fica fora, e por quê

- **Elliptic:** Bitcoin tem outra dinâmica e o artigo original (Weber et al., 2019) já publica resultados de GCN e Random Forest nesse dataset.
- **Feature store em Redis:** overkill para o volume do desafio; o SQL indexado responde em milissegundos.
- **CUSUM e drift como job do worker:** o drift vira uma análise (PSI entre o nosso gerador e o PixSim) dentro da V3.
- Continuam fora RNN/LSTM, LLM e Benford ([plano 2](plano-de-implementacao-2.md#o-que-continua-fora-e-por-quê)).

## Cuidados

- Código e dados do PixSim são de terceiros: leitura antes de executar, ambiente isolado em `scripts/out/pixsim/` (fora do Git), nada com privilégio.
- Memória: um agente por vez, processos pesados com limite (`ulimit -v`), arquivos lidos em fatias.
- Cada fase termina com `make reset check`, `make parity`, `make calibrate-check` e CI verde.
