"""Routes that power the Lifesim job system."""
from __future__ import annotations

from decimal import Decimal

from flask import jsonify, render_template, request
from sqlalchemy.exc import SQLAlchemyError

from ..banking.models import BankTransaction
from ..banking.services import (
    decimal_to_number,
    ensure_bank_defaults,
    fetch_accounts,
    find_account,
    format_currency,
    quantize_amount,
)
from ..extensions import db
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


def _build_payout_options() -> list[dict[str, object]]:
    """Return the available payout options based on open bank accounts."""

    ensure_bank_defaults()
    accounts = fetch_accounts()

    options: list[dict[str, object]] = [
        {
            "value": "cash",
            "label": "Cash",
            "description": "Receive the payment as cash on hand.",
            "account_slug": "hand",
        }
    ]

    for slug, fallback_label in ("checking", "Checking Account"), ("savings", "Savings Account"):
        account = next(
            (acct for acct in accounts if acct.slug == slug and not acct.is_closed),
            None,
        )
        if not account:
            continue
        options.append(
            {
                "value": slug,
                "label": account.name or fallback_label,
                "description": f"Deposit directly into {account.name or fallback_label}.",
                "account_slug": slug,
            }
        )

    return options


def _deposit_job_income(
    amount: Decimal, payout_method: str, *, job_title: str, company_name: str
) -> tuple[BankTransaction, str]:
    """Deposit job earnings into the selected account and return the ledger entry."""

    ensure_bank_defaults()

    method = (payout_method or "").strip().lower()
    slug_map = {"cash": "hand", "checking": "checking", "savings": "savings"}
    destination_slug = slug_map.get(method)
    if not destination_slug:
        raise ValueError("Choose how you'd like to receive the payment.")

    destination = find_account(destination_slug, include_closed=True)
    if not destination or destination.is_closed:
        raise LookupError("The selected account is unavailable.")

    quantized_amount = quantize_amount(amount)
    if quantized_amount <= 0:
        raise ValueError("Unable to deposit a non-positive amount.")

    description = f"{job_title} payment from {company_name}"
    transaction = BankTransaction(
        account=destination,
        name=company_name,
        description=description,
        direction="credit",
        amount=quantized_amount,
    )

    try:
        destination.balance = quantize_amount(destination.balance + quantized_amount)
        db.session.add(destination)
        db.session.add(transaction)
        db.session.commit()
    except SQLAlchemyError as exc:  # pragma: no cover - defensive
        db.session.rollback()
        raise RuntimeError("Unable to record the payment at this time.") from exc

    return transaction, destination_slug


@bp.route("/")
def listings():
    """Display all available jobs for the player."""

    jobs = JobRepository.serialize_jobs()
    settings = JobRepository.settings().to_dict()
    payout_options = _build_payout_options()
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
        payout_options=payout_options,
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
                "payout_options": _build_payout_options(),
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
    company_name_input = payload.get("payroll_company_name")

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
            payroll_company_name=company_name_input,
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


@bp.route("/api/jobs/<job_id>/start", methods=["POST"])
def api_job_start(job_id: str):
    """Start or resume a time-based job."""

    try:
        job = JobRepository.start_time_job(job_id)
    except KeyError:
        return _json_error("Job not found.", status=404)
    except ValueError as exc:
        return _json_error(str(exc))

    settings = JobRepository.settings()
    job_dict = job.to_dict(settings)
    action = "Resumed" if job_dict.get("active_session_seconds") else "Started"

    log_manager.record(
        component="Job",
        action="time-start",
        level="info",
        result="success",
        title=f"{action} time-based job",
        user_summary=f"{action} the shift for {job.title}.",
        technical_details=f"job.start activated session for job {job_id}.",
    )

    return jsonify(
        {
            "success": True,
            "job": job_dict,
            "message": f"{action} {job.title}.",
        }
    )


@bp.route("/api/jobs/<job_id>/pause", methods=["POST"])
def api_job_pause(job_id: str):
    """Pause an active time-based job."""

    try:
        job = JobRepository.pause_time_job(job_id)
    except KeyError:
        return _json_error("Job not found.", status=404)
    except ValueError as exc:
        return _json_error(str(exc))

    settings = JobRepository.settings()
    job_dict = job.to_dict(settings)

    log_manager.record(
        component="Job",
        action="time-pause",
        level="info",
        result="success",
        title="Paused time-based job",
        user_summary=f"Paused the shift for {job.title}.",
        technical_details=f"job.pause stored {job_dict.get('active_session_seconds', 0)} seconds of progress.",
    )

    return jsonify(
        {
            "success": True,
            "job": job_dict,
            "message": f"Paused {job.title}.",
        }
    )


@bp.route("/api/jobs/<job_id>/complete", methods=["POST"])
def api_job_complete(job_id: str):
    """Complete a job and deposit the earnings."""

    payload = request.get_json(silent=True) or {}
    payout_method = (payload.get("payout_method") or "").strip()

    if not payout_method:
        return _json_error("Choose how you'd like to receive payment.")

    try:
        job, earnings = JobRepository.complete_job(job_id)
    except KeyError:
        return _json_error("Job not found.", status=404)
    except ValueError as exc:
        return _json_error(str(exc))

    settings = JobRepository.settings()

    try:
        transaction, destination_slug = _deposit_job_income(
            earnings,
            payout_method,
            job_title=job.title,
            company_name=settings.payroll_company_name,
        )
    except LookupError:
        return _json_error("The selected account is unavailable. Open the account before depositing.")
    except ValueError as exc:
        return _json_error(str(exc))
    except RuntimeError as exc:
        log_manager.record(
            component="Job",
            action="job-complete",
            level="error",
            result="error",
            title="Job completion failed",
            user_summary="The payment could not be deposited due to a banking error.",
            technical_details=f"job.complete encountered banking error: {exc}",
        )
        return _json_error("Unable to deposit the payment right now. Please try again shortly.", status=500)

    account = transaction.account
    job_dict = job.to_dict(settings)
    amount_display = format_currency(transaction.amount)
    message = f"Deposited {amount_display} to {account.name}."

    log_manager.record(
        component="Job",
        action="job-complete",
        level="info",
        result="success",
        title="Job completed",
        user_summary=f"Completed {job.title} and {message.lower()}",
        technical_details=(
            "job.complete recorded earnings of {} for job {} and deposited into {} ({}).".format(
                amount_display,
                job_id,
                account.name,
                destination_slug,
            )
        ),
    )

    return jsonify(
        {
            "success": True,
            "job": job_dict,
            "message": message,
            "payout": {
                "amount": decimal_to_number(transaction.amount),
                "amount_display": amount_display,
                "account": account.name,
                "account_slug": account.slug,
                "balance": decimal_to_number(account.balance),
            },
        }
    )

