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
    return render_template(
        "job/workspace.html",
        title="Lifesim — Job",
        shifts=shifts,
        milestones=milestones,
        active_nav="job",
    )
