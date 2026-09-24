"""
analysis.py — GradeMind AI: Deterministic Analysis Engine (PROTOTYPE)

Status: Prototype / Week 2-3 scope. NOT final.

Purpose
-------
This module is the "Python Analysis Layer" described in Design Doc §1 and §3.
It performs every calculation the system needs — percentages, grades, trends,
target gaps, and what-if recomputation — with zero AI involvement. Per the
hard architectural rule in Design Doc §1 and §3.5, the LLM is NEVER allowed
to do arithmetic; it only ever receives the JSON output of this module.

What's intentionally NOT here yet (later weeks / other files)
---------------------------------------------------------------
- SQLite persistence (Week 3 — this prototype uses in-memory dicts/lists)
- Flask routes (see app.py)
- The LLM call itself (get_ai_response — Week 5-6, Design Doc §3.5)
- Attendance-correlation flagging (Design Doc §3.1 field `attendance_flag`
  is stubbed as None here; real logic is PRD §4.5, first thing cut if
  the team falls behind schedule)

Known simplifications in this prototype
----------------------------------------
- No input validation yet (PRD §4.1 requires it before Week 2 is "done" —
  this file only contains the calculation logic; validation belongs in
  app.py's request handling, or a dedicated validators.py later)
- Grade boundaries below are a placeholder scale — swap for whatever
  scale the college/hackathon rubric actually uses
"""

from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class SubjectResult:
    """One subject's marks for one exam_label ('midterm', 'final', etc.)."""
    name: str
    marks_obtained: float
    max_marks: float
    exam_label: str = "current"
    attendance_percent: Optional[float] = None


@dataclass
class SubjectAnalysis:
    """Computed output for a single subject — this is what gets serialized
    into the AI JSON contract (Design Doc §3.1)."""
    name: str
    percent: float
    trend: Optional[float] = None          # percentage-point delta vs prior, if available
    attendance_flag: Optional[str] = None  # PRD §4.5 — stub for now


# ---------------------------------------------------------------------------
# Grade scale (PLACEHOLDER — replace with actual rubric)
# ---------------------------------------------------------------------------

GRADE_BOUNDARIES = [
    (90, "A"),
    (80, "B+"),
    (70, "B"),
    (60, "C"),
    (50, "D"),
    (0, "F"),
]


def percent_to_grade(percent: float) -> str:
    for boundary, grade in GRADE_BOUNDARIES:
        if percent >= boundary:
            return grade
    return "F"


# ---------------------------------------------------------------------------
# Core calculations
# ---------------------------------------------------------------------------

def subject_percent(result: SubjectResult) -> float:
    """Single-subject percentage. Guards against divide-by-zero on bad data —
    real validation should prevent max_marks <= 0 from ever reaching here,
    but this is a safety net, not a substitute for that validation."""
    if result.max_marks <= 0:
        return 0.0
    return round((result.marks_obtained / result.max_marks) * 100, 2)


def overall_percent(results: list[SubjectResult]) -> float:
    """Simple average of subject percentages.
    NOTE: this assumes equal weighting across subjects. If the real
    grading scheme weights subjects differently (credit hours, etc.),
    this function is where that weighting gets added — flag for Week 2
    requirements discussion, not decided here."""
    if not results:
        return 0.0
    percents = [subject_percent(r) for r in results]
    return round(sum(percents) / len(percents), 2)


def compute_trend(current: list[SubjectResult], prior: list[SubjectResult]) -> dict[str, float]:
    """Per-subject percentage-point delta between two result sets.
    Matches by subject name. Subjects present in `current` but not `prior`
    are returned with trend=None (Design Doc §3.4 edge case: 'no comparison
    available' rather than a fabricated trend)."""
    prior_by_name = {r.name: subject_percent(r) for r in prior}
    trends = {}
    for r in current:
        cur_pct = subject_percent(r)
        if r.name in prior_by_name:
            trends[r.name] = round(cur_pct - prior_by_name[r.name], 2)
        else:
            trends[r.name] = None
    return trends


def recompute_overall(current_results: list[SubjectResult], hypothetical: dict[str, float]) -> float:
    """
    Design Doc §4 — the single shared function behind BOTH the Target
    Calculator and the What-If UI. Do not fork this into two implementations.

    hypothetical: {subject_name: new_marks_obtained} — overrides for the
    subjects being changed. Subjects not in this dict keep their current
    marks_obtained. max_marks is unchanged.
    """
    updated = []
    for r in current_results:
        if r.name in hypothetical:
            updated.append(SubjectResult(
                name=r.name,
                marks_obtained=hypothetical[r.name],
                max_marks=r.max_marks,
                exam_label=r.exam_label,
            ))
        else:
            updated.append(r)
    return overall_percent(updated)


def target_gaps(current_results: list[SubjectResult], target_percent: float) -> list[dict]:
    """
    Naive equal-effort distribution: how many more marks each subject needs
    if the shortfall were spread evenly. This is a starting heuristic, not
    a claimed-optimal solution — PRD doesn't specify an optimization
    strategy, so this is the simplest defensible one for a prototype.

    Returns list of {name, points_needed} for subjects below their
    proportional share of the target. Subjects already meeting/exceeding
    target are omitted (Design Doc §3.4: don't manufacture a gap that
    doesn't exist).
    """
    current_overall = overall_percent(current_results)
    if current_overall >= target_percent:
        return []  # already at or above target — nothing to report

    gaps = []
    for r in current_results:
        cur_pct = subject_percent(r)
        if cur_pct < target_percent:
            gaps.append({
                "name": r.name,
                "points_needed": round(target_percent - cur_pct, 2),
            })
    return gaps


# ---------------------------------------------------------------------------
# Top-level: build the structured payload for the AI layer
# ---------------------------------------------------------------------------

def build_ai_payload(
    current_results: list[SubjectResult],
    prior_results: Optional[list[SubjectResult]] = None,
    target_percent: Optional[float] = None,
) -> dict:
    """
    Assembles exactly the JSON shape specified in Design Doc §3.1.
    This is the ONLY object that should ever be passed to get_ai_response()
    (Design Doc §3.5) — the LLM must never see raw SubjectResult data.
    """
    prior_results = prior_results or []
    trends = compute_trend(current_results, prior_results) if prior_results else {}

    subjects = []
    for r in current_results:
        subjects.append({
            "name": r.name,
            "percent": subject_percent(r),
            "trend": trends.get(r.name),
            "attendance_flag": None,  # PRD §4.5 stub — real logic not in this prototype
        })

    if subjects:
        weakest = min(subjects, key=lambda s: s["percent"])["name"]
        strongest = max(subjects, key=lambda s: s["percent"])["name"]
    else:
        weakest = strongest = None

    payload = {
        "overall_percent": overall_percent(current_results),
        "grade": percent_to_grade(overall_percent(current_results)),
        "subjects": subjects,
        "weakest_subject": weakest,
        "strongest_subject": strongest,
    }

    if target_percent is not None:
        payload["target_percent"] = target_percent
        payload["target_gaps"] = target_gaps(current_results, target_percent)

    return payload


# ---------------------------------------------------------------------------
# Manual smoke test — run this file directly to sanity-check the logic
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    current = [
        SubjectResult("Mathematics", 48, 100),
        SubjectResult("Physics", 67, 100),
        SubjectResult("Chemistry", 74, 100),
        SubjectResult("Programming", 91, 100),
    ]
    prior = [
        SubjectResult("Mathematics", 50, 100, exam_label="midterm"),
        SubjectResult("Physics", 69, 100, exam_label="midterm"),
    ]

    payload = build_ai_payload(current, prior, target_percent=80)
    import json
    print(json.dumps(payload, indent=2))

    print("\nWhat-if: Mathematics -> 70")
    print("New overall:", recompute_overall(current, {"Mathematics": 70}))
