# GradeMind AI

**An AI-powered student performance intelligence platform** — not a marks calculator with a chatbot bolted on. GradeMind converts raw marks, attendance, and target grades into trend analysis, gap calculations, and a personalized weekly study plan.

Built as an 8-week college project by Yogita Singh, Garima Mishra, and Komal.

---

## What this actually does

Students normally just see percentages. GradeMind answers the questions the percentage doesn't:

- Which subjects are dragging performance down
- Whether a subject is improving or declining
- How many marks are needed, per subject, to hit a target grade
- What a hypothetical score change ("what if I get 70 in Maths?") does to the overall
- What to study first, and how much time to give it

See [`GradeMind_AI_PRD.md`](./GradeMind_AI_PRD.md) for the full requirements and the reasoning behind every scope decision.

---

## Repository contents

| File | What it is |
|---|---|
| `GradeMind_AI_PRD.md` | Product requirements — problem statement, features, scope cuts, success criteria |
| `GradeMind_AI_Design_Doc.md` | System architecture, data model, the AI safety contract, team risk mitigation |
| `GradeMind_AI_Tech_Stack.md` | Stack choices and the reasoning for each (Flask vs FastAPI, Ollama model choice, etc.) |
| `IMPLEMENTATION_PLAN.md` | Week-by-week build plan mapped to owners and deliverables |
| `analysis.py` | **Prototype.** Deterministic calculation engine — percentages, grades, trends, target gaps, what-if. Zero AI involvement, by design. |
| `app.py` | **Prototype.** Flask routes wiring `analysis.py` to HTTP endpoints. In-memory storage only; no DB yet. |

**Prototype status:** `analysis.py` and `app.py` are working prototypes, not final code. No input validation, no SQLite persistence, no real AI call yet — see the docstrings at the top of each file for exactly what's stubbed and why. Do not treat a clean prototype run as "the feature is done" — check the file's own docstring and the Implementation Plan for what's still outstanding.

---

## The one architectural rule that matters most

**The AI never does arithmetic.** Every number the AI Advisor talks about is computed by `analysis.py` first and handed to the LLM as structured JSON — the LLM only interprets and recommends. This is what stops the AI from contradicting the dashboard during a live demo. Full detail in Design Doc §3.

---

## Running the prototype locally

```bash
pip install flask
python app.py
# server starts on http://127.0.0.1:5000
```

Try it:

```bash
curl -X POST http://127.0.0.1:5000/api/results \
  -H "Content-Type: application/json" \
  -d '{"current": [{"name": "Mathematics", "marks_obtained": 48, "max_marks": 100}]}'

curl http://127.0.0.1:5000/api/dashboard
```

---

## Stack

Python + Flask, SQLite, Bootstrap + Chart.js, Ollama (Phi-3 mini default) with an optional Gemini fallback path. ₹0 budget, must run fully offline at demo time. Full reasoning in `GradeMind_AI_Tech_Stack.md`.

---

## Team

| Person | Role |
|---|---|
| Yogita Singh | AI + Backend Lead |
| Garima Mishra | Frontend + Product Lead (also co-owns the AI JSON contract — see Design Doc §6 for why) |
| Komal | Documentation + QA |
