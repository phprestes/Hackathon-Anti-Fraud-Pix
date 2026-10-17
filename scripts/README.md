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
