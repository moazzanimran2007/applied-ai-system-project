"""Temporary terminal script to exercise pawpal_system scheduling, sorting, and filtering."""

from __future__ import annotations

from datetime import date

from pawpal_system import (
    ConstraintSet,
    DailyPlan,
    DailyPlanItem,
    Owner,
    PawPalAppController,
    Pet,
    Scheduler,
    TaskRepository,
)


def _build_controller(owner: Owner, pet: Pet) -> PawPalAppController:
    return PawPalAppController(owner=owner, pet=pet, task_repo=TaskRepository())


def main() -> None:
    owner = Owner(
        owner_id="o-demo",
        name="Alex Rivera",
        available_minutes_per_day=240,
        preferences={"preferred_categories": ["walk", "feeding"]},
    )

    pet_dog = Pet(pet_id="p-dog", name="Mochi", species="dog", age_years=3.0)
    pet_cat = Pet(pet_id="p-cat", name="Nimbus", species="cat", age_years=2.0)

    shared_repo = TaskRepository()
    scheduler = Scheduler()

    # Add tasks out of order by preferred `time` (HH:MM); mixed pets.
    shared_repo.add_task(
        PawPalAppController.new_task(
            "Afternoon walk",
            duration_minutes=30,
            priority="high",
            category="walk",
            time="16:00",
            pet_name="Mochi",
        )
    )
    shared_repo.add_task(
        PawPalAppController.new_task(
            "Feed breakfast",
            duration_minutes=15,
            priority="high",
            category="feeding",
            is_required=True,
            time="07:30",
            pet_name="Nimbus",
        )
    )
    shared_repo.add_task(
        PawPalAppController.new_task(
            "Midday puzzle",
            duration_minutes=20,
            priority="medium",
            category="enrichment",
            time="12:15",
            pet_name="Nimbus",
        )
    )
    shared_repo.add_task(
        PawPalAppController.new_task(
            "Morning walk",
            duration_minutes=35,
            priority="high",
            category="walk",
            is_required=True,
            time="08:45",
            pet_name="Mochi",
        )
    )

    breakfast_id = next(t.task_id for t in shared_repo.list_tasks() if t.title == "Feed breakfast")
    shared_repo.complete_task(breakfast_id, completion_date=date.today())

    print("Tasks in insertion order (not sorted by time)")
    print("---------------------------------------------")
    for t in shared_repo.list_tasks():
        print(
            f"  {t.time}  {t.pet_name or '(no pet)':8}  "
            f"{'done' if t.is_complete else 'open':4}  {t.title}"
        )

    print("\nSorted by CareTask.time (key = minutes since midnight)")
    print("------------------------------------------------------")
    for t in scheduler.sort_by_time(shared_repo.list_tasks()):
        print(f"  {t.time}  {t.pet_name or '-':8}  {t.title}")

    print("\nFilter: incomplete tasks only")
    print("-----------------------------")
    for t in shared_repo.filter_tasks(is_complete=False):
        print(f"  {t.time}  {t.pet_name}  {t.title}")

    print("\nFilter: pet_name == Mochi")
    print("-------------------------")
    for t in shared_repo.filter_tasks(pet_name="Mochi"):
        print(f"  {t.time}  {t.title}")

    print("\nFilter: incomplete + Mochi")
    print("--------------------------")
    for t in shared_repo.filter_tasks(is_complete=False, pet_name="Mochi"):
        print(f"  {t.time}  {t.title}")

    constraints = ConstraintSet(
        max_daily_minutes=owner.available_minutes_per_day,
        must_include_categories=["feeding"],
        preferred_categories=list(owner.preferences.get("preferred_categories", [])),
    )

    today = date.today().isoformat()

    print("\nToday's Schedule (per-pet controllers, original demo)")
    print("=======================================================")

    dog_ctrl = _build_controller(owner, pet_dog)
    cat_ctrl = _build_controller(owner, pet_cat)
    for t in shared_repo.list_tasks():
        if t.pet_name == "Mochi":
            dog_ctrl.task_repo.add_task(t)
        elif t.pet_name == "Nimbus":
            cat_ctrl.task_repo.add_task(t)

    for label, ctrl in (("Mochi (dog)", dog_ctrl), ("Nimbus (cat)", cat_ctrl)):
        plan = ctrl.create_daily_plan(constraints, target_date=today)
        print(f"\n{label} — {plan.date}")
        if not plan.items:
            print("  (no tasks scheduled)")
            continue
        for item in plan.items:
            print(
                f"  {item.start_time}–{item.end_time}  {item.task.title}  "
                f"({item.task.duration_minutes} min, {item.task.priority}) — {item.reason}"
            )
        print(f"  Total: {plan.total_minutes} min planned, {plan.leftover_minutes} min free")
        if plan.conflict_warnings:
            print("  Scheduler warnings (double-booking):")
            for w in plan.conflict_warnings:
                print(f"    WARNING: {w}")

    print("\nConflict detection demo (same clock window, two pets)")
    print("=====================================================")
    overlap_a = PawPalAppController.new_task(
        "Morning walk",
        30,
        "high",
        "walk",
        pet_name="Mochi",
    )
    overlap_b = PawPalAppController.new_task(
        "Indoor play",
        30,
        "medium",
        "enrichment",
        pet_name="Nimbus",
    )
    clash_plan = DailyPlan(date=today)
    clash_plan.add_item(DailyPlanItem(overlap_a, "10:00", "10:30", "demo: same start"))
    clash_plan.add_item(DailyPlanItem(overlap_b, "10:00", "10:30", "demo: same start"))
    clash_warnings = scheduler.find_time_conflicts(clash_plan)
    if clash_warnings:
        print("Scheduler identifies overlapping items (soft warnings, no crash):")
        for msg in clash_warnings:
            print(f"  WARNING: {msg}")
    else:
        print("(unexpected: no overlap detected)")


if __name__ == "__main__":
    main()
