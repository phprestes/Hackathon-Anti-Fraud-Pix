# Hackathon-Anti-Fraud-Pix

**Integrantes:** Pedro H. S. Prestes · Laura Pazini Medeiros

Motor antifraude de Pix do Hackathon QI Tech 2026: uma API que recebe um Pix e responde `approved`, `two_factor_required` ou `rejected`, sempre com o motivo. Feito a partir do [`bootcamp-base-api`](docs/referencia/base-service-readme.md). Stack: Python 3.11, FastAPI, PostgreSQL 16, Docker. Enunciado completo em [docs/01-contexto/enunciado.md](docs/01-contexto/enunciado.md).

> **Em números:** 15 regras que decidem, 5 modelos em shadow, 113 testes black box, CI verde. No PixSim (simulador de terceiros, mundo A, [validação](docs/05-motor/validacao-pixsim.md)): 3,8% de 2FA em legítimos, 0,01% reprovados, 52% dos Pix de vítima barrados (conta tomada: 99% dos eventos com ao menos um Pix barrado) e custo ponderado de R$ 132,13 por 1.000 Pix; no mundo B de confirmação, R$ 153,51 contra R$ 161,87 antes da [calibração](docs/05-motor/calibracao.md) (mesmo modelo de custo: reprovar legítimo custa R$ 50 mais 2% do valor). O backtest em memória avalia um Pix em P95 de 0,63 ms (2,6 mil Pix/s). Histórico no [CHANGELOG](CHANGELOG.md).

## Como o motor de decisão funciona

Cada `POST /pix/transaction` atravessa as camadas do Base Service. O controller confere se esse `id` de Pix já foi analisado (idempotência) e passa o Pix ao motor (`src/rules/core/engine.py`). O motor carrega do banco o histórico relevante do pagador, do aparelho e do destino, roda **todas** as regras sobre esse contexto e decide pela mais severa. Pix, análise e motivos são gravados no mesmo commit, e o `GET /pix/transaction/{id}` devolve a análise gravada.

Dois caminhos, como em produção:

- **Hot path (síncrono, dentro do POST):** 15 regras explícitas, que decidem, e 5 modelos em **shadow**, que calculam, gravam e nunca mudam a decisão.
- **Cold path (assíncrono):** um container `worker` que, a cada 30 s, calcula a reputação de cada conta de destino a partir do grafo pagador → destino, mais um GraphSAGE e um HMM de sequência. O hot path só lê o score pronto.

Detalhe em [motor de regras](docs/05-motor/motor-de-regras.md) e nos [diagramas C4](docs/02-arquitetura/c4.md). O porquê de cada escolha, com as alternativas descartadas, está nas [decisões](docs/02-arquitetura/decisoes/README.md).

## Regras

Fonte da verdade, com o porquê completo de cada parâmetro: [catálogo de regras](docs/05-motor/regras.md). Os parâmetros marcados com ★ foram ajustados no PixSim pelo custo ponderado, escolhidos no mundo A e confirmados no B ([calibração](docs/05-motor/calibracao.md)); "PixSim" na coluna "Por quê" é o efeito medido lá, em simulador de terceiros, não em Pix real. Todos são variáveis `RULE_*` em `src/constants.py`.

| Regra | Lógica | Parâmetros | Por quê (fonte e número do PixSim, mundo B) |
|-------|--------|------------|---------|
| `LIMIT_NIGHT_AMOUNT` | Pix entre 20h e 6h (hora local) acima do teto; não vale para CNPJ | R$ 1.000 | [Res. BCB 142/2021, art. 2º, I](https://www.bcb.gov.br/estabilidadefinanceira/exibenormativo?tipo=Resolu%C3%A7%C3%A3o%20BCB&numero=142) e IN BCB 512/2024, art. 3º, §7º, II: R$ 1.000 no período noturno para pessoa física. Mantido por âncora regulatória. PixSim: dispara em 0,57% dos legítimos e 4,6% das vítimas; ablação −R$ 6,52 por 1.000 Pix (sem efeito no PixSim, custa); R$ 2.000 custaria R$ 4,80 a menos |
| `LIMIT_SINGLE_AMOUNT` | Valor de um Pix acima do teto | R$ 50 mil CPF, R$ 200 mil CNPJ | Teto de exposição; o art. 37 do Regulamento do Pix só exige critério de risco, sem valor. PixSim: dispara em 0,02% dos legítimos e 0,0% das vítimas; ablação −R$ 0,22 por 1.000 Pix (sem efeito no PixSim, custa) |
| `VELOCITY_SOURCE_COUNT` | Tentativas do pagador em 10 min, inclusive reprovadas | 2FA a partir de 5, reprova a partir de 10 | Velocity do enunciado; limiares do time, sem fonte externa. PixSim: nunca dispara, sem efeito |
| `VELOCITY_DEVICE_SOURCES` | Pagadores distintos no mesmo aparelho em 24 h | reprova acima de 3 | Fazenda de contas; limiar do time, sem fonte externa. PixSim: nunca dispara, sem efeito |
| `VELOCITY_POISSON_GAMMA` | Rajada da última hora improvável para o ritmo histórico do pagador | ★ cauda < 30 ppm, 24 h de histórico | Gamma–Poisson (Gelman et al., 2013) sobre o perfil do titular (Bolton & Hand, 2002). PixSim: dispara em 0,15% dos legítimos e 6,8% das vítimas; ablação +R$ 3,77 por 1.000 Pix (contribui); lift 46x |
| `PROFILE_NEW_DEVICE` | Pagador com histórico, aparelho nunca visto | ★ a partir de R$ 200 | Troca de aparelho abre a conta tomada (Pizzolato et al., 2025). PixSim: dispara em 0,00% dos legítimos e 15,0% das vítimas; ablação +R$ 5,60 por 1.000 Pix (contribui); precisão ponderada 43,8% (o legítimo do PixSim quase não troca de aparelho) |
| `PROFILE_NEW_SOURCE_ACCOUNT` | Conta de origem nova com valor alto | < 7 dias e > R$ 2.000 | Analogia ao fator "idade da conta" do [Regulamento do Pix, art. 39-B](https://www.bcb.gov.br/content/estabilidadefinanceira/pix/Pix_Regulation/Resolution_BCB_1.pdf), §1º, II, que na norma é a do recebedor. PixSim: dispara em 0,00% dos legítimos e 0,1% das vítimas; ablação +R$ 0,18 por 1.000 Pix (contribui) |
| `PROFILE_AMOUNT_ROBUST_Z` | z robusto de log(valor) sobre 30 dias do pagador (mediana/MAD) | ★ z > 4,5, mínimo 5 Pix | z modificado com MAD (Iglewicz & Hoaglin, 1993; corte 3,5 sob normalidade) e perfil do titular (Bolton & Hand, 2002). PixSim: dispara em 0,12% dos legítimos e 1,0% das vítimas; ablação −R$ 1,54 por 1.000 Pix (sem efeito no PixSim, custa) |
| `PROFILE_GEO_VELOCITY` | Distância ao último Pix com GPS ÷ tempo | > 50 km e > 900 km/h | Viagem impossível; 900 km/h é convenção do time, sem fonte. PixSim: nunca dispara, sem efeito (o PixSim não tem geolocalização) |
| `COUNTERPARTY_NEW_ACCOUNT` | Idade da conta de destino | 2FA < 30 dias; reprova < 3 dias e > R$ 1.000 | [Regulamento do Pix, art. 39-B](https://www.bcb.gov.br/content/estabilidadefinanceira/pix/Pix_Regulation/Resolution_BCB_1.pdf), §1º, II: tempo de abertura da conta do recebedor. PixSim: dispara em 1,13% dos legítimos e 1,1% das vítimas; ablação −R$ 25,38 por 1.000 Pix (sem efeito no PixSim, custa); as mulas do PixSim têm idade comum |
| `COUNTERPARTY_FAN_IN` | Pagadores distintos para o destino em 1 h | reprova acima de 10 | Conta de passagem (funil); limiar do time. PixSim: nunca dispara, sem efeito |
| `COUNTERPARTY_FIRST_TIME_HIGH` | Primeiro Pix do pagador para esse destino, valor alto | ★ > R$ 1.000 | [Regulamento do Pix, art. 39-B](https://www.bcb.gov.br/content/estabilidadefinanceira/pix/Pix_Regulation/Resolution_BCB_1.pdf), §1º, IV: recorrência entre pagador e recebedor. PixSim: dispara em 1,29% dos legítimos e 32,7% das vítimas; ablação +R$ 34,63 por 1.000 Pix (contribui); precisão ponderada 0,2%, lift 25,4x: a regra de maior contribuição |
| `COUNTERPARTY_GRAPH_RISK` | Reputação do destino calculada pelo worker no grafo, com até 120 min | 2FA ≥ 0,6; reprova ≥ 0,9 | Conta laranja é padrão de rede; GraphSAGE offline tem AUC de nó 0,919 (Hamilton et al., 2017). PixSim: nunca dispara, sem efeito (o worker não roda no backtest) |
| `TYPOLOGY_ACCOUNT_TAKEOVER` | Histórico + aparelho novo + (viagem impossível ou z > 3,0) | z > 3,0 | Tomada de conta e acesso remoto (Pizzolato et al., 2025). PixSim: dispara em 0,00% dos legítimos e 1,0% das vítimas; ablação +R$ 0,31 por 1.000 Pix (contribui); precisão ponderada 100% |
| `TYPOLOGY_MULE` | Destino < 30 dias recebendo de 5+ pagadores em 1 h | 5 pagadores | Idade da conta do recebedor ([Regulamento do Pix, art. 39-B](https://www.bcb.gov.br/content/estabilidadefinanceira/pix/Pix_Regulation/Resolution_BCB_1.pdf), §1º, II) com padrão funil. PixSim: dispara em 0,00% dos legítimos e 0,0% das vítimas; ablação −R$ 0,39 por 1.000 Pix (sem efeito no PixSim, custa) |

**Descartadas** ([ADR 0033](docs/02-arquitetura/decisoes/0033-regras-descartadas-pela-ablacao.md)): `TYPOLOGY_SPLITTING`, `COUNTERPARTY_FLAGGED` e `AMOUNT_SOURCE_DAILY_SUM` custavam mais do que evitavam nos dois mundos do PixSim e não têm âncora regulatória verificada. Sem as três, o custo cai de R$ 132,13 para R$ 109,61 por 1.000 Pix no mundo A e de R$ 153,51 para R$ 118,82 no B. Fica a regra que contribui no PixSim, tem âncora do BCB ou cobre um sinal que o PixSim não gera.

**Calibração no PixSim** (mundos A e B, 30 dias avaliados, 125 mil Pix legítimos e 986 eventos de fraude cada): no mundo A, 96,2% dos legítimos aprovados, 3,8% com 2FA, 0,01% reprovados, 51,7% dos Pix pagador→mula barrados e ao menos um Pix barrado em 591 dos 986 eventos de fraude (conta tomada 98,6%, engenharia social 57,3%, QR adulterado 29,4%, Pix errado 12,1%). No B: 4,1% de 2FA, 0,03% reprovados, 51,8% barrados. É simulador de terceiros, não Pix real: mede fricção e custo relativo entre configurações, não eficácia em produção ([calibração](docs/05-motor/calibracao.md), [validação](docs/05-motor/validacao-pixsim.md)). Nosso simulador (`scripts/fixture/simulate.py`) é só fixture do CI e alimenta a trava de regressão `make calibrate-check`.

## Como as regras viram decisão

Todas as 15 regras rodam, sem parar na primeira. Cada uma devolve nada, `two_factor_required` ou `rejected`, e a decisão final é a mais severa: `rejected` > `two_factor_required` > `approved`. Sem disparo, `approved`. A ordem das regras não muda a decisão, só a ordem dos motivos.

- **2FA** quando um sinal isolado gera dúvida, mas acontece com cliente bom: limites, aparelho novo, valor fora do perfil, conta de destino nova, primeiro Pix alto para alguém. O cliente legítimo resolve com um toque.
- **Reprovação** quando o risco é claro: um sinal extremo (conta de destino com menos de 3 dias e mais de R$ 1.000, 10 Pix em 10 min, aparelho com mais de 3 contas, mais de 10 pagadores para o mesmo destino em 1 h) ou uma **tipologia** (conta tomada, mula). Dois 2FA não somam uma reprovação: só uma tipologia explícita combina sinais.
- O `metadata` traz `reasons` (regra, decisão, motivo em português, do mais severo ao menos severo), `signals` (os números que cada regra usou) e `rule_set_version`.

Exemplos em [como as regras viram decisão](docs/05-motor/decisao.md).

## Além das regras: modelos em shadow

Sem rótulo real, nenhum modelo decide. Todos rodam em shadow: aparecem em `metadata.shadow` com o score e o que **decidiriam**, e o backtest mede como seria. A logística, o LightGBM e o GraphSAGE são treinados no mundo A do PixSim e avaliados no B (o Isolation Forest e o HMM instalados vêm do nosso simulador), então isto prova que o caminho completo é viável, não que funciona contra fraude real ([ADR 0017](docs/02-arquitetura/decisoes/0017-ml-fora-do-prazo-e-do-hot-path.md)).

| Modelo | Onde roda | Como | Resultado (PixSim, treino em A, teste em B) |
|---|---|---|---|
| Regressão logística + Platt | hot path | Treino em `scripts/` (sklearn só em dev), pesos em JSON, inferência em Python puro | AUC 0,990 |
| LightGBM | hot path | Árvores exportadas para JSON, avaliadas em Python puro (diferença máxima de 1,1e-16 contra a biblioteca; 1,1e-15 na logística e 1,7e-16 no Isolation Forest, em 14.202 Pix) | AUC 0,990. No mundo B, com as regras de antes da calibração, regras + LightGBM barrariam 70,8% dos Pix de vítima no limiar, contra 38,4% só com as regras (as regras atuais sozinhas barram 51,8%) |
| Isolation Forest | hot path | Não supervisionado (só legítimos), árvores em JSON | Instalado o do simulador: AUC 0,788 no mundo B. O treinado no PixSim (AUC 0,846, captura só 8,5% no limiar p99) não atendeu ao critério de troca |
| GraphSAGE | worker | 2 camadas, até 10 vizinhos, numpy | AUC de nó 0,92 no mundo B, otimista: o rótulo `is_mule` é estático por conta |
| HMM de sequência | worker | 3 estados, Baum-Welch, numpy | Instalado o do simulador; não avaliado no PixSim, onde a sequência de Pix sozinha diz pouco |

Os mundos A e B vêm do mesmo gerador, então a generalização medida é entre amostras, não entre geradores. A imagem da `api` não ganhou nenhuma biblioteca de ML. Detalhes na [validação no PixSim](docs/05-motor/validacao-pixsim.md) e nas ADRs [0022](docs/02-arquitetura/decisoes/0022-shadow-mode.md) a [0026](docs/02-arquitetura/decisoes/0026-graphsage-e-hmm-no-worker.md).

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
| `make simulate` | Fixture do CI, sem valor estatístico: manda tráfego sintético nosso (legítimos + 5 tipologias de fraude) pela API e mede latência |
| `make backtest` | O mesmo motor sobre um arquivo de eventos, sem HTTP e sem banco |
| `make parity` | Confere que API e backtest decidem igual, Pix a Pix |
| `make calibrate-pixsim` | Grid de parâmetros pelo custo ponderado no PixSim: escolhe no mundo A, confirma no B |
| `make rule-ablation` | Ablação por regra e sensibilidade dos parâmetros no mundo B do PixSim ([validação](docs/05-motor/validacao-pixsim.md#contribuição-de-cada-regra)) |
| `make calibrate` / `make calibrate-check` | Grid no nosso simulador (fixture, sem valor estatístico) / trava de regressão de fricção e captura (roda no CI) |
| `make train-models`, `make train-graphsage`, `make train-hmm` | Retreina os modelos em shadow |
| `make analyze` | Análises estatísticas no PixSim ([docs/05-motor/analises.md](docs/05-motor/analises.md)) |

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
