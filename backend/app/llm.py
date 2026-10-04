"""Optional Ollama integration. The LLM only PHRASES feedback; it never decides the diagnosis.
If Ollama is not running, we fall back to the dataset's own intervention text - the demo never depends on it."""
import json
import os
import urllib.request

OLLAMA = os.environ.get("OLLAMA_URL", "http://localhost:11434")
MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2")


def available():
    try:
        urllib.request.urlopen(OLLAMA + "/api/tags", timeout=0.6)
        return True
    except Exception:
        return False


def explain(diagnosis, intervention, question_text):
    """Return (text, source). Prompt is locked to the structured diagnosis so the model cannot invent one."""
    fallback = (f"{diagnosis['evidence']} {intervention['text']}" if intervention else diagnosis["evidence"])
    if os.environ.get("RELEARN_USE_LLM", "1") != "1" or not available():
        return fallback, "dataset"
    prompt = (
        "You are a kind maths tutor for a Maharashtra SSC student (Std 9/10). Use ONLY the facts below. "
        "Do not name any other mistake. In at most 4 short sentences, explain the thinking error in simple "
        f"language and encourage the student.\nQuestion: {question_text}\nDiagnosed misconception: "
        f"{diagnosis['misconception_name']}\nEvidence: {diagnosis['evidence']}\nCorrect idea: "
        f"{diagnosis.get('correct_concept', '')}")
    try:
        req = urllib.request.Request(OLLAMA + "/api/generate", method="POST",
                                     data=json.dumps({"model": MODEL, "prompt": prompt, "stream": False}).encode(),
                                     headers={"Content-Type": "application/json"})
        out = json.loads(urllib.request.urlopen(req, timeout=25).read())["response"].strip()
        return (out or fallback), ("ollama:" + MODEL if out else "dataset")
    except Exception:
        return fallback, "dataset"
