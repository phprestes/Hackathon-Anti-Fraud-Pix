---
title: "ADR 0025: Cold path em container worker, com scores pré-calculados lidos pelo hot path"
summary: Um container worker recalcula periodicamente a reputação de cada conta de destino a partir do grafo pagador → destino e grava em account_risk_score; a regra COUNTERPARTY_GRAPH_RISK só lê o score mais recente.
related: [0002-monolito-sincrono-sem-dependencia-externa.md, 0019-reputacao-de-contraparte-derivada.md, 0017-ml-fora-do-prazo-e-do-hot-path.md, ../c4.md]
sources: [Pesquisa QITech (GNN: padrões funil e dispersão; "pontuação pré-calculada de risco da conta recebedora"), Plano de implementação 2 (G5)]
---

# ADR 0025: Cold path em container worker, com scores pré-calculados lidos pelo hot path

> [Índice](../../README.md) › [Decisões](README.md) › 0025

**Status:** aceita

## Contexto

A pesquisa separa o que cabe no hot path (regras, ensembles, milissegundos) do que não cabe (análise de grafo, segundos). Em produção, a reputação de rede de cada conta é calculada fora do caminho do Pix e consultada já pronta. Os padrões de conta laranja são estruturais: funil (muitos pagadores para uma conta) e dispersão (recebe e repassa em seguida para várias contas).

## Decisão

- **Container `worker`**, com a mesma imagem e o mesmo código da `api` e o comando `python -m worker`. Recalcula a cada `WORKER_INTERVAL_SECONDS` (30). Erro num ciclo é logado e o laço segue.
- **Relógio dos dados:** o ciclo usa o maior `transaction_date` da base como "agora", coerente com a [ADR 0007](0007-relogio-da-transacao.md). Um ciclo é pulado se nada mudou.
- **Features de grafo em SQL**, para cada documento que foi destino nas últimas 72 h:
  - pagadores distintos em 24 h (funil);
  - destinos distintos para onde repassou em 6 h (dispersão);
  - pagadores que também pagaram destinos reprovados (2 saltos);
  - valor recebido;
  - idade da conta.
- **Score** logístico com pesos fixos (`GRAPH_RISK_*`), sem treino, gravado em `account_risk_score` (append-only) junto com as contribuições de cada feature.
- **Hot path:** `COUNTERPARTY_GRAPH_RISK` lê o score mais recente do destino com até 120 min de idade. Score ≥ 0,6 pede 2FA; ≥ 0,9 reprova. O motivo cita as features que mais pesaram. A regra decide, porque é explícita e explicável; o modelo aprendido (GraphSAGE, fase G6) fica em shadow.
- **Testes determinísticos:** `make test` para o worker; cada teste roda um ciclo de forma explícita (`docker compose run --rm worker python -m worker --once`), como processo externo, sem importar `src/`.

## Alternativas descartadas

- **Calcular o grafo dentro do POST.**
  - **Preço:** consultas de 2 saltos a cada Pix; a latência cresce com o grafo.
  - **Ganharia se** o grafo fosse pequeno e estável.
- **Kafka + Flink + Redis (streaming).**
  - **Preço:** três serviços a mais para mostrar o mesmo padrão.
  - **Ganharia se** fossem dezenas de milhares de Pix por segundo.
- **Cron fora do compose.**
  - **Preço:** quebra o "um comando sobe tudo" (R2).
  - **Ganharia se** houvesse um orquestrador como Airflow.

## Consequências

- O score tem atraso de até um ciclo. Por isso a regra exige score recente e fica muda sem ele.
- **Limite do simulador:** ele reproduz 14 dias em segundos, e o worker não acompanha, então a regra quase não dispara na simulação. A cobertura vem dos testes, que controlam o relógio. No backtest em lote o score é `None` (o `InMemoryHistory` não roda o worker), e por isso a paridade continua exata.
- `payer_sequence_score` já existe para o HMM.
