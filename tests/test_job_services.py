from datetime import timedelta
from decimal import Decimal

import pytest

from app.job.services import JobRepository, JobSettings


@pytest.fixture(autouse=True)
def isolate_job_repository():
    original_jobs = JobRepository._jobs
    original_sequence = JobRepository._sequence
    original_settings = JobRepository._settings
    JobRepository._jobs = {}
    JobRepository._sequence = 1
    JobRepository._settings = JobSettings()
    try:
        yield
    finally:
        JobRepository._jobs = original_jobs
        JobRepository._sequence = original_sequence
        JobRepository._settings = original_settings


def test_complete_task_job_returns_rate_and_updates_remaining():
    job = JobRepository.create(
        title="Task",
        description="Complete a task",
        pay_type="task",
        pay_rate=Decimal("42.00"),
        daily_limit=2,
    )

    updated_job, amount = JobRepository.complete_job(job.id)

    assert amount == Decimal("42.00")
    assert updated_job.completions_today == 1
    assert updated_job.remaining_today == 1


def test_time_job_rounds_up_to_nearest_cent():
    job = JobRepository.create(
        title="Shift",
        description="Hourly work",
        pay_type="time",
        pay_rate=Decimal("20.00"),
        daily_limit=None,
    )

    JobRepository.start_time_job(job.id)
    job.active_session_started_at -= timedelta(minutes=10, seconds=10)

    updated_job, amount = JobRepository.complete_job(job.id)

    assert amount == Decimal("3.39")
    assert updated_job.completions_today == 1
    assert not updated_job.is_session_active
    assert updated_job.active_session_seconds == 0


def test_pause_and_resume_time_job_tracks_elapsed_time():
    job = JobRepository.create(
        title="Support",
        description="Assist customers",
        pay_type="time",
        pay_rate=Decimal("18.00"),
        daily_limit=3,
    )

    JobRepository.start_time_job(job.id)
    job.active_session_started_at -= timedelta(minutes=5)
    paused_job = JobRepository.pause_time_job(job.id)

    assert paused_job.active_session_seconds >= 300
    assert not paused_job.is_session_active

    resumed_job = JobRepository.start_time_job(job.id)
    assert resumed_job.is_session_active


def test_cannot_start_time_job_after_limit_reached():
    job = JobRepository.create(
        title="Design",
        description="Design session",
        pay_type="time",
        pay_rate=Decimal("30.00"),
        daily_limit=1,
    )

    JobRepository.start_time_job(job.id)
    job.active_session_started_at -= timedelta(minutes=15)
    JobRepository.complete_job(job.id)

    with pytest.raises(ValueError):
        JobRepository.start_time_job(job.id)
