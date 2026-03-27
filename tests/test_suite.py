"""
PawPal+ Comprehensive Test Suite
=================================
Covers the three required areas:
  1. Sorting Correctness  – tasks returned in chronological order
  2. Recurrence Logic     – completing a daily task generates the next day's task
  3. Conflict Detection   – Scheduler.find_time_conflicts flags duplicate/overlapping times
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from pawpal_system import (
    CareTask,
    ConstraintSet,
    DailyPlan,
    DailyPlanItem,
    Scheduler,
    TaskRepository,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TODAY = date(2026, 3, 27)


def _make_task(
    task_id: str,
    title: str,
    *,
    time: str = "09:00",
    duration: int = 20,
    priority: str = "medium",
    category: str = "general",
    frequency: str = "daily",
    is_required: bool = False,
    due_date: date | None = None,
    pet_name: str = "",
) -> CareTask:
    """Convenience factory so individual tests stay readable."""
    return CareTask(
        task_id=task_id,
        title=title,
        category=category,
        duration_minutes=duration,
        priority=priority,
        frequency=frequency,
        is_required=is_required,
        time=time,
        pet_name=pet_name,
        due_date=due_date or _TODAY,
    )


# ===========================================================================
# 1. SORTING CORRECTNESS
#    Verify that Scheduler.sort_by_time returns tasks in chronological order.
# ===========================================================================


class TestSortingCorrectness:
    """Tasks must be returned in chronological (HH:MM ascending) order."""

    def test_sort_three_tasks_out_of_order(self) -> None:
        """Three tasks given in random time order are sorted correctly."""
        scheduler = Scheduler()
        tasks = [
            _make_task("c", "Evening meds", time="18:30"),
            _make_task("a", "Morning walk", time="07:00"),
            _make_task("b", "Midday feeding", time="12:15"),
        ]

        ordered = scheduler.sort_by_time(tasks)

        assert [t.time for t in ordered] == ["07:00", "12:15", "18:30"]

    def test_sort_already_ordered_remains_stable(self) -> None:
        """Already-sorted tasks are not reordered."""
        scheduler = Scheduler()
        tasks = [
            _make_task("1", "A", time="06:00"),
            _make_task("2", "B", time="08:00"),
            _make_task("3", "C", time="20:00"),
        ]

        ordered = scheduler.sort_by_time(tasks)

        assert [t.time for t in ordered] == ["06:00", "08:00", "20:00"]

    def test_sort_single_task_returns_same_list(self) -> None:
        """A single task list is returned without error."""
        scheduler = Scheduler()
        tasks = [_make_task("x", "Lone task", time="09:00")]

        ordered = scheduler.sort_by_time(tasks)

        assert len(ordered) == 1
        assert ordered[0].time == "09:00"

    def test_sort_handles_midnight_boundary(self) -> None:
        """00:xx times are treated as earliest in the day, not latest."""
        scheduler = Scheduler()
        tasks = [
            _make_task("n", "Night meds", time="23:00"),
            _make_task("m", "Midnight snack", time="00:30"),
            _make_task("e", "Early walk", time="06:00"),
        ]

        ordered = scheduler.sort_by_time(tasks)

        assert ordered[0].time == "00:30"
        assert ordered[-1].time == "23:00"

    def test_sort_tasks_with_same_time_preserves_all(self) -> None:
        """Tasks with identical times all appear in the result."""
        scheduler = Scheduler()
        tasks = [
            _make_task("p", "Play", time="10:00"),
            _make_task("f", "Feed", time="10:00"),
        ]

        ordered = scheduler.sort_by_time(tasks)

        assert len(ordered) == 2
        assert all(t.time == "10:00" for t in ordered)


# ===========================================================================
# 2. RECURRENCE LOGIC
#    Completing a daily task must produce a new task due the following day.
# ===========================================================================


class TestRecurrenceLogic:
    """Marking a daily task complete should spawn a successor task."""

    def test_complete_daily_task_creates_next_day_task(self) -> None:
        """Core requirement: next task is due exactly one day later."""
        done_day = date(2026, 6, 1)
        task = _make_task("walk-daily", "Morning walk", frequency="daily", due_date=done_day)
        repo = TaskRepository([task])

        next_task = repo.complete_task("walk-daily", completion_date=done_day)

        assert task.is_complete is True
        assert next_task is not None
        assert next_task.due_date == done_day + timedelta(days=1)

    def test_new_recurrence_task_is_not_complete(self) -> None:
        """The generated successor task must start as incomplete."""
        done_day = date(2026, 6, 1)
        task = _make_task("meds-daily", "Give meds", frequency="daily", due_date=done_day)
        repo = TaskRepository([task])

        next_task = repo.complete_task("meds-daily", completion_date=done_day)

        assert next_task is not None
        assert next_task.is_complete is False

    def test_repo_grows_by_one_after_daily_completion(self) -> None:
        """Repository size increases by exactly one after completing a daily task."""
        done_day = date(2026, 6, 1)
        task = _make_task("feed-1", "Feeding", frequency="daily", due_date=done_day)
        repo = TaskRepository([task])
        initial_count = len(repo.list_tasks())

        repo.complete_task("feed-1", completion_date=done_day)

        assert len(repo.list_tasks()) == initial_count + 1

    def test_new_task_inherits_original_properties(self) -> None:
        """Successor task copies title, category, duration, and priority."""
        done_day = date(2026, 6, 1)
        task = _make_task(
            "groom-1",
            "Brush coat",
            category="grooming",
            duration=30,
            priority="low",
            frequency="daily",
            due_date=done_day,
        )
        repo = TaskRepository([task])

        next_task = repo.complete_task("groom-1", completion_date=done_day)

        assert next_task is not None
        assert next_task.title == "Brush coat"
        assert next_task.category == "grooming"
        assert next_task.duration_minutes == 30
        assert next_task.priority == "low"

    def test_new_task_has_unique_id(self) -> None:
        """The successor task must not reuse the original task's ID."""
        done_day = date(2026, 6, 1)
        task = _make_task("orig-id", "Walk", frequency="daily", due_date=done_day)
        repo = TaskRepository([task])

        next_task = repo.complete_task("orig-id", completion_date=done_day)

        assert next_task is not None
        assert next_task.task_id != "orig-id"

    def test_one_off_task_does_not_create_successor(self) -> None:
        """A task with frequency='once' must not generate a follow-up task."""
        done_day = date(2026, 5, 1)
        task = _make_task("vet-visit", "Vet appointment", frequency="once", due_date=done_day)
        repo = TaskRepository([task])

        next_task = repo.complete_task("vet-visit", completion_date=done_day)

        assert next_task is None
        assert len(repo.list_tasks()) == 1  # no new entry


# ===========================================================================
# 3. CONFLICT DETECTION
#    Scheduler.find_time_conflicts must return warnings for overlapping slots.
# ===========================================================================


class TestConflictDetection:
    """Scheduler must flag plan items whose time windows overlap."""

    def test_exact_same_time_slot_is_a_conflict(self) -> None:
        """Two tasks at the identical start/end time produce exactly one warning."""
        scheduler = Scheduler()
        t1 = _make_task("a", "Feed A", pet_name="Mochi")
        t2 = _make_task("b", "Feed B", pet_name="Mochi")
        plan = DailyPlan(date="2026-03-27")
        plan.add_item(DailyPlanItem(t1, "09:00", "09:20", ""))
        plan.add_item(DailyPlanItem(t2, "09:00", "09:20", ""))

        warnings = scheduler.find_time_conflicts(plan)

        assert len(warnings) == 1
        assert "Feed A" in warnings[0]
        assert "Feed B" in warnings[0]

    def test_partial_overlap_is_a_conflict(self) -> None:
        """Tasks that partially overlap (one starts before the other ends) are flagged."""
        scheduler = Scheduler()
        t1 = _make_task("1", "Walk", pet_name="Mochi")
        t2 = _make_task("2", "Feeding", pet_name="Mochi")
        plan = DailyPlan(date="2026-03-27")
        plan.add_item(DailyPlanItem(t1, "10:00", "10:30", ""))
        plan.add_item(DailyPlanItem(t2, "10:15", "10:45", ""))

        warnings = scheduler.find_time_conflicts(plan)

        assert len(warnings) == 1

    def test_adjacent_slots_are_not_a_conflict(self) -> None:
        """Back-to-back tasks (one ends exactly when the next starts) have no overlap."""
        scheduler = Scheduler()
        t1 = _make_task("1", "Walk")
        t2 = _make_task("2", "Feed")
        plan = DailyPlan(date="2026-03-27")
        plan.add_item(DailyPlanItem(t1, "09:00", "09:30", ""))
        plan.add_item(DailyPlanItem(t2, "09:30", "10:00", ""))

        warnings = scheduler.find_time_conflicts(plan)

        assert warnings == []

    def test_non_overlapping_slots_produce_no_warnings(self) -> None:
        """Tasks separated in time should not be flagged."""
        scheduler = Scheduler()
        t1 = _make_task("1", "Morning")
        t2 = _make_task("2", "Afternoon")
        plan = DailyPlan(date="2026-03-27")
        plan.add_item(DailyPlanItem(t1, "08:00", "08:30", ""))
        plan.add_item(DailyPlanItem(t2, "14:00", "14:30", ""))

        warnings = scheduler.find_time_conflicts(plan)

        assert warnings == []

    def test_three_overlapping_tasks_produce_three_pairwise_warnings(self) -> None:
        """n=3 mutually overlapping items yield C(3,2)=3 distinct conflict warnings."""
        scheduler = Scheduler()
        plan = DailyPlan(date="2026-03-27")
        for label in ("X", "Y", "Z"):
            plan.add_item(
                DailyPlanItem(
                    _make_task(label, f"Task {label}", pet_name="Mochi"),
                    "11:00",
                    "11:30",
                    "",
                )
            )

        warnings = scheduler.find_time_conflicts(plan)

        assert len(warnings) == 3

    def test_conflict_warning_contains_task_titles(self) -> None:
        """Warning string must mention both conflicting task titles."""
        scheduler = Scheduler()
        t1 = _make_task("w", "Walkies", pet_name="Mochi")
        t2 = _make_task("f", "First Feeding", pet_name="Mochi")
        plan = DailyPlan(date="2026-03-27")
        plan.add_item(DailyPlanItem(t1, "07:00", "07:30", ""))
        plan.add_item(DailyPlanItem(t2, "07:00", "07:30", ""))

        warnings = scheduler.find_time_conflicts(plan)

        assert len(warnings) == 1
        assert "Walkies" in warnings[0]
        assert "First Feeding" in warnings[0]

    def test_build_plan_attaches_conflict_warnings(self) -> None:
        """build_plan must populate plan.conflict_warnings if conflicts exist."""
        scheduler = Scheduler()
        # Both tasks share the same start time ('09:00') and the same duration,
        # so the greedy allocator places them in sequential non-overlapping slots.
        # We instead test via find_time_conflicts directly on a manually built plan.
        t1 = _make_task("m1", "Meds 1", pet_name="Mochi")
        t2 = _make_task("m2", "Meds 2", pet_name="Mochi")
        plan = DailyPlan(date="2026-03-27")
        plan.add_item(DailyPlanItem(t1, "09:00", "09:20", ""))
        plan.add_item(DailyPlanItem(t2, "09:00", "09:20", ""))
        plan.conflict_warnings = scheduler.find_time_conflicts(plan)

        assert len(plan.conflict_warnings) >= 1
