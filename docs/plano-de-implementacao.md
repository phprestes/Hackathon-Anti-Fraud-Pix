---
title: Plano de implementação
summary: Triagem da pesquisa do time (o que fazer, talvez ou não até domingo 12:00), sugestões novas, fases com time-box, paralelismo e riscos.
related: [05-motor/motor-de-regras.md, 05-motor/regras.md, 02-arquitetura/decisoes/README.md, ../CHANGELOG.md]
sources: [Pesquisa QITech (PDF do time, 13 p.), Desafio Antifraude Pix, ADRs 0001–0015]
---

# Plano de implementação

> [Índice](README.md) › Plano de implementação
>
> **Responde a:** o que da pesquisa entra até o prazo? em que ordem? quem faz o quê? o que cortar se atrasar?

**Estado:** aprovado como plano. As decisões novas daqui (sugestões N1–N6, sinais estatísticos) **ainda não viraram ADR**; isso acontece numa etapa seguinte, com autorização.

## Premissas

- 3 pessoas + agentes de código; ~21h úteis a partir de sábado 15:00.
- **Código congelado domingo 09:00.** De 09:00 a 12:00, só README, calibração final e apresentação.
- **Nenhuma dependência nova de runtime.** Estatística em Python puro (`math`, `statistics`); a imagem continua a do Base Service.
- O enunciado não traz rótulo de fraude: o núcleo é regra explícita + estatística sobre o histórico que a própria API acumula.

## Triagem da pesquisa

| Item da pesquisa | Veredito | Porquê |
|---|---|---|
| M0 regras determinísticas (limite, velocity, montante, conta nova, fan-in, device) | **FAZER (núcleo)** | Critérios 1 e 4; já desenhado nas [ADRs 0004–0008](02-arquitetura/decisoes/README.md) |
| Features: idade das contas, velocity 1h/24h, soma 24h, recorrência do par, fan-in, device novo, device compartilhado | **FAZER** | Só payload + SQL indexado; o art. 39-B do Regulamento do Pix dá o "porquê" regulatório |
| M1 z robusto (mediana/MAD de `log(amount)`) | **FAZER** | Python puro; resolve "Perfil" com histórico pequeno e assimétrico (Bolton & Hand, 2002) |
| M1 velocity Poisson–Gamma (preditiva binomial negativa) | **FAZER** | Python puro (`math.lgamma`); dá score a pagador novo sem limiar arbitrário |
| Distância geográfica (haversine, viagem impossível) | **FAZER** | Barato; `geolocation` é opcional, então a regra fica muda sem ela |
| Horário atípico por conta (frequência suavizada) | **TALVEZ** (F4) | A pesquisa contradiz o limite noturno fixo; só se sobrar tempo |
| Metadata com regras, z-scores e versão do conjunto de regras | **FAZER** | Explicabilidade + base para o art. 20 da LGPD |
| Testes dos 3 cenários (normal, mula, conta tomada) | **FAZER** | Critério 4; vem direto da pesquisa |
| Medir P95 local | **FAZER** (via simulador) | Argumento de latência na apresentação |
| Análise 7: sensibilidade de limiar (% em cada faixa) | **FAZER** (via simulador) | A banca vai perguntar de fricção |
| Análises 1–2: QQ-plot de `log(amount)`, dispersão média × variância | **TALVEZ** | Só sobre dado simulado, evidência fraca; um parágrafo no README se sobrar |
| M2 Isolation Forest | **NÃO (roadmap)** | sklearn na imagem; treino em dado sintético é circular; explicação ruim |
| M3 regressão logística / LightGBM + calibração Platt | **NÃO (roadmap)** | Sem rótulo real; a própria pesquisa admite a circularidade |
| M4 score ponderado | **NÃO** | Conflita com as [ADRs 0004](02-arquitetura/decisoes/0004-motor-de-regras-em-codigo.md) e [0006](02-arquitetura/decisoes/0006-pior-decisao-vence-e-todas-as-regras-rodam.md); substituído por regras compostas (N1) |
| GNN, RNN/LSTM, HMM, JEV/LLM, Benford, PSI/drift, Kafka/Flink/Redis | **NÃO (roadmap)** | Fora do escopo e do prazo; viram o slide "o que faríamos em produção" |
| Tabelas `accounts`/`devices` normalizadas | **NÃO** | A [ADR 0009](02-arquitetura/decisoes/0009-historico-append-only.md) já decidiu retrato por Pix; `first_seen` sai de `MIN(transaction_date)` |
| Listas de bloqueio em memória | **TROCAR** por N2 | Lista em memória some no restart e não tem fonte de dados |

## Sugestões novas (não estão na pesquisa)

- **N1. Regras compostas por tipologia** (taxonomia de Pizzolato et al., 2025):
  - `TYPOLOGY_ACCOUNT_TAKEOVER`: device novo + geo distante + valor fora do perfil → `rejected`.
  - `TYPOLOGY_MULE`: destino novo + fan-in alto.
  - `TYPOLOGY_SPLITTING`: vários Pix pequenos somando acima do teto.

  Substitui o M4 sem perder a explicação.
- **N2. Reputação de contraparte derivada do próprio histórico.** Destino que recebeu Pix `rejected` nos últimos 7 dias → 2FA para outros pagadores. É uma "GNN do pobre", sem lista externa.
- **N3. Simulador de calibração** `scripts/fixture/simulate.py` (fora de `src/`, usa `requests`). Gera uma população legítima e fraudes injetadas por tipologia, manda tudo pela API e imprime a tabela por faixa, a matriz por tipologia e o P95. É o "porquê" numérico dos parâmetros.
- **N4. Redutores de fricção.** Pix para o mesmo documento (self-transfer) não dispara regras de contraparte; CPF e CNPJ têm limites diferentes.
- **N5. O que conta em cada janela.** Velocity conta **todas** as tentativas; montante soma só as não reprovadas, porque Pix reprovado não saiu.
- **N6. Versão do conjunto de regras** (`rule_set_version`) gravada na análise e no metadata, para auditoria e reprocessamento.

## Fases

Time-box por fase. Se uma fase atrasar, corte o que a última coluna indica antes de invadir a próxima.

| Fase | Janela | Entrega | Arquivos principais | Corta se atrasar? |
|---|---|---|---|---|
| **F0** Esqueleto | sáb 15–17h | DDL do [modelo](04-dados/modelo.md) em `database/database.sql`; models; schema `post_pix_transaction.json`; POST/GET sempre `approved`; idempotência ([ADR 0012](02-arquitetura/decisoes/0012-idempotencia-pelo-id-do-pix.md)); remover `sample_entity` e os códigos `QIT001xxx` | `database/database.sql`, `src/models/`, `src/schemas/`, `src/resources/pix_transaction.py`, `src/controllers/pix_transaction_controller.py`, `src/repositories/pix_transaction_repository.py`, `src/dtos/`, `src/app.py`, `tests/integration/pix/` | não |
| **F1** Núcleo do motor | sáb 17–20h | `BaseRule`, `RuleResult`, `RuleContext`, `ACTIVE_RULES`, agregação por severidade, gravação de motivos; primeiras regras: `COUNTERPARTY_NEW_ACCOUNT`, `VELOCITY_SOURCE_COUNT`, `AMOUNT_SOURCE_DAILY_SUM` | `src/rules/`, `src/constants.py` | não |
| **F2** Regras M0 restantes | sáb 20h – dom 01h | `LIMIT_*`, `VELOCITY_DEVICE_SOURCES`, `COUNTERPARTY_FAN_IN`, `PROFILE_NEW_DEVICE`, `PROFILE_NEW_SOURCE_ACCOUNT`, `COUNTERPARTY_FIRST_TIME_HIGH`; N4 e N5 | `src/rules/*_rule.py` | corta `LIMIT_SINGLE_AMOUNT` e `COUNTERPARTY_FIRST_TIME_HIGH` |
| **F3** Sinais estatísticos (M1) | dom 01–04h | `PROFILE_AMOUNT_ROBUST_Z`, `VELOCITY_POISSON_GAMMA`, `PROFILE_GEO_VELOCITY`; z-scores no metadata; N6 | `src/rules/`, `src/utils/statistics.py` | corta Poisson–Gamma (fica a velocity fixa) |
| **F4** Compostas + reputação | dom 04–06h | N1, N2; horário atípico se sobrar | `src/rules/typology_*_rule.py` | corta a fase inteira |
| **F5** Simulador e calibração | dom 06–09h | N3: tabela de faixas, matriz por tipologia, P95; ajustar os padrões de `constants.py` com o resultado | `scripts/fixture/simulate.py`, `docs/05-motor/calibracao.md` | reduz a uma tabela + P95 |
| **F6** Entrega | dom 09–12h | README final (tabela "Regras" com o porquê numérico), ADRs de `proposta` para `aceita`, slide "roadmap ML/GNN/LLM", ensaio dos 7 minutos | `README.md`, `docs/` | não |

## Paralelismo

| Pessoa | Sábado | Madrugada |
|---|---|---|
| **A** (caminho crítico) | F0 → F1 | metade de F2 |
| **B** | testes vermelhos de F2 e esqueleto do simulador (F5), escritos contra o contrato | metade de F2, depois F5 |
| **C** | `src/utils/statistics.py` + testes (F3) e docs | F3 → F4 |

## Regras de execução

- TDD por regra ([skill nova-regra](../.agents/skills/nova-regra/SKILL.md)), mais os 3 testes de cenário da pesquisa: pagador normal → `approved`; mula → `rejected`; conta tomada → `rejected` ou 2FA.
- Regra pura; o relógio é o `transaction_date`; parâmetros `RULE_*` em `src/constants.py` ([ADRs 0005](02-arquitetura/decisoes/0005-regras-puras-com-contexto-carregado.md), [0007](02-arquitetura/decisoes/0007-relogio-da-transacao.md), [0008](02-arquitetura/decisoes/0008-parametros-de-regra-por-ambiente.md)).
- Cada fase termina com `make reset check` verde, uma linha no [CHANGELOG](../CHANGELOG.md) e commit atômico.

## Riscos

| Risco | Mitigação |
|---|---|
| Histórico vazio na banca: regras de perfil e estatísticas ficam mudas no 1º Pix | M0 (payload puro: idade de conta, limites) vem antes de tudo |
| Banca manda Pix fora de ordem cronológica | As janelas usam `transaction_date` ([ADR 0007](02-arquitetura/decisoes/0007-relogio-da-transacao.md)), então funciona; documentar |
| Calibração com dado sintético é circular | Dizer isso explicitamente na apresentação, como a própria pesquisa alerta |
| F0/F1 atrasam e travam o resto | B e C trabalham contra o contrato ([rotas](03-api/rotas.md)) desde o início, sem depender do código de A |

## Próxima etapa (depende de autorização)

Documentar em nível de decisão:

- ADRs novas:
  - 0016: sinais estatísticos como regras (z robusto, Poisson–Gamma), sem ML;
  - 0017: ML, GNN e LLM fora do hot path e do prazo (roadmap);
  - 0018: regras compostas por tipologia;
  - 0019: reputação de contraparte derivada;
  - 0020: simulador para calibração;
  - 0021: o que cada janela conta (N5) + `rule_set_version`.
- Atualizar [regras.md](05-motor/regras.md), [motor-de-regras.md](05-motor/motor-de-regras.md), [decisao.md](05-motor/decisao.md), [modelo.md](04-dados/modelo.md) (coluna `rule_set_version`), o índice de ADRs, o `llms.txt` e o CHANGELOG.
