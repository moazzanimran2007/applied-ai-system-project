import streamlit as st
from datetime import time
from logic import (
    CareTask,
    ConstraintSet,
    Owner,
    PawPalAppController,
    Pet,
    TaskRepository,
    TimeWindow,
)

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

# Persist domain objects across reruns: only construct once, then mutate from widgets.
# Check with `in` (or try/except KeyError). Avoid `setdefault(k, Owner(...))` because
# `Owner(...)` is evaluated every run even when the key already exists.
if "owner" not in st.session_state:
    st.session_state.owner = Owner(
        owner_id="owner-1",
        name="Jordan",
        available_minutes_per_day=180,
    )
if "pet" not in st.session_state:
    st.session_state.pet = Pet(pet_id="pet-1", name="Mochi", species="dog")

st.title("🐾 PawPal+")

st.markdown(
    """
Welcome to the PawPal+ starter app.

This file is intentionally thin. It gives you a working Streamlit app so you can start quickly,
but **it does not implement the project logic**. Your job is to design the system and build it.

Use this app as your interactive demo once your backend classes/functions exist.
"""
)

with st.expander("Scenario", expanded=True):
    st.markdown(
        """
**PawPal+** is a pet care planning assistant. It helps a pet owner plan care tasks
for their pet(s) based on constraints like time, priority, and preferences.

You will design and implement the scheduling logic and connect it to this Streamlit UI.
"""
    )

with st.expander("What you need to build", expanded=True):
    st.markdown(
        """
At minimum, your system should:
- Represent pet care tasks (what needs to happen, how long it takes, priority)
- Represent the pet and the owner (basic info and preferences)
- Build a plan/schedule for a day that chooses and orders tasks based on constraints
- Explain the plan (why each task was chosen and when it happens)
"""
    )

st.divider()

st.subheader("Quick Demo Inputs (UI only)")
owner_name = st.text_input("Owner name", value="Jordan")
pet_name = st.text_input("Pet name", value="Mochi")
species = st.selectbox("Species", ["dog", "cat", "other"])
available_minutes = st.number_input(
    "Owner available minutes today", min_value=30, max_value=720, value=180
)

st.markdown("### Scheduling Constraints")
blocked_enabled = st.checkbox("Add blocked time window", value=False)
col_b1, col_b2 = st.columns(2)
with col_b1:
    blocked_start = st.time_input("Blocked start", value=time(12, 0), key="blocked_start")
with col_b2:
    blocked_end = st.time_input("Blocked end", value=time(13, 0), key="blocked_end")

preferred_categories_input = st.text_input(
    "Preferred categories (comma-separated)", value="walk,feeding"
)
must_include_input = st.text_input(
    "Must-include categories (comma-separated)", value="feeding,meds"
)

st.markdown("### Tasks")
st.caption("Add a few tasks. In your final version, these should feed into your scheduler.")

if "tasks" not in st.session_state:
    st.session_state.tasks = []

col1, col2, col3 = st.columns(3)
with col1:
    task_title = st.text_input("Task title", value="Morning walk")
with col2:
    duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
with col3:
    priority = st.selectbox("Priority", ["low", "medium", "high"], index=2)
col4, col5 = st.columns(2)
with col4:
    category = st.selectbox(
        "Category",
        ["walk", "feeding", "meds", "enrichment", "grooming", "other"],
        index=0,
    )
with col5:
    is_required = st.checkbox("Required task", value=False)

if st.button("Add task"):
    st.session_state.tasks.append(
        {
            "title": task_title.strip(),
            "duration_minutes": int(duration),
            "priority": priority,
            "category": category,
            "is_required": is_required,
        }
    )

if st.session_state.tasks:
    remove_options = ["None"] + [t["title"] for t in st.session_state.tasks]
    remove_selection = st.selectbox("Remove a task", remove_options)
    if st.button("Remove selected task") and remove_selection != "None":
        for idx, task in enumerate(st.session_state.tasks):
            if task["title"] == remove_selection:
                st.session_state.tasks.pop(idx)
                break

if st.session_state.tasks:
    st.write("Current tasks:")
    st.table(st.session_state.tasks)
else:
    st.info("No tasks yet. Add one above.")

st.divider()

st.subheader("Build Schedule")
st.caption("This button should call your scheduling logic once you implement it.")

if st.button("Generate schedule"):
    owner = st.session_state.owner
    owner.name = owner_name.strip() or "Owner"
    owner.available_minutes_per_day = int(available_minutes)
    owner.update_preferences(
        {
            "preferred_categories": [
                c.strip() for c in preferred_categories_input.split(",") if c.strip()
            ]
        }
    )
    pet = st.session_state.pet
    pet.name = pet_name.strip() or "Pet"
    pet.species = species

    repo = TaskRepository()
    controller = PawPalAppController(owner=owner, pet=pet, task_repo=repo)

    for task in st.session_state.tasks:
        repo.add_task(
            controller.new_task(
                title=task["title"],
                duration_minutes=task["duration_minutes"],
                priority=task["priority"],
                category=task["category"],
                is_required=task["is_required"],
            )
        )

    blocked_windows = []
    if blocked_enabled and blocked_start < blocked_end:
        blocked_windows.append(
            TimeWindow(
                start_time=blocked_start.strftime("%H:%M"),
                end_time=blocked_end.strftime("%H:%M"),
            )
        )

    constraints = ConstraintSet(
        max_daily_minutes=int(available_minutes),
        blocked_time_windows=blocked_windows,
        must_include_categories=[c.strip() for c in must_include_input.split(",") if c.strip()],
        preferred_categories=[c.strip() for c in preferred_categories_input.split(",") if c.strip()],
    )
    plan = controller.create_daily_plan(constraints)
    explanation = controller.get_plan_explanation(plan, constraints)
    # If the explainer stored the last retrieved snippets, surface them in the UI.
    retrieved_snippets = []
    try:
        retrieved_snippets = controller.explainer.last_retrieved_snippets  # type: ignore[attr-defined]
    except Exception:
        retrieved_snippets = []

    if not plan.items:
        st.warning("No tasks could be scheduled with the current constraints.")
    else:
        st.success("Schedule generated.")
        st.table(
            [
                {
                    "start": i.start_time,
                    "end": i.end_time,
                    "task": i.task.title,
                    "category": i.task.category,
                    "priority": i.task.priority,
                    "reason": i.reason,
                }
                for i in plan.items
            ]
        )
        st.caption(
            f"Total minutes scheduled: {plan.total_minutes} | Remaining minutes: {plan.leftover_minutes}"
        )

    st.markdown("### Why this plan")
    for line in explanation:
        st.write(f"- {line}")

    if retrieved_snippets:
        st.markdown("### KB snippets used for explanation")
        for s in retrieved_snippets:
            st.write(f"> {s}")
