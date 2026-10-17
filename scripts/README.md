# scripts

`simulate.py`: calibration traffic simulator (ADR 0020). Legitimate payers plus injected frauds
(account_takeover, mule, splitting, night_kidnapping, device_farm), sent to `POST /pix/transaction`.

```
.venv/bin/python scripts/simulate.py --dry-run          # no HTTP, payload stats only
.venv/bin/python scripts/simulate.py --out result.md    # real run against the API
```

Options: `--base-url` (default `http://localhost:$API_PORT`), `--token` (default `$INTERNAL_TOKEN`),
`--seed` (42), `--payers` (200), `--days` (14). Fraud labels live only in the simulator.
Calibration is circular: the frauds are ours.

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
