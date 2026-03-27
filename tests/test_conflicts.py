from pawpal_system import CareTask, DailyPlan, DailyPlanItem, Scheduler


def test_find_time_conflicts_warns_on_overlap_same_pet() -> None:
    sched = Scheduler()
    pet = "Mochi"
    t1 = CareTask("1", "Walk A", "walk", 30, "high", pet_name=pet)
    t2 = CareTask("2", "Walk B", "walk", 30, "high", pet_name=pet)
    plan = DailyPlan(date="2026-01-01")
    plan.add_item(DailyPlanItem(t1, "10:00", "10:30", ""))
    plan.add_item(DailyPlanItem(t2, "10:00", "10:30", ""))

    warnings = sched.find_time_conflicts(plan)

    assert len(warnings) == 1
    assert "Walk A" in warnings[0] and "Walk B" in warnings[0]
    assert pet in warnings[0]


def test_find_time_conflicts_warns_different_pets() -> None:
    sched = Scheduler()
    plan = DailyPlan(date="2026-01-01")
    plan.add_item(
        DailyPlanItem(
            CareTask("1", "Task1", "x", 20, "low", pet_name="Mochi"),
            "14:00",
            "14:30",
            "",
        )
    )
    plan.add_item(
        DailyPlanItem(
            CareTask("2", "Task2", "x", 20, "low", pet_name="Nimbus"),
            "14:15",
            "14:45",
            "",
        )
    )

    assert len(sched.find_time_conflicts(plan)) == 1


def test_find_time_conflicts_empty_when_no_overlap() -> None:
    sched = Scheduler()
    plan = DailyPlan(date="2026-01-01")
    t = CareTask("1", "Only", "x", 10, "low")
    plan.add_item(DailyPlanItem(t, "08:00", "08:10", ""))
    plan.add_item(
        DailyPlanItem(CareTask("2", "Later", "x", 10, "low"), "09:00", "09:10", "")
    )

    assert sched.find_time_conflicts(plan) == []


def test_manual_plan_conflict_warnings_list() -> None:
    sched = Scheduler()
    m = CareTask("m", "M", "x", 30, "low", pet_name="A")
    n = CareTask("n", "N", "x", 30, "low", pet_name="B")
    plan = DailyPlan(date="2026-06-01")
    plan.add_item(DailyPlanItem(m, "11:00", "11:30", ""))
    plan.add_item(DailyPlanItem(n, "11:00", "11:30", ""))
    plan.conflict_warnings = sched.find_time_conflicts(plan)

    assert len(plan.conflict_warnings) == 1
