"""
app.py — GradeMind AI: Flask Backend (PROTOTYPE)

Status: Prototype / Week 2-3 scope. NOT final.

Purpose
-------
Thin HTTP layer over analysis.py. Every route here is a wrapper that:
  1. reads request JSON,
  2. builds SubjectResult objects,
  3. calls into analysis.py (never re-implements calculation logic here —
     Design Doc §1's hard rule "Python does math" applies to this file too,
     meaning app.py should only ORCHESTRATE analysis.py, not duplicate it),
  4. returns JSON.

What's intentionally NOT here yet (later weeks)
-------------------------------------------------
- SQLite persistence — this prototype holds one student's data in an
  in-memory dict (STUDENT_DATA) that resets on server restart. Week 3
  swaps this for real reads/writes against the schema in Design Doc §2.
- Input validation middleware (PRD §4.1) — routes currently trust the
  request shape. Do not treat this prototype's lack of validation as
  acceptable for the real Week 2 deliverable; validation is required
  there, not optional polish.
- /api/advisor (the AI endpoint) — intentionally stubbed to return the
  analysis payload with a placeholder message instead of calling
  get_ai_response(), since that function doesn't exist until the Ollama/
  Gemini integration lands (Design Doc §3.5, Week 5-6). Wiring the real
  AI call into an already-defined route is a small change when that
  work starts; the payload shape will not need to change.
- CORS config, auth, error-handling middleware — not needed for local
  prototype testing.

Run locally
-----------
    pip install flask
    python app.py
    # server on http://127.0.0.1:5000
"""

from flask import Flask, jsonify, request

from analysis import (
    SubjectResult,
    build_ai_payload,
    overall_percent,
    recompute_overall,
    target_gaps,
)

app = Flask(__name__)

# ---------------------------------------------------------------------------
# In-memory store (PROTOTYPE ONLY — replaced by SQLite in Week 3,
# Design Doc §2 schema: students / subjects / results / attendance / targets)
# ---------------------------------------------------------------------------

STUDENT_DATA = {
    "current_results": [],   # list[SubjectResult]
    "prior_results": [],     # list[SubjectResult]
    "target_percent": None,
}


def _parse_results(raw: list[dict], exam_label: str = "current") -> list[SubjectResult]:
    """
    raw: [{"name": str, "marks_obtained": float, "max_marks": float}, ...]
    No validation here yet — see module docstring. Real Week 2 code needs
    to reject non-numeric / out-of-range values before they reach this
    point (PRD §4.1), not silently coerce or crash.
    """
    return [
        SubjectResult(
            name=item["name"],
            marks_obtained=float(item["marks_obtained"]),
            max_marks=float(item["max_marks"]),
            exam_label=exam_label,
        )
        for item in raw
    ]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/api/health", methods=["GET"])
def health():
    """Basic liveness check — useful for confirming the server + venue
    setup works before a demo, independent of any feature logic."""
    return jsonify({"status": "ok"})


@app.route("/api/results", methods=["POST"])
def submit_results():
    """
    Accepts the student's current marks (and optionally a prior result
    set for trend comparison) and stores them in memory.

    Expected body:
    {
      "current": [{"name": "Mathematics", "marks_obtained": 48, "max_marks": 100}, ...],
      "prior": [{"name": "Mathematics", "marks_obtained": 50, "max_marks": 100}, ...]  # optional
    }
    """
    data = request.get_json(force=True)

    if not data or "current" not in data or not data["current"]:
        # PRD §4.1: "at least 1 subject required" — this is the minimum
        # check; full validation (marks <= max, non-negative, numeric)
        # still needs to be added here for the real Week 2 deliverable.
        return jsonify({"error": "At least one subject is required"}), 400

    STUDENT_DATA["current_results"] = _parse_results(data["current"], exam_label="current")
    STUDENT_DATA["prior_results"] = (
        _parse_results(data["prior"], exam_label="prior") if data.get("prior") else []
    )

    return jsonify({"status": "stored", "count": len(STUDENT_DATA["current_results"])})


@app.route("/api/dashboard", methods=["GET"])
def dashboard():
    """
    Returns the full computed payload for the dashboard (Design Doc §5),
    built by analysis.py — this route does not calculate anything itself.
    """
    current = STUDENT_DATA["current_results"]
    if not current:
        return jsonify({"error": "No results submitted yet"}), 400

    payload = build_ai_payload(
        current_results=current,
        prior_results=STUDENT_DATA["prior_results"],
        target_percent=STUDENT_DATA["target_percent"],
    )
    return jsonify(payload)


@app.route("/api/target", methods=["POST"])
def set_target():
    """
    Sets the target overall percentage and returns the per-subject gaps.
    Body: {"target_percent": 80}
    """
    data = request.get_json(force=True)
    if not data or "target_percent" not in data:
        return jsonify({"error": "target_percent is required"}), 400

    current = STUDENT_DATA["current_results"]
    if not current:
        return jsonify({"error": "No results submitted yet"}), 400

    target = float(data["target_percent"])
    STUDENT_DATA["target_percent"] = target

    return jsonify({
        "target_percent": target,
        "current_overall": overall_percent(current),
        "gaps": target_gaps(current, target),
    })


@app.route("/api/whatif", methods=["POST"])
def what_if():
    """
    Design Doc §4: same underlying function as the target calculator
    (recompute_overall), exposed as a separate endpoint for the What-If
    UI panel. Do NOT reimplement this calculation here — it must call
    the shared function in analysis.py.

    Body: {"hypothetical": {"Mathematics": 70}}
    """
    data = request.get_json(force=True)
    if not data or "hypothetical" not in data:
        return jsonify({"error": "hypothetical is required"}), 400

    current = STUDENT_DATA["current_results"]
    if not current:
        return jsonify({"error": "No results submitted yet"}), 400

    hypothetical = {k: float(v) for k, v in data["hypothetical"].items()}
    new_overall = recompute_overall(current, hypothetical)
    current_overall = overall_percent(current)

    return jsonify({
        "current_overall": current_overall,
        "new_overall": new_overall,
        "delta": round(new_overall - current_overall, 2),
    })


@app.route("/api/advisor", methods=["POST"])
def advisor():
    """
    STUB — Design Doc §3.5's get_ai_response() is not implemented yet
    (Ollama/Gemini integration is Week 5-6 scope). This route returns
    the same structured payload the AI would receive, plus a placeholder
    message, so the frontend can be built against a stable response
    shape now rather than waiting on the AI layer.

    Real implementation later: call get_ai_response(payload, backend=...)
    per Design Doc §3.2 (prompt template) and §3.3 (validate the response
    before returning it — never pass an unvalidated AI response straight
    through to the frontend).
    """
    current = STUDENT_DATA["current_results"]
    if not current:
        return jsonify({"error": "No results submitted yet"}), 400

    payload = build_ai_payload(
        current_results=current,
        prior_results=STUDENT_DATA["prior_results"],
        target_percent=STUDENT_DATA["target_percent"],
    )

    return jsonify({
        "payload_sent_to_ai": payload,
        "priority": payload["weakest_subject"],
        "reason": f"AI integration not yet wired — this is the Python "
                  f"fallback sentence per Design Doc §3.3. "
                  f"{payload['weakest_subject']} is at "
                  f"{next(s['percent'] for s in payload['subjects'] if s['name'] == payload['weakest_subject'])}%.",
        "action": "Prioritize this subject this week.",
    })


if __name__ == "__main__":
    app.run(debug=True)
