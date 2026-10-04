"""Learning journey: diagnose -> intervention -> reassessment -> transfer -> resolution, plus the learner model (SQLite).

Resolution rule (deliberately strict, as the problem statement demands):
  resolved  = reassessment passed WITH visible correct working  AND  transfer passed with working.
  A correct answer alone, or a correct reassessment alone, is never 'resolved'.
"""
import json
import sqlite3
import time
import uuid
from pathlib import Path

from .rules import Q

DB = Path(__file__).resolve().parents[2] / "relearn.db"

STATUS_LABEL = {
    "detected": "Misconception detected", "intervention_completed": "Intervention completed",
    "improving": "Improving", "resolved": "Resolved", "persistent": "Persistent misconception",
    "insufficient": "Insufficient evidence",
}
FINGERPRINT = ["Sign error", "Distribution error", "Formula selection", "Arithmetic", "Variable / Interpretation",
               "Conceptual", "Procedural"]
_TYPE_TO_FP = {"Sign error": "Sign error", "Distribution error": "Distribution error",
               "Formula selection": "Formula selection", "Arithmetic": "Arithmetic",
               "Interpretation": "Variable / Interpretation", "Conceptual": "Conceptual", "Procedural": "Procedural"}


def db():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    c.executescript("""
    CREATE TABLE IF NOT EXISTS sessions(id TEXT PRIMARY KEY, student_id TEXT, question_id TEXT, misconception_id TEXT,
        status TEXT, stage TEXT, data TEXT, created REAL, updated REAL);
    CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY AUTOINCREMENT, student_id TEXT, session_id TEXT,
        misconception_id TEXT, kind TEXT, status TEXT, ts REAL);
    """)
    return c


def _event(c, student, sid, mid, kind, status):
    c.execute("INSERT INTO events(student_id,session_id,misconception_id,kind,status,ts) VALUES(?,?,?,?,?,?)",
              (student, sid, mid, kind, status, time.time()))


class Journey:
    def __init__(self, engine):
        self.E = engine

    # ---------------------------------------------------------------- step 1: first attempt
    def start(self, student_id, question_id, working, final):
        q = self.E.get_q(question_id)
        d = self.E.diagnose(q, working, final)
        sid = uuid.uuid4().hex[:10]
        out = {"session_id": sid, "diagnosis_result": d, "intervention": None, "status": None, "next": None}
        c = db()
        now = time.time()
        if d["status"] == "diagnosed":
            mid = d["diagnosis"]["misconception_id"]
            iv = self.intervention_for(mid)
            out["intervention"] = iv
            out["status"] = "detected"
            out["next"] = "intervention"
            c.execute("INSERT INTO sessions VALUES(?,?,?,?,?,?,?,?,?)",
                      (sid, student_id, question_id, mid, "detected", "intervention", json.dumps({"first": d["diagnosis"]}), now, now))
            _event(c, student_id, sid, mid, "detected", "detected")
        elif d["status"] == "answer_correct_reasoning_flawed":
            out["status"] = "insufficient"
            out["next"] = "show_more_working"
            c.execute("INSERT INTO sessions VALUES(?,?,?,?,?,?,?,?,?)",
                      (sid, student_id, question_id, None, "insufficient", "retry", "{}", now, now))
        elif d["status"] == "correct":
            out["status"] = "correct"
            out["next"] = "next_question"
        else:
            out["status"] = "insufficient"
            out["next"] = "show_more_working"
            c.execute("INSERT INTO sessions VALUES(?,?,?,?,?,?,?,?,?)",
                      (sid, student_id, question_id, None, "insufficient", "retry", "{}", now, now))
        c.commit(); c.close()
        return out

    def intervention_for(self, mid):
        iv = self.E.intervs.get(mid)
        if not iv:
            return None
        m = self.E.mis.get(mid, {})
        return {"misconception_id": mid, "type": iv["intervention_type"], "text": iv["intervention_text"],
                "hint": iv["hint"], "worked_example": iv["worked_example"],
                "reassessment_question": iv["reassessment_question"], "transfer_question": iv["transfer_question"],
                "correct_concept": m.get("correct_concept", ""), "success_criteria": iv["success_criteria"],
                "from_extension": bool(iv.get("extension"))}

    # ---------------------------------------------------------------- steps 2 & 3
    def _grade(self, mid, text, expected, working, final):
        q = Q(id=f"{mid}-check", text=text, expected=str(expected), candidates=[mid])
        d = self.E.diagnose(q, working, final)
        has_work = len([s for s in working.splitlines() if s.strip()]) >= 1 and working.strip() != (final or "").strip()
        same = bool(d["diagnosis"] and d["diagnosis"]["misconception_id"] == mid)
        passed = d["status"] == "correct" and has_work
        return d, passed, same, has_work

    def submit_stage(self, session_id, stage, working, final):
        c = db()
        s = c.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
        if not s or not s["misconception_id"]:
            c.close()
            raise KeyError("unknown session")
        mid, student = s["misconception_id"], s["student_id"]
        iv = self.E.intervs[mid]
        data = json.loads(s["data"])
        text, exp = ((iv["reassessment_question"], iv["expected_answer"]) if stage == "reassessment"
                     else (iv["transfer_question"], iv["transfer_expected_answer"]))
        d, passed, same, has_work = self._grade(mid, text, exp, working, final)
        data[stage] = {"passed": passed, "same_misconception": same, "answer_correct": d["answer_correct"]}
        status, msg, nxt = s["status"], "", None
        if stage == "reassessment":
            if passed:
                status, nxt = "improving", "transfer"
                msg = "Reassessment correct with sound working. One more check: a transfer question in a different form."
            elif d["answer_correct"] and not has_work:
                status, nxt = "intervention_completed", "retry_reassessment"
                msg = "Correct answer, but I can't see your working, so I can't confirm the misconception is gone. Show your steps."
            elif same:
                status, nxt = "persistent", "reintervene"
                msg = "The same misconception appeared again. Let's try a different explanation."
            else:
                status, nxt = "intervention_completed", "retry_reassessment"
                msg = "Not quite - and it is a different slip from before. Check the step flagged below and try again."
        else:
            if data.get("reassessment", {}).get("passed") is not True:
                c.close(); raise ValueError("pass reassessment first")
            if passed:
                status, nxt = "resolved", "done"
                msg = "Transfer correct in a new form. This misconception is marked resolved."
            elif same:
                status, nxt = "persistent", "reintervene"
                msg = "It reappeared in the new context, so the idea has not fully transferred yet."
            else:
                status, nxt = "improving", "retry_transfer"
                msg = "You are close - the transfer question is not fully correct yet. You stay at Improving."
        c.execute("UPDATE sessions SET status=?, stage=?, data=?, updated=? WHERE id=?",
                  (status, nxt, json.dumps(data), time.time(), session_id))
        _event(c, student, session_id, mid, stage, status)
        c.commit(); c.close()
        return {"session_id": session_id, "stage": stage, "passed": passed, "same_misconception_again": same,
                "status": status, "status_label": STATUS_LABEL[status], "message": msg, "next": nxt,
                "diagnosis_result": d}

    def mark_intervention_done(self, session_id):
        c = db()
        s = c.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
        if s and s["status"] in ("detected", "persistent"):
            c.execute("UPDATE sessions SET status='intervention_completed', stage='reassessment', updated=? WHERE id=?",
                      (time.time(), session_id))
            _event(c, s["student_id"], session_id, s["misconception_id"], "intervention", "intervention_completed")
            c.commit()
        c.close()
        return {"status": "intervention_completed", "next": "reassessment"}

    # ---------------------------------------------------------------- learner model
    def learner(self, student_id):
        c = db()
        rows = c.execute("SELECT * FROM sessions WHERE student_id=? AND misconception_id IS NOT NULL ORDER BY updated",
                         (student_id,)).fetchall()
        ev = c.execute("SELECT * FROM events WHERE student_id=? ORDER BY ts", (student_id,)).fetchall()
        c.close()
        per = {}
        for r in rows:
            m = per.setdefault(r["misconception_id"], {"misconception_id": r["misconception_id"], "attempts": 0, "status": None})
            m["attempts"] += 1
            m["status"] = r["status"]            # latest session wins
        out = []
        for mid, m in per.items():
            info = self.E.mis.get(mid, {})
            ui = {"detected": "New", "intervention_completed": "New", "improving": "Improving",
                  "persistent": "Persistent", "resolved": "Resolved"}.get(m["status"], "New")
            if m["attempts"] > 1 and ui == "New":
                ui = "Persistent"
            out.append({**m, "name": info.get("misconception_name", mid), "type": info.get("misconception_type", ""),
                        "topic": info.get("topic", ""), "state": ui, "status_label": STATUS_LABEL.get(m["status"], m["status"])})
        fp = {k: {"total": 0, "New": 0, "Improving": 0, "Persistent": 0, "Resolved": 0} for k in FINGERPRINT}
        for m in out:
            k = _TYPE_TO_FP.get(m["type"], "Conceptual")
            fp[k]["total"] += 1
            fp[k][m["state"]] += 1
        timeline, resolved_cum, seen = [], 0, set()
        for e in ev:
            seen.add(e["misconception_id"])
            if e["status"] == "resolved":
                resolved_cum += 1
            timeline.append({"ts": e["ts"], "kind": e["kind"], "status": e["status"],
                             "misconception_id": e["misconception_id"], "resolved_so_far": resolved_cum,
                             "seen_so_far": len(seen)})
        return {"student_id": student_id, "misconceptions": out, "fingerprint": fp, "timeline": timeline,
                "summary": {"seen": len(out), "resolved": sum(m["state"] == "Resolved" for m in out),
                            "improving": sum(m["state"] == "Improving" for m in out),
                            "persistent": sum(m["state"] == "Persistent" for m in out)}}
