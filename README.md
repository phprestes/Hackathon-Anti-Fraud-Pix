# [Nome do grupo]

**Integrantes:** [nomes]

Motor antifraude de Pix do Hackathon QI Tech 2026: uma API que recebe um Pix e responde `approved`, `two_factor_required` ou `rejected`, sempre com o motivo. Feito a partir do [`bootcamp-base-api`](docs/referencia/base-service-readme.md). Stack: Python 3.11, FastAPI, PostgreSQL 16, Docker. Enunciado completo em [docs/01-contexto/enunciado.md](docs/01-contexto/enunciado.md).

> **Estado:** estrutura e decisões prontas; motor em construção. O que já mudou está no [CHANGELOG](CHANGELOG.md).

## Como o motor de decisão funciona

Cada `POST /pix/transaction` atravessa as camadas do Base Service. O controller confere se esse `id` de Pix já foi analisado (idempotência), carrega do banco o histórico relevante do pagador, do aparelho e do destino, e passa o Pix e esse contexto por **todas** as regras. Cada regra é uma classe pequena em `src/rules/` que olha um sinal e diz se dispara. Pix, análise e motivos são gravados no mesmo commit, e o `GET /pix/transaction/{id}` devolve a análise gravada.

Detalhe em [motor de regras](docs/05-motor/motor-de-regras.md). O porquê de cada escolha, com as alternativas descartadas, está nas [decisões](docs/02-arquitetura/decisoes/README.md).

## Regras

Fonte da verdade: [catálogo de regras](docs/05-motor/regras.md). Os parâmetros abaixo são **sugestões iniciais**, que o time ainda vai calibrar e justificar.

| Regra | Lógica | Parâmetros | Por quê |
|-------|--------|------------|---------|
| `LIMIT_NIGHT_AMOUNT` | Pix entre 20h e 6h acima do teto noturno | R$ 1.000 | O limite noturno padrão do BC para pessoa física; golpes de sequestro concentram-se à noite |
| `VELOCITY_SOURCE_COUNT` | Pix do pagador nos últimos 10 min | 2FA a partir de 5, reprova a partir de 10 | Conta tomada é esvaziada em rajada |
| `VELOCITY_DEVICE_SOURCES` | Pagadores distintos no mesmo aparelho em 24h | reprova acima de 3 | Aparelho operando várias contas = fazenda de contas |
| `AMOUNT_SOURCE_DAILY_SUM` | Soma do pagador em 24h | R$ 10.000 | Fracionamento para fugir do teto por Pix |
| `PROFILE_AMOUNT_OUTLIER` | Valor × média de 30 dias do pagador | 5×, com 5 Pix de histórico no mínimo | Fora do padrão do cliente |
| `COUNTERPARTY_NEW_ACCOUNT` | Idade da conta de destino | 2FA abaixo de 30 dias | Contas laranja são novas |
| `COUNTERPARTY_FAN_IN` | Pagadores distintos para o mesmo destino em 1h | reprova acima de 10 | Conta de passagem recebendo de várias vítimas |

Lista completa, com as candidatas restantes, no [catálogo](docs/05-motor/regras.md).

## Como as regras viram decisão

Todas as regras rodam, sem parar na primeira. Cada uma devolve nada, `two_factor_required` (dúvida: o sinal sozinho não prova fraude) ou `rejected` (risco claro). A decisão final é a mais severa: `rejected` > `two_factor_required` > `approved`. Sem disparo, `approved`. Todos os disparos vão para `metadata.reasons`, do mais severo ao menos severo, e a ordem das regras não muda a decisão.

Exemplos e critérios de 2FA em [como as regras viram decisão](docs/05-motor/decisao.md).

## Como rodar e testar

Pré-requisitos: Docker com `docker compose`, Git e Python 3.11 (ou `uv`).

```bash
make all      # sobe api e db, espera ficarem healthy, cria o .venv (Python 3.11) e roda o pytest
```

Sem `make`:

```bash
docker compose up -d --wait
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -v
```

A API responde em `http://localhost:3000`. Toda rota, menos `/` e `/health_check`, exige `INTERNAL-TOKEN: default_token`.

```bash
curl -X POST http://localhost:3000/pix/transaction \
  -H "INTERNAL-TOKEN: default_token" -H "Content-Type: application/json" \
  -d @docs/03-api/exemplo-pix.json

curl http://localhost:3000/pix/transaction/pix-000123 -H "INTERNAL-TOKEN: default_token"
```

Outros comandos (`make up`, `make test`, `make lint`, `make reset`…) em [rodando localmente](docs/06-operacao/rodando-localmente.md).

## Documentação

| Quero entender… | Leia |
|---|---|
| o que foi pedido | [enunciado](docs/01-contexto/enunciado.md) |
| o problema e as garantias | [problema](docs/01-contexto/problema.md) |
| por que cada decisão | [decisões (ADRs)](docs/02-arquitetura/decisoes/README.md) |
| o contrato da API | [rotas](docs/03-api/rotas.md), [erros](docs/03-api/erros.md) |
| o banco | [modelo de dados](docs/04-dados/modelo.md) |
| como testamos | [estratégia de testes](docs/07-testes/estrategia.md) |
| o que mudou e quem mudou | [CHANGELOG](CHANGELOG.md) |
| tudo | [índice da documentação](docs/README.md) ou [`llms.txt`](llms.txt) |

Agentes de código seguem o [`AGENTS.md`](AGENTS.md) e as skills em [`.agents/`](.agents/README.md).

## Estrutura

```
src/        api em camadas do Base Service (+ rules/ para o motor)
tests/      testes black box por HTTP
database/   imagem do Postgres e schema (database.sql)
docs/       documentação navegável, ADRs e o enunciado
.agents/    skills para agentes de IA (ponto de entrada: AGENTS.md)
```

## Licença

[MIT](LICENSE)
