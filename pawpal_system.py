from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any
import uuid
import logging


PRIORITY_SCORES = {"low": 1, "medium": 2, "high": 3}


def _time_to_minutes(value: str) -> int:
    """Convert an HH:MM string to minutes since midnight."""
    hours, minutes = value.split(":")
    return int(hours) * 60 + int(minutes)


def _minutes_to_time(total_minutes: int) -> str:
    """Format minutes since midnight as an HH:MM string."""
    total_minutes = total_minutes % (24 * 60)
    return f"{total_minutes // 60:02d}:{total_minutes % 60:02d}"


@dataclass
class Owner:
    owner_id: str
    name: str
    available_minutes_per_day: int
    preferences: dict[str, Any] = field(default_factory=dict)

    def update_preferences(self, preferences: dict[str, Any]) -> None:
        """Merge new keys into the owner's preference mapping."""
        self.preferences.update(preferences)


@dataclass
class Pet:
    pet_id: str
    name: str
    species: str
    age_years: float = 0.0
    special_needs: list[str] = field(default_factory=list)
    tasks: list["CareTask"] = field(default_factory=list)

    def add_special_need(self, need: str) -> None:
        """Record a unique special need for this pet if non-empty."""
        cleaned = need.strip()
        if cleaned and cleaned not in self.special_needs:
            self.special_needs.append(cleaned)

    def add_task(self, task: "CareTask") -> None:
        """Append a care task to this pet's task list."""
        self.tasks.append(task)

    @property
    def task_count(self) -> int:
        """Return how many tasks are assigned to this pet."""
        return len(self.tasks)


@dataclass
class CareTask:
    task_id: str
    title: str
    category: str
    duration_minutes: int
    priority: str
    frequency: str = "daily"
    is_required: bool = False
    notes: str = ""
    is_complete: bool = False
    time: str = "09:00"
    pet_name: str = ""
    due_date: date = field(default_factory=date.today)

    def estimate_effort_score(self) -> float:
        """Return a rough scheduling weight from priority, required flag, and duration."""
        base = PRIORITY_SCORES.get(self.priority, 1) * 10
        required_bonus = 20 if self.is_required else 0
        return max(0.0, base + required_bonus - (self.duration_minutes * 0.1))

    def is_valid(self) -> bool:
        """Return True if title, duration, and priority are usable for scheduling."""
        return bool(self.title.strip()) and self.duration_minutes > 0 and self.priority in PRIORITY_SCORES

    def mark_complete(self) -> None:
        """Mark this task as finished."""
        self.is_complete = True

    def next_occurrence_after(self, completed_on: date) -> CareTask | None:
        """If frequency is daily or weekly, return a new open task due after ``completed_on`` using timedelta; else None."""
        if self.frequency == "daily":
            delta = timedelta(days=1)
        elif self.frequency == "weekly":
            delta = timedelta(days=7)
        else:
            return None
        next_due = completed_on + delta
        return CareTask(
            task_id=str(uuid.uuid4()),
            title=self.title,
            category=self.category,
            duration_minutes=self.duration_minutes,
            priority=self.priority,
            frequency=self.frequency,
            is_required=self.is_required,
            notes=self.notes,
            is_complete=False,
            time=self.time,
            pet_name=self.pet_name,
            due_date=next_due,
        )


@dataclass
class TimeWindow:
    start_time: str
    end_time: str

    def overlaps(self, other: "TimeWindow") -> bool:
        """Return True if this interval intersects another half-open [start, end) window."""
        start_a = _time_to_minutes(self.start_time)
        end_a = _time_to_minutes(self.end_time)
        start_b = _time_to_minutes(other.start_time)
        end_b = _time_to_minutes(other.end_time)
        return max(start_a, start_b) < min(end_a, end_b)


@dataclass
class ConstraintSet:
    max_daily_minutes: int
    blocked_time_windows: list[TimeWindow] = field(default_factory=list)
    must_include_categories: list[str] = field(default_factory=list)
    preferred_categories: list[str] = field(default_factory=list)

    def validate_task(self, task: CareTask) -> bool:
        """Return True if the task is well-formed and fits the daily minute budget."""
        return task.is_valid() and task.duration_minutes <= self.max_daily_minutes


@dataclass
class DailyPlanItem:
    task: CareTask
    start_time: str
    end_time: str
    reason: str

    def duration(self) -> int:
        """Return scheduled length of this slot in minutes."""
        return _time_to_minutes(self.end_time) - _time_to_minutes(self.start_time)


@dataclass
class DailyPlan:
    date: str
    items: list[DailyPlanItem] = field(default_factory=list)
    total_minutes: int = 0
    leftover_minutes: int = 0
    skipped_reasons: list[str] = field(default_factory=list)
    conflict_warnings: list[str] = field(default_factory=list)

    def add_item(self, item: DailyPlanItem) -> None:
        """Append one scheduled block to the plan."""
        self.items.append(item)

    def compute_totals(self, max_daily_minutes: int) -> None:
        """Recompute total scheduled minutes and remaining capacity for the day."""
        self.total_minutes = sum(item.duration() for item in self.items)
        self.leftover_minutes = max(0, max_daily_minutes - self.total_minutes)

    def explain(self) -> list[str]:
        """Return human-readable lines for each item plus any skip messages."""
        explanations = [f"{i.start_time}-{i.end_time}: {i.task.title} ({i.reason})" for i in self.items]
        return explanations + self.skipped_reasons + self.conflict_warnings


class Scheduler:
    def __init__(self, strategy_name: str = "priority_weighted") -> None:
        """Create a scheduler with an optional named ranking strategy label."""
        self.strategy_name = strategy_name

    def rank_tasks(self, tasks: list[CareTask], constraints: ConstraintSet) -> list[CareTask]:
        """Order tasks by priority, required flags, category rules, and duration penalty."""
        preferred = set(constraints.preferred_categories)
        required_categories = set(constraints.must_include_categories)

        def score(task: CareTask) -> float:
            priority_score = PRIORITY_SCORES[task.priority] * 10
            required_bonus = 100 if task.is_required else 0
            category_required_bonus = 40 if task.category in required_categories else 0
            preference_bonus = 8 if task.category in preferred else 0
            duration_penalty = task.duration_minutes * 0.2
            return priority_score + required_bonus + category_required_bonus + preference_bonus - duration_penalty

        return sorted(tasks, key=score, reverse=True)

    def sort_by_time(self, tasks: list[CareTask]) -> list[CareTask]:
        """Return tasks ordered by ``CareTask.time`` (HH:MM), using minutes since midnight as the sort key."""
        return sorted(tasks, key=lambda t: _time_to_minutes(t.time))

    @staticmethod
    def _plan_slots_overlap(start_a: str, end_a: str, start_b: str, end_b: str) -> bool:
        """True if two half-open [start, end) plan intervals intersect in clock time."""
        sa, ea = _time_to_minutes(start_a), _time_to_minutes(end_a)
        sb, eb = _time_to_minutes(start_b), _time_to_minutes(end_b)
        return max(sa, sb) < min(ea, eb)

    def find_time_conflicts(self, plan: DailyPlan) -> list[str]:
        """Lightweight O(n^2) overlap scan: return warning strings only (never raises)."""
        warnings: list[str] = []
        items = plan.items
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                a, b = items[i], items[j]
                if not self._plan_slots_overlap(a.start_time, a.end_time, b.start_time, b.end_time):
                    continue
                pa = a.task.pet_name.strip() or "(no pet)"
                pb = b.task.pet_name.strip() or "(no pet)"
                warnings.append(
                    f"Time overlap: '{a.task.title}' ({pa}) [{a.start_time}-{a.end_time}] vs "
                    f"'{b.task.title}' ({pb}) [{b.start_time}-{b.end_time}]"
                )
        return warnings

    def _shift_to_next_available(self, start_minute: int, duration: int, blocked: list[TimeWindow]) -> int:
        """Return the earliest start minute where a block of length duration avoids blocked windows."""
        candidate = start_minute
        while True:
            end_candidate = candidate + duration
            overlap_window = None
            for window in blocked:
                window_start = _time_to_minutes(window.start_time)
                window_end = _time_to_minutes(window.end_time)
                if max(candidate, window_start) < min(end_candidate, window_end):
                    overlap_window = window
                    break
            if overlap_window is None:
                return candidate
            candidate = _time_to_minutes(overlap_window.end_time)

    def build_plan(self, tasks: list[CareTask], constraints: ConstraintSet, target_date: str | None = None) -> DailyPlan:
        """Build a feasible daily plan from ranked tasks, skipping what exceeds the time budget."""
        target_date = target_date or date.today().isoformat()
        plan = DailyPlan(date=target_date)
        plan_day = date.fromisoformat(target_date)
        ranked_tasks = self.rank_tasks(
            [
                t
                for t in tasks
                if constraints.validate_task(t)
                and not t.is_complete
                and t.due_date == plan_day
            ],
            constraints,
        )
        used_minutes = 0
        current_start = _time_to_minutes("08:00")
        required_categories = set(constraints.must_include_categories)

        for task in ranked_tasks:
            if used_minutes + task.duration_minutes > constraints.max_daily_minutes:
                plan.skipped_reasons.append(
                    f"Skipped '{task.title}' because it would exceed the daily time limit."
                )
                continue

            scheduled_start = self._shift_to_next_available(
                current_start, task.duration_minutes, constraints.blocked_time_windows
            )
            scheduled_end = scheduled_start + task.duration_minutes
            current_start = scheduled_end

            reason_parts = [
                f"priority={task.priority}",
                "required task" if task.is_required else "optional task",
            ]
            if task.category in required_categories:
                reason_parts.append("must-include category")
            if task.category in constraints.preferred_categories:
                reason_parts.append("owner-preferred category")

            plan.add_item(
                DailyPlanItem(
                    task=task,
                    start_time=_minutes_to_time(scheduled_start),
                    end_time=_minutes_to_time(scheduled_end),
                    reason=", ".join(reason_parts),
                )
            )
            used_minutes += task.duration_minutes

        plan.compute_totals(constraints.max_daily_minutes)
        plan.conflict_warnings = self.find_time_conflicts(plan)
        return plan


class PlanExplainer:
    def generate_reasons(self, plan: DailyPlan, constraints: ConstraintSet) -> list[str]:
        """Produce summary bullets plus per-item explanations for a plan.

        This method is augmented with a small Retrieval-Augmented step: it will consult
        a local knowledge base (assets/*.txt) for short guidance snippets relevant to
        scheduled task titles, categories, and the active constraints. Retrieved
        snippets are included at the top of the explanation so downstream UIs can
        surface them to users.
        """
        summary = [
            f"Planned {len(plan.items)} tasks for {plan.total_minutes} minutes.",
            f"Remaining capacity: {plan.leftover_minutes} minutes.",
        ]
        if constraints.preferred_categories:
            summary.append(f"Preferred categories considered: {', '.join(constraints.preferred_categories)}.")

        # Lightweight retriever: load local assets and rank snippets by keyword overlap.
        retriever = _LocalRetriever()
        # Build a small query corpus: task titles, categories, and must-include categories.
        queries = [item.task.title for item in plan.items]
        queries += [item.task.category for item in plan.items]
        queries += list(constraints.must_include_categories)
        queries = [q for q in queries if q]

        retrieved = retriever.find_relevant_snippets(queries, top_k=3)
        # Store for external use (UI/testing) and log for auditability.
        try:
            self.last_retrieved_snippets = list(retrieved)
        except Exception:
            # If PlanExplainer is used in a context where attributes are frozen,
            # ignore silently but still continue to return the explanation.
            pass
        if retrieved:
            logging.getLogger(__name__).info("Retrieved KB snippets: %s", retrieved)
            summary.append("Relevant guidance from local knowledge:")
            for s in retrieved:
                summary.append(f"- {s}")

        # Simple confidence heuristic (0..1): start at 0.4, boost for required tasks scheduled,
        # penalize skipped reasons, and slightly boost when KB snippets are present.
        try:
            confidence = 0.4
            # if at least one required task is scheduled, boost
            if any(item.task.is_required for item in plan.items):
                confidence += 0.2
            # penalize if planner skipped tasks due to time
            if plan.skipped_reasons:
                confidence -= 0.15
            # small boost for KB context
            confidence += min(0.2, 0.05 * len(retrieved))
            # normalize
            confidence = max(0.0, min(1.0, confidence))
            self.last_confidence = confidence
            logging.getLogger(__name__).info("Plan confidence score: %.2f", confidence)
        except Exception:
            # best-effort: don't raise from explainer
            try:
                self.last_confidence = 0.0
            except Exception:
                pass

        return summary + plan.explain()


class _LocalRetriever:
    """Simple file-based retriever that returns snippets from text files in assets/.

    It performs basic case-insensitive keyword matching and ranks by overlap count.
    This is intentionally lightweight (no external deps) so tests remain fast and
    the feature is reproducible.
    """

    def __init__(self, assets_dir: str | None = None) -> None:
        import os

        root = assets_dir or os.path.join(os.path.dirname(__file__), "assets")
        self.snippets: list[str] = []
        if os.path.isdir(root):
            for name in os.listdir(root):
                if not name.lower().endswith(".txt"):
                    continue
                try:
                    with open(os.path.join(root, name), "r", encoding="utf-8") as fh:
                        text = fh.read()
                except Exception:
                    continue
                # Split into non-empty lines and keep lines as candidate snippets.
                for line in [l.strip() for l in text.splitlines()]:
                    if line:
                        self.snippets.append(line)

    def _score(self, snippet: str, query_terms: list[str]) -> int:
        s = snippet.lower()
        score = 0
        for term in query_terms:
            term = term.lower()
            if not term:
                continue
            # Count occurrences (simple proxy for relevance)
            score += s.count(term)
            # Also give a small boost if the term appears as a whole word
            if f" {term} " in f" {s} ":
                score += 1
        return score

    def find_relevant_snippets(self, queries: list[str], top_k: int = 3) -> list[str]:
        if not self.snippets or not queries:
            return []
        # Flatten queries into terms (split on non-alpha) to increase match chances
        import re

        terms: list[str] = []
        for q in queries:
            terms += [t for t in re.split(r"[^a-zA-Z0-9]+", q) if t]

        scored: list[tuple[int, str]] = []
        for s in self.snippets:
            sc = self._score(s, terms)
            if sc > 0:
                scored.append((sc, s))

        scored.sort(reverse=True, key=lambda x: x[0])
        # Deduplicate while preserving order
        seen = set()
        out: list[str] = []
        for _, snippet in scored:
            if snippet in seen:
                continue
            seen.add(snippet)
            out.append(snippet)
            if len(out) >= top_k:
                break
        return out


class TaskRepository:
    def __init__(self, tasks: list[CareTask] | None = None) -> None:
        """Initialize storage, optionally seeded with existing tasks."""
        self.tasks = tasks or []

    def add_task(self, task: CareTask) -> None:
        """Append a task to the in-memory repository."""
        self.tasks.append(task)

    def edit_task(self, task_id: str, updates: dict[str, Any]) -> bool:
        """Apply attribute updates to the first task with the given id; return success."""
        for task in self.tasks:
            if task.task_id == task_id:
                for key, value in updates.items():
                    if hasattr(task, key):
                        setattr(task, key, value)
                return True
        return False

    def remove_task(self, task_id: str) -> bool:
        """Remove the first task with the given id; return whether one was removed."""
        for idx, task in enumerate(self.tasks):
            if task.task_id == task_id:
                del self.tasks[idx]
                return True
        return False

    def list_tasks(self) -> list[CareTask]:
        """Return a shallow copy of all stored tasks."""
        return list(self.tasks)

    def filter_tasks(
        self,
        *,
        is_complete: bool | None = None,
        pet_name: str | None = None,
    ) -> list[CareTask]:
        """Return tasks matching completion status and/or pet name (case-insensitive); omit a filter to skip it."""
        result = self.list_tasks()
        if is_complete is not None:
            result = [t for t in result if t.is_complete is is_complete]
        if pet_name is not None:
            want = pet_name.strip().lower()
            result = [t for t in result if t.pet_name.strip().lower() == want]
        return result

    def complete_task(self, task_id: str, *, completion_date: date | None = None) -> CareTask | None:
        """Mark the task complete; for daily/weekly tasks append the next occurrence and return that new task."""
        completion_date = completion_date or date.today()
        for task in self.tasks:
            if task.task_id != task_id:
                continue
            task.mark_complete()
            nxt = task.next_occurrence_after(completion_date)
            if nxt is not None:
                self.add_task(nxt)
            return nxt
        raise KeyError(task_id)


class PawPalAppController:
    def __init__(
        self,
        owner: Owner,
        pet: Pet,
        task_repo: TaskRepository | None = None,
        scheduler: Scheduler | None = None,
        explainer: PlanExplainer | None = None,
    ) -> None:
        """Wire owner, pet, and optional task, scheduling, and explanation collaborators."""
        self.owner = owner
        self.pet = pet
        self.task_repo = task_repo or TaskRepository()
        self.scheduler = scheduler or Scheduler()
        self.explainer = explainer or PlanExplainer()

    def create_daily_plan(self, constraints: ConstraintSet, target_date: str | None = None) -> DailyPlan:
        """Schedule all repository tasks into a DailyPlan for the given date."""
        tasks = self.task_repo.list_tasks()
        return self.scheduler.build_plan(tasks, constraints, target_date=target_date)

    def get_plan_explanation(self, plan: DailyPlan, constraints: ConstraintSet) -> list[str]:
        """Return narrative lines explaining totals and each planned item."""
        return self.explainer.generate_reasons(plan, constraints)

    @staticmethod
    def new_task(
        title: str,
        duration_minutes: int,
        priority: str,
        category: str = "general",
        is_required: bool = False,
        notes: str = "",
        time: str = "09:00",
        pet_name: str = "",
        frequency: str = "daily",
        due_date: date | None = None,
    ) -> CareTask:
        """Factory for a new CareTask with a fresh id and incomplete status."""
        return CareTask(
            task_id=str(uuid.uuid4()),
            title=title,
            category=category,
            duration_minutes=duration_minutes,
            priority=priority,
            frequency=frequency,
            is_required=is_required,
            notes=notes,
            is_complete=False,
            time=time,
            pet_name=pet_name,
            due_date=due_date if due_date is not None else date.today(),
        )
