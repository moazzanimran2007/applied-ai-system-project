from pawpal_system import CareTask, Scheduler, TaskRepository


def test_sort_by_time_orders_hh_mm_chronologically() -> None:
    scheduler = Scheduler()
    tasks = [
        CareTask("1", "c", "x", 10, "low", time="14:00"),
        CareTask("2", "a", "x", 10, "low", time="07:05"),
        CareTask("3", "b", "x", 10, "low", time="07:30"),
    ]

    ordered = scheduler.sort_by_time(tasks)

    assert [t.time for t in ordered] == ["07:05", "07:30", "14:00"]


def test_filter_tasks_by_completion_and_pet() -> None:
    repo = TaskRepository(
        [
            CareTask("1", "t1", "x", 5, "low", is_complete=False, pet_name="Mochi"),
            CareTask("2", "t2", "x", 5, "low", is_complete=True, pet_name="Mochi"),
            CareTask("3", "t3", "x", 5, "low", is_complete=False, pet_name="Nimbus"),
        ]
    )

    open_nimbus = repo.filter_tasks(is_complete=False, pet_name="Nimbus")
    assert len(open_nimbus) == 1 and open_nimbus[0].title == "t3"

    mochi_all = repo.filter_tasks(pet_name="Mochi")
    assert len(mochi_all) == 2
