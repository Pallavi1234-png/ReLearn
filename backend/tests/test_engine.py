"""Run:  python -m tests.test_engine   (from backend/)  - no pytest needed."""
import os, tempfile, warnings
warnings.filterwarnings("ignore")
from app import journey
journey.DB = journey.Path(tempfile.mkdtemp()) / "t.db"
from app.diagnose import Engine
from app.rules import Q
from app.typed_cases import CASES

E = Engine(); J = journey.Journey(E)
fails = 0
def check(name, cond):
    global fails
    print(("PASS " if cond else "FAIL ") + name); fails += (not cond)

ok = 0
for q, w, f, gold, st in CASES:
    qq = Q(**q) if isinstance(q, dict) else E.get_q(q)
    d = E.diagnose(qq, w, f)
    pm = d["diagnosis"]["misconception_id"] if d["diagnosis"] else None
    ok += (d["status"] == st and pm == gold)
check(f"typed cases {ok}/{len(CASES)}", ok == len(CASES))

# headline demo, full journey
r = J.start("t1", "EXT-Q9-DIST-001", "3x + 2 = 15\n3x = 13\nx = 13/3", "x = 13/3")
check("demo diagnosed as distribution error", r["diagnosis_result"]["diagnosis"]["misconception_id"] == "EXT-DIST-01")
check("error step flagged = 1", r["diagnosis_result"]["steps"][0]["flag"] == "error")
J.mark_intervention_done(r["session_id"])
a = J.submit_stage(r["session_id"], "reassessment", "4x + 12 = 28\n4x = 16\nx = 4", "x = 4")
check("reassessment pass -> improving (NOT resolved)", a["status"] == "improving")
try:
    J2 = J.start("t2", "EXT-Q9-DIST-001", "3x + 2 = 15\n3x = 13\nx = 13/3", "x = 13/3"); J.mark_intervention_done(J2["session_id"])
    J.submit_stage(J2["session_id"], "transfer", "3x+15=36\nx=7", "x = 7"); check("transfer blocked before reassessment", False)
except ValueError:
    check("transfer blocked before reassessment", True)
b = J.submit_stage(r["session_id"], "transfer", "3(x+5) = 36\n3x + 15 = 36\n3x = 21\nx = 7", "x = 7")
check("transfer pass -> resolved", b["status"] == "resolved")
# answer-only never resolves
r3 = J.start("t3", "EXT-Q9-DIST-001", "3x + 2 = 15\n3x = 13\nx = 13/3", "x = 13/3"); J.mark_intervention_done(r3["session_id"])
c = J.submit_stage(r3["session_id"], "reassessment", "", "x = 4")
check("correct answer with no working is not accepted", c["status"] != "improving" and not c["passed"])
# repeat error -> persistent
r4 = J.start("t4", "EXT-Q9-DIST-001", "3x + 2 = 15\n3x = 13\nx = 13/3", "x = 13/3"); J.mark_intervention_done(r4["session_id"])
d4 = J.submit_stage(r4["session_id"], "reassessment", "4x + 3 = 28\n4x = 25\nx = 25/4", "x = 25/4")
check("same error again -> persistent", d4["status"] == "persistent")
# abstention
q = E.get_q("Q10-QE-003"); d = E.diagnose(q, "", "x=2, -3")
check("answer without working -> insufficient evidence", d["status"] == "insufficient" and d["diagnosis"] is None)
check("learner model has fingerprint", "Distribution error" in J.learner("t1")["fingerprint"])
print("\nALL PASSED" if not fails else f"\n{fails} FAILED"); raise SystemExit(fails)
