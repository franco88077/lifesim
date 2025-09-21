"""Routes for the Lifesim home hub."""
from __future__ import annotations

from flask import render_template

from ..logging_service import log_manager
from . import bp


@bp.route("/")
def home():
    """Render the main dashboard hub."""

    log_manager.record(
        component="Home",
        action="view",
        level="info",
        result="success",
        title="Homepage accessed",
        user_summary="Dashboard hub loaded successfully.",
        technical_details="index.home endpoint served Lifesim hub without issues.",
    )

    quick_metrics = {
        "balance": 12500,
        "credit_score": 720,
        "properties": 1,
        "job_hours": 12,
    }

    return render_template(
        "index/home.html",
        title="Lifesim — Home",
        metrics=quick_metrics,
        active_nav="home",
    )
