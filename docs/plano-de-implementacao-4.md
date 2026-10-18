---
title: Plano de implementação 4
summary: PixSim como referência de todas as métricas (o nosso simulador fica só para CI/CD) e retroalimentação pelo desfecho do MED simulada no backtest — desfechos na linha do tempo, sinal de fraude confirmada, curva semanal, retreino com champion/challenger e monitoramento.
related: [plano-de-implementacao-3.md, 05-motor/validacao-pixsim.md, 05-motor/calibracao.md, 02-arquitetura/decisoes/0017-ml-fora-do-prazo-e-do-hot-path.md]
sources: [PixSim (draw_report_delay, reported), Dal Pozzolo et al. (2018), Pesquisa QITech (MED, rótulos atrasados)]
---

# Plano de implementação 4

> **Registro histórico.** Plano escrito antes da implementação; caminhos, contagens e números podem não bater com o código entregue. O estado atual está no [README](../README.md), no [catálogo de regras](05-motor/regras.md) e nas [decisões](02-arquitetura/decisoes/README.md).

> [Índice](README.md) › Plano de implementação 4
>
> **Responde a:** de onde vêm os números do projeto daqui em diante? como o desfecho do MED volta para o motor?

**Estado:** aprovado pelo time.

## Decisões do time

- **O nosso simulador fica só para CI/CD:** testes, paridade e trava de regressão. Ele é rápido, determinístico e roda em máquina limpa, mas as fraudes dele foram desenhadas por nós.
- **Todas as outras métricas vêm do PixSim:** calibração, análises, modelos, README e apresentação. O PixSim também é simulado (de terceiros, calibrado com dados abertos do BC); os documentos dizem "métricas no PixSim", nunca "dado real".
- **A retroalimentação existe só no backtest:** a API continua com o contrato do enunciado (`POST` e `GET`), sem tabela nem regra nova.

## Fases

| Fase | Entrega |
|---|---|
| **P1** PixSim como referência | Grid de calibração com custo sobre o PixSim (mundo A para escolher, mundo B para confirmar); análises estatísticas regeradas no PixSim; `calibracao.md` e README com os números do PixSim; os números do nosso simulador ficam só na página de CI |
| **P2** Retroalimentação no backtest | Desfechos do MED na linha do tempo do backtest, no instante `transaction_date + atraso de reporte` do PixSim; Pix reprovado por nós não liquida e não gera desfecho (viés de seleção); sinal de "destino com fraude confirmada" registrado só no backtest; curva semana a semana de captura e custo com e sem retroalimentação; retreino semanal do LightGBM com rótulos maduros e champion/challenger (o desafiante roda em shadow na semana seguinte e é promovido se custar menos); monitoramento semanal (fraude que escapou e depois foi confirmada, precisão de 2FA e reprovação onde há rótulo) |
| **P3** Entrega | ADR do ciclo de retroalimentação (e o desenho da rota de desfechos como próximo passo de produção), C4, README, CHANGELOG |

## Fica fora

- Rota HTTP ou tabela para receber desfechos (fora do contrato do enunciado; fica desenhada na ADR).
- Rótulo do 2FA (o PixSim não modela) e marcação no DICT (externo).

## Cuidados

Um agente por vez, `ulimit -v`, leitura em streaming; mundos A e B do PixSim já gerados.
