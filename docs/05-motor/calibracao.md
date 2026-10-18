---
title: Calibração
summary: Como os parâmetros das regras foram escolhidos no PixSim (custo ponderado, mundo A para escolher e mundo B para confirmar), a configuração final, o que ficou de fora de propósito e a trava de regressão do CI.
related: [regras.md, analises.md, validacao-pixsim.md, ../02-arquitetura/decisoes/0020-simulador-para-calibracao.md, regras.md]
sources: [scripts/calibration/calibrate.py, scripts/calibration/calibration-grid-pixsim.json, scripts/backtest/costs.py, scripts/backtest/cost-model.json, scripts/out/calibration-pixsim.md, scripts/calibration/calibration-gate.json]
---

# Calibração

> [Índice](../README.md) › Motor › Calibração
>
> **Responde a:** por que cada parâmetro tem o valor que tem? quanto custa, em fricção e em fraude barrada, mudar um parâmetro? quanto isso vale como evidência?

**Métricas no PixSim, simulador de terceiros.** O PixSim ([validação](validacao-pixsim.md)) não é Pix real, mas as tipologias e o tráfego não foram desenhados por nós. O nosso simulador (`scripts/fixture/simulate.py`) é só fixture de CI e não justifica nenhum parâmetro desta página.

Regerar: `make calibrate-pixsim` (cerca de 20 passadas de 1 min; o cache em `scripts/out/pixsim/calibration-cache.json` retoma uma execução interrompida).

## Como foi medido

- **Dados.** Mundo A (`scripts/out/pixsim/events.jsonl`, seed 20260910) para escolher; mundo B (`events-b.jsonl`, seed 20261017) para confirmar. Cada um tem 5.025 contas, 30 dias avaliados depois de 30 de burn-in, 125 mil Pix legítimos e 986 eventos de fraude.
- **Objetivo.** Menor custo esperado por 1.000 Pix na visão do pagador (legítimo mais fraude `victim_to_mule`), com o [modelo de custo](../../scripts/backtest/cost-model.json) e a fraude multiplicada pelo peso de importância do PixSim (0,0071), que desfaz a superamostragem. Empates: menos legítimos reprovados, depois mais sequências barradas. A dispersão (lado da mula) é reportada à parte e não entra no objetivo.
- **Grid.** Um parâmetro por vez a partir da linha de base (os padrões anteriores, fixados em `scripts/calibration/calibration-grid-pixsim.json`), mais a combinação dos melhores valores de cada parâmetro: 21 combinações no mundo A. O mundo B confirma a linha de base, a vencedora e as próximas colocadas.
- **Parâmetros varridos:** teto diário, cauda da Poisson, corte do fracionamento, z do perfil, valor mínimo de aparelho novo, valor mínimo de primeiro Pix para um destino e limite noturno. São os do grid antigo mais as regras que mais disparam no PixSim.

**Metas, nesta ordem:** (1) legítimos reprovados perto de zero; (2) custo mínimo; (3) 2FA em legítimos abaixo de 5% quando o custo empata.

## Experimentos no mundo A

Efeito de cada parâmetro sozinho sobre a linha de base (custo R$ 143,58 por 1.000 Pix; 3,50% de 2FA em legítimos; 36,1% dos Pix de vítima barrados; 383 de 986 eventos com algum Pix barrado):

**Duas bases para o mesmo eixo.** Esta tabela move um parâmetro por vez a partir dos valores de antes da calibração (por isso Poisson a 1.000 ppm custa R$ 166,48). A [análise de sensibilidade](analises.md) varre o mesmo eixo com os outros parâmetros já nos valores atuais, e lá 1.000 ppm custa R$ 134,12. Os dois números não se contradizem: a base é outra.

| Mudança | Custo R$/1.000 | 2FA legítimos | Pix de vítima barrados | Eventos barrados |
|---|---|---|---|---|
| `FIRST_TIME_MIN_AMOUNT_CENTS` R$ 3.000 → **R$ 1.000** | **135,72** | 4,16% | 52,2% | 577 |
| `LIMIT_NIGHT_AMOUNT_CENTS` R$ 1.000 → R$ 2.000 (não aplicado, ver abaixo) | 139,01 | 3,18% | 34,4% | 365 |
| `POISSON_TAIL_PPM` 100 → **30** | 142,30 | 3,30% | 33,3% | 368 |
| `PROFILE_Z_2FA_TENTHS` 35 → **45** | 142,33 | 3,35% | 35,2% | 376 |
| `NEW_DEVICE_MIN_AMOUNT_CENTS` R$ 500 → **R$ 200** | 142,91 | 3,50% | 38,8% | 413 |
| `AMOUNT_DAILY_SUM_CENTS` R$ 30.000 → **R$ 45.000** | 143,11 | 3,47% | 36,1% | 383 |
| `POISSON_TAIL_PPM` 100 → 1.000 | 166,48 | 5,03% | 42,0% | 426 |
| `SPLITTING_MIN_SUM_CENTS` R$ 15.000 → R$ 5.000 | 250,23 | 5,91% | 36,2% | 384 |
| `LIMIT_NIGHT_AMOUNT_CENTS` R$ 1.000 → R$ 500 | 152,77 | 4,10% | 40,9% | 434 |

Leituras: o valor mínimo do primeiro Pix para um destino é o parâmetro de maior efeito no custo; o corte do fracionamento a R$ 5 mil é o pior ponto do grid (reprova 0,13% dos legítimos); acima de R$ 45 mil o teto diário não muda nada (R$ 45 mil e R$ 60 mil empatam). A tabela completa, com a visão de dispersão, fica em `scripts/out/calibration-pixsim.md`.

## Configuração calibrada (`2026.10.18-pixsim`, ainda com 18 regras)

> O conjunto em vigor é `2026.10.18-pixsim-2`: os mesmos valores, menos as três regras descartadas e o `RULE_AMOUNT_DAILY_SUM_CENTS` ([seção abaixo](#depois-da-calibração-três-regras-descartadas)).

Cinco parâmetros mudam juntos. O ganho da combinação (R$ 11,92) é menor que a soma dos ganhos isolados (R$ 15,4): os efeitos se sobrepõem, porque os parâmetros barram em parte os mesmos Pix.

| Parâmetro | Antes | Depois | Por quê (PixSim) |
|---|---|---|---|
| `RULE_FIRST_TIME_MIN_AMOUNT_CENTS` | R$ 3.000 | **R$ 1.000** | Maior queda de custo isolada (143,58 → 135,72); o Pix de vítima para destino novo passa a ser barrado a partir de R$ 1.000 (Pix de vítima barrados: 36,1% → 52,2%). Custo: +0,66 p.p. de 2FA em legítimos |
| `RULE_NEW_DEVICE_MIN_AMOUNT_CENTS` | R$ 500 | **R$ 200** | Barra mais Pix de vítima (36,1% → 38,8%) sem mexer na fricção (3,50%) |
| `RULE_POISSON_TAIL_PPM` | 100 | **30** | Menos 2FA em legítimos (3,50% → 3,30%) por um escape pequeno; 1.000 ppm é o pior ponto do eixo (5,03% de 2FA, custo 166,48) |
| `RULE_PROFILE_Z_2FA_TENTHS` | 35 | **45** (z > 4,5) | Menos 2FA em legítimos (3,35%) com a captura praticamente igual (35,2%); z 2,5 custa 149,66 |
| `RULE_AMOUNT_DAILY_SUM_CENTS` | R$ 30.000 | **R$ 45.000** | Platô: R$ 45 mil e R$ 60 mil custam o mesmo; fica o menor valor do platô, a maior sensibilidade. O ganho isolado é pequeno (R$ 0,47) |

Resultado da combinação, linha de base → final:

| Mundo | Custo R$/1.000 Pix | 2FA em legítimos | Legítimos reprovados | Pix de vítima barrados | Eventos com Pix barrado | Custo da dispersão R$/1.000 |
|---|---|---|---|---|---|---|
| A (escolha) | 143,58 → **131,66** (−8,3%) | 3,50% → 3,81% | 0,01% → 0,01% | 36,1% → 51,7% | 383 → 591 de 986 | 237,54 → 229,18 |
| B (confirmação) | 157,60 → **149,24** (−5,3%) | 3,74% → 4,13% | 0,03% → 0,03% | 38,4% → 51,8% | 427 → 622 de 986 | 263,19 → 259,51 |

**Custo do falso bloqueio.** Os custos desta tabela foram medidos com R$ 50 fixos por legítimo reprovado. O modelo passou a usar R$ 50 + 2% do valor, como o PixSim (A3.5, ASSUMED): a configuração final fica em R$ 132,13 (A) e R$ 153,51 (B) por 1.000 Pix, uma soma constante de R$ 0,47 e R$ 4,27 sobre os valores acima. A configuração vencedora não muda: os mesmos 15 legítimos (A) e 36 (B) são reprovados em todas as combinações do grid, menos uma (162 reprovados em A, que só piora), então a parte proporcional soma o mesmo valor a todas e preserva a ordem. Nenhum parâmetro foi alterado.

A melhora aparece nos dois mundos, com 2FA em legítimos ainda abaixo de 5% e sem reprovar mais legítimos. O ganho em B é menor que em A (o grid foi escolhido em A); essa diferença é a melhor estimativa do quanto a escolha é específica de um mundo.

### Mantido de propósito: limite noturno

`RULE_LIMIT_NIGHT_AMOUNT_CENTS` fica em **R$ 1.000**, mantido por âncora regulatória (BCB), apesar de o grid preferir R$ 2.000. R$ 1.000 é o limite noturno padrão de pessoa física do Banco Central ([Res. BCB 142/2021, art. 2º, I](https://www.bcb.gov.br/estabilidadefinanceira/exibenormativo?tipo=Resolu%C3%A7%C3%A3o%20BCB&numero=142), hoje na IN BCB 512/2024, art. 3º, §7º, II; detalhes e fontes em [regras.md](regras.md)); subir o corte pararia de pedir 2FA abaixo do teto que o regulador associa ao risco de sequestro relâmpago. O custo medido dessa escolha no PixSim, com os outros cinco parâmetros já aplicados: R$ 131,66 contra R$ 127,07 no mundo A (+R$ 4,59 por 1.000 Pix) e R$ 149,24 contra R$ 144,44 no mundo B (+R$ 4,80). O parâmetro está fixado como `pinned` no grid: é medido, nunca escolhido.

### Não mudou

`RULE_SPLITTING_MIN_SUM_CENTS` (R$ 15.000): o único valor testado abaixo dele piorou o custo e a reprovação de legítimos. Os limites de PJ e os demais parâmetros não foram varridos; não há evidência para movê-los.

### Depois da calibração: três regras descartadas

Com os parâmetros acima, a ablação mostrou que `TYPOLOGY_SPLITTING`, `COUNTERPARTY_FLAGGED` e `AMOUNT_SOURCE_DAILY_SUM` custam mais do que evitam. Desligadas juntas (`RULE_SET_VERSION` `2026.10.18-pixsim-2`), o custo vai de R$ 132,13 para R$ 109,61 por 1.000 Pix no mundo A e de R$ 153,51 para R$ 118,82 no B, com o modelo de custo final ([ADR 0033](../02-arquitetura/decisoes/0033-regras-descartadas-pela-ablacao.md)). `RULE_AMOUNT_DAILY_SUM_CENTS` e `RULE_SPLITTING_MIN_SUM_CENTS` saíram do código e do grid; as tabelas acima ficam como registro do que foi medido.

## O que os números dizem e o que não dizem

**Medem bem:** o efeito relativo de cada parâmetro sobre fricção, captura e custo ponderado em dois mundos de uma população que não desenhamos.

**Não medem:**
- **Eficácia em produção.** O PixSim é sintético; os níveis absolutos de captura (≈ 52% dos Pix de vítima) não valem como previsão.
- **O custo absoluto.** Depende das premissas de [`cost-model.json`](../../scripts/backtest/cost-model.json) e do peso de importância; o que se compara é a diferença entre configurações.
- **Independência total.** Escolhi em A e confirmei em B, mas os dois mundos vêm do mesmo gerador; B não é dado novo no sentido de outra população.
- **Fraude de dispersão.** É reportada, não otimizada.

## Trava de regressão no CI

`make calibrate-check` roda o backtest com os padrões sobre o nosso simulador (seed 42, 200 pagadores, 14 dias) e compara com [`scripts/calibration/calibration-gate.json`](../../scripts/calibration/calibration-gate.json): legítimos reprovados ≤ 0,1%, 2FA em legítimos ≤ 7,0% e 100% das sequências com algum Pix barrado. É uma **trava contra regressão**, não a meta: o fixture não tem valor estatístico e não justifica parâmetro.

Com os parâmetros novos e as 18 regras a trava mediu 0,04% de reprovados, 6,59% de 2FA; com as 15 regras de hoje, 0% de reprovados e 6,6% de 2FA ([ADR 0033](../02-arquitetura/decisoes/0033-regras-descartadas-pela-ablacao.md)) (o primeiro Pix mais baixo para destino novo pede mais 2FA no fixture) e 100% das sequências. O teto de 2FA subiu de 5,0% para 7,0%, o valor medido com folga; os outros dois ficaram. Os experimentos antigos no fixture foram descartados: eram circulares (as fraudes são nossas) e não justificam nenhum parâmetro.

## Como recalibrar

1. `make calibrate-pixsim` (precisa dos mundos A e B; `make pixsim-datasets` gera).
2. Mudar os padrões escolhidos em `src/constants.py` (ou exportar `RULE_*` no ambiente da `api`), atualizar `RULE_SET_VERSION`.
3. `make reset check`, `make calibrate-check` e `make analyze`; se a trava falhar, ajustar o teto em `scripts/calibration/calibration-gate.json` para o valor medido e registrar aqui.
4. Atualizar esta página, o [catálogo](regras.md), o README e o CHANGELOG.
