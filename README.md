# [Nome do grupo]

**Integrantes:** [nomes]

Motor antifraude de Pix do Hackathon QI Tech 2026: uma API que recebe um Pix e responde `approved`, `two_factor_required` ou `rejected`, sempre com o motivo. Feito a partir do [`bootcamp-base-api`](docs/referencia/base-service-readme.md). Stack: Python 3.11, FastAPI, PostgreSQL 16, Docker. Enunciado completo em [docs/01-contexto/enunciado.md](docs/01-contexto/enunciado.md).

> **Em números:** 18 regras que decidem, 5 modelos em shadow, 130 testes black box, CI verde. No simulador: cerca de 4% de 2FA em legítimos, 0,04% reprovados e nenhuma sequência de fraude simulada passa sem barreira. P95 de 55 ms pela API; o backtest em lote processa 8 mil Pix/s. Histórico no [CHANGELOG](CHANGELOG.md).

## Como o motor de decisão funciona

Cada `POST /pix/transaction` atravessa as camadas do Base Service. O controller confere se esse `id` de Pix já foi analisado (idempotência) e passa o Pix ao motor (`src/rules/engine.py`). O motor carrega do banco o histórico relevante do pagador, do aparelho e do destino, roda **todas** as regras sobre esse contexto e decide pela mais severa. Pix, análise e motivos são gravados no mesmo commit, e o `GET /pix/transaction/{id}` devolve a análise gravada.

Dois caminhos, como em produção:

- **Hot path (síncrono, dentro do POST):** 18 regras explícitas, que decidem, e 5 modelos em **shadow**, que calculam, gravam e nunca mudam a decisão.
- **Cold path (assíncrono):** um container `worker` que, a cada 30 s, calcula a reputação de cada conta de destino a partir do grafo pagador → destino, mais um GraphSAGE e um HMM de sequência. O hot path só lê o score pronto.

Detalhe em [motor de regras](docs/05-motor/motor-de-regras.md) e nos [diagramas C4](docs/02-arquitetura/c4.md). O porquê de cada escolha, com as alternativas descartadas, está nas [decisões](docs/02-arquitetura/decisoes/README.md).

## Regras

Fonte da verdade, com o porquê completo de cada parâmetro: [catálogo de regras](docs/05-motor/regras.md). Os parâmetros marcados com ★ foram ajustados com o simulador ([calibração](docs/05-motor/calibracao.md)). Todos são variáveis `RULE_*` em `src/constants.py`.

| Regra | Lógica | Parâmetros | Por quê |
|-------|--------|------------|---------|
| `LIMIT_NIGHT_AMOUNT` | Pix entre 20h e 6h (hora local) acima do teto; não vale para CNPJ | R$ 1.000 | Limite noturno padrão do BC para pessoa física (Res. 142/2021); sequestro relâmpago |
| `LIMIT_SINGLE_AMOUNT` | Valor de um Pix acima do teto | R$ 50 mil CPF, R$ 200 mil CNPJ | Teto de exposição de um Pix só |
| `VELOCITY_SOURCE_COUNT` | Tentativas do pagador em 10 min, inclusive reprovadas | 2FA a partir de 5, reprova a partir de 10 | Conta tomada é esvaziada em rajada; protege o pagador sem histórico |
| `VELOCITY_DEVICE_SOURCES` | Pagadores distintos no mesmo aparelho em 24 h | reprova acima de 3 | Fazenda de contas; família raramente passa de 3 |
| `VELOCITY_POISSON_GAMMA` | Rajada da última hora improvável para o ritmo histórico do pagador | ★ cauda < 0,0001, 24 h de histórico | O "rápido demais" de cada um: a 0,001 travava 143 legítimos, a 0,0001 trava 47 |
| `AMOUNT_SOURCE_DAILY_SUM` | Soma de 24 h (só não reprovados) + este Pix | ★ R$ 30 mil CPF, R$ 50 mil CNPJ | Fracionamento; a R$ 10 mil gerava 266 dos 347 casos de 2FA em legítimos |
| `PROFILE_NEW_DEVICE` | Pagador com histórico, aparelho nunca visto | a partir de R$ 500 | Primeiro passo da tomada de conta; piso evita fricção no cafezinho |
| `PROFILE_NEW_SOURCE_ACCOUNT` | Conta de origem nova com valor alto | < 7 dias e > R$ 2.000 | Conta aberta com identidade falsa é usada logo (art. 39-B do Regulamento do Pix) |
| `PROFILE_AMOUNT_ROBUST_Z` | z robusto de log(valor) sobre 30 dias do pagador (mediana/MAD) | z > 3,5, mínimo 5 Pix | Fora do padrão do próprio cliente (Bolton & Hand); robusto a histórico pequeno |
| `PROFILE_GEO_VELOCITY` | Distância ao último Pix com GPS ÷ tempo | > 50 km e > 900 km/h | Viagem impossível; 900 km/h é um avião comercial |
| `COUNTERPARTY_NEW_ACCOUNT` | Idade da conta de destino | 2FA < 30 dias; reprova < 3 dias e > R$ 1.000 | Contas laranja são novas; com vítima coagida, só o destino denuncia |
| `COUNTERPARTY_FAN_IN` | Pagadores distintos para o destino em 1 h | reprova acima de 10 | Conta de passagem (funil) |
| `COUNTERPARTY_FIRST_TIME_HIGH` | Primeiro Pix do pagador para esse destino, valor alto | > R$ 3.000 | Falso parente e falso boleto vão para destino novo; o aluguel não |
| `COUNTERPARTY_FLAGGED` | Destino recebeu Pix reprovado de outro pagador em 7 dias | 7 dias | Reputação derivada do próprio histórico, sem lista externa |
| `COUNTERPARTY_GRAPH_RISK` | Score de reputação do destino calculado pelo worker no grafo (funil, dispersão, 2 saltos, idade), com até 120 min | 2FA ≥ 0,6; reprova ≥ 0,9 | Conta laranja é um padrão de rede: muitos pagadores entrando e repasse para várias contas logo em seguida |
| `TYPOLOGY_ACCOUNT_TAKEOVER` | Histórico + aparelho novo + (viagem impossível ou z > 3,0) | z > 3,0 | Os sinais juntos descrevem tomada de conta: risco claro |
| `TYPOLOGY_MULE` | Destino < 30 dias recebendo de 5+ pagadores em 1 h | 5 pagadores | Barra a conta laranja antes do fan-in genérico |
| `TYPOLOGY_SPLITTING` | 6+ Pix pequenos (≤ R$ 2.000) para 4+ destinos **novos** em 24 h acima do corte | ★ R$ 15 mil | Fracionamento espalha para contas novas; contar só destinos novos zerou os legítimos reprovados |

**Calibração** (simulador com 4.926 Pix legítimos e 136 de fraude em 5 tipologias): cerca de 96% de legítimos aprovados, 3,8% com 2FA, 2 reprovados (0,04%), e as 22 sequências de fraude com ao menos um Pix barrado. Os dados são sintéticos e as fraudes foram desenhadas por nós, então isso mede fricção e coerência, não eficácia contra fraude real ([calibração](docs/05-motor/calibracao.md)).

## Como as regras viram decisão

Todas as 18 regras rodam, sem parar na primeira. Cada uma devolve nada, `two_factor_required` ou `rejected`, e a decisão final é a mais severa: `rejected` > `two_factor_required` > `approved`. Sem disparo, `approved`. A ordem das regras não muda a decisão, só a ordem dos motivos.

- **2FA** quando um sinal isolado gera dúvida, mas acontece com cliente bom: limites, aparelho novo, valor fora do perfil, conta de destino nova, primeiro Pix alto para alguém, destino sinalizado. O cliente legítimo resolve com um toque.
- **Reprovação** quando o risco é claro: um sinal extremo (conta de destino com menos de 3 dias e mais de R$ 1.000, 10 Pix em 10 min, aparelho com mais de 3 contas, mais de 10 pagadores para o mesmo destino em 1 h) ou uma **tipologia** (conta tomada, mula, fracionamento). Dois 2FA não somam uma reprovação: só uma tipologia explícita combina sinais.
- O `metadata` traz `reasons` (regra, decisão, motivo em português, do mais severo ao menos severo), `signals` (os números que cada regra usou) e `rule_set_version`.

Exemplos em [como as regras viram decisão](docs/05-motor/decisao.md).

## Além das regras: modelos em shadow

Sem rótulo real, nenhum modelo decide. Todos rodam em shadow: aparecem em `metadata.shadow` com o score e o que **decidiriam**, e o simulador mede como seria. Os rótulos de treino vêm do simulador, então isto prova que o caminho completo é viável, não que funciona contra fraude real ([ADR 0017](docs/02-arquitetura/decisoes/0017-ml-fora-do-prazo-e-do-hot-path.md)).

| Modelo | Onde roda | Como | Resultado (sintético) |
|---|---|---|---|
| Regressão logística + Platt | hot path | Treino em `scripts/` (sklearn só em dev), pesos em JSON, inferência em Python puro | AUC 0,98 |
| LightGBM | hot path | Árvores exportadas para JSON, avaliadas em Python puro (diferença de 6e-17 contra a biblioteca) | AUC 0,99. Regras + LightGBM barrariam 89% das fraudes, contra 81% só com as regras |
| Isolation Forest | hot path | Não supervisionado (só legítimos), árvores em JSON | AUC 0,87 |
| GraphSAGE | worker | 2 camadas, até 10 vizinhos, numpy | AUC 1,0, otimista: o grafo sintético é fácil |
| HMM de sequência | worker | 3 estados, Baum-Welch, numpy | AUC 0,51 no que o hot path vê: a sequência de Pix sozinha diz pouco |

Os três modelos do hot path custam 0,15 ms por Pix juntos. A imagem da `api` não ganhou nenhuma biblioteca de ML. Detalhes em [`scripts/model-results.md`](scripts/model-results.md) e nas ADRs [0022](docs/02-arquitetura/decisoes/0022-shadow-mode.md) a [0026](docs/02-arquitetura/decisoes/0026-graphsage-e-hmm-no-worker.md).

## Como rodar e testar

Pré-requisitos: Docker com `docker compose`, Git e Python 3.11 (ou `uv`).

```bash
make all      # sobe api, db e worker, espera ficarem healthy, cria o .venv (Python 3.11) e roda o pytest
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

Ferramentas de risco (rodam fora da API):

| Comando | Faz |
|---|---|
| `make simulate` | Manda tráfego sintético (legítimos + 5 tipologias de fraude) pela API e mede fricção, captura e latência |
| `make backtest` | O mesmo motor sobre um arquivo de eventos, sem HTTP e sem banco |
| `make parity` | Confere que API e backtest decidem igual, Pix a Pix |
| `make calibrate` / `make calibrate-check` | Grid de parâmetros / trava de regressão de fricção e captura (roda no CI) |
| `make train-models`, `make train-graphsage`, `make train-hmm` | Retreina os modelos em shadow |
| `make analyze` | Análises estatísticas ([docs/05-motor/analises.md](docs/05-motor/analises.md)) |

`make test` para o worker para que os testes controlem cada ciclo; `make up` religa. Outros comandos em [rodando localmente](docs/06-operacao/rodando-localmente.md).

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
src/        api em camadas do Base Service (+ rules/ para o motor, worker/ para o cold path)
tests/      testes black box por HTTP
scripts/    simulador, backtest, paridade, calibração, treino e análises
database/   imagem do Postgres e schema (database.sql)
docs/       documentação navegável, ADRs e o enunciado
.agents/    skills para agentes de IA (ponto de entrada: AGENTS.md)
```

## Licença

[MIT](LICENSE)
