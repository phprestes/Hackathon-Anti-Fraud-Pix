# scripts

`simulate.py`: CI fixture, **no statistical value** (ADR 0020, superseded in part by ADR 0029). Legitimate payers plus injected frauds
(account_takeover, mule, splitting, night_kidnapping, device_farm), sent to `POST /pix/transaction`. It feeds `make parity`
and the regression gate `make calibrate-check`; calibration and every reported metric come from PixSim.

```
.venv/bin/python scripts/simulate.py --dry-run          # no HTTP, payload stats only
.venv/bin/python scripts/simulate.py --out result.md    # real run against the API
```

Options: `--base-url` (default `http://localhost:$API_PORT`), `--token` (default `$INTERNAL_TOKEN`),
`--seed` (42), `--payers` (200), `--days` (14). Fraud labels live only in the simulator.
The frauds are ours, so any number from it is circular.

## Backtest sem HTTP e sem banco

```
make events      # scripts/out/events.jsonl (seed 42, 60 pagadores, 7 dias)
make backtest    # motor de src/ sobre o arquivo, com InMemoryHistory
make parity      # reset + API x backtest, Pix a Pix (status, regras, features)
.venv/bin/python scripts/simulate.py --generate-only --events e.jsonl   # só gera
.venv/bin/python scripts/replay.py e.jsonl --responses r.jsonl          # manda pela API
.venv/bin/python scripts/backtest.py e.jsonl --set RULE_SPLITTING_MIN_COUNT=4 --json m.json
```

`--set` só sobrescreve parâmetros das regras; as janelas do contexto (`engine.build_context`) continuam vindo de `constants.py`.

## Ablação por regra (PixSim)

```
make rule-ablation    # scripts/rule_ablation.py run + render: uma passada por regra e por valor de parâmetro, mundo B
.venv/bin/python scripts/backtest.py e.jsonl --disable RULE_A,RULE_B   # liga o motor sem as regras citadas
```

`rule_ablation.py` guarda cada passada em `scripts/out/pixsim/ablation.json` (retoma de onde parou) e recalcula o custo a partir de
`scripts/cost-model.json` na hora de gerar a seção "Contribuição de cada regra" de `docs/05-motor/validacao-pixsim.md`.
