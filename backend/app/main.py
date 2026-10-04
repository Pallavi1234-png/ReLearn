"""FastAPI app.  Run:  uvicorn app.main:app --reload --port 8000   (from the backend/ folder)"""
import json
from collections import Counter
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .diagnose import Engine
from .journey import Journey, STATUS_LABEL
from . import llm, ocr

app = FastAPI(title="Re:Learn API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
E = Engine()
J = Journey(E)
DOCS = Path(__file__).resolve().parents[2] / "docs"

CHAPTERS = {  # the four allowed topics only
    "Quadratic Equations": 10, "Arithmetic Progression": 10, "Algebraic Expressions": 9, "Real Numbers": 9}


class Submit(BaseModel):
    student_id: str = "demo"
    question_id: str
    working: str = ""
    final_answer: str = ""


class Stage(BaseModel):
    working: str = ""
    final_answer: str = ""


@app.get("/api/health")
def health():
    return {"ok": True, "ollama": llm.available(), "questions": len(E.questions), "misconceptions": len(E.mis)}


@app.get("/api/meta")
def meta():
    return {"standards": [9, 10], "topics": [{"chapter": c, "standard": s} for c, s in CHAPTERS.items()],
            "difficulties": ["Easy", "Medium", "Hard"]}


@app.get("/api/questions")
def questions(standard: int = None, chapter: str = None, difficulty: str = None):
    out = []
    for qid, r in E.questions.items():
        if standard and int(r["standard"]) != standard: continue
        if chapter and r["chapter"] != chapter: continue
        if difficulty and r["difficulty"] != difficulty: continue
        out.append({"question_id": qid, "question": r["question"], "difficulty": r["difficulty"],
                    "chapter": r["chapter"], "standard": int(r["standard"]), "topic": r["topic"]})
    return out


@app.post("/api/submit")
def submit(b: Submit):
    if b.question_id not in E.questions:
        raise HTTPException(404, "unknown question")
    r = J.start(b.student_id, b.question_id, b.working, b.final_answer)
    d = r["diagnosis_result"]
    if d["diagnosis"] and r["intervention"]:
        text, src = llm.explain(d["diagnosis"], r["intervention"], E.questions[b.question_id]["question"])
        r["explanation"], r["explanation_source"] = text, src
    r["status_label"] = STATUS_LABEL.get(r["status"], r["status"])
    return r


@app.post("/api/session/{sid}/intervention-done")
def intervention_done(sid: str):
    return J.mark_intervention_done(sid)


@app.post("/api/session/{sid}/{stage}")
def stage(sid: str, stage: str, b: Stage):
    if stage not in ("reassessment", "transfer"):
        raise HTTPException(400, "stage must be reassessment or transfer")
    try:
        return J.submit_stage(sid, stage, b.working, b.final_answer)
    except KeyError:
        raise HTTPException(404, "unknown session")
    except ValueError as e:
        raise HTTPException(409, str(e))


@app.get("/api/learner/{student_id}")
def learner(student_id: str):
    return J.learner(student_id)


@app.get("/api/map")
def misconception_map():
    nodes, links = [], []
    seen = set()
    def add(i, label, kind):
        if i not in seen:
            seen.add(i); nodes.append({"id": i, "label": label, "kind": kind})
    for mid, m in E.mis.items():
        topic = m["topic"]; concept = m["misconception_type"]
        add("T:" + topic, topic, "topic"); add(f"C:{topic}:{concept}", concept, "concept")
        add("M:" + mid, m["misconception_name"], "misconception")
        links += [{"source": "T:" + topic, "target": f"C:{topic}:{concept}"},
                  {"source": f"C:{topic}:{concept}", "target": "M:" + mid}]
        iv = E.intervs.get(mid)
        if iv:
            add("I:" + mid, iv["intervention_type"] + ": " + mid, "intervention")
            add("R:" + mid, "Resolved", "resolution")
            links += [{"source": "M:" + mid, "target": "I:" + mid}, {"source": "I:" + mid, "target": "R:" + mid}]
    return {"nodes": nodes, "links": links}


@app.get("/api/evaluation")
def evaluation():
    p = DOCS / "evaluation_report.json"
    if not p.exists():
        raise HTTPException(404, "run: python -m app.evaluate")
    return json.loads(p.read_text(encoding="utf-8"))


@app.get("/api/demo-cases")
def demo_cases():
    return [
        {"title": "Distribution error (headline demo)", "question_id": "EXT-Q9-DIST-001",
         "working": "3x + 2 = 15\n3x = 13\nx = 13/3", "final_answer": "x = 13/3",
         "reassessment": {"working": "4x + 12 = 28\n4x = 16\nx = 4", "final_answer": "x = 4"},
         "transfer": {"working": "3(x + 5) = 36\n3x + 15 = 36\n3x = 21\nx = 7", "final_answer": "x = 7"}},
        {"title": "Sign error reading roots from factors", "question_id": "Q10-QE-003",
         "working": "(x-2)(x-3)=0\nx=2 or x=-3", "final_answer": "x=2, -3"},
        {"title": "AP: n instead of n-1", "question_id": "Q10-AP-003",
         "working": "a=3, d=4, n=10\na10 = 3 + 10(4) = 43", "final_answer": "43"},
        {"title": "Answer only - system refuses to guess", "question_id": "Q10-QE-003", "working": "",
         "final_answer": "x=2, -3"},
    ]


class Drawing(BaseModel):
    image: str


@app.post("/api/ocr")
def run_ocr(b: Drawing):
    return ocr.from_b64(b.image)


@app.get("/api/teacher")
def teacher():
    """Class-level view: which misconceptions are most common and how many are resolved (all students on this server)."""
    from .journey import db
    c = db()
    rows = c.execute("SELECT misconception_id, status, COUNT(*) n FROM sessions WHERE misconception_id IS NOT NULL "
                     "GROUP BY misconception_id, status").fetchall()
    students = c.execute("SELECT COUNT(DISTINCT student_id) n FROM sessions").fetchone()["n"]
    c.close()
    agg = {}
    for r in rows:
        a = agg.setdefault(r["misconception_id"], {"misconception_id": r["misconception_id"], "total": 0, "resolved": 0})
        a["total"] += r["n"]
        if r["status"] == "resolved":
            a["resolved"] += r["n"]
    out = []
    for a in agg.values():
        a["name"] = E.mis.get(a["misconception_id"], {}).get("misconception_name", a["misconception_id"])
        out.append(a)
    out.sort(key=lambda z: -z["total"])
    return {"students": students, "misconceptions": out[:15]}
