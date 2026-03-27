from datetime import date

from pawpal_system import CareTask, ConstraintSet, Scheduler, TimeWindow

_PLAN_DAY = date(2026, 3, 27)


def _task(
    title: str,
    duration: int,
    priority: str,
    category: str = "general",
    is_required: bool = False,
) -> CareTask:
    return CareTask(
        task_id=title.lower().replace(" ", "-"),
        title=title,
        category=category,
        duration_minutes=duration,
        priority=priority,
        is_required=is_required,
        due_date=_PLAN_DAY,
    )


def test_scheduler_respects_daily_time_limit() -> None:
    scheduler = Scheduler()
    tasks = [
        _task("Morning walk", 30, "high", "walk"),
        _task("Feed breakfast", 15, "high", "feeding", is_required=True),
        _task("Long enrichment", 90, "low", "enrichment"),
    ]
    constraints = ConstraintSet(max_daily_minutes=60)

    plan = scheduler.build_plan(tasks, constraints, target_date=_PLAN_DAY.isoformat())

    assert plan.total_minutes <= 60
    scheduled_titles = [item.task.title for item in plan.items]
    assert "Feed breakfast" in scheduled_titles


def test_required_task_ranked_before_optional_same_priority() -> None:
    scheduler = Scheduler()
    tasks = [
        _task("Optional meds", 10, "medium", "meds", is_required=False),
        _task("Required meds", 10, "medium", "meds", is_required=True),
    ]
    constraints = ConstraintSet(max_daily_minutes=30)

    ranked = scheduler.rank_tasks(tasks, constraints)

    assert ranked[0].title == "Required meds"


def test_scheduler_avoids_blocked_window() -> None:
    scheduler = Scheduler()
    tasks = [_task("Walk", 30, "high", "walk")]
    constraints = ConstraintSet(
        max_daily_minutes=120,
        blocked_time_windows=[TimeWindow(start_time="08:00", end_time="09:00")],
    )

    plan = scheduler.build_plan(tasks, constraints, target_date=_PLAN_DAY.isoformat())

    assert len(plan.items) == 1
    assert plan.items[0].start_time == "09:00"
    assert plan.items[0].end_time == "09:30"


def test_preferred_category_gets_bonus() -> None:
    scheduler = Scheduler()
    tasks = [
        _task("Light walk", 20, "medium", "walk"),
        _task("Puzzle game", 20, "medium", "enrichment"),
    ]
    constraints = ConstraintSet(
        max_daily_minutes=60,
        preferred_categories=["enrichment"],
    )

    ranked = scheduler.rank_tasks(tasks, constraints)

    assert ranked[0].category == "enrichment"
