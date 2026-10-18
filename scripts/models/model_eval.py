"""Out-of-distribution evaluation of the hot-path models on labelled feature rows (docs/05-motor/validacao-pixsim.md)."""
import json
import os
import re
import sys
from datetime import datetime
from array import array
from collections import Counter

import numpy as np
from sklearn.metrics import roc_auc_score

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import _paths  # noqa: E402,F401

from costs import COMPONENTS, DECISION_SCORE, KS, PrecisionAccumulator, expected_cost  # noqa: E402

FRICTION_STATUS = "two_factor_required"
VICTIM_ROLES = ("none", "victim_to_mule")


class View:
    """Victim view of one feature file: legitimate Pix plus the Pix a victim sends to a mule."""

    def __init__(self, path, feature_names):
        self.names = list(feature_names)
        values, self.y = array("d"), array("b")
        self.typology, self.status, self.amount, self.day, self.weight = [], [], array("q"), [], array("d")
        self.at, self.delay_days, self.reported = array("d"), array("d"), array("b")
        with open(path, encoding="utf-8") as handle:
            for line in handle:
                row = json.loads(line)
                role = row.get("role")
                if role is not None and role not in VICTIM_ROLES:
                    continue
                features = row["features"]
                values.extend(features[n] for n in self.names)
                self.y.append(row["label"] if role is None else int(role == "victim_to_mule"))
                self.typology.append(row["typology"])
                self.status.append(row["status"])
                self.amount.append(row["amount"])
                self.day.append(row["day"])
                self.weight.append(row.get("weight", 1.0))
                self.at.append(datetime.fromisoformat(row["at"]).timestamp() if "at" in row else float("nan"))
                self.delay_days.append(row.get("report_delay_days", float("nan")))
                self.reported.append(int(row.get("reported", False)))
        self.X = np.frombuffer(values, dtype=float).reshape(-1, len(self.names))
        self.y = np.frombuffer(self.y, dtype=np.int8).astype(int)
        self.weight = np.frombuffer(self.weight, dtype=float)
        self.at = np.frombuffer(self.at, dtype=float)
        self.delay_days = np.frombuffer(self.delay_days, dtype=float)
        self.reported = np.frombuffer(self.reported, dtype=np.int8).astype(bool)
        self.fraud_weight = float(self.weight[self.y == 1].mean()) if self.y.sum() else 1.0

    def columns(self, names):
        return self.X[:, [self.names.index(n) for n in names]]

    def __len__(self):
        return len(self.y)


def pixsim_sha(setup_script):
    with open(setup_script, encoding="utf-8") as handle:
        return re.search(r"PIXSIM_SHA=(\w+)", handle.read()).group(1)


def deciders(view, scores, thresholds):
    """Per decider: continuous score and the status it would give each Pix (a model flag is a 2FA, as in shadow)."""
    rules_status = np.array(view.status)
    out = {}
    for name, score in scores.items():
        flagged = score >= thresholds[name]
        out[name] = (score, np.where(flagged, FRICTION_STATUS, "approved"))
    rule_score = np.array([DECISION_SCORE[s] for s in view.status])
    out["rules"] = (rule_score, rules_status)
    lgbm_flag = scores["lightgbm"] >= thresholds["lightgbm"]
    combined = np.where((rules_status == "approved") & lgbm_flag, FRICTION_STATUS, rules_status)
    out["rules+lightgbm"] = (np.maximum(rule_score, scores["lightgbm"]), combined)
    return out


def _cost_per_1000(view, statuses):
    legit, fraud = view.y == 0, view.y == 1

    def events(mask, label):
        return [{"label": label, "payload": {"amount": int(a)}, "response": {"status": s}}
                for a, s in zip(np.array(view.amount)[mask], statuses[mask])]

    cost_legit, cost_fraud = expected_cost(events(legit, "legit")), expected_cost(events(fraud, "fraud"))
    weight = view.fraud_weight
    parts = {k: cost_legit["components_cents"][k] + weight * cost_fraud["components_cents"][k] for k in COMPONENTS}
    effective = int(legit.sum()) + weight * int(fraud.sum())
    return {"total": round(sum(parts.values()) * 1000 / effective),
            "fraud": round((parts["fraud_approved"] + parts["fraud_2fa_escape"]) * 1000 / effective),
            "friction": round((parts["legit_2fa"] + parts["legit_rejected"]) * 1000 / effective)}


def _p_at_k(view, score):
    accumulator = PrecisionAccumulator()
    for s, a, d, y in zip(score, view.amount, view.day, view.y):
        accumulator.add_scored(float(s), int(a), d, bool(y))
    return accumulator.result(KS)


def evaluate(view, decider_map):
    """AUC, recall, weighted precision, friction, P@k, weighted cost and capture per typology for every decider."""
    y, weight = view.y, view.weight
    fraud, legit = y == 1, y == 0
    result = {}
    typologies = sorted({t for t, label in zip(view.typology, y) if label})
    typology_index = {t: np.array([x == t for x in view.typology]) for t in typologies}
    for name, (score, statuses) in decider_map.items():
        flagged = statuses != "approved"
        tp, fp = float((weight * (flagged & fraud)).sum()), float((weight * (flagged & legit)).sum())
        result[name] = {
            "auc": float(roc_auc_score(y, score)),
            "recall": float((flagged & fraud).sum() / fraud.sum()),
            "precision_weighted": tp / (tp + fp) if tp + fp else 0.0,
            "friction": float((flagged & legit).sum() / legit.sum()),
            "p_at_k": _p_at_k(view, score),
            "cost": _cost_per_1000(view, statuses),
            "capture": {t: float((flagged & mask).sum() / mask.sum()) for t, mask in typology_index.items()},
        }
    return result


def summarise(view):
    fraud_by_typology = Counter(t for t, y in zip(view.typology, view.y) if y)
    return {"pix": len(view), "fraud": int(view.y.sum()), "legit": int((view.y == 0).sum()),
            "fraud_weight": view.fraud_weight, "typologies": dict(sorted(fraud_by_typology.items()))}


def _pct(value):
    return f"{100 * value:.1f}%".replace(".", ",")


def _reais(cents):
    return f"R$ {cents / 100:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def _metric_table(title, scenarios, results, deciders_shown, fmt):
    lines = [f"| {title} | " + " | ".join(label for label, _ in scenarios) + " |", "|---|" + "---|" * len(scenarios)]
    for name in deciders_shown:
        cells = [fmt(results[key][name]) for _, key in scenarios]
        lines.append(f"| {name} | " + " | ".join(cells) + " |")
    return lines + [""]


def render_tables(results, worlds):
    shown = ["logreg", "lightgbm", "iforest", "rules", "rules+lightgbm"]
    scenarios = [("nosso → PixSim B", "ours_to_b"), ("PixSim A → PixSim B", "a_to_b"),
                 ("PixSim A → nosso", "a_to_ours"), ("nosso → nosso (referência)", "ours_to_ours")]
    lines = ["| Conjunto | Pix avaliados | Legítimos | Fraude pagador→mula | Peso médio da fraude |", "|---|---|---|---|---|"]
    for label, w in worlds.items():
        lines.append(f"| {label} | {w['pix']} | {w['legit']} | {w['fraud']} | {w['fraud_weight']:.4f} |".replace(".", ","))
    lines.append("")
    for title, fmt in [
        ("AUC", lambda r: f"{r['auc']:.3f}".replace(".", ",")),
        ("Recall no limiar", lambda r: _pct(r["recall"])),
        ("Precisão ponderada", lambda r: _pct(r["precision_weighted"])),
        ("Fricção em legítimos", lambda r: _pct(r["friction"])),
        ("Custo ponderado por 1.000 Pix", lambda r: _reais(r["cost"]["total"])),
    ]:
        lines += [f"**{title}**", ""] + _metric_table("decisor", scenarios, results, shown, fmt)
    lines += ["**P@k diário** (fraude superamostrada: a precisão do PixSim é inflada na proporção do peso)", "",
              "| cenário | decisor | " + " | ".join(f"P@{k}" for k in KS) + " |", "|---|---|" + "---|" * len(KS)]
    for label, key in scenarios[:3]:
        for name in shown:
            values = results[key][name]["p_at_k"]
            lines.append(f"| {label} | {name} | " + " | ".join(_pct(values[k]) for k in KS) + " |")
    lines.append("")
    for label, a_key, b_key in (("PixSim B", "ours_to_b", "a_to_b"),):
        typologies = list(results[a_key]["rules"]["capture"])
        head = ["tipologia"] + [f"{m} (nosso)" for m in ("logreg", "lightgbm", "iforest")] + \
               [f"{m} (PixSim A)" for m in ("logreg", "lightgbm", "iforest")] + ["regras"]
        lines += [f"**Captura por tipologia do PixSim em {label}** (Pix de vítima acima do limiar do modelo, ou fora de `approved` nas regras)", "",
                  "| " + " | ".join(head) + " |", "|---|" + "---|" * (len(head) - 1)]
        for t in typologies:
            cells = [_pct(results[a_key][m]["capture"][t]) for m in ("logreg", "lightgbm", "iforest")]
            cells += [_pct(results[b_key][m]["capture"][t]) for m in ("logreg", "lightgbm", "iforest")]
            cells.append(_pct(results[a_key]["rules"]["capture"][t]))
            lines.append(f"| {t} | " + " | ".join(cells) + " |")
        lines.append("")
    typologies = list(results["a_to_ours"]["rules"]["capture"])
    lines += ["**Captura por tipologia do nosso simulador (modelos do PixSim A)**", "",
              "| tipologia | " + " | ".join(shown) + " |", "|---|" + "---|" * len(shown)]
    for t in typologies:
        lines.append(f"| {t} | " + " | ".join(_pct(results["a_to_ours"][m]["capture"][t]) for m in shown) + " |")
    return lines + [""]
