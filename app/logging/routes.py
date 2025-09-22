"""Routes for interacting with the structured logging system."""
from __future__ import annotations

from flask import jsonify, render_template, request

from ..logging_service import log_manager
from . import bp


@bp.route("/")
def console():
    """Render the dedicated log console."""
    log_manager.record(
        component="Logging",
        action="view",
        level="info",
        result="success",
        title="Logging console accessed",
        user_summary="Log console opened for review.",
        technical_details="logging.console rendered detailed monitoring interface.",
    )
    return render_template(
        "logs/console.html",
        title="Lifesim — Logs",
        active_nav="logs",
    )


@bp.route("/feed")
def feed():
    """Return filtered logs as JSON data."""
    level = request.args.get("level")
    component = request.args.get("component")
    search = request.args.get("search")
    limit = request.args.get("limit", type=int) or 50
    logs = log_manager.fetch_logs(level=level, component=component, search=search, limit=limit)
    return jsonify(
        {
            "logs": logs,
            "latest": log_manager.latest_timestamp(),
        }
    )
