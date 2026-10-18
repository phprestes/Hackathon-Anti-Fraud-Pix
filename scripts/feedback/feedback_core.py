"""MED feedback loop for the batch backtest only: outcome timeline, confirmed-fraud signal, weekly retrain."""
import heapq
import json
import os
import random
import sys
from array import array
from collections import defaultdict

import numpy as np
from sklearn.metrics import roc_auc_score


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import _paths  # noqa: E402

from costs import COMPONENTS, load_cost_model, reject_cost  # noqa: E402
from delayed_labels import known_labels  # noqa: E402
from in_memory_history import InMemoryHistory  # noqa: E402
from model_eval import View  # noqa: E402
from replay import iter_events  # noqa: E402
from rules import build_rules  # noqa: E402
from rules.core import engine  # noqa: E402
from rules.core.base_rule import BaseRule, RuleResult  # noqa: E402
from rules.core.decision import APPROVED, REJECTED, SEVERITY, TWO_FACTOR_REQUIRED  # noqa: E402
from rules.core.features import FEATURE_NAMES  # noqa: E402
from rules.models import gbdt  # noqa: E402
from rules.core.pix_snapshot import PixSnapshot  # noqa: E402
from train_models import train_lightgbm, VALIDATION_SHARE  # noqa: E402

DAY = 86400.0
WEEK = 7 * DAY
VICTIM_ROLES = ("none", "victim_to_mule")
MODEL_PATH = os.path.join(_paths.ROOT, "src", "rules", "models", "artifacts", "lightgbm.json")
MIN_POSITIVES = 20


class ConfirmedFraudBook:
    """Payers whose Pix to a destination was confirmed as fraud by the MED, per destination."""

    def __init__(self):
        self.payers = defaultdict(set)


class CounterpartyConfirmedFraudRule(BaseRule):
    code = "COUNTERPARTY_CONFIRMED_FRAUD"
    family = "counterparty"

    def __init__(self, book, decision):
        self.book = book
        self.decision = decision

    def evaluate(self, pix, context):
        payers = self.book.payers.get(pix.destination_document)
        if not payers or pix.is_self_transfer:
            return None
        others = len(payers - {pix.source_document})
        if not others:
            return None
        return RuleResult(self.code, self.decision,
                          "Destino recebeu Pix com fraude confirmada (MED) de outro pagador.",
                          {"confirmed_payers": others})


class Pool:
    """Victim-view rows of the replayed world, to retrain on outcomes as they mature."""

    def __init__(self):
        self.X, self.at = array("d"), array("d")
        self.known = array("b")

    def __len__(self):
        return len(self.at)

    def add(self, features, at):
        self.X.extend(features)
        self.at.append(at)
        self.known.append(0)


def cost_parts(model, is_fraud, status, amount, weight):
    parts = dict.fromkeys(COMPONENTS, 0.0)
    if not is_fraud:
        if status == TWO_FACTOR_REQUIRED:
            parts["legit_2fa"] = model["friction_cost_2fa_cents"]
        elif status == REJECTED:
            parts["legit_rejected"] = reject_cost(model, amount)
    elif status == APPROVED:
        parts["fraud_approved"] = weight * amount * model["fraud_loss_factor"]
    elif status == TWO_FACTOR_REQUIRED:
        parts["fraud_2fa_escape"] = weight * amount * model["two_factor_escape_rate"]
    return parts


class Arm:
    """Weighted cost of one decision policy over a stretch of victim-view Pix."""

    def __init__(self):
        self.parts = dict.fromkeys(COMPONENTS, 0.0)
        self.legit = 0
        self.fraud_weight = 0.0

    def add(self, model, is_fraud, status, amount, weight):
        for name, value in cost_parts(model, is_fraud, status, amount, weight).items():
            self.parts[name] += value
        if is_fraud:
            self.fraud_weight += weight
        else:
            self.legit += 1

    def per_1000(self):
        effective = self.legit + self.fraud_weight
        return sum(self.parts.values()) * 1000 / effective if effective else 0.0


def worse(status, flagged):
    return max(status, TWO_FACTOR_REQUIRED, key=SEVERITY.get) if flagged else status


def new_week(index, champion):
    return {"week": index, "champion": champion, "pix": 0, "legit": 0, "fraud": 0, "fraud_w": 0.0,
            "caught": 0, "caught_w": 0.0, "n2fa": 0, "tp2fa_w": 0.0, "fp2fa": 0, "nrej": 0, "tprej_w": 0.0,
            "fprej": 0, "no_outcome_w": 0.0, "escapes": 0, "escape_cents": 0, "confirmed_from_2fa": 0, "confirmed_from_2fa_w": 0.0,
            "confirmed_total": 0, "scores": array("d"), "labels": array("b")}


def seed_from_world(path_features):
    """Historical rows (world A) with the labels known at its own end, as the starting pool."""
    world = View(path_features, FEATURE_NAMES)
    labels = known_labels(world, float(world.at.max()))
    seed = (np.array(world.X), labels.astype(int))
    del world
    return seed


def train_challenger(pool, seed, now, maturity_days):
    """Fits LightGBM on seed + the pool rows whose label is positive or old enough to trust as negative."""
    at = np.frombuffer(pool.at, dtype=float)
    known = np.frombuffer(pool.known, dtype=np.int8)
    mask = (known == 1) | (at <= now - maturity_days * DAY)
    X_parts, y_parts = [], []
    if seed is not None:
        X_parts.append(seed[0])
        y_parts.append(seed[1])
    if len(pool):
        matrix = np.frombuffer(pool.X, dtype=float).reshape(-1, len(FEATURE_NAMES))
        X_parts.append(matrix[mask])
        y_parts.append(known[mask].astype(int))
    if not X_parts:
        return None, 0, 0
    X, y = np.vstack(X_parts), np.concatenate(y_parts)
    split = int(len(y) * (1 - VALIDATION_SHARE))
    if y[:split].sum() < MIN_POSITIVES or y[split:].sum() < 1:
        return None, len(y), int(y.sum())
    model, _, _ = train_lightgbm(X[:split], y[:split], X[split:], y[split:])
    return model, len(y), int(y.sum())


def simulate(events_path, cfg, seed=None):
    """Replays one world. cfg: signal (None|decision), use_model, retrain, maturity_days, rng_seed."""
    cost_model = load_cost_model()
    book = ConfirmedFraudBook()
    rules = [r for r in build_rules({}) if not r.shadow]
    if cfg.get("signal"):
        rules.append(CounterpartyConfirmedFraudRule(book, cfg["signal"]))
    with open(MODEL_PATH, encoding="utf-8") as handle:
        champion = json.load(handle)
    champion_name = "instalado (mundo A)"
    challenger, challenger_info = None, None
    history, pool = InMemoryHistory(), Pool()
    heap, counter = [], 0
    weeks, promotions = [], []
    t0, current = None, 0
    week = None
    chal_arm, champ_arm = Arm(), Arm()
    escape_rate = cost_model["two_factor_escape_rate"]

    def apply_due(now):
        while heap and heap[0][0] <= now:
            reported_at, _, row, payer, destination, amount, decided_as, weight = heapq.heappop(heap)
            book.payers[destination].add(payer)
            pool.known[row] = 1
            index = int((reported_at - t0) // WEEK) if t0 is not None else 0
            target = weeks_by_index(index)
            target["confirmed_total"] += 1
            if decided_as == APPROVED:
                target["escapes"] += 1
                target["escape_cents"] += amount
            else:
                target["confirmed_from_2fa"] += 1
                target["confirmed_from_2fa_w"] += weight

    arrivals = defaultdict(lambda: None)

    def weeks_by_index(index):
        if index == current and week is not None:
            return week
        if arrivals[index] is None:
            arrivals[index] = new_week(index, champion_name)
        return arrivals[index]

    def close_week(boundary, last=False):
        nonlocal champion, champion_name, challenger, challenger_info, chal_arm, champ_arm
        apply_due(boundary)
        labels = np.frombuffer(week["labels"], dtype=np.int8)
        scores = np.frombuffer(week["scores"], dtype=float)
        week["auc"] = float(roc_auc_score(labels, scores)) if 0 < labels.sum() < len(labels) else None
        week["cost"] = champ_arm.per_1000()
        week["parts"] = dict(champ_arm.parts)
        week["challenger_cost"] = chal_arm.per_1000() if challenger else None
        del week["scores"], week["labels"]
        if challenger is not None:
            promoted = chal_arm.per_1000() < champ_arm.per_1000()
            promotions.append({"week": week["week"], "champion_cost": champ_arm.per_1000(),
                               "challenger_cost": chal_arm.per_1000(), "promoted": promoted, **challenger_info})
            if promoted:
                champion, champion_name = challenger, f"desafiante da semana {challenger_info['trained_week']}"
            challenger = None
        if cfg.get("retrain") and not last:
            model, rows, positives = train_challenger(pool, seed, boundary, cfg["maturity_days"])
            if model is not None:
                challenger = model
                challenger_info = {"trained_week": week["week"] + 1, "rows": rows, "positives": positives}
            else:
                promotions.append({"week": week["week"], "skipped": True, "rows": rows, "positives": positives})
        champ_arm, chal_arm = Arm(), Arm()

    def flush_week():
        merged = arrivals.pop(week["week"], None)
        if merged is not None:
            for key in ("escapes", "escape_cents", "confirmed_from_2fa", "confirmed_from_2fa_w", "confirmed_total"):
                week[key] += merged[key]
        weeks.append(week)

    counts = defaultdict(int)
    for event in iter_events(events_path):
        payload = event["payload"]
        snapshot = PixSnapshot.from_payload(payload)
        now = snapshot.transaction_date.timestamp()
        burn_in = bool(event.get("burn_in"))
        if not burn_in and t0 is None:
            t0 = now
            week = new_week(0, champion_name)
        apply_due(now)
        if not burn_in:
            index = int((now - t0) // WEEK)
            while index > current:
                boundary = t0 + (current + 1) * WEEK
                close_week(boundary)
                flush_week()
                current += 1
                week = new_week(current, champion_name)
        outcome = engine.evaluate(snapshot, engine.build_context(snapshot, history), rules)
        status = outcome.status
        role = event.get("role")
        victim_view = not burn_in and role in VICTIM_ROLES
        if not victim_view:
            history.record(snapshot, status)
            continue
        is_fraud = role == "victim_to_mule"
        weight = event.get("weight", 1.0)
        score = gbdt.score(champion, outcome.features)
        flagged = score >= champion["threshold"]
        final = worse(status, flagged and cfg.get("use_model"))
        history.record(snapshot, final)
        amount = payload["amount"]
        features = [outcome.features[name] for name in FEATURE_NAMES]
        row = len(pool)
        pool.add(features, now)
        counts["pix"] += 1
        week["pix"] += 1
        week["scores"].append(score)
        week["labels"].append(int(is_fraud))
        champ_arm.add(cost_model, is_fraud, final, amount, weight)
        if challenger is not None:
            chal_flag = gbdt.score(challenger, outcome.features) >= challenger["threshold"]
            chal_arm.add(cost_model, is_fraud, worse(status, chal_flag), amount, weight)
        flagged_final = final != APPROVED
        if is_fraud:
            week["fraud"] += 1
            week["fraud_w"] += weight
            week["caught"] += flagged_final
            week["caught_w"] += weight * flagged_final
        else:
            week["legit"] += 1
        if final == TWO_FACTOR_REQUIRED:
            week["n2fa"] += 1
            if is_fraud:
                week["tp2fa_w"] += weight
            else:
                week["fp2fa"] += 1
        elif final == REJECTED:
            week["nrej"] += 1
            if is_fraud:
                week["tprej_w"] += weight
            else:
                week["fprej"] += 1
        if is_fraud:
            settles = final == APPROVED or (
                final == TWO_FACTOR_REQUIRED
                and random.Random(f"{cfg['rng_seed']}:{payload['id']}").random() < escape_rate)
            if settles and event.get("reported"):
                counter += 1
                heapq.heappush(heap, (now + event["report_delay_days"] * DAY, counter, row,
                                      snapshot.source_document, snapshot.destination_document, amount, final, weight))
            else:
                week["no_outcome_w"] += weight
    if week is not None:
        close_week(t0 + (current + 1) * WEEK, last=True)
        flush_week()
    return {"weeks": weeks, "promotions": promotions, "pix": counts["pix"],
            "confirmed_destinations": len(book.payers)}
