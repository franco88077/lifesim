"""Routes for property management."""
from __future__ import annotations

from flask import render_template

from ..logging_service import log_manager
from . import bp


@bp.route("/")
def portfolio():
    """Show the user's property portfolio."""
    log_manager.record(
        component="RealEstate",
        action="view",
        level="info",
        result="success",
        title="Real estate portfolio opened",
        user_summary="Property overview displayed.",
        technical_details="real_estate.portfolio served property inventory and pipeline.",
    )
    properties = [
        {
            "name": "Downtown Loft",
            "value": 265000,
            "status": "Owner-occupied",
            "yield": "N/A",
        },
        {
            "name": "Lakeview Cottage",
            "value": 189000,
            "status": "Rental",
            "yield": "5.2%",
        },
    ]
    prospects = [
        {"address": "14 Palm Street", "type": "Condo", "price": 210000, "score": 82},
        {"address": "78 Sunrise Ave", "type": "Townhome", "price": 245000, "score": 76},
    ]
    if any(property['yield'] == 'N/A' for property in properties):
        log_manager.record(
            component="RealEstate",
            action="yield-check",
            level="warn",
            result="warn",
            title="Property yield requires update",
            user_summary="One or more properties are missing yield data; consider recalculating ROI.",
            technical_details="Real estate portfolio identified properties without yield metrics.",
        )
    return render_template(
        "real_estate/portfolio.html",
        title="Lifesim — Real Estate",
        properties=properties,
        prospects=prospects,
        active_nav="real_estate",
    )
