"""Gera um mundo PixSim de escala reduzida em Parquet. Roda com o Python do venv do PixSim (python -I)."""
import argparse
import pathlib
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
PIXSIM = HERE / "out" / "pixsim" / "src"
sys.path.insert(0, str(PIXSIM))

import pandas as pd  # noqa: E402
from pixsim import load_config  # noqa: E402
from pixsim.experiment import burn_in_world, fraud_world  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--accounts", type=int, default=5000)
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--burn-in-days", type=int, default=30)
    parser.add_argument("--fraud-events-per-month", type=int, default=1000,
                        help="substitui fraud.target_accepted_per_month (2000 foi calibrado para 100 mil contas)")
    parser.add_argument("--seed", type=int, default=20260910)
    parser.add_argument("--out", default=str(HERE / "out" / "pixsim" / "data"))
    args = parser.parse_args()
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    started = time.time()
    cfg = load_config(PIXSIM / "configs" / "baseline.yaml", overrides={
        "seed": args.seed,
        "population": {"n_accounts": args.accounts},
        "simulation": {"days": args.days, "burn_in_days": args.burn_in_days},
        "fraud": {"target_accepted_per_month": args.fraud_events_per_month},
    })
    cfg2, pop, _, _, tx, frauds, _ = fraud_world(cfg, use_cache=False)
    burn = burn_in_world(cfg2, pop)

    tx = tx.drop(columns=["tx_id", "sender_balance_before"])
    tx["burn_in"] = False
    burn = burn.drop(columns=["tx_id", "sender_balance_before"])
    burn["burn_in"] = True
    for column in ("role", "hop_depth", "ring_id", "weight", "hop_delay_s"):
        burn[column] = {"role": "none", "hop_depth": -1, "ring_id": -1, "weight": 1.0}.get(column, float("nan"))
    all_tx = pd.concat([burn, tx], ignore_index=True)
    del burn, tx
    for column in ("channel", "device", "nature", "label", "role"):
        all_tx[column] = all_tx[column].astype(str)
    all_tx = all_tx.sort_values("t", kind="stable").reset_index(drop=True)
    all_tx["tx_id"] = range(len(all_tx))
    types = frauds.set_index("scenario_id")["type"]
    all_tx["fraud_type"] = all_tx["scenario_id"].map(types).fillna("legit")
    all_tx.to_parquet(out / "transactions.parquet", index=False)
    all_tx.to_csv(out / "transactions.csv", index=False)

    accounts = pop.accounts.drop(columns=["mule_recruit_day", "initial_balance", "expected_monthly_outflow"])
    accounts["opening_date"] = accounts["opening_date"].dt.strftime("%Y-%m-%d")
    accounts["start_date"] = pop.start_date.isoformat()
    accounts.to_parquet(out / "accounts.parquet", index=False)
    frauds.to_parquet(out / "frauds.parquet", index=False)
    # O .venv do projeto nao tem pyarrow: o adaptador le CSV em streaming.
    accounts.to_csv(out / "accounts.csv", index=False)
    frauds.to_csv(out / "frauds.csv", index=False)

    print(f"accounts={len(accounts)} tx={len(all_tx)} burn_in={int(all_tx['burn_in'].sum())} "
          f"fraud_events={len(frauds)} fraud_tx={int((all_tx['label'] == 'fraud').sum())} "
          f"elapsed={time.time() - started:.0f}s")
    print(frauds["type"].value_counts().to_string())
    print(all_tx.loc[all_tx["label"] == "fraud", "role"].value_counts().to_string())


if __name__ == "__main__":
    main()
