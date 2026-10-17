---
title: Rodando localmente
summary: Comandos do Makefile, variáveis de ambiente, portas e armadilhas comuns.
related: [../07-testes/estrategia.md, ../referencia/base-service-readme.md]
sources: [bootcamp-base-api README (seções 1 a 3), Makefile]
---

# Rodando localmente

> [Índice](../README.md) › Operação › Rodando localmente
>
> **Responde a:** como subir, testar, resetar? que variável muda o quê? o que fazer quando quebra?

## Pré-requisitos

Docker com `docker compose`, Git e Python 3.11 (ou `uv`, que o `make install` usa para baixar o 3.11). O SQLAlchemy 2.0.23 quebra no Python 3.12+.

## Comandos

| Comando | Faz | Quando |
|---|---|---|
| `make` | lista os alvos | sempre que esquecer |
| `make all` | `up` + `test`: do clone ao verde | primeira vez; antes de entregar |
| `make up` | sobe `api`, `db` e `worker` e espera `healthy` | começo do trabalho |
| `make test` | para o `worker` e roda `pytest -v` (os testes disparam um ciclo do worker quando precisam) | a cada mudança |
| `make lint` | `flake8 src tests` | antes de commitar |
| `make check` | `lint` + `test` | antes de dizer que terminou |
| `make reset` | apaga o volume e recria o banco | depois de mudar `database/database.sql` |
| `make rebuild` | reconstrói a imagem sem cache | depois de mudar `requirements.txt` |
| `make logs` | segue o log da `api` | para achar um `x-request-id` |
| `make simulate` | tráfego sintético pela API (~3 min); suja o banco | medir fricção e latência |
| `make events` / `make backtest` | gera eventos / roda o motor em lote, sem HTTP e sem banco | experimentos rápidos |
| `make parity` | zera o banco e compara API × backtest Pix a Pix | depois de mexer em agregados |
| `make calibrate` / `make calibrate-check` | grid de parâmetros / trava de regressão | antes de mudar parâmetro de regra |
| `make datasets`, `make train-models`, `make train-graphsage`, `make train-hmm`, `make model-parity` | dados de treino, treino e fidelidade dos modelos em shadow | retreinar |
| `make analyze` | análises estatísticas em `docs/05-motor/analises.md` | revisar hipóteses das regras |
| `make clean` | remove containers, volume, `.venv` e caches | recomeçar do zero |

Sem `make`: `docker compose up -d --wait`, depois `python3.11 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt && .venv/bin/pytest -v`.

## Variáveis

Nenhum `.env` é necessário: todo valor tem padrão no `docker-compose.yml`. Para trocar, `cp .env.example .env` e edite.

| Variável | Padrão | Para quê |
|---|---|---|
| `API_PORT` | 3000 | porta da API na sua máquina |
| `DB_PORT` | 5432 | porta do banco na sua máquina (mude também a `DATABASE_URL`) |
| `INTERNAL_TOKEN` | `default_token` | header exigido em toda rota de negócio |
| `RULE_*` | ver [catálogo de regras](../05-motor/regras.md) | parâmetros das regras ([ADR 0008](../02-arquitetura/decisoes/0008-parametros-de-regra-por-ambiente.md)) |

## Armadilhas

| Sintoma | Correção |
|---|---|
| `port is already allocated` | `API_PORT`/`DB_PORT` no `.env` |
| `relation "…" does not exist` | `make reset` |
| primeiro teste falha com conexão recusada | espere o `(healthy)`; `make up` já espera |
| teste quebra depois de mudar `requirements.txt` | `make rebuild` |

Mais detalhes no [README original da base](../referencia/base-service-readme.md#3-quando-dá-errado).
