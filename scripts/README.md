# scripts

Uma pasta por finalidade: `fixture/` (simulador do CI, replay, relatório), `backtest/` (backtest, `InMemoryHistory`, paridade, custo),
`calibration/` (grid, trava do CI, ablação), `pixsim/`, `models/` (features, treino, paridade dos modelos), `feedback/` e `analysis/`.
Cada script importa `_paths.py`, que põe `src/` e todas as pastas no `sys.path`; a saída fica em `scripts/out/`.
Mapa completo em [camadas](../docs/02-arquitetura/camadas.md#onde-fica-o-quê).

`fixture/simulate.py`: Fixture do CI, **sem valor estatístico** (ADR 0020, substituída em parte pela ADR 0029). Pagadores legítimos mais fraudes injetadas
(roubo_de_conta, mula, fracionamento, sequestro_relampago, fazenda_de_dispositivos), enviados para `POST /pix/transaction`. Ele alimenta o `make parity`
e a trava de regressão `make calibrate-check`; a calibração e cada métrica reportada vêm do PixSim.

```
.venv/bin/python scripts/fixture/simulate.py --dry-run          # sem HTTP, apenas estatísticas do payload
.venv/bin/python scripts/fixture/simulate.py --out result.md    # execução real contra a API
```

Opções: `--base-url` (padrão `http://localhost:$API_PORT`), `--token` (padrão `$INTERNAL_TOKEN`),
`--seed` (42), `--payers` (200), `--days` (14). As classificações (labels) de fraude vivem apenas no simulador.
As fraudes são nossas, então qualquer número derivado dele é circular.

## Backtest sem HTTP e sem banco

```
make events      # scripts/out/events.jsonl (seed 42, 60 pagadores, 7 dias)
make backtest    # motor de src/ sobre o arquivo, com InMemoryHistory
make parity      # reset + API x backtest, Pix a Pix (status, regras, features)
.venv/bin/python scripts/fixture/simulate.py --generate-only --events e.jsonl   # só gera
.venv/bin/python scripts/fixture/replay.py e.jsonl --responses r.jsonl          # manda pela API
.venv/bin/python scripts/backtest/backtest.py e.jsonl --set RULE_POISSON_TAIL_PPM=100 --json m.json
```

`--set` só sobrescreve parâmetros das regras; as janelas do contexto (`engine.build_context`) continuam vindo de `constants.py`.

## Ablação por regra (PixSim)

```
make rule-ablation    # scripts/calibration/rule_ablation.py run + render: uma passada por regra e por valor de parâmetro, mundo B
.venv/bin/python scripts/backtest/backtest.py e.jsonl --disable RULE_A,RULE_B   # liga o motor sem as regras citadas
```

`rule_ablation.py` guarda cada passada em `scripts/out/pixsim/ablation.json` (retoma de onde parou) e recalcula o custo a partir de
`scripts/backtest/cost-model.json` na hora de gerar a seção "Contribuição de cada regra" de `docs/05-motor/validacao-pixsim.md`.