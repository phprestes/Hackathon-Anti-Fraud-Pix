---
title: "ADR 0027: Pipeline de calibração automático e CI com trava de regressão"
summary: make calibrate varre parâmetros sobre o backtest em lote; make calibrate-check falha se a fricção ou a captura piorarem; o GitHub Actions roda make all, make parity e make calibrate-check em todo push.
related: [0020-simulador-para-calibracao.md, 0023-motor-extraido-e-history-port.md, ../../05-motor/calibracao.md]
sources: [Plano de implementação 2 (G3), scripts/calibrate.py, .github/workflows/ci.yml]
---

# ADR 0027: Pipeline de calibração automático e CI com trava de regressão

> [Índice](../../README.md) › [Decisões](README.md) › 0027

**Status:** aceita

## Contexto

A primeira calibração foi manual: editar `src/constants.py`, `make reset`, simular por 3 minutos, anotar. Com várias pessoas e agentes mudando regras ao mesmo tempo, uma regra nova pode aumentar a fricção sem que ninguém perceba.

## Decisão

- **`make calibrate`**: `scripts/calibration-grid.json` lista os parâmetros e os valores. O script gera os eventos uma vez e roda o backtest em lote ([ADR 0023](0023-motor-extraido-e-history-port.md)) para cada combinação: 18 combinações em cerca de 12 s.
  - **Função objetivo** (lexicográfica): menos legítimos reprovados; mais sequências de fraude barradas; menos 2FA em legítimos; menos fraude aprovada.
  - **Saída:** tabela, vencedora e fronteira não dominada em `scripts/out/`. O script nunca altera `src/constants.py`: a escolha final é do time.
- **`make calibrate-check`**: roda o backtest com os padrões atuais e falha se passar de `scripts/calibration-gate.json` (legítimos reprovados ≤ 0,1%, 2FA ≤ 5%, 100% das sequências de fraude barradas). Leva cerca de 1 s.
- **CI** (`.github/workflows/ci.yml`), em push e pull request: `make all` (sobe do zero e roda os testes), `make parity` (API × backtest) e `make calibrate-check`. Leva cerca de 1m40s.

## Alternativas descartadas

- **Grid pela API.**
  - **Preço:** 3 minutos por combinação, quase 1 hora para o mesmo grid.
  - **Ganharia se** não houvesse backtest em lote.
- **Calibração que escreve os padrões sozinha.**
  - **Preço:** parâmetro mudando sem porquê registrado; a [ADR 0008](0008-parametros-de-regra-por-ambiente.md) pede que cada valor tenha justificativa.
  - **Ganharia se** houvesse dado real e monitoramento em produção.

## Consequências

- Mudar regra ou parâmetro que piore a fricção quebra o build.
- O grid só varia parâmetros de regra. As janelas do contexto (10 min, 24 h, 30 dias) vêm de `constants.py` no `build_context` e não entram no `--set`.
