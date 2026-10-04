# Re:Learn - find the thinking error, not just the wrong answer

Adaptive misconception diagnosis for Maharashtra SSC Std 9/10 algebra
(Quadratic Equations, Factorisation, Arithmetic Progression, Real Numbers).

Flow: **Attempt -> Diagnosis + Evidence -> Targeted intervention -> Reassessment -> Transfer -> Resolution -> Learner model**

## Run locally (2 terminals)

### 1) Backend (Python 3.10+)
```bash
cd backend
python -m venv .venv
# Windows:   .venv\Scripts\activate        Mac/Linux:  source .venv/bin/activate
pip install -r requirements.txt
python -m tests.test_engine          # should end with ALL PASSED
python -m app.evaluate               # writes docs/evaluation_report.json
uvicorn app.main:app --reload --port 8000
```
Check http://localhost:8000/api/health

### 2) Frontend (Node 18+)
```bash
cd frontend
npm install
npm run dev
```
Open http://localhost:5173 and press **Run the demo: 3(x + 2) = 15**.
On each stage press "Autofill demo answer" to walk Attempt -> Reassessment -> Transfer -> Resolved,
then open **My Fingerprint** and **Misconception Map**.

### Optional: Ollama (nicer explanations)
```bash
ollama pull llama3.2
ollama serve
```
Ollama only *phrases* the explanation. The diagnosis never depends on it; if it is off the dataset's own
intervention text is used (the UI shows the explanation source).
Disable with `RELEARN_USE_LLM=0`. Change model with `OLLAMA_MODEL=...`.

## Deploy
**Backend (Render, free tier)**: New > Web Service > connect repo, Root Directory `backend`,
Build `pip install -r requirements.txt`, Start `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
Note: Render's free disk is ephemeral, so `relearn.db` (learner history) resets on redeploy - fine for a demo.
Ollama will not be available there; the dataset text fallback is used automatically.

**Frontend (Vercel)**: Import repo, Root Directory `frontend`, Framework Vite,
add env var `VITE_API_URL=https://<your-render-service>.onrender.com`.

## How diagnosis works (honest version)
1. **Answer check** - SymPy compares the final answer to `expected_answer` (roots, expressions, fully-factored form).
2. **Rule detectors** (`app/rules.py`, ~25 patterns) read the *actual maths* in each step and produce evidence,
   e.g. "multiplier 3 applied to x but not to 2". Each detector maps to a `misconception_id` in the supplied taxonomy.
3. **Step-consistency check** - flags a step that does not follow from the previous equation.
4. **ML signal** (`app/ml.py`) - TF-IDF + Logistic Regression over the supplied attempts, including a "no misconception" class.
   Used only when no rule fires, and it needs both a close dataset match and high probability.
5. **Abstention** - below confidence 0.70, or with no working, the system says
   "Not enough evidence. Please show the next step of your working."
6. **Resolution** requires: reassessment passed with visible working AND transfer passed. A bare correct answer never counts.

## Data notes (read before the demo)
- Datasets used: `data/questions.csv`, `misconceptions.csv`, `student_attempts.csv`, `interventions.csv` (your supplied files, unmodified).
- **`data/extension_distribution.json` is NOT supplied data.** The taxonomy has no distribution-error record,
  so the headline demo uses a team-authored extension (`EXT-DIST-01`, 2 questions). The UI labels it as such.
- The supplied misconception descriptions / evidence patterns are templated, and most wrong attempts narrate the
  mistake in words instead of showing maths. So the rule engine, not the ML model, does the real diagnosis.
- Some `candidate_misconception_ids` look misaligned with the misconception names (e.g. AP nth-term vs "term check" ids).
  Rules therefore choose the id by meaning first and use candidates only to break ties. Worth a teacher review.

## Evaluation (all synthetic - no real students)
Run `python -m app.evaluate`. Reports three separate experiments:
A. ML-only on the 250 simulated attempts: random 10-fold vs unseen-wording 10-fold. B. Full engine on 58 developer-written
typed cases (including false-alarm and abstention checks). C. Unseen misconceptions removed from training.
Do not quote B as "accuracy": the cases were written by the same person who wrote the rules.

## Layout
```
data/        the 4 CSVs + extension_distribution.json
backend/app  mathparse.py rules.py ml.py diagnose.py journey.py llm.py ocr.py evaluate.py typed_cases.py main.py
backend/tests/test_engine.py
frontend/src App.jsx Solve.jsx Pages.jsx ui.jsx api.js
docs/        evaluation_report.json
```
OCR: the drawing pad sends a PNG to `/api/ocr`; `app/ocr.py` is a stub (`available:false`). Implement `recognise()` to plug in a real engine.
