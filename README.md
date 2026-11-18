# PawPal+

A pet-care planner that builds a daily schedule around an owner's free time and explains each choice, with short care tips pulled from a local knowledge base.

Built as a course project across three modules: it started from a provided starter app, and the scheduling engine, tests and retrieval-based explanations were added on top.

## What it does

- **Plans the day.** You enter how much time you have, any blocked time windows, and the pet's care tasks (each with a duration, priority and category such as feeding, walks, meds or enrichment). PawPal+ ranks the tasks and fits them into the time you have.
- **Respects constraints.** It works around blocked windows, puts required tasks and must-include categories first, and gives a boost to categories you prefer.
- **Handles recurring tasks.** Completing a daily task creates the next day's copy.
- **Warns about clashes.** It flags tasks whose times overlap.
- **Explains itself.** Every plan comes with plain-language reasons ("priority high, required task") and remaining time.
- **Adds care tips.** A small retriever looks up matching guidance in `assets/pet_care_guidance.txt` and adds it to the explanation.

## Example

Input: 90 free minutes; tasks "Feed breakfast" (15 min, high priority, required), "Morning walk" (30 min, high) and "Puzzle" (20 min, medium, enrichment); enrichment preferred.

Output from the explainer:

```
Planned 3 tasks for 65 minutes.
Remaining capacity: 25 minutes.
Preferred categories considered: enrichment.
Relevant guidance from local knowledge:
- - Short, frequent walks are better than one long walk for many dogs.
- - Cats benefit from environmental enrichment like puzzle feeders and vertical spaces.
- - Owners often prefer walks and feeding to happen early or late in the day depending on work schedules.
08:00-08:15: Feed breakfast (priority=high, required task)
08:15-08:45: Morning walk (priority=high, optional task)
08:45-09:05: Puzzle (priority=medium, optional task, owner-preferred category)
```

## Run it

You need Python 3.9 or newer.

```bash
git clone https://github.com/moazzanimran2007/applied-ai-system-project.git
cd applied-ai-system-project
python3 -m venv .venv
source .venv/bin/activate        # on Windows: .venv\Scripts\activate
pip install -r requirements.txt

streamlit run app.py             # the web app
python3 main.py                  # a quick run in the terminal
python3 -m pytest -q             # the tests
```

## Tests

37 tests cover sorting (including times that cross midnight), recurrence, conflict detection, filtering, the scheduler and the retriever. All 37 pass.

## How it's built

| Part | Role |
| :--- | :--- |
| `app.py` | Streamlit interface for owner, pet, tasks and constraints |
| `PawPalAppController` | Connects the task store, scheduler and explainer |
| `TaskRepository` | Stores care tasks in memory |
| `Scheduler` | Ranks tasks, avoids blocked windows and builds the daily plan |
| `PlanExplainer` | Writes the reasons for the plan and adds retrieved tips |
| `_LocalRetriever` | Finds relevant lines in the local knowledge base by keyword overlap |

All of these except `app.py` live in `pawpal_system.py`. The system diagram is in `assets/system_diagram.svg`, and `reflection.md` covers the design process.

## Design choices

- **Simple, local retrieval.** Keyword matching on a text file is fast, repeatable and needs no API keys or network, at the cost of missing reworded matches that embeddings would catch.
- **Tips don't change the plan.** Retrieval only adds to the explanation, so the scheduling logic stays deterministic and easy to test.
- **A greedy scheduler.** Tasks are scored and placed in order, which keeps the logic easy to follow and test.

## Next steps

- Embedding-based retrieval for better matching
- An end-to-end test for the Streamlit interface
