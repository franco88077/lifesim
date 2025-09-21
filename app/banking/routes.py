"""Routes for the Lifesim banking system."""
from __future__ import annotations

from flask import render_template

from ..logging_service import log_manager
from . import bp


@bp.route("/")
def dashboard():
    """Display banking overview."""
    log_manager.record(
        component="Banking",
        action="view",
        level="info",
        result="success",
        title="Banking dashboard opened",
        user_summary="Banking overview displayed for the user.",
        technical_details="banking.dashboard rendered account summaries and goals.",
    )
    accounts = [
        {"name": "Checking", "balance": 5400.25, "type": "Daily Spending"},
        {"name": "Savings", "balance": 8200.00, "type": "Emergency Fund"},
        {"name": "Investments", "balance": 13250.75, "type": "Index Portfolio"},
    ]
    goals = [
        {"goal": "Vacation Fund", "target": 2000, "current": 1200},
        {"goal": "Student Loan", "target": 15000, "current": 4500},
    ]
    for goal in goals:
        progress = goal['current'] / goal['target'] if goal['target'] else 0
        if progress < 0.5:
            log_manager.record(
                component="Banking",
                action="goal-check",
                level="warn",
                result="warn",
                title=f"Goal {goal['goal']} behind schedule",
                user_summary=f"{goal['goal']} is {progress * 100:.0f}% funded. Consider allocating more savings.",
                technical_details="Banking goals analysis flagged a low funding ratio under 50 percent.",
            )
    return render_template(
        "banking/dashboard.html",
        title="Lifesim — Banking",
        accounts=accounts,
        goals=goals,
        active_nav="banking",
    )
