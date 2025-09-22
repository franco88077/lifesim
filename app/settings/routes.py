"""HTTP routes for managing global system settings."""
from __future__ import annotations

from flask import render_template, request
from sqlalchemy.exc import SQLAlchemyError

from ..logging_service import log_manager
from . import bp
from .services import (
    describe_timezone,
    get_app_settings,
    get_timezone_options,
    set_timezone,
)


@bp.route("/", methods=["GET", "POST"])
def preferences():
    """Display and update system-wide preferences."""

    feedback: dict[str, str] | None = None
    settings = get_app_settings()
    timezone_options = get_timezone_options()
    timezone_values = {option.value for option in timezone_options}

    if request.method == "POST":
        requested_timezone = request.form.get("timezone", "")

        if requested_timezone not in timezone_values:
            feedback = {
                "type": "error",
                "message": "Select a timezone from the list before saving.",
            }
        else:
            try:
                set_timezone(requested_timezone)
            except SQLAlchemyError as exc:
                log_manager.record(
                    component="Settings",
                    action="update-timezone",
                    level="error",
                    result="error",
                    title="Timezone update failed",
                    user_summary="The system could not save the new timezone. Try again shortly.",
                    technical_details=(
                        "settings.set_timezone raised"
                        f" {exc.__class__.__name__}: {exc}"
                    ),
                )
                feedback = {
                    "type": "error",
                    "message": (
                        "We were unable to update the timezone. Refresh the page and try again."
                    ),
                }
            else:
                settings = get_app_settings()
                timezone_label = describe_timezone(settings.timezone)
                log_manager.record(
                    component="Settings",
                    action="update-timezone",
                    level="info",
                    result="success",
                    title="Timezone updated",
                    user_summary=f"System timezone changed to {timezone_label}.",
                    technical_details=(
                        "settings.set_timezone persisted"
                        f" timezone={settings.timezone}"
                    ),
                )
                feedback = {
                    "type": "success",
                    "message": f"Timezone updated to {timezone_label}.",
                }

    else:
        log_manager.record(
            component="Settings",
            action="view-settings",
            level="info",
            result="success",
            title="Settings viewed",
            user_summary="System settings page opened to review global preferences.",
            technical_details="settings.preferences rendered the timezone selector.",
        )

    timezone_label = describe_timezone(settings.timezone)

    return render_template(
        "settings/system.html",
        title="Lifesim — Settings",
        settings=settings,
        timezone_options=timezone_options,
        timezone_label=timezone_label,
        feedback=feedback,
        active_nav="settings",
    )
