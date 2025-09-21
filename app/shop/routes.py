"""Routes for the Lifesim shop."""
from __future__ import annotations

from flask import render_template

from ..logging_service import log_manager
from . import bp


@bp.route("/")
def catalog():
    """Render the shop catalog."""
    log_manager.record(
        component="Shop",
        action="view",
        level="info",
        result="success",
        title="Shop catalog opened",
        user_summary="Shopping catalog displayed successfully.",
        technical_details="shop.catalog provided product collections without error.",
    )
    essentials = [
        {"name": "Groceries", "cost": 75, "category": "Weekly"},
        {"name": "Transit Pass", "cost": 45, "category": "Monthly"},
    ]
    luxuries = [
        {"name": "Smart Watch", "cost": 320, "category": "Electronics"},
        {"name": "Sound System", "cost": 580, "category": "Home"},
    ]
    return render_template(
        "shop/catalog.html",
        title="Lifesim — Shop",
        essentials=essentials,
        luxuries=luxuries,
        active_nav="shop",
    )
