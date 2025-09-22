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

    managed_jobs = [
        {"title": "Product Consultant", "status": "Active", "rate": "$45/hr", "hours": 12},
        {"title": "Beta Coordinator", "status": "Paused", "rate": "$30/hr", "hours": 6},
        {"title": "Design QA", "status": "Draft", "rate": "$25/hr", "hours": 4},
    ]

    shifts = [
        {"day": "Monday", "hours": 4, "activity": "Client project"},
        {"day": "Wednesday", "hours": 3, "activity": "Research"},
        {"day": "Friday", "hours": 5, "activity": "Deliverables"},
    ]
    total_hours = sum(shift['hours'] for shift in shifts)
    if total_hours < 15:
        log_manager.record(
            component="Job",
            action="capacity-check",
            level="warn",
            result="warn",
            title="Weekly hours below target",
            user_summary=f"Planned hours total {total_hours}, which is below the 15 hour target.",
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
        shifts=shifts,
        milestones=milestones,
        job_preferences=job_preferences,
        active_nav="job",
    )
