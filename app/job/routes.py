"""Routes that power the Lifesim job system."""
from __future__ import annotations

from flask import jsonify, render_template, request

from ..logging_service import log_manager
from . import bp
from .services import JobRepository


def _json_error(message: str, *, status: int = 400):
    """Return a consistently formatted JSON error response."""

    response = jsonify({"success": False, "message": message})
    response.status_code = status
    return response


def _parse_job_payload(data: dict[str, object]) -> dict[str, object]:
    """Validate and normalize incoming job payloads."""

    title = (data.get("title") or "").strip()
    description = (data.get("description") or "").strip()
    pay_type = (data.get("pay_type") or "").strip().lower()
    pay_rate = data.get("pay_rate")
    daily_limit_raw = data.get("daily_limit")

    if not title:
        raise ValueError("A job title is required.")
    if not description:
        raise ValueError("A job description is required.")
    if pay_type not in {"time", "task"}:
        raise ValueError("Choose whether the job is time or task based.")
    if pay_rate in (None, ""):
        raise ValueError("Provide a pay rate for the job.")

    if daily_limit_raw in (None, ""):
        daily_limit = None
    else:
        try:
            daily_limit = int(daily_limit_raw)
        except (TypeError, ValueError) as exc:  # pragma: no cover - defensive
            raise ValueError("Daily limit must be a whole number.") from exc
        if daily_limit <= 0:
            raise ValueError("Daily limit must be positive or left blank for unlimited completions.")

    return {
        "title": title,
        "description": description,
        "pay_type": pay_type,
        "pay_rate": pay_rate,
        "daily_limit": daily_limit,
    }


@bp.route("/")
def listings():
    """Display all available jobs for the player."""

    jobs = JobRepository.serialize_jobs()
    settings = JobRepository.settings().to_dict()
    time_jobs = [job for job in jobs if job["pay_type"] == "time"]
    task_jobs = [job for job in jobs if job["pay_type"] == "task"]
    available_jobs = sum(1 for job in jobs if job["is_available"])

    log_manager.record(
        component="Job",
        action="view",
        level="info",
        result="success",
        title="Job listings opened",
        user_summary="Presented the current job board to the player.",
        technical_details="job.listings rendered time and task job collections.",
    )

    return render_template(
        "job/listings.html",
        title="Lifesim — Job Listings",
        jobs=jobs,
        time_jobs=time_jobs,
        task_jobs=task_jobs,
        summary={
            "total": len(jobs),
            "available": available_jobs,
            "time": len(time_jobs),
            "task": len(task_jobs),
        },
        settings=settings,
        active_nav="job",
        active_job_tab="listings",
    )


@bp.route("/manage")
def manage():
    """Render the job management dashboard."""

    jobs = JobRepository.serialize_jobs()
    settings = JobRepository.settings().to_dict()

    log_manager.record(
        component="Job",
        action="manage-view",
        level="info",
        result="success",
        title="Job management opened",
        user_summary="Loaded the job management console for editing listings.",
        technical_details="job.manage rendered job list and creation form.",
    )

    return render_template(
        "job/manage.html",
        title="Lifesim — Manage Jobs",
        jobs=jobs,
        settings=settings,
        active_nav="job",
        active_job_tab="manage",
    )


@bp.route("/settings")
def job_settings():
    """Allow players to update job-related defaults."""

    jobs = JobRepository.serialize_jobs()
    settings = JobRepository.settings().to_dict()

    log_manager.record(
        component="Job",
        action="settings-view",
        level="info",
        result="success",
        title="Job settings opened",
        user_summary="Displayed job configuration controls.",
        technical_details="job.settings rendered wage and reset options.",
    )

    return render_template(
        "job/settings.html",
        title="Lifesim — Job Settings",
        jobs=jobs,
        settings=settings,
        active_nav="job",
        active_job_tab="settings",
    )


@bp.route("/api/jobs", methods=["GET", "POST"])
def api_jobs():
    """Provide job information or create new jobs."""

    if request.method == "GET":
        return jsonify(
            {
                "success": True,
                "jobs": JobRepository.serialize_jobs(),
                "settings": JobRepository.settings().to_dict(),
            }
        )

    payload = request.get_json(silent=True) or {}

    try:
        params = _parse_job_payload(payload)
        job = JobRepository.create(**params)
        job_dict = job.to_dict(JobRepository.settings())
    except ValueError as exc:
        return _json_error(str(exc))

    log_manager.record(
        component="Job",
        action="create",
        level="info",
        result="success",
        title="Job created",
        user_summary=f"Added new job listing '{job_dict['title']}'.",
        technical_details="job.api create stored new job in repository.",
    )

    response = jsonify({
        "success": True,
        "job": job_dict,
        "message": "Job created successfully.",
    })
    response.status_code = 201
    return response


@bp.route("/api/jobs/<job_id>", methods=["PUT", "DELETE"])
def api_job_detail(job_id: str):
    """Update or remove an individual job."""

    if request.method == "DELETE":
        deleted = JobRepository.delete(job_id)
        if not deleted:
            return _json_error("Job not found.", status=404)

        log_manager.record(
            component="Job",
            action="delete",
            level="info",
            result="success",
            title="Job removed",
            user_summary=f"Removed job listing {job_id}.",
            technical_details="job.api delete removed job from repository.",
        )

        return jsonify({
            "success": True,
            "job_id": job_id,
            "message": "Job removed.",
        })

    payload = request.get_json(silent=True) or {}

    try:
        params = _parse_job_payload(payload)
        job = JobRepository.update(job_id, **params)
        job_dict = job.to_dict(JobRepository.settings())
    except KeyError:
        return _json_error("Job not found.", status=404)
    except ValueError as exc:
        return _json_error(str(exc))

    log_manager.record(
        component="Job",
        action="update",
        level="info",
        result="success",
        title="Job updated",
        user_summary=f"Updated job listing '{job_dict['title']}'.",
        technical_details="job.api update refreshed job details.",
    )

    return jsonify({
        "success": True,
        "job": job_dict,
        "message": "Job updated successfully.",
    })


@bp.route("/api/settings", methods=["GET", "PATCH"])
def api_settings():
    """Expose or update job settings."""

    if request.method == "GET":
        return jsonify({
            "success": True,
            "settings": JobRepository.settings().to_dict(),
        })

    payload = request.get_json(silent=True) or {}

    minimum_wage_input = payload.get("minimum_hourly_wage")
    default_limit_input = payload.get("default_daily_limit")
    reset_hour_input = payload.get("daily_reset_hour")

    minimum_wage = None if minimum_wage_input in (None, "") else minimum_wage_input
    try:
        default_limit = (
            None
            if default_limit_input in (None, "")
            else int(default_limit_input)
        )
    except (TypeError, ValueError):
        return _json_error("Default daily limit must be a whole number.")

    try:
        reset_hour = (
            None
            if reset_hour_input in (None, "")
            else int(reset_hour_input)
        )
    except (TypeError, ValueError):
        return _json_error("Choose a valid hour between 0 and 23 for the reset time.")

    try:
        settings = JobRepository.update_settings(
            minimum_hourly_wage=minimum_wage,
            default_daily_limit=default_limit,
            daily_reset_hour=reset_hour,
        ).to_dict()
    except (ValueError, ArithmeticError) as exc:
        return _json_error(str(exc))

    log_manager.record(
        component="Job",
        action="settings-update",
        level="info",
        result="success",
        title="Job settings updated",
        user_summary="Job defaults were updated from the settings screen.",
        technical_details="job.api settings saved configuration values.",
    )

    return jsonify({
        "success": True,
        "settings": settings,
        "message": "Job settings saved.",
    })

