---
title: Validação externa no PixSim
summary: O motor de regras e os modelos em shadow rodados sobre o PixSim, um simulador de Pix de terceiros, em escala reduzida; mostra o que se mantém e o que cai fora do nosso gerador.
related: [calibracao.md, analises.md, regras.md, ../plano-de-implementacao-3.md, ../../scripts/pixsim_export.py, ../../scripts/pixsim_adapter.py, ../../scripts/pixsim_report.py]
sources: [github.com/BashirZeimarani/pixsim_public (SHA 7fdfc90013960f46df60c3ea01838e768e7a420a), scripts/pixsim_export.py, scripts/pixsim_adapter.py, scripts/pixsim_report.py, scripts/backtest.py, scripts/costs.py, scripts/analyze.py]
---

# Validação externa no PixSim

> [Índice](../README.md) › Motor › Validação no PixSim
>
> **Responde a:** o motor, calibrado só com o nosso simulador, continua útil em fraudes que nós não desenhamos? quais regras se mantêm e quais caem? os modelos treinados no nosso gerador generalizam? quão diferentes são as distribuições das features?

**Aviso: continua sendo dado sintético.** O PixSim não é Pix real; ele é de terceiros, com tipologias que não desenhamos. É a validação externa possível no prazo, não uma medida de desempenho em produção.

Regerar: `make pixsim` (clone, venv e mundo reduzido) e `make validate-pixsim` (adaptador, backtest e as tabelas abaixo). A paridade com a API roda em `make pixsim-parity`.

## O que é o PixSim

Zeimarani, B.; Khatib, A.; Mousavinasr, S.; Figueiredo, C. M. S. (2026). *PixSim: a calibrated open-source simulator of instant-payment fraud, recovery and interdiction under analyst capacity constraints*. Repositório [BashirZeimarani/pixsim_public](https://github.com/BashirZeimarani/pixsim_public), licença Apache-2.0, usado no commit `7fdfc90013960f46df60c3ea01838e768e7a420a`. Calibrado com dados abertos do Banco Central, gera contas (PF e PJ, região, faixa etária, idade da conta), tráfego legítimo (Poisson não homogêneo por conta), quatro tipologias de fraude do lado do pagador (engenharia social, conta tomada, Pix errado e QR adulterado) e cadeias de dispersão por mulas até contas de saída, com atraso de reporte ao MED. A parte de política de analistas, bloqueios e recuperação pelo MED do artigo **não** foi usada: só a geração de transações.

**Código de terceiro, tratado como não confiável.** Antes de executar li `README.md`, `environment.yml`, `requirements.txt`, `pixsim/__init__.py` e os módulos chamados (`config.py`, `experiment.py`, `runner.py`, `population.py`, `traffic.py`, `fraud.py`), mais `scripts/demo.py` e `configs/baseline.yaml`. Não rodei os testes, os notebooks nem scripts de instalação dele. As dependências pinadas do `requirements.txt` dele foram instaladas com `uv` num venv próprio (`scripts/out/pixsim/.venv`, Python 3.13.5; o artigo usou 3.13.13), nunca no `.venv` do projeto, sem privilégio. O código gerador roda com `python -I` e `ulimit -v`. Tudo fica em `scripts/out/pixsim/`, fora do Git.

## Escala usada e por que é reduzida

| Item | Valor |
|---|---|
| Contas | 5.025 (5.000 mais 25 contas de saída do PixSim) |
| Janela avaliada | 30 dias (seed 20260910) |
| Burn-in | 30 dias antes do dia 0, 122.967 Pix legítimos, enviados ao motor como histórico (`burn_in: true`) e excluídos das métricas |
| Pix totais | 254.795 (125.518 legítimos avaliados) |
| Eventos de fraude | 986: 618 engenharia social, 209 conta tomada, 91 Pix errado, 68 QR adulterado |
| Pix de fraude | 6.310: 1.380 pagador→mula, 91 sementes de Pix errado, 1.771 `mule_forward`, 3.068 `cash_out` |

O artigo roda 1,08 milhão de contas (19 GB por parte); a máquina de desenvolvimento tem cerca de 2 GB livres e o backtest guarda os eventos em memória (pico de 2,1 GB no `scripts/backtest.py` com este mundo). Duas escolhas fora do `baseline.yaml` do PixSim: burn-in de 30 dias (o config traz 90; 30 dias cobre a maior janela do motor) e 1.000 eventos de fraude por mês no lugar dos 2.000, que foram calibrados para 100 mil contas. A fraude é superamostrada de propósito, e cada Pix de fraude carrega o peso de importância do PixSim (0,0071 aqui); os custos "ponderados" abaixo usam esse peso.

## O que foi mapeado, inventado e não existe

| Campo do contrato | Origem |
|---|---|
| `amount` | Valor em R$ do PixSim para centavos inteiros, arredondamento meio para cima (`Decimal`); mínimo 1 centavo |
| `transaction_date` | Início fixo 2026-09-01T00:00-03:00 mais `t` (segundos do PixSim); o burn-in tem `t` negativo |
| `source_account` e `destination_account` | **Inventados**: agência, conta e ISPB determinísticos a partir do `account_id`; `opening_date` é a do PixSim deslocada para a mesma origem de tempo, preservando a idade da conta |
| `owner.document_number` | **Inventado**: CPF (PF) ou CNPJ (PJ) sintético com dígitos verificadores válidos, derivado do `account_id` por um mapa bijetor (sem colisão, sem documento real) |
| `source.device_id` | O dispositivo do PixSim |
| `source.channel` | `mobile`→`app`, `internet`→`internet_banking`; nas saídas da dispersão, `crypto_exit`, `cash_withdrawal`, `merchant_purchase` |
| `source.ip` | **Inventado**: derivado do hash do dispositivo, faixa 198.18.0.0/15 |
| `source.geolocation` | **Não existe** no PixSim: o campo (opcional) fica ausente, então as regras e features de geolocalização ficam inertes |

Extras no `events.jsonl` (não vão ao motor): `typology` (tipo de fraude do PixSim ou `legit`), `role` (`none`, `victim_to_mule`, `fraudster_seed`, `mule_forward`, `cash_out`), `burn_in`, `weight`, `ring_id`, `report_delay_days` e `reported` (atraso de reporte ao MED do evento). Os 254.795 payloads passam no JSON Schema do enunciado: **0 inválidos**.

**Perspectiva.** O motor vê todos os Pix, mas a leitura é a da instituição pagadora. "Pagador→mula" (`victim_to_mule`) é a fraude contra o nosso cliente e é o que o motor deve barrar. A dispersão (`mule_forward`, `cash_out`) e a semente do Pix errado só chegariam ao motor se a mula fosse cliente do mesmo banco; por isso entram numa visão separada e não somam na captura principal.

<!-- pixsim:tables:start -->

### Tamanho avaliado

| Conjunto | Pix totais | Burn-in (histórico) | Legítimos avaliados | Fraude pagador→mula | Fraude dispersão |
|---|---|---|---|---|---|
| PixSim | 254795 | 122967 | 125518 | 1380 | 4930 |
| Nosso simulador (seed 42) | 7995 | 0 | 7794 | 201 | n/a |

### Fricção em legítimos

| Conjunto | Legítimos | approved | 2FA | rejected |
|---|---|---|---|---|
| PixSim | 125518 | 96,49% | 3,50% | 0,01% |
| Nosso simulador | 7794 | 96,55% | 3,45% | 0,00% |

### Captura por tipologia do PixSim

Pagador→mula é o Pix que a vítima faz (a fraude contra o nosso cliente). `fraudster_seed` é o Pix semente do golpe do Pix errado, enviado pelo fraudador à vítima. Dispersão (`mule_forward`, `cash_out`) é a mula movendo o dinheiro: o nosso motor só a veria se a mula fosse cliente do mesmo banco.

| Tipologia | Papel | Pix | approved (escapou) | 2FA | rejected |
|---|---|---|---|---|---|
| account_takeover | cash_out | 663 | 69,68% | 30,32% | 0,00% |
| account_takeover | mule_forward | 440 | 72,95% | 27,05% | 0,00% |
| account_takeover | victim_to_mule | 323 | 33,44% | 62,23% | 4,33% |
| pix_errado | cash_out | 215 | 78,14% | 21,86% | 0,00% |
| pix_errado | fraudster_seed | 91 | 95,60% | 4,40% | 0,00% |
| pix_errado | mule_forward | 118 | 83,90% | 16,10% | 0,00% |
| pix_errado | victim_to_mule | 91 | 95,60% | 4,40% | 0,00% |
| qr_substitution | cash_out | 152 | 80,92% | 19,08% | 0,00% |
| qr_substitution | mule_forward | 88 | 86,36% | 13,64% | 0,00% |
| qr_substitution | victim_to_mule | 68 | 88,24% | 11,76% | 0,00% |
| social_engineering | cash_out | 2038 | 68,60% | 30,77% | 0,64% |
| social_engineering | mule_forward | 1125 | 73,69% | 25,51% | 0,80% |
| social_engineering | victim_to_mule | 898 | 69,82% | 30,18% | 0,00% |

### Sequências e anéis

| Tipologia (eventos de fraude) | Eventos com ao menos um Pix de vítima barrado | Taxa |
|---|---|---|
| account_takeover | 176/209 | 84,2% |
| pix_errado | 4/91 | 4,4% |
| qr_substitution | 8/68 | 11,8% |
| social_engineering | 195/618 | 31,6% |

- Eventos com ao menos um Pix barrado em qualquer papel (vítima ou dispersão): 655/986 (66,4%).
- Anéis de mulas com ao menos um Pix barrado (qualquer papel): 75/75 (100,0%).

- Atraso de reporte ao MED nos eventos: mediana 2,06 dia(s), p90 19,8 dias; 98,2% reportados dentro da janela de contestação.

### Custo esperado (V1)

Modelo de [`scripts/cost-model.json`](../../scripts/cost-model.json). "Bruto" usa a fração de fraude da amostra; "ponderado" multiplica a fraude pelo peso de importância do PixSim (a amostra tem fraude superamostrada), aproximando a taxa real.

| Visão | Bruto por 1.000 Pix | Ponderado por 1.000 Pix | Parte fraude (pond.) | Parte fricção (pond.) |
|---|---|---|---|---|
| PixSim, visão pagador (legítimo + pagador→mula) | R$ 9.480,71 | R$ 143,58 | R$ 67,69 | R$ 75,88 |
| PixSim, visão dispersão (legítimo + dispersão) | R$ 21.930,78 | R$ 237,54 | R$ 161,67 | R$ 75,87 |
| Nosso simulador | R$ 3.299,23 | R$ 3.299,23 | R$ 3.231,94 | R$ 67,29 |

Peso médio de importância da fraude no PixSim: 0,0071 (um evento de fraude vale 0,0071 de um real).

### P@k diário (V1)

Média diária da precisão nos k Pix mais bem ranqueados (fraude superamostrada: a precisão é inflada na mesma proporção do peso).

| Conjunto, ranking | P@5 | P@10 | P@25 | P@50 |
|---|---|---|---|---|
| PixSim, visão pagador, regras | 10,7% | 8,7% | 16,9% | 17,9% |
| PixSim, visão pagador, regras + LightGBM | 24,7% | 15,0% | 6,3% | 3,2% |
| PixSim, visão dispersão, regras | 16,8% | 15,8% | 23,7% | 28,0% |
| PixSim, visão dispersão, regras + LightGBM | 36,8% | 25,5% | 16,9% | 12,1% |
| Nosso simulador, regras | 71,4% | 63,6% | 43,7% | 26,6% |
| Nosso simulador, regras + LightGBM | 85,7% | 81,4% | 53,4% | 28,6% |

### Regras que disparam

Parcela de cada grupo em que a regra disparou (qualquer decisão).

| Regra | PixSim legítimo | PixSim pagador→mula | PixSim dispersão | Nosso legítimo | Nosso fraude |
|---|---|---|---|---|---|
| PROFILE_NEW_DEVICE | 0,0% | 12,2% | 0,0% | 0,6% | 12,9% |
| COUNTERPARTY_FIRST_TIME_HIGH | 0,4% | 11,4% | 3,7% | 0,8% | 3,0% |
| VELOCITY_POISSON_GAMMA | 0,3% | 9,5% | 14,8% | 0,4% | 17,4% |
| LIMIT_NIGHT_AMOUNT | 0,6% | 5,0% | 3,4% | 0,7% | 26,9% |
| PROFILE_AMOUNT_ROBUST_Z | 0,3% | 3,1% | 1,1% | 0,9% | 32,8% |
| COUNTERPARTY_FLAGGED | 0,6% | 1,7% | 7,1% | 0,0% | 34,8% |
| COUNTERPARTY_NEW_ACCOUNT | 1,2% | 0,0% | 1,0% | 0,0% | 52,2% |
| TYPOLOGY_ACCOUNT_TAKEOVER | 0,0% | 1,0% | 0,0% | 0,0% | 8,5% |
| AMOUNT_SOURCE_DAILY_SUM | 0,4% | 0,1% | 0,0% | 0,2% | 0,5% |
| LIMIT_SINGLE_AMOUNT | 0,0% | 0,1% | 0,0% | 0,0% | 0,0% |
| PROFILE_NEW_SOURCE_ACCOUNT | 0,0% | 0,1% | 0,0% | 0,0% | 0,0% |
| TYPOLOGY_SPLITTING | 0,0% | 0,0% | 0,4% | 0,0% | 0,0% |
| VELOCITY_DEVICE_SOURCES | 0,0% | 0,0% | 0,0% | 0,0% | 8,0% |
| PROFILE_GEO_VELOCITY | 0,0% | 0,0% | 0,0% | 0,0% | 1,0% |
| COUNTERPARTY_FAN_IN | 0,0% | 0,0% | 0,0% | 0,0% | 2,5% |
| VELOCITY_SOURCE_COUNT | 0,0% | 0,0% | 1,2% | 0,0% | 0,0% |
| TYPOLOGY_MULE | 0,0% | 0,0% | 0,0% | 0,0% | 24,4% |

### Modelos em shadow (treinados no nosso simulador)

AUC é pontuação do modelo na fraude contra o legítimo; recall e fricção usam o limiar do próprio modelo. No "Nosso simulador" os modelos foram treinados nesse mesmo gerador (seed 42): é desempenho dentro da distribuição.

| Modelo | PixSim AUC pagador | PixSim recall pagador | PixSim AUC dispersão | PixSim fricção legítimo | Nosso AUC | Nosso recall | Nossa fricção |
|---|---|---|---|---|---|---|---|
| MODEL_IFOREST | 0,797 | 37,0% | 0,500 | 8,0% | 0,892 | 22,9% | 1,0% |
| MODEL_LIGHTGBM | 0,707 | 27,8% | 0,663 | 7,0% | 1,000 | 99,0% | 0,0% |
| MODEL_LOGREG | 0,756 | 8,0% | 0,822 | 0,9% | 0,997 | 82,6% | 0,1% |
| regras (decisão como score) | 0,663 |  | 0,621 |  | 0,954 |  |  |

### PSI das features (nosso gerador × PixSim)

Base: nosso simulador (seed 42); comparado: PixSim. PSI acima de 0,25 é deriva forte, entre 0,1 e 0,25 atenção. Features constantes nos dois lados ficam de fora.

| Feature | PSI (todos os Pix) | PSI (Pix de fraude pagador→mula) |
|---|---|---|
| speed_kmh_since_last_geolocation | 8,282 | 8,198 |
| km_since_last_geolocation | 8,282 | 8,198 |
| hours_since_first_seen | 5,329 | 8,293 |
| history_30d_median_cents | 2,117 | 4,066 |
| source_history_size | 1,996 | 4,204 |
| history_30d_size | 1,350 | 3,079 |
| source_attempts_poisson_lookback | 1,348 | 3,265 |
| source_age_days | 0,871 | 0,808 |
| amount | 0,738 | 0,589 |
| log_amount | 0,738 | 0,589 |
| destination_distinct_other_sources_last_1h | 0,425 | 2,040 |
| destination_age_days | 0,377 | 4,393 |
| source_sum_last_24h_cents | 0,350 | 0,237 |
| poisson_tail_log10 | 0,279 | 0,203 |
| amount_robust_z | 0,239 | 2,920 |

### Latência do backtest

- `scripts/backtest.py`: 254795 Pix em 98,6 s (2585 Pix/s).
- Avaliação em streaming deste relatório (motor + histórico em memória, sem HTTP): 254795 Pix, 2759 Pix/s; por Pix P50 0,32 ms, P95 0,61 ms, P99 0,86 ms.

<!-- pixsim:tables:end -->

## O que se mantém e o que cai

- **Se mantém.** Fricção em legítimos: 3,5% de 2FA e 0,01% de reprovação no PixSim, contra 3,5% e 0% no nosso gerador. As regras de perfil e de contraparte continuam raras em legítimos (cada uma abaixo de 1,3%). Conta tomada continua sendo a tipologia mais barrada: 66,6% dos Pix de vítima viram 2FA ou reprovação e 84% dos eventos têm ao menos um Pix barrado. No conjunto das vítimas, as regras que mais disparam são `PROFILE_NEW_DEVICE` (12,2%), `COUNTERPARTY_FIRST_TIME_HIGH` (11,4%) e a Poisson–Gamma (9,5%).
- **Cai.** A captura global de Pix de vítima fica em cerca de 36% (nosso gerador: perto de 92%), e só 1,7% do valor das vítimas é reprovado (nosso gerador: 50%); 41,9% do valor da vítima passa aprovado. `COUNTERPARTY_NEW_ACCOUNT`, a regra que mais pega no nosso gerador (52% da fraude), praticamente não dispara em Pix de vítima no PixSim (0,0%): as mulas do PixSim são contas com idade comum, não contas recém-abertas. `TYPOLOGY_MULE` e `COUNTERPARTY_FAN_IN` também ficam em zero, provavelmente porque as vítimas do PixSim chegam à mesma mula espalhadas no tempo, e não em rajada como no nosso gerador (hipótese: não medi a distribuição temporal). Pix errado (4,4% dos eventos) e QR adulterado (11,8%) escapam quase todos: o Pix da vítima parece um pagamento comum (hipótese; não separei por valor).
- **Engenharia social** (63% dos eventos) é barrada em 30% dos Pix e em 31,6% dos eventos: o golpe é a própria vítima pagando, com valores dentro do perfil dela.
- **Anéis.** Todos os 75 anéis de mulas têm ao menos um Pix barrado em algum papel (vítima ou dispersão); a parte da dispersão só ajuda se a mula for cliente do banco.

## Modelos em shadow: teste fora da distribuição

Os três modelos (regressão logística, LightGBM, Isolation Forest) foram treinados no nosso simulador. No PixSim o AUC contra legítimos cai de 1,000 para 0,707 (LightGBM), de 0,997 para 0,756 (logística) e de 0,892 para 0,797 (Isolation Forest); o recall no limiar do próprio modelo cai de 99% para 28% no LightGBM, com 7% de fricção em legítimos. Isso é esperado de um modelo que aprendeu os sinais do nosso gerador (conta destino nova, geolocalização) e não os do PixSim. O resumo do artigo cita um *synthetic scorer* de 0,82 AUC; a referência vale só como ordem de grandeza, sem equivalência: aquele scorer foi treinado e testado dentro do próprio PixSim, com outras features. O AUC por decisão das regras (0,663) fica abaixo do melhor modelo isolado (Isolation Forest, 0,797), o que sugere ganho de ordenação no PixSim com um modelo treinado nele.

## Deriva das features

O PSI usa o nosso gerador (seed 42, 14 dias) como base. Boa parte do desvio é artefato de construção, não de realismo: as features de geolocalização (`km_since_last_geolocation`, `speed_kmh_since_last_geolocation`, PSI 8,3) mudam porque o PixSim não tem geolocalização, e as de histórico (`source_history_size`, `history_30d_*`, `hours_since_first_seen`) mudam porque o PixSim tem 30 dias de burn-in e 30 de janela contra 14 dias no nosso. O que sobra de informação real: `amount` e `log_amount` (PSI 0,74), `source_age_days` (0,87) e, na fraude, `destination_age_days` (4,39, coerente com o `COUNTERPARTY_NEW_ACCOUNT` zerado: no nosso gerador o destino da fraude é conta nova, no PixSim não).

## Conclusão

O motor sobrevive à troca de gerador no que mede pouco e é barato: fricção em legítimos igual (3,5% de 2FA, quase nada de reprovação) e boa captura de conta tomada (84% dos eventos). Fora disso a captura de golpes em que a própria vítima paga (engenharia social, Pix errado, QR adulterado) é baixa, e 42% do valor das vítimas passa aprovado. As regras mais fortes no nosso gerador (conta destino nova, rajada de vítimas para a mesma mula) dependem de como nós desenhamos a mula; o PixSim a desenha diferente e essas regras caem a zero. Os modelos em shadow perdem a maior parte do poder fora da distribuição. Isso reforça que a calibração anterior era circular e que os números do nosso simulador não devem ser lidos como desempenho esperado. Recalibrar com base no PixSim seria outro tipo de circularidade (ajustar ao gerador de outra pessoa), então este documento não muda nenhum parâmetro.

## Limitações

- Escala reduzida (5.025 contas, 30 dias) e uma única seed; não há intervalo de confiança.
- Fraude superamostrada. Pesos de importância corrigem o custo, mas não o P@k, que é inflado.
- Documento, IP, agência e conta são sintéticos; sem geolocalização, regras e features geográficas não são exercitadas.
- O motor só recebe o lado do banco pagador; a dispersão foi tratada à parte porque exige a mula ser cliente.
- O PixSim também é um simulador: as tipologias refletem as hipóteses dos autores, calibradas com dados agregados do Banco Central, e não casos reais.
- O worker (graph risk, GraphSAGE, HMM) não rodou: as features dele ficam em -1, como no backtest padrão.
- Paridade API × backtest verificada em 500 Pix (cerca de 40 de fraude, janela na virada do burn-in): **0 divergências**. Fora dessa amostra, o backtest em memória não foi comparado com a API.
