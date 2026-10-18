---
title: "ADR 0032: Retroalimentação pelo MED simulada no backtest, não na API"
summary: O desfecho do MED volta para o motor só no backtest — reputação de destino com fraude confirmada, retreino semanal com champion/challenger e monitoramento —; a API mantém o contrato do enunciado e a rota de desfechos fica desenhada como próximo passo.
related: [0031-modelos-treinados-no-pixsim-e-rotulos-atrasados.md, 0019-reputacao-de-contraparte-derivada.md, 0022-shadow-mode.md, ../../05-motor/validacao-pixsim.md]
sources: [PixSim (report_delay, reported), Dal Pozzolo, Boracchi, Caelen, Alippi & Bontempi (2018), Credit card fraud detection: a realistic modeling and a novel learning strategy, IEEE Transactions on Neural Networks and Learning Systems 29(8), https://re.public.polimi.it/handle/11311/1044896, scripts/feedback/feedback.py]
---

# ADR 0032: Retroalimentação pelo MED simulada no backtest, não na API

> [Índice](../../README.md) › [Decisões](README.md) › 0032

**Status:** aceita

## Contexto

Um banco aprende com os desfechos: a fraude confirmada no MED marca o destino, alimenta o monitoramento e vira rótulo de treino. O enunciado limita a API a `POST` e `GET` e põe "outras APIs" fora do escopo. O time decidiu mostrar o ciclo onde ele cabe: no backtest, sobre o PixSim.

## Decisão

- **Linha do tempo de desfechos:**
  - Cada fraude reportada gera um desfecho em `transaction_date + atraso de reporte` (do PixSim).
  - Pix reprovado não liquida e não gera desfecho, o que reproduz o viés de seleção.
  - Pix com 2FA gera desfecho em 10% dos casos (`two_factor_escape_rate`).
- **Sinal imediato** `COUNTERPARTY_CONFIRMED_FRAUD`, só no backtest: o destino que já teve fraude confirmada, de outro pagador, pede 2FA. 2FA foi escolhido no mundo A (R$ 130 contra R$ 268 por mil Pix se reprovasse).
- **Retreino semanal com champion/challenger:** o LightGBM treina com os rótulos já chegados; o desafiante roda em shadow na semana seguinte e só é promovido se custar menos.
- **Monitoramento semanal:** fraude aprovada e depois confirmada, precisão observada × real do 2FA e da reprovação, fração de fraude sem desfecho possível.

## Resultados no PixSim (mundo B, custo ponderado por mil Pix)

| Cenário | Custo | Captura de vítimas |
|---|---|---|
| Só regras | R$ 158 | 38% |
| + sinal de fraude confirmada | R$ 145 | 60% |
| + LightGBM decidindo (só no backtest) | R$ 128 | 78% |
| + retreino semanal | R$ 128 | 78%; nenhum desafiante promovido |

O viés de seleção cresce com a eficácia: 72% das fraudes de vítima nunca geram desfecho no melhor cenário, e a precisão observada do 2FA fica cerca de 10 vezes abaixo da real.

## Alternativas descartadas

- **Rota `POST /pix/transaction/{id}/outcome` e tabela `pix_outcome` na API.**
  - **Preço:** sai do contrato do enunciado; vira o primeiro passo de produção, desenhado aqui.
  - **Ganharia se** o banco já recebesse o arquivo de retorno do MED.
- **Retreinar a cada rótulo.**
  - **Preço:** caro, instável, um rótulo muda pouco o modelo.
  - **Ganharia se** houvesse aprendizado online com pouca variância.

## Consequências

- O sinal de fraude confirmada é o ganho mais barato (−8% de custo, +21 pontos de captura) e o primeiro candidato a ir para a API.
- O retreino semanal não promoveu nenhum desafiante: o mundo do PixSim é estacionário e só cabem 4 retreinos em 30 dias. Retreinar compensa quando o padrão muda (drift); aqui não muda.
- As fraudes barradas entram no treino como negativas (sem desfecho), o que provavelmente prejudica os desafiantes; corrigir isso exige saber o que teria acontecido, que é o problema clássico de inferência de rejeitados.
