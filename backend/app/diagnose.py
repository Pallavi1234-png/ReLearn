"""Diagnosis pipeline.

working text -> steps -> (answer check, rule detectors, step-consistency check, ML signal) -> fusion
-> structured diagnosis, or an explicit 'insufficient evidence' result. Nothing here calls an LLM.
"""
import json
import re
from pathlib import Path
from typing import Optional

import sympy as sp

from .mathparse import (normalize, parse_expr_safe, root_set, sets_equal, numbers_in, is_fully_factored,
                        parse_struct)
from .ml import MLDiagnoser, load_tables, DATA, NONE
from .rules import Q, Ctx, Finding, run_rules, check_steps, resolve_id

ACCEPT_THRESHOLD = 0.70     # below this we do NOT name a misconception
NO_WORKING_CAP = 0.60       # an answer with no working can never reach the threshold from rules alone
MSG_INSUFFICIENT = "Not enough evidence. Please show the next step of your working."


# ---------------------------------------------------------------- answers
def split_steps(working: str):
    if not working:
        return []
    parts = re.split(r"[\n;]+|→|⇒|=>", working)
    return [p.strip() for p in parts if p and p.strip()]


def _tokens(s):
    return set(re.findall(r"[a-z0-9√²³]+", normalize(s).lower())) - {"the", "a", "an", "is", "of", "and", "to"}


def answers_match(expected: str, given: str) -> Optional[bool]:
    """True/False when we can decide, None when the answer is free text we cannot judge."""
    if not given or not given.strip():
        return None
    e, g = expected.strip(), given.strip()
    # factorised / expression answers: must be equal AND fully factored if expected is factored
    es, gs = parse_struct(e.split(";")[0]), parse_struct(g.split(";")[0])
    if (isinstance(es, sp.Expr) and isinstance(gs, sp.Expr) and "," not in e and "..." not in e
            and not re.search(r"=", e.split(";")[0])):
        try:
            same = sp.expand(es - gs) == 0
        except Exception:
            same = False
        if same and not es.is_Add and gs is not None:
            return bool(is_fully_factored(gs))
        if same:
            return True
        return False
    # root lists
    re_, rg = root_set(e), root_set(g)
    if re_ is not None and rg is not None:
        return sets_equal(re_, rg)
    # numeric answers with units/symbols, e.g. "₹1000", "2⁷ = 128", "37=5(7)+2"
    ne, ng = numbers_in(e), numbers_in(g)
    if ne and ng and len(e) < 40:
        if "=" in e and not re.match(r"^\s*[a-zA-Z]\s*=", e):
            return ne[-1] == ng[-1]
        return ne == ng if len(ne) > 1 else ne[-1] == ng[-1]
    # free text: token overlap
    te, tg = _tokens(e), _tokens(g)
    if te and tg:
        overlap = len(te & tg) / len(te)
        if overlap >= 0.6:
            return True
        if overlap <= 0.2:
            return False
    return None


# ---------------------------------------------------------------- engine
class Engine:
    def __init__(self):
        self.q_df, self.m_df, self.a_df, self.i_df = load_tables()
        ext = json.loads((DATA / "extension_distribution.json").read_text(encoding="utf-8"))
        self.mis = {r["misconception_id"]: r for r in self.m_df.to_dict("records")}
        self.intervs = {r["misconception_id"]: r for r in self.i_df.to_dict("records")}
        for r in ext["misconceptions"]:
            self.mis[r["misconception_id"]] = {**r, "extension": True}
        for r in ext["interventions"]:
            self.intervs[r["misconception_id"]] = {**r, "extension": True}
        self.questions = {r["question_id"]: r for r in self.q_df.to_dict("records")}
        for r in ext.get("questions", []):
            self.questions[r["question_id"]] = {**r, "extension": True}
        self.ml = MLDiagnoser(self.a_df)

    # -- questions
    def get_q(self, qid) -> Q:
        r = self.questions[qid]
        cands = [c for c in str(r.get("candidate_misconception_ids") or "").split(";") if c]
        return Q(id=qid, text=r["question"], expected=str(r["expected_answer"]), candidates=cands,
                 topic=str(r["topic"]), chapter=str(r["chapter"]), standard=int(r["standard"]))

    # -- diagnosis
    def diagnose(self, q: Q, working: str, final: Optional[str] = None, use_ml: bool = True) -> dict:
        steps = split_steps(working)
        final = (final or "").strip()
        if not final and steps:
            final = steps[-1]
        has_working = len(steps) > 0 and not (len(steps) == 1 and normalize(steps[0]) == normalize(final))
        step_view = [{"index": i + 1, "text": s, "flag": None} for i, s in enumerate(steps)]

        if not working.strip() and not final:
            return self._result(q, "insufficient", None, None, None, step_view, message="Please enter your working.")

        ans_ok = answers_match(q.expected, final)
        ctx = Ctx(q, steps, final)
        findings = run_rules(ctx)
        generic = check_steps(ctx)
        ml = self.ml.predict(q.text, working or final, q.candidates) if use_ml else None

        scored = []
        for f in findings:
            mid = resolve_id(f.kind, q.candidates)
            if not mid:
                continue
            conf = f.confidence
            if not has_working:
                conf = min(conf, NO_WORKING_CAP)
            if ml and ml["top"] and ml["top"][0][0] == mid:
                conf = min(0.98, conf + 0.03)
            scored.append((conf, mid, f))
        scored.sort(key=lambda z: -z[0])

        # ML-only fallback: needs working, a close match in the dataset AND high calibrated probability
        ml_choice = None
        if not scored and ml and has_working and ml["top"]:
            mid, pr = ml["top"][0]
            if mid != NONE:
                conf = pr * min(1.0, ml["sim"] / 0.70)
                if conf >= ACCEPT_THRESHOLD:
                    ml_choice = (conf, mid)

        if scored and scored[0][0] >= ACCEPT_THRESHOLD:
            conf, mid, f = scored[0]
            if f.step and 1 <= f.step <= len(step_view):
                step_view[f.step - 1]["flag"] = "error"
            diag = self._diag_dict(mid, conf, f.evidence, f.step, f.expected_step, "rule:" + f.rule)
            alts = [self._alt(m, c, ff.evidence) for c, m, ff in scored[1:3] if m != mid]
            return self._result(q, "diagnosed", ans_ok, False, diag, step_view, alternatives=alts, ml=ml)

        if ml_choice:
            conf, mid = ml_choice
            ev = (f"Your working resembles dataset attempt {ml['nearest']} labelled with this misconception"
                  + (f" (key terms: {', '.join(ml['terms'])})." if ml["terms"] else "."))
            diag = self._diag_dict(mid, conf, ev, 0, "", "ml:tfidf-logreg")
            return self._result(q, "diagnosed", ans_ok, False, diag, step_view, ml=ml)

        # nothing diagnosable: be explicit about *why*
        hyp = [self._alt(m, c, f.evidence) for c, m, f in scored[:2]]
        if generic and ans_ok is not True:
            kind, idx, text = generic
            step_view[idx - 1]["flag"] = "unexplained"
            msg = (f"Step {idx} ({text}) does not follow from the previous line, but I can't tell why. "
                   f"Please show the next step of your working.")
            return self._result(q, "insufficient", ans_ok, False, None, step_view, message=msg,
                                alternatives=hyp, ml=ml, error_step=idx)
        if ans_ok is True:
            if generic:       # correct final answer but a step is wrong
                kind, idx, text = generic
                step_view[idx - 1]["flag"] = "unexplained"
                return self._result(q, "answer_correct_reasoning_flawed", True, False, None, step_view,
                                    message=f"The final answer is right, but step {idx} ({text}) does not follow "
                                            f"from the previous line. Check how you got there.", ml=ml,
                                    error_step=idx)
            if not has_working:
                return self._result(q, "insufficient", True, None, None, step_view,
                                    message="Correct answer - but with no working I can't check your reasoning. "
                                            "Show your steps so Re:Learn can confirm you understand it.", ml=ml)
            return self._result(q, "correct", True, True, None, step_view, ml=ml)
        if ans_ok is None:
            return self._result(q, "insufficient", None, None, None, step_view,
                                message="I can't automatically judge this free-text answer. " + MSG_INSUFFICIENT,
                                alternatives=hyp, ml=ml)
        return self._result(q, "insufficient", False, None, None, step_view,
                            message=MSG_INSUFFICIENT, alternatives=hyp, ml=ml)

    # -- helpers
    def _diag_dict(self, mid, conf, evidence, step, expected_step, source):
        m = self.mis.get(mid, {})
        return {"misconception_id": mid, "misconception_name": m.get("misconception_name", mid),
                "misconception_type": m.get("misconception_type", ""), "confidence": round(float(conf), 2),
                "evidence": evidence, "error_step": step, "expected_step": expected_step,
                "reasoning_correct": False, "source": source,
                "correct_concept": m.get("correct_concept", "")}

    def _alt(self, mid, conf, ev):
        return {"misconception_id": mid, "misconception_name": self.mis.get(mid, {}).get("misconception_name", mid),
                "confidence": round(float(conf), 2), "evidence": ev}

    def _result(self, q, status, ans_ok, reasoning_ok, diag, steps, message=None, alternatives=None, ml=None,
                error_step=None):
        return {"question_id": q.id, "status": status, "answer_correct": ans_ok, "reasoning_correct": reasoning_ok,
                "diagnosis": diag, "message": message, "steps": steps, "alternatives": alternatives or [],
                "error_step": diag["error_step"] if diag else error_step,
                "ml": ({"top": [{"misconception_id": m, "p": round(p, 3)} for m, p in ml["top"]],
                        "similarity": round(ml["sim"], 2), "nearest_attempt": ml["nearest"],
                        "terms": ml["terms"]} if ml else None),
                "threshold": ACCEPT_THRESHOLD}
