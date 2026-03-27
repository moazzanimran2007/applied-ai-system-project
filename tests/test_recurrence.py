from datetime import date, timedelta

import pytest

from pawpal_system import CareTask, TaskRepository


def test_complete_daily_schedules_next_day_with_timedelta() -> None:
    done_day = date(2026, 6, 1)
    task = CareTask(
        task_id="walk-1",
        title="Walk",
        category="walk",
        duration_minutes=20,
        priority="high",
        frequency="daily",
        due_date=done_day,
    )
    repo = TaskRepository([task])

    nxt = repo.complete_task("walk-1", completion_date=done_day)

    assert task.is_complete is True
    assert nxt is not None
    assert nxt.frequency == "daily"
    assert nxt.is_complete is False
    assert nxt.due_date == done_day + timedelta(days=1)
    assert len(repo.list_tasks()) == 2


def test_complete_weekly_schedules_seven_days_later() -> None:
    done_day = date(2026, 6, 10)
    task = CareTask(
        task_id="groom-1",
        title="Nail trim",
        category="grooming",
        duration_minutes=30,
        priority="low",
        frequency="weekly",
        due_date=done_day,
    )
    repo = TaskRepository([task])

    nxt = repo.complete_task("groom-1", completion_date=done_day)

    assert nxt is not None
    assert nxt.due_date == done_day + timedelta(days=7)


def test_complete_oneoff_does_not_clone() -> None:
    task = CareTask(
        task_id="once",
        title="One-time vet",
        category="meds",
        duration_minutes=60,
        priority="high",
        frequency="once",
        due_date=date(2026, 4, 1),
    )
    repo = TaskRepository([task])

    nxt = repo.complete_task("once", completion_date=date(2026, 4, 1))

    assert nxt is None
    assert len(repo.list_tasks()) == 1


def test_complete_task_missing_id_raises() -> None:
    repo = TaskRepository([])
    with pytest.raises(KeyError, match="nope"):
        repo.complete_task("nope")
