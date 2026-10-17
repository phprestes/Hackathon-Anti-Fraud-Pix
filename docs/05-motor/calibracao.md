---
title: Calibração
summary: Como os parâmetros das regras foram escolhidos com o simulador — metas, experimentos, configuração final, números e limites da evidência.
related: [regras.md, ../02-arquitetura/decisoes/0020-simulador-para-calibracao.md, ../../scripts/calibration-results.md]
sources: [scripts/simulate.py (seed 42), scripts/calibration-results.md]
---

# Calibração

> [Índice](../README.md) › Motor › Calibração
>
> **Responde a:** por que cada parâmetro tem o valor que tem? quanta fricção o motor gera? quanta fraude simulada ele barra? quanto isso vale como evidência?

## Como foi medido

[`scripts/simulate.py`](../../scripts/simulate.py) (seed 42) gera 200 pagadores por 14 dias: 5.062 Pix, sendo 4.926 legítimos e 136 de fraude em 22 sequências de 5 tipologias (conta tomada, mula, fracionamento, sequestro noturno, fazenda de contas). Tudo vai pelo `POST /pix/transaction` em ordem cronológica, e o simulador compara a decisão com o rótulo que só ele conhece ([ADR 0020](../02-arquitetura/decisoes/0020-simulador-para-calibracao.md)). A tabela completa dos experimentos está em [`scripts/calibration-results.md`](../../scripts/calibration-results.md).

**Metas, nesta ordem:**

1. Nenhum legítimo reprovado.
2. Toda sequência de fraude com pelo menos um Pix barrado.
3. 2FA em legítimos o mais baixo possível (meta ≤ 5%).

Os dados são sintéticos, então a busca parou na primeira configuração razoável, sem tuning fino.

## Experimentos

| # | Mudança | Legítimos: aprovado / 2FA / reprovado | Sequências barradas | Escape de fracionamento | P95 |
|---|---|---|---|---|---|
| 0 | Linha de base (`2026.10.17-f4`) | 90,4% / 8,3% / **1,3%** (66 por `TYPOLOGY_SPLITTING`) | 22/22 | 21% | 52 ms |
| 1 | `TYPOLOGY_SPLITTING` passa a contar só destinos **novos** | 89,8% / 10,0% / 0,2% | 22/22 | 21% | 57 ms |
| 2 | Teto diário R$ 10 mil → R$ 30 mil | 94,3% / 5,7% / 0,0% | 22/22 | 32% | 57 ms |
| 3 | Corte da Poisson 1.000 → 100 ppm | 96,2% / 3,8% / 0,0% | 22/22 | 40% | 56 ms |
| 4 | Fracionamento com corte próprio de R$ 5 mil (desacoplado do teto diário) | 95,7% / 3,8% / 0,5% | 22/22 | 32% | 55 ms |
| **5** | **Corte do fracionamento R$ 15 mil** | **≈ 96% / 3,8% / 0,04%** (2 Pix) | **22/22** | 34% | 55 ms |

Alternativas medidas e descartadas:

- Poisson a 10 ppm: 3,0% de 2FA, mas 58% de escape no fracionamento.
- Fracionamento com corte de R$ 10 mil: 0,2% de legítimos reprovados.
- Mínimo de 5 destinos novos: 0,3% de legítimos reprovados.

## Configuração final (`2026.10.18-calib3`)

| Parâmetro | Antes | Depois | Por quê |
|---|---|---|---|
| `RULE_AMOUNT_DAILY_SUM_CENTS` | R$ 10.000 | **R$ 30.000** | Respondia por 266 dos 347 casos de 2FA em legítimos: pagador intenso passa de R$ 10 mil por dia sem ser fraude. Acima de R$ 30 mil o 2FA quase só aparece em fraude |
| `RULE_POISSON_TAIL_PPM` | 1.000 | **100** | A 0,001 a regra pedia 2FA a 143 legítimos; a 0,0001 sobram 47, e todas as rajadas simuladas continuam improváveis o bastante para disparar |
| `RULE_SPLITTING_MIN_SUM_CENTS` | (usava o teto diário) | **R$ 15.000** | Desacoplar a tipologia do teto diário mantém o fracionamento visível mesmo com o teto em R$ 30 mil; R$ 15 mil é o menor corte com reprovação de legítimos ≈ 0 |

## O que os números dizem e o que não dizem

**Medem bem:**
- **Fricção:** cerca de 4% dos Pix legítimos pedem 2FA e praticamente nenhum é reprovado.
- **Latência:** P95 de 55 ms com as 17 regras e cerca de 15 consultas por Pix.
- **Coerência:** cada regra dispara onde o catálogo diz.

**Não medem:** eficácia contra fraude real. As fraudes foram desenhadas por nós e as regras procuram exatamente esses padrões, então a calibração é **circular**. Ainda escapam 34% dos Pix de fracionamento e 24% dos de fazenda de contas, mas em toda sequência pelo menos um Pix é barrado. Medir a eficácia exigiria backtest com rótulos reais (MED, contestações); o caminho está na [ADR 0017](../02-arquitetura/decisoes/0017-ml-fora-do-prazo-e-do-hot-path.md).

## Como recalibrar

1. `make reset && make simulate` para ter a linha de base.
2. Mudar um padrão em `src/constants.py` (ou exportar a variável `RULE_*` no ambiente da `api`).
3. `make reset && make simulate` de novo; comparar.
4. Ficou melhor: atualizar `RULE_SET_VERSION`, esta página, o [catálogo](regras.md), o README e o CHANGELOG.
