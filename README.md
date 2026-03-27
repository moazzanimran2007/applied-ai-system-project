# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.

## Testing PawPal+

### Running the test suite

```bash
python3 -m pytest          # run all 34 tests
python3 -m pytest -v       # verbose output with test names
python3 -m pytest tests/test_suite.py -v   # run only the main suite
```

### What the tests cover

The automated suite (`tests/`) is organized into five files and covers the most
critical scheduling behaviors:

| File | What it verifies |
|---|---|
| `test_suite.py` | **Core suite** — sorting correctness, recurrence logic, conflict detection |
| `test_scheduler.py` | Daily time-limit enforcement, blocked-window avoidance, priority ranking |
| `test_recurrence.py` | Daily & weekly re-scheduling, one-off tasks, missing-ID error |
| `test_conflicts.py` | Overlap detection for same/different pets, warning message formatting |
| `test_sort_filter.py` | Chronological sort, completion-status and pet-name filtering |
| `test_pawpal.py` | `CareTask.mark_complete`, `Pet.add_task` / `task_count` |

**Key behaviors verified:**

- **Sorting Correctness** — `Scheduler.sort_by_time` returns tasks in strict
  `HH:MM` ascending order including midnight-boundary and tie cases.
- **Recurrence Logic** — Completing a `frequency="daily"` task creates a new
  task due exactly one day later with a fresh ID and `is_complete=False`;
  `frequency="once"` tasks produce no successor.
- **Conflict Detection** — `Scheduler.find_time_conflicts` returns one warning
  per overlapping pair (exact duplicates, partial overlaps) and zero warnings
  for adjacent or separated slots.

### Confidence Level

⭐⭐⭐⭐☆ **4 / 5 stars**

All 34 automated tests pass (0 failures, 0 errors). The suite covers the
scheduler's critical paths — time ordering, recurrence, and conflict detection —
as well as edge cases like midnight boundaries, one-off tasks, and C(n,2)
pairwise overlap counts. One star is held back because the Streamlit UI layer
(`app.py`) is not covered by automated tests and would require integration or
end-to-end testing for full confidence.
