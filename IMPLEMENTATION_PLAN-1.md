# Implementation Plan — GradeMind AI

Companion to `GradeMind_AI_PRD.md` and `GradeMind_AI_Design_Doc.md`. This is the execution schedule — if a decision needs justifying, it's in those two docs, not repeated here.

**Team:** Yogita (AI + Backend), Garima (Frontend + Product, co-owns AI contract), Komal (Docs + QA)

---

## Week 1 — Requirements, Schema, Setup

**Owner:** Whole team

- [ ] Finalize GitHub repo structure, branch strategy, PR review rule (at least one other person approves before merge to `main`)
- [ ] Lock the SQLite schema from Design Doc §2 (students / subjects / results / attendance / targets)
- [ ] Confirm the actual grade-boundary scale to use (the prototype's `GRADE_BOUNDARIES` in `analysis.py` is a placeholder — replace with the real rubric)
- [ ] Confirm subject-weighting rule: are all subjects weighted equally, or by credit hours? (`analysis.py`'s `overall_percent()` currently assumes equal weighting — flagged in its own docstring as a decision this project hasn't made yet)
- [ ] Each team member: clone repo, run the prototype `app.py` locally, confirm it works before Week 2 starts

**Exit criteria:** everyone has the repo running locally; schema and grading rules are written down, not just assumed.

---

## Week 2 — Marks Calculator + Validation

**Owner:** Yogita (engine), Garima (input UI)

- [ ] Add real input validation to `app.py` / a new `validators.py` (PRD §4.1 — **not optional**, must exist before this week is called done):
  - marks_obtained ≤ max_marks
  - no negative values
  - at least 1 subject required
  - reject non-numeric input with an inline error, not a silent zero
- [ ] Replace `analysis.py`'s placeholder `GRADE_BOUNDARIES` with the real scale from Week 1
- [ ] Resolve the subject-weighting decision from Week 1 in `overall_percent()` if it's not equal weighting
- [ ] Frontend: basic subject-entry form (add/remove subject rows) wired to `/api/results`

**Exit criteria:** submitting bad input (blank field, mark > max, non-numeric) produces a visible error, not a crash or silent bad calculation. This is the demo-breaking failure mode identified in the PRD — test it explicitly, don't assume it works.

---

## Week 3 — Flask Backend + SQLite

**Owner:** Yogita

- [ ] Replace `app.py`'s in-memory `STUDENT_DATA` dict with real SQLite reads/writes against the Week 1 schema
- [ ] Add a `seed.py` script so any team member can generate consistent sample data for testing (Tech Stack §5)
- [ ] Add `.gitignore` entry for the local `.db` file — never commit real or test student data
- [ ] Trend calculation (`compute_trend()` in `analysis.py`) — already implemented in the prototype; verify it against real stored current+prior result sets instead of the prototype's hardcoded smoke-test data

**Exit criteria:** data survives a server restart. Trend comparison works against two real stored result sets, not just the `if __name__ == "__main__"` smoke test.

---

## Week 4 — Dashboard + Charts + Attendance Correlation

**Owner:** Garima (dashboard/charts), Yogita (attendance logic)

- [ ] Build the dashboard UI per Design Doc §5 (overall %, grade, strongest/weakest, trend chart via Chart.js, subject bars)
- [ ] Wire dashboard to `/api/dashboard`
- [ ] Implement attendance-correlation flagging (PRD §4.5): flag subjects where attendance dropped and performance also declined in the same period. Word it as a correlation, not causation, in the UI copy.
- [ ] **Explicit checkpoint:** if attendance correlation isn't working cleanly by end of Week 4, cut it per PRD §4.5 — do not carry it half-built into Week 5. The dashboard and AI payload must not assume `attendance_flag` is populated if this is cut (the prototype already defaults it to `None`, so cutting it is a no-op change, not a refactor).

**Exit criteria:** dashboard renders real stored data correctly; a go/no-go call has been made on attendance correlation, not left ambiguous.

---

## Week 5 — Target Calculator + What-If + AI Backend Selection

**Owner:** Yogita (calculation + AI setup), Garima (UI panel, joint on AI JSON contract)

- [ ] Build the Target Calculator / What-If UI panel as **one shared panel**, calling `/api/target` and `/api/whatif` — both already implemented in the prototype against the shared `recompute_overall()` function. Do not let this become two separate code paths (Design Doc §4 is explicit about this).
- [ ] **Model hardware test (do this early in the week, not late):** pull Phi-3 mini via Ollama on the actual laptop that will run the live demo. Run the exact prompt template from Design Doc §3.2 against real sample data. Time the response — target under ~5 seconds.
  - If any team laptop has more RAM/a GPU, also test Llama 3 8B / Mistral 7B there for comparison (Tech Stack §3).
  - If even Phi-3 mini is too slow on demo hardware, decide now whether to run inference on a better teammate machine over local network during the demo (Tech Stack §3) — this is a Week 5 decision, not a Week 8 scramble.
- [ ] Implement `get_ai_response(payload, backend="ollama")` per Design Doc §3.5 — Ollama path only this week; Gemini path is Week 6.

**Exit criteria:** target/what-if panel works end-to-end against real data. A model has been chosen and timed on real demo hardware, with a documented fallback if it's too slow.

---

## Week 6 — AI Advisor Integration + Validation Layer

**Owner:** Yogita (integration), Garima (joint — validation logic, since she co-owns the JSON contract per Design Doc §6)

- [ ] Replace `app.py`'s `/api/advisor` stub with a real call to `get_ai_response()`
- [ ] Implement the Design Doc §3.3 post-response validation: does the AI's named "Priority" subject actually exist in the payload? Does "Reason" cite a real number from the payload? If either check fails, fall back to the templated Python sentence (already written in the current `/api/advisor` stub — reuse it as the fallback, don't rewrite it).
- [ ] Add the optional Gemini backend path behind the same `get_ai_response()` interface (Design Doc §3.5) — confirm automatic fallback to Ollama works if Gemini is unreachable
- [ ] **Test all four edge cases from Design Doc §3.4 explicitly, before marking this integration done:**
  - No weak subject (all subjects above 80%)
  - Student already at/above target
  - Only one subject entered
  - Two subjects tied for weakest (confirm deterministic tie-break, e.g., alphabetical)

**Exit criteria:** all four edge cases produce a sensible response (real AI or fallback) with no crash and no contradiction of the dashboard numbers.

---

## Week 7 — Study Plan, Report Export, Integration Pass

**Owner:** Garima (UI), Yogita (study plan generation logic), Komal (test cases)

- [ ] Implement the Study Plan feature (PRD §4.6): AI generates a day-by-day time allocation from the weak-subject list + target + available study minutes — reuses the same AI backend and validation layer, not a new pipeline
- [ ] Implement "Export Report" as a button on the existing dashboard (PRD §4.7) — formats already-computed data, does **not** get its own generation pipeline
- [ ] Full integration pass: every screen talks to real backend + real (or fallback) AI, no more prototype/stub code paths left in the app
- [ ] Komal: write test cases covering the 3 bad-input scenarios from PRD §7 success criteria, plus the 4 AI edge cases from Week 6

**Exit criteria:** a full run-through (enter marks → view dashboard → set target → ask advisor → generate study plan → export report) works without hitting any remaining stub or placeholder.

---

## Week 8 — Final Testing, Documentation, Demo Prep

**Owner:** Whole team, Komal leads QA

- [ ] Run the full PRD §7 success criteria list end-to-end and confirm each one passes
- [ ] Rehearse the live demo **offline** (disable Wi-Fi) to confirm the Ollama-only path works with no network dependency — this is the scenario the whole architecture was built to survive
- [ ] Finalize documentation, README, and presentation material
- [ ] Bug bash: deliberately try to break the app with bad input, rapid clicking, empty states — fix what's found, log what isn't fixed with a known-issues note rather than leaving it undocumented

**Exit criteria:** the app survives an offline demo rehearsal without the AI Advisor going blank or contradicting the dashboard.

---

## Cross-cutting rules that apply every week

- **The LLM never calculates.** If any code change has the LLM producing a number that isn't in the JSON payload it was given, that's a bug, not a feature — see Design Doc §1 and §3.
- **What-if and target-gap logic live in one function** (`recompute_overall` in `analysis.py`). If you find yourself writing a second version of this math anywhere, stop and reuse the existing function instead.
- **Anything cut (attendance correlation, standalone what-if, standalone AI report) stays cut.** These were removed from scope for reasons documented in the PRD — don't reintroduce them mid-project without updating the PRD first.
