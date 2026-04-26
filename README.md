# PawPal+ (Module 2 Project)
# PawPal+ (Modules 1–3 project)

PawPal+ began as the Module 2 pet-care scheduling project: a small Streamlit demo and a Python logic layer that models pet care tasks, schedules them against owner constraints, and explains why tasks were chosen. Its original goals were to represent tasks and owners, produce a feasible daily plan from a repository of tasks, and provide readable explanations for the generated schedule.

## Title and summary

PawPal+ — Pet care planning assistant with a small Retrieval-Augmented Explanation (RAG) feature.

PawPal+ helps busy pet owners plan daily care activities for their pets by ranking tasks by priority and preferences, avoiding blocked time windows, and producing a human-readable plan. The app now includes a simple RAG-style explainer: it looks up local pet-care guidance files and includes relevant snippets alongside the scheduler's reasoning so owners get both a schedule and short, actionable tips.

Why it matters: owners get plans they can trust and quick context-aware guidance (e.g., "meds should be given on schedule") without needing an external internet service.

## Architecture overview

High-level components (see `assets/system_diagram.svg`):

- Streamlit UI (`app.py`): accepts owner, pet, task, and constraint inputs and displays the schedule and explanation.
- PawPalAppController (`pawpal_system.PawPalAppController`): orchestrates repository, scheduler, and explainer.
- TaskRepository (`pawpal_system.TaskRepository`): in-memory store of `CareTask` objects.
- Scheduler (`pawpal_system.Scheduler`): ranks tasks, avoids blocked windows, and builds a `DailyPlan`.
- PlanExplainer (`pawpal_system.PlanExplainer`): produces textual reasons for the plan and now consults `_LocalRetriever`.
- _LocalRetriever (`pawpal_system._LocalRetriever`): simple file-based retriever that finds relevant KB lines from `assets/*.txt` by keyword overlap.
- Tests (`tests/*.py`): unit tests that validate core business rules (sorting, recurrence, conflicts, filtering).

Data flow (simplified):

1. UI gathers inputs and calls `PawPalAppController.create_daily_plan`.
2. Controller asks `TaskRepository` for tasks and sends them and the constraints to `Scheduler.build_plan`.
3. Scheduler returns a `DailyPlan` (scheduled items, totals, warnings).
4. Controller calls `PlanExplainer.generate_reasons`, which queries `_LocalRetriever` and merges retrieved KB snippets with algorithmic reasons.
5. The UI presents the plan and the RAG-augmented explanation to the user.

## Setup instructions

Prerequisites: macOS/Linux/Windows with Python 3.8+.

1. Clone the repo and enter the project directory.

```bash
git clone <your-repo-url>
cd applied-ai-system-project
```

2. Create and activate a virtual environment, then install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate   # macOS / Linux
# On Windows use: .venv\\Scripts\\activate
pip install -r requirements.txt
```

3. Run the Streamlit UI locally (optional):

```bash
streamlit run app.py
```

4. Run the test suite:

```bash
python3 -m pytest -q
```

Notes:
- The RAG retriever is file-based and requires no network access.
- A small KB file lives at `assets/pet_care_guidance.txt`; you can edit it to customize guidance.

## Sample interactions

These examples demonstrate expected inputs and resulting AI-augmented outputs. The "AI outputs" here are fragments of the explainer that include KB snippets returned by the retriever.

Example 1 — simple morning schedule

Input (via UI):
- Owner available minutes: 90
- Tasks: "Feed breakfast" (15m, high, feeding, required), "Morning walk" (30m, high, walk), "Puzzle" (20m, medium, enrichment)
- Preferred categories: enrichment

Result (summary + sample explanation):
- Schedule: Feed breakfast (07:30–07:45), Morning walk (08:00–08:30), Puzzle (08:30–08:50)
- AI output (explanation):
  - "Planned 3 tasks for 65 minutes."
  - "Remaining capacity: 25 minutes."
  - "Relevant guidance from local knowledge:"  
    - "Feed your pet at consistent times."  ← (retrieved from `assets/pet_care_guidance.txt`)
  - "07:30-07:45: Feed breakfast (priority=high, required task, must-include category)"

Example 2 — blocked time window handling

Input:
- Owner available minutes: 60
- Blocked window: 12:00–13:00
- Tasks: "Midday puzzle" (20m, medium, enrichment), "Afternoon walk" (30m, high, walk)

Result:
- Scheduler avoids 12:00–13:00 and schedules the puzzle at 13:00 if needed.
- AI output (explanation):
  - "Preferred categories considered: enrichment."
  - "Relevant guidance from local knowledge:"  
    - "Short, frequent walks are better than one long walk for many dogs."
  - "13:00-13:20: Midday puzzle (priority=medium, optional task, owner-preferred category)"

Example 3 — missing must-include category

Input:
- must_include_categories: ['meds']
- No task matching 'meds' in repository

Result:
- Scheduler schedules nothing for meds; PlanExplainer will list skipped/remaining reasons and retriever may return medication guidance if present in KB.
- AI output example:
  - "Planned 0 tasks for 0 minutes."
  - "Remaining capacity: 60 minutes."
  - "Relevant guidance from local knowledge:"  
    - "Medication should be given on schedule; set reminders for time-sensitive meds."

## Design decisions & trade-offs

- Retrieval approach: I implemented a small file-based retriever that uses keyword overlap to score and return local snippets. Trade-offs:
  - Pros: deterministic, fast, reproducible, requires no API keys or external services.
  - Cons: limited semantic understanding compared to vector embeddings + neural reranking; may miss paraphrased matches.

- RAG integration point: PlanExplainer only augments explanations and does not influence scheduling decisions. This keeps core logic fully testable and pure while still giving helpful contextual guidance.

- No external AI dependencies: to keep the project portable and runnable in restricted environments (CI, offline demos), no cloud NLP APIs are used. This limits sophistication but increases reproducibility.

- Simplicity over complexity: the scheduler uses a greedy allocator with a scoring function; it avoids over-engineering and stays easy to reason about and test.

## Testing summary

What I tested:
- Sorting (chronological ordering including midnight boundary)
- Recurrence (completing daily tasks clones a new task for the next day)
- Conflict detection (pairwise overlap warnings)
- Retriever unit tests: ensure KB snippets are found for matching terms and return empty for no match.

What worked:
- Core scheduler & repository logic is well-covered by unit tests and is stable.
- Retriever tests pass locally in the repo (they use temporary asset directories).

What didn't work in the hosted attempt:
- Converting the SVG to PNG in this execution environment failed because the native `cairo` library was unavailable. This is a system-level dependency; I documented how to convert locally using Homebrew + rsvg-convert or by installing Cairo and `cairosvg`.

What I learned:
- Keep retrieval logic simple and testable; using local files reduces flakes and privacy concerns.
- Decouple explanation (RAG) from planning so tests for scheduling remain deterministic.

## Reflection

This project reinforced practical engineering trade-offs when integrating AI: you can add useful AI-like features (RAG, context-aware guidance) without depending on expensive or opaque services. The most valuable parts are the clear data contracts (CareTask, DailyPlan) and thorough tests that make iterating on the scheduler low-risk. Future steps would be to add embedding-based retrieval, richer natural-language explanations, and an E2E test for the Streamlit UI.

---

If you'd like, I can now:
- Add a PNG version of the system diagram (I can convert it locally if you run the supplied Homebrew commands),
- Add tests for PlanExplainer to assert that KB snippets appear for certain plans, or
- Create a short walkthrough video script showing the Streamlit UI interactions.

Which should I do next?
