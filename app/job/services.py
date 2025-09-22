"""Utilities that power the job system blueprint."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP, ROUND_UP
from typing import ClassVar


def _now() -> datetime:
    """Return the current UTC timestamp."""

    return datetime.now(UTC)


def _quantize_currency(value: Decimal | float | str) -> Decimal:
    """Normalize numeric input to two decimal places."""

    if isinstance(value, Decimal):
        decimal_value = value
    else:
        decimal_value = Decimal(str(value))
    return decimal_value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _format_currency(value: Decimal) -> str:
    """Format currency using standard USD formatting."""

    quantized = _quantize_currency(value)
    return f"${quantized:,.2f}"


def _format_reset_label(hour: int) -> str:
    """Return a human-friendly description of the reset time."""

    hour = max(0, min(hour, 23))
    suffix = "AM" if hour < 12 else "PM"
    display_hour = hour % 12 or 12
    return f"{display_hour:02d}:00 {suffix}"


def _resolve_reset_boundary(moment: datetime, reset_hour: int) -> datetime:
    """Return the timestamp representing the most recent reset."""

    boundary = moment.replace(hour=reset_hour, minute=0, second=0, microsecond=0)
    if moment.hour < reset_hour:
        boundary -= timedelta(days=1)
    return boundary


@dataclass
class JobSettings:
    """Configuration values that impact the job system."""

    minimum_hourly_wage: Decimal = Decimal("15.00")
    default_daily_limit: int = 3
    limit_reset_hour: int = 0
    payroll_company_name: str = "Lifesim Career Services"

    def to_dict(self) -> dict[str, object]:
        """Serialize settings for templates and JSON responses."""

        return {
            "minimum_hourly_wage": float(self.minimum_hourly_wage),
            "minimum_hourly_wage_display": _format_currency(self.minimum_hourly_wage),
            "default_daily_limit": self.default_daily_limit,
            "daily_reset_hour": self.limit_reset_hour,
            "daily_reset_label": _format_reset_label(self.limit_reset_hour),
            "reset_summary": (
                "Job limits refresh each day at {}.".format(
                    _format_reset_label(self.limit_reset_hour)
                )
            ),
            "payroll_company_name": self.payroll_company_name,
        }


@dataclass
class Job:
    """In-memory representation of a job listing."""

    id: str
    title: str
    description: str
    pay_type: str
    pay_rate: Decimal
    daily_limit: int | None = None
    completions_today: int = 0
    last_reset: datetime = field(default_factory=_now)
    minimum_applied: bool = False
    active_session_started_at: datetime | None = None
    active_session_seconds: int = 0

    def __post_init__(self) -> None:
        """Ensure stored values remain normalized."""

        self.pay_type = self.pay_type.lower()
        self.pay_rate = _quantize_currency(self.pay_rate)
        if self.daily_limit is not None and self.daily_limit <= 0:
            self.daily_limit = None
        self.last_reset = self.last_reset or _now()
        self.active_session_seconds = max(int(self.active_session_seconds), 0)

    @property
    def has_limit(self) -> bool:
        """Return True when the job has a daily cap."""

        return self.daily_limit is not None

    @property
    def remaining_today(self) -> int | None:
        """Expose how many completions remain for the current reset period."""

        if not self.has_limit:
            return None
        remaining = max(self.daily_limit - self.completions_today, 0)
        return remaining

    @property
    def is_available(self) -> bool:
        """Flag whether the job can be performed right now."""

        remaining = self.remaining_today
        return remaining is None or remaining > 0

    def refresh_limit(self, *, reset_hour: int) -> None:
        """Reset the completion counter if a new day has begun."""

        if not self.has_limit:
            return

        now = _now()
        boundary = _resolve_reset_boundary(now, reset_hour)
        if self.last_reset < boundary:
            self.completions_today = 0
            self.last_reset = boundary
            self.reset_session()

    @property
    def is_session_active(self) -> bool:
        """Return True when a time-based session is actively running."""

        return self.active_session_started_at is not None

    def start_session(self) -> None:
        """Begin tracking time for a time-based job."""

        if self.is_session_active:
            raise ValueError("Job already has an active session.")
        self.active_session_started_at = _now()

    def pause_session(self) -> None:
        """Pause the current session and accumulate elapsed seconds."""

        if not self.is_session_active:
            return
        elapsed = int((_now() - self.active_session_started_at).total_seconds())
        self.active_session_seconds = max(self.active_session_seconds + max(elapsed, 0), 0)
        self.active_session_started_at = None

    def reset_session(self) -> None:
        """Clear any tracked session progress."""

        self.active_session_started_at = None
        self.active_session_seconds = 0

    def total_session_seconds(self) -> int:
        """Return accumulated seconds including the active session."""

        total = self.active_session_seconds
        if self.is_session_active:
            total += max(int((_now() - self.active_session_started_at).total_seconds()), 0)
        return max(total, 0)

    def calculate_session_earnings(self) -> Decimal:
        """Compute earnings for the tracked session rounded up to cents."""

        seconds = self.total_session_seconds()
        if seconds <= 0:
            return Decimal("0.00")
        hours = Decimal(seconds) / Decimal(3600)
        amount = hours * self.pay_rate
        return amount.quantize(Decimal("0.01"), rounding=ROUND_UP)

    def to_dict(self, settings: JobSettings) -> dict[str, object]:
        """Return job details for both templates and JSON consumers."""

        is_time_based = self.pay_type == "time"
        pay_type_label = "Time-based" if is_time_based else "Task-based"
        rate_display = _format_currency(self.pay_rate)
        rate_display = (
            f"{rate_display} / hr" if is_time_based else f"{rate_display} per task"
        )
        limit_display = (
            "Unlimited daily completions"
            if not self.has_limit
            else f"Up to {self.daily_limit} per day"
        )
        remaining = self.remaining_today
        if remaining is None:
            remaining_display = "Unlimited availability"
            status = "available"
            status_label = "Available"
        elif remaining > 0:
            remaining_display = f"{remaining} remaining today"
            status = "available"
            status_label = "Available"
        else:
            remaining_display = "Limit reached"
            status = "full"
            status_label = "Limit reached"

        if is_time_based:
            if self.minimum_applied:
                note = "This hourly rate meets the minimum wage of {}.".format(
                    _format_currency(settings.minimum_hourly_wage)
                )
            else:
                note = "Hourly work respects the minimum wage of {}.".format(
                    _format_currency(settings.minimum_hourly_wage)
                )
        else:
            note = "Task-based work pays this amount each completion."

        session_seconds = self.active_session_seconds
        session_started_at = self.active_session_started_at
        if session_started_at and session_seconds < 0:
            session_seconds = 0
        total_session_seconds = self.total_session_seconds() if is_time_based else 0
        session_earnings = (
            self.calculate_session_earnings() if is_time_based else Decimal("0.00")
        )

        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "pay_type": self.pay_type,
            "pay_type_label": pay_type_label,
            "rate": float(self.pay_rate),
            "rate_display": rate_display,
            "rate_unit_label": "Per hour" if is_time_based else "Per task",
            "daily_limit": self.daily_limit,
            "daily_limit_display": limit_display,
            "remaining_today": remaining,
            "remaining_display": remaining_display,
            "status": status,
            "status_label": status_label,
            "is_available": status == "available",
            "completions_today": self.completions_today,
            "reset_label": _format_reset_label(settings.limit_reset_hour),
            "note": note,
            "minimum_applied": self.minimum_applied,
            "active_session_seconds": session_seconds,
            "active_session_total_seconds": total_session_seconds,
            "active_session_started_at": (
                session_started_at.isoformat() if session_started_at else None
            ),
            "active_session_earnings": float(session_earnings),
            "active_session_earnings_display": _format_currency(session_earnings)
            if is_time_based
            else _format_currency(Decimal("0.00")),
            "is_session_active": self.is_session_active,
        }


class JobRepository:
    """Simple in-memory store that manages job data."""

    _jobs: ClassVar[dict[str, Job]] = {}
    _sequence: ClassVar[int] = 1
    _settings: ClassVar[JobSettings] = JobSettings()

    @classmethod
    def all(cls) -> list[Job]:
        """Return all jobs after ensuring limits are refreshed."""

        cls._refresh_limits()
        return sorted(cls._jobs.values(), key=lambda job: job.title)

    @classmethod
    def get(cls, job_id: str) -> Job | None:
        """Return a single job by identifier."""

        cls._refresh_limits()
        return cls._jobs.get(job_id)

    @classmethod
    def create(
        cls,
        *,
        title: str,
        description: str,
        pay_type: str,
        pay_rate: Decimal | float | str,
        daily_limit: int | None,
    ) -> Job:
        """Create and store a new job listing."""

        normalized_type = pay_type.lower()
        cls._validate_pay_type(normalized_type)
        normalized_rate = cls._normalize_rate(normalized_type, pay_rate)
        limit = cls._normalize_limit(daily_limit)

        job_id = str(cls._sequence)
        cls._sequence += 1

        job = Job(
            id=job_id,
            title=title.strip(),
            description=description.strip(),
            pay_type=normalized_type,
            pay_rate=normalized_rate,
            daily_limit=limit,
            completions_today=0,
            last_reset=_resolve_reset_boundary(_now(), cls._settings.limit_reset_hour),
            minimum_applied=normalized_rate == cls._settings.minimum_hourly_wage
            if normalized_type == "time"
            else False,
        )
        cls._jobs[job_id] = job
        return job

    @classmethod
    def update(
        cls,
        job_id: str,
        *,
        title: str,
        description: str,
        pay_type: str,
        pay_rate: Decimal | float | str,
        daily_limit: int | None,
    ) -> Job:
        """Update an existing job listing."""

        job = cls._jobs.get(job_id)
        if job is None:
            raise KeyError(job_id)

        normalized_type = pay_type.lower()
        cls._validate_pay_type(normalized_type)
        normalized_rate = cls._normalize_rate(normalized_type, pay_rate)
        limit = cls._normalize_limit(daily_limit)

        job.title = title.strip()
        job.description = description.strip()
        job.pay_type = normalized_type
        job.pay_rate = normalized_rate
        job.daily_limit = limit
        job.minimum_applied = (
            normalized_type == "time"
            and normalized_rate == cls._settings.minimum_hourly_wage
        )
        if normalized_type != "time":
            job.reset_session()
        return job

    @classmethod
    def delete(cls, job_id: str) -> bool:
        """Remove a job listing if it exists."""

        return cls._jobs.pop(job_id, None) is not None

    @classmethod
    def settings(cls) -> JobSettings:
        """Expose the mutable settings object."""

        return cls._settings

    @classmethod
    def update_settings(
        cls,
        *,
        minimum_hourly_wage: Decimal | float | str | None = None,
        default_daily_limit: int | None = None,
        daily_reset_hour: int | None = None,
        payroll_company_name: str | None = None,
    ) -> JobSettings:
        """Update job configuration and enforce new rules."""

        if minimum_hourly_wage is not None:
            new_wage = _quantize_currency(minimum_hourly_wage)
            if new_wage <= 0:
                raise ValueError("Minimum wage must be greater than zero.")
            cls._settings.minimum_hourly_wage = new_wage
            cls._enforce_minimum_wage()

        if default_daily_limit is not None:
            if default_daily_limit < 0:
                raise ValueError("Default daily limit cannot be negative.")
            cls._settings.default_daily_limit = default_daily_limit

        if daily_reset_hour is not None:
            if not 0 <= daily_reset_hour <= 23:
                raise ValueError("Reset hour must be between 0 and 23.")
            cls._settings.limit_reset_hour = daily_reset_hour
            cls._refresh_limits(force=True)

        if payroll_company_name is not None:
            company = payroll_company_name.strip()
            if not company:
                raise ValueError("Provide a company name for job payments.")
            cls._settings.payroll_company_name = company

        return cls._settings

    @classmethod
    def serialize_jobs(cls) -> list[dict[str, object]]:
        """Return all jobs in a JSON-friendly format."""

        settings = cls._settings
        return [job.to_dict(settings) for job in cls.all()]

    @classmethod
    def seed_defaults(cls) -> None:
        """Populate the repository with a few starter jobs."""

        if cls._jobs:
            return

        cls.create(
            title="Freelance UI Sprint",
            description=(
                "Deliver pixel-polished interface updates for client dashboards. Track milestones"
                " and report progress at the end of each shift."
            ),
            pay_type="time",
            pay_rate=Decimal("24.50"),
            daily_limit=2,
        )
        cls.create(
            title="Courier Delivery Route",
            description=(
                "Cover the afternoon delivery route across downtown. Includes pickups and drop-offs"
                " with mileage reimbursement."
            ),
            pay_type="time",
            pay_rate=Decimal("18.00"),
            daily_limit=1,
        )
        research = cls.create(
            title="Product Survey Reviews",
            description=(
                "Audit consumer survey responses for clarity and categorize feedback into actionable"
                " insights."
            ),
            pay_type="task",
            pay_rate=Decimal("32.00"),
            daily_limit=5,
        )
        research.completions_today = 1
        bugfix = cls.create(
            title="Bug Fix Bounty",
            description=(
                "Resolve prioritized issues reported by QA. Each task includes reproduction steps"
                " and an acceptance checklist."
            ),
            pay_type="task",
            pay_rate=Decimal("75.00"),
            daily_limit=2,
        )
        bugfix.completions_today = 2

    @classmethod
    def _validate_pay_type(cls, pay_type: str) -> None:
        if pay_type not in {"time", "task"}:
            raise ValueError("Unsupported pay type.")

    @classmethod
    def _normalize_rate(
        cls, pay_type: str, pay_rate: Decimal | float | str
    ) -> Decimal:
        rate = _quantize_currency(pay_rate)
        if rate <= 0:
            raise ValueError("Pay rate must be greater than zero.")

        if pay_type == "time" and rate < cls._settings.minimum_hourly_wage:
            return cls._settings.minimum_hourly_wage
        return rate

    @staticmethod
    def _normalize_limit(daily_limit: int | None) -> int | None:
        if daily_limit in (None, ""):
            return None
        limit = int(daily_limit)
        if limit <= 0:
            return None
        return limit

    @classmethod
    def _refresh_limits(cls, *, force: bool = False) -> None:
        reset_hour = cls._settings.limit_reset_hour
        for job in cls._jobs.values():
            if force:
                job.last_reset = _resolve_reset_boundary(_now(), reset_hour)
                if job.has_limit:
                    job.completions_today = min(job.completions_today, job.daily_limit or 0)
                job.reset_session()
            job.refresh_limit(reset_hour=reset_hour)

    @classmethod
    def _enforce_minimum_wage(cls) -> None:
        minimum = cls._settings.minimum_hourly_wage
        for job in cls._jobs.values():
            if job.pay_type == "time" and job.pay_rate < minimum:
                job.pay_rate = minimum
                job.minimum_applied = True
            elif job.pay_type == "time":
                job.minimum_applied = job.pay_rate == minimum

    @classmethod
    def start_time_job(cls, job_id: str) -> Job:
        """Begin or resume a time-based job session."""

        job = cls._jobs.get(job_id)
        if job is None:
            raise KeyError(job_id)
        if job.pay_type != "time":
            raise ValueError("Only time-based jobs can be started.")
        if job.is_session_active:
            raise ValueError("This job is already running.")
        remaining = job.remaining_today
        if remaining == 0:
            raise ValueError("This job has reached its daily limit.")
        job.start_session()
        return job

    @classmethod
    def pause_time_job(cls, job_id: str) -> Job:
        """Pause an active time-based job session."""

        job = cls._jobs.get(job_id)
        if job is None:
            raise KeyError(job_id)
        if job.pay_type != "time":
            raise ValueError("Only time-based jobs can be paused.")
        if not job.is_session_active:
            raise ValueError("This job is not currently running.")
        job.pause_session()
        return job

    @classmethod
    def complete_job(cls, job_id: str) -> tuple[Job, Decimal]:
        """Mark a job as complete and return the earnings."""

        job = cls._jobs.get(job_id)
        if job is None:
            raise KeyError(job_id)

        if job.pay_type == "task":
            return cls._complete_task_job(job)
        if job.pay_type == "time":
            return cls._complete_time_job(job)
        raise ValueError("Unsupported job type.")

    @staticmethod
    def _complete_task_job(job: Job) -> tuple[Job, Decimal]:
        if not job.is_available:
            raise ValueError("No remaining task completions are available today.")
        job.completions_today += 1
        return job, job.pay_rate

    @staticmethod
    def _complete_time_job(job: Job) -> tuple[Job, Decimal]:
        if job.is_session_active:
            job.pause_session()
        total_seconds = job.total_session_seconds()
        if total_seconds <= 0:
            raise ValueError("Start the job before completing it.")
        if job.has_limit and job.remaining_today == 0 and total_seconds <= 0:
            raise ValueError("This job has reached its daily limit.")
        earnings = job.calculate_session_earnings()
        job.reset_session()
        job.completions_today += 1
        return job, earnings


# Seed the repository with initial data when the module loads.
JobRepository.seed_defaults()

