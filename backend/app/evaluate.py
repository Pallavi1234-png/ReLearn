"""Evaluation module. Run:  python -m app.evaluate   (writes docs/evaluation_report.json + .md)

Three clearly separated experiments - none of them uses real students:
 A. ML-only on the supplied SIMULATED attempts (two split regimes).
 B. Full engine (rules + ML + abstention) on developer-authored typed cases.
 C. Behaviour on UNSEEN misconceptions (classes removed from training).
"""
import json
import warnings
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix
from sklearn.model_selection import GroupKFold, KFold

from .diagnose import Engine, ACCEPT_THRESHOLD
from .ml import MLDiagnoser, NONE, load_tables
from .rules import Q
from .typed_cases import CASES

warnings.filterwarnings("ignore")
OUT = Path(__file__).resolve().parents[2] / "docs"


def _prf(y, p, labels):
    pr, rc, f1, sup = precision_recall_fscore_support(y, p, labels=labels, zero_division=0)
    return {"macro_precision": round(float(pr.mean()), 3), "macro_recall": round(float(rc.mean()), 3),
            "macro_f1": round(float(f1.mean()), 3)}


def _ml_cv(att, splitter, groups=None):
    att = att.reset_index(drop=True)
    att["label"] = att.misconception_id.fillna(NONE)
    preds = [None] * len(att)
    for tr, te in (splitter.split(att, groups=groups) if groups is not None else splitter.split(att)):
        m = MLDiagnoser(att.iloc[tr])
        for j in te:
            r = att.iloc[j]
            res = m.predict(r.question, str(r.student_working), None, topn=1)
            preds[j] = res["top"][0][0]
    return att, preds


def exp_a(att):
    out = {}
    for name, splitter, groups in (
        ("A1_random_10fold (same wording may appear in train - optimistic)", KFold(10, shuffle=True, random_state=0), None),
        ("A2_unseen_wording_10fold (identical working text never in train)", GroupKFold(10), att.student_working.astype(str).values),
    ):
        a, preds = _ml_cv(att, splitter, groups)
        y = a.label.tolist()
        wrong = a.label != NONE
        labels = sorted(set(y))
        yw = [y[i] for i in range(len(y)) if wrong.iloc[i]]
        pw = [preds[i] for i in range(len(y)) if wrong.iloc[i]]
        detect_true = wrong.astype(int).values
        detect_pred = np.array([int(p != NONE) for p in preds])
        pr, rc, f1, _ = precision_recall_fscore_support(detect_true, detect_pred, average="binary", zero_division=0)
        out[name] = {
            "n_attempts": len(a), "n_wrong_attempts": int(wrong.sum()),
            "misconception_accuracy_on_wrong_attempts": round(accuracy_score(yw, pw), 3),
            "misconception_metrics_on_wrong_attempts": _prf(yw, pw, sorted(set(yw))),
            "detect_wrong_vs_not_precision": round(float(pr), 3), "detect_recall": round(float(rc), 3),
            "detect_f1": round(float(f1), 3),
            "chance_level_note": f"{len(set(yw))} classes, ~{len(yw) / max(1, len(set(yw))):.1f} wrong attempts per class",
        }
    return out


def exp_b(E):
    rows = []
    for q, w, f, gold, st in CASES:
        qq = Q(**q) if isinstance(q, dict) else E.get_q(q)
        d = E.diagnose(qq, w, f)
        pm = d["diagnosis"]["misconception_id"] if d["diagnosis"] else None
        rows.append({"q": qq.id, "gold": gold or "-", "pred": pm or "-", "status": d["status"], "expect": st,
                     "conf": d["diagnosis"]["confidence"] if d["diagnosis"] else None})
    df = pd.DataFrame(rows)
    mis = df[df.expect == "diagnosed"]
    correct_cases = df[df.expect == "correct"]
    abst = df[df.expect == "insufficient"]
    labels = sorted(set(mis.gold) | set(p for p in mis.pred if p != "-"))
    cm = confusion_matrix(mis.gold, mis.pred, labels=labels + (["-"] if "-" in set(mis.pred) else []))
    return {
        "n_cases": len(df), "note": "developer-authored typed cases; NOT real students",
        "misconception_cases": {
            "n": len(mis), "accuracy": round(float((mis.gold == mis.pred).mean()), 3),
            **_prf(mis.gold, mis.pred, labels),
            "confusion_labels": labels + (["-"] if "-" in set(mis.pred) else []), "confusion_matrix": cm.tolist(),
            "mean_confidence_when_correct": round(float(mis[mis.gold == mis.pred].conf.mean()), 3),
        },
        "false_alarm_on_correct_working": {"n": len(correct_cases),
                                           "false_diagnoses": int((correct_cases.status == "diagnosed").sum())},
        "abstention_on_insufficient_evidence": {"n": len(abst), "correctly_abstained": int((abst.status == "insufficient").sum())},
        "failures": df[(df.gold != df.pred) | (df.status != df.expect)].to_dict("records"),
    }


def exp_c(att):
    """Remove one misconception from training; how often is it still (wrongly) named?"""
    wrong = att[att.misconception_id.notna()]
    forced, abstain, total = 0, 0, 0
    per = []
    for mid in sorted(wrong.misconception_id.unique()):
        m = MLDiagnoser(att, exclude_ids=[mid])
        rows = wrong[wrong.misconception_id == mid]
        f = 0
        for r in rows.itertuples():
            res = m.predict(r.question, str(r.student_working), None, topn=1)
            top, pr = res["top"][0]
            conf = pr * min(1.0, res["sim"] / 0.70)
            if top != NONE and conf >= ACCEPT_THRESHOLD:
                f += 1
            total += 1
        forced += f
        abstain += len(rows) - f
    return {"unseen_misconception_attempts": total, "forced_wrong_label": forced,
            "abstained_or_none": abstain, "abstention_rate": round(abstain / total, 3),
            "note": "Higher abstention is better here: the true class was never seen, so any named misconception is wrong."}


def main():
    E = Engine()
    _, _, att, _ = load_tables()
    report = {"threshold": ACCEPT_THRESHOLD,
              "dataset_caveat": ("The supplied student_attempts working text narrates the mistake in words "
                                 "(e.g. 'I used a+n d instead of a+(n-1)d') and is not real mathematical working; "
                                 "templated wording is repeated across questions. ML scores below therefore measure "
                                 "classification of simulated explanations, not of real student work."),
              "A_ml_on_simulated_attempts": exp_a(att),
              "B_full_engine_on_typed_cases": exp_b(E),
              "C_unseen_misconceptions": exp_c(att),
              "real_student_results": "None - no real student data was available."}
    OUT.mkdir(exist_ok=True)
    (OUT / "evaluation_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "B_full_engine_on_typed_cases"}, indent=2))
    b = report["B_full_engine_on_typed_cases"]
    print(json.dumps({k: v for k, v in b.items() if k not in ("misconception_cases",)}, indent=2))
    print({k: v for k, v in b["misconception_cases"].items() if "confusion" not in k})


if __name__ == "__main__":
    main()
