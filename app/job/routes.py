"""Routes for the Lifesim job system."""
from __future__ import annotations

from flask import render_template

from ..logging_service import log_manager
from . import bp


@bp.route("/")
def workspace():
    """Render the job planner."""
    log_manager.record(
        component="Job",
        action="view",
        level="info",
        result="success",
        title="Job workspace opened",
        user_summary="Work planning view rendered successfully.",
        technical_details="job.workspace delivered shift planner and productivity widgets.",
    )
    job_catalog = [
        {
            "id": "ux-research",
            "title": "UX Research Sprint",
            "rate": "$32/hr",
            "type": "Contract · Remote",
            "description": "Interview five customers, synthesize key quotes, and deliver a playback deck by Friday.",
            "skills": ["User interviews", "Affinity mapping", "Reporting"],
        },
        {
            "id": "support-shift",
            "title": "Product Support Rotation",
            "rate": "$28/hr",
            "type": "Part-time · Hybrid",
            "description": "Cover live chat, triage bugs, and route feature requests during the afternoon block.",
            "skills": ["Customer empathy", "Ticket triage", "Product expertise"],
        },
        {
            "id": "ops-optimization",
            "title": "Operations Optimisation",
            "rate": "$40/hr",
            "type": "Freelance · Remote",
            "description": "Audit recurring workflows, identify automation opportunities, and publish an execution roadmap.",
            "skills": ["Process design", "Automation", "Stakeholder updates"],
        },
    ]

    job_rules = {
        "minimum_wage": 18,
        "minimum_fixed_pay": 25,
        "daily_completion_limit": 4,
    }

    job_categories = [
        {"id": "cleaning", "label": "Cleaning"},
        {"id": "fitness", "label": "Fitness"},
        {"id": "errands", "label": "Errands"},
        {"id": "pet-care", "label": "Pet Care"},
        {"id": "creative", "label": "Creative"},
    ]

    managed_jobs = [
        {
            "id": "apartment-refresh",
            "title": "Apartment Refresh Crew",
            "category": "Cleaning",
            "pay_type": "hourly",
            "rate_display": "$20/hr",
            "rate_value": 20,
            "weekly_hours": 6,
            "weekly_tasks": 0,
            "daily_limit": 2,
            "completions_today": 1,
            "status": "Scheduled",
            "next_window": "Thu · 9–11am",
        },
        {
            "id": "spin-class-setup",
            "title": "Spin Studio Setup",
            "category": "Fitness",
            "pay_type": "hourly",
            "rate_display": "$22/hr",
            "rate_value": 22,
            "weekly_hours": 4,
            "weekly_tasks": 0,
            "daily_limit": 1,
            "completions_today": 0,
            "status": "Active",
            "next_window": "Today · 5–7pm",
        },
        {
            "id": "grocery-runs",
            "title": "Evening Grocery Runs",
            "category": "Errands",
            "pay_type": "task",
            "rate_display": "$30/task",
            "rate_value": 30,
            "weekly_hours": 0,
            "weekly_tasks": 10,
            "daily_limit": 3,
            "completions_today": 2,
            "status": "Active",
            "next_window": "Daily · 6pm",
        },
        {
            "id": "neighborhood-walks",
            "title": "Neighborhood Dog Walks",
            "category": "Pet Care",
            "pay_type": "task",
            "rate_display": "$18/walk",
            "rate_value": 18,
            "weekly_hours": 3,
            "weekly_tasks": 8,
            "daily_limit": 4,
            "completions_today": 3,
            "status": "Paused",
            "next_window": "Resume Sat",
        },
    ]

    for job in managed_jobs:
        if job["pay_type"] == "hourly":
            job["weekly_value"] = job["rate_value"] * job["weekly_hours"]
            job["frequency_label"] = f"{job['weekly_hours']} hrs/week"
            job["pay_label"] = "Per hour"
        else:
            job["weekly_value"] = job["rate_value"] * job["weekly_tasks"]
            job["frequency_label"] = f"{job['weekly_tasks']} tasks/week"
            job["pay_label"] = "Per task"

        daily_limit = job.get("daily_limit", 0) or 0
        completions_today = job.get("completions_today", 0) or 0
        if daily_limit:
            job["progress"] = round((completions_today / daily_limit) * 100)
        else:
            job["progress"] = 0
        job["progress_label"] = f"{completions_today} of {daily_limit} complete" if daily_limit else "No limit set"
        job["status_class"] = job["status"].lower().replace(" ", "-")
        job["projected_label"] = f"${job['weekly_value']:,.0f}/wk"

    projected_weekly_income = sum(job["weekly_value"] for job in managed_jobs)
    total_committed_hours = sum(job["weekly_hours"] for job in managed_jobs)
    daily_capacity = sum(job.get("daily_limit", 0) for job in managed_jobs)
    active_jobs = sum(1 for job in managed_jobs if job["status"].lower() != "paused")

    job_metrics = [
        {
            "title": "Weekly runway",
            "value": f"${projected_weekly_income:,.0f}",
            "support": f"{total_committed_hours} hrs/week scheduled",
        },
        {
            "title": "Active workload",
            "value": str(active_jobs),
            "support": f"{daily_capacity} completions/day capacity",
        },
        {
            "title": "Guardrails met",
            "value": "100%",
            "support": "All jobs meet minimum pay rules",
        },
    ]

    category_summary = {}
    for job in managed_jobs:
        bucket = category_summary.setdefault(
            job["category"], {"jobs": 0, "hours": 0, "tasks": 0, "value": 0}
        )
        bucket["jobs"] += 1
        bucket["value"] += job["weekly_value"]
        if job["pay_type"] == "hourly":
            bucket["hours"] += job["weekly_hours"]
        else:
            bucket["tasks"] += job["weekly_tasks"]

    category_totals = []
    for label, data in sorted(category_summary.items()):
        if data["hours"] and data["tasks"]:
            effort = f"{data['hours']} hrs + {data['tasks']} tasks/wk"
        elif data["hours"]:
            effort = f"{data['hours']} hrs/week"
        elif data["tasks"]:
            effort = f"{data['tasks']} tasks/week"
        else:
            effort = "No effort recorded"
        category_totals.append(
            {
                "label": label,
                "jobs": data["jobs"],
                "effort": effort,
                "value": f"${data['value']:,.0f}/wk",
            }
        )

    shifts = [
        {"day": "Monday", "hours": 4, "activity": "Client project"},
        {"day": "Wednesday", "hours": 3, "activity": "Research"},
        {"day": "Friday", "hours": 5, "activity": "Deliverables"},
    ]
    scheduled_hours = sum(shift["hours"] for shift in shifts)
    if scheduled_hours < 15:
        log_manager.record(
            component="Job",
            action="capacity-check",
            level="warn",
            result="warn",
            title="Weekly hours below target",
            user_summary=f"Planned hours total {scheduled_hours}, which is below the 15 hour target.",
            technical_details="Job workspace detected lower-than-target commitment level.",
        )
    milestones = [
        {"name": "Certification", "deadline": "2024-06-01", "status": "In progress"},
        {"name": "Performance Review", "deadline": "2024-05-15", "status": "Scheduled"},
    ]

    job_preferences = {
        "auto_assign": True,
        "default_shift_length": 4,
        "max_weekly_hours": 24,
        "notifications": {"email": True, "sms": False},
        "reminder_window": "1 day before",
    }
    return render_template(
        "job/workspace.html",
        title="Lifesim — Job",
        job_catalog=job_catalog,
        managed_jobs=managed_jobs,
        job_rules=job_rules,
        job_categories=job_categories,
        job_metrics=job_metrics,
        category_totals=category_totals,
        shifts=shifts,
        milestones=milestones,
        job_preferences=job_preferences,
        active_nav="job",
    )
