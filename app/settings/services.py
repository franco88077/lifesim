"""Utility functions for managing global Lifesim settings."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import List
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from ..extensions import db
from .models import AppSettings

AVAILABLE_TIMEZONES: tuple[tuple[str, str], ...] = (
    ("UTC", "Coordinated Universal Time"),
    ("America/New_York", "Eastern Time — US & Canada"),
    ("America/Chicago", "Central Time — US & Canada"),
    ("America/Denver", "Mountain Time — US & Canada"),
    ("America/Los_Angeles", "Pacific Time — US & Canada"),
    ("Europe/London", "Greenwich Mean Time"),
    ("Europe/Berlin", "Central European Time"),
    ("Asia/Kolkata", "India Standard Time"),
    ("Asia/Tokyo", "Japan Standard Time"),
    ("Australia/Sydney", "Australian Eastern Time"),
)

_timezone_cache: dict[str, ZoneInfo] = {}
_cached_timezone_name: str | None = None


@dataclass(frozen=True)
class TimezoneOption:
    """Simple representation of a selectable timezone."""

    value: str
    label: str
    offset: str

    @property
    def display_label(self) -> str:
        """Combine the label and offset for user-friendly rendering."""

        return f"{self.label} ({self.offset})"


def _resolve_zoneinfo(name: str) -> ZoneInfo:
    """Return a ZoneInfo instance for the provided timezone name."""

    zone = _timezone_cache.get(name)
    if zone:
        return zone
    try:
        zone = ZoneInfo(name)
    except ZoneInfoNotFoundError:
        zone = ZoneInfo("UTC")
    _timezone_cache[name] = zone
    return zone


def _normalize_timezone_choice(value: str | None) -> str:
    """Ensure submitted values map to a supported timezone."""

    valid_names = {choice[0] for choice in AVAILABLE_TIMEZONES}
    if value in valid_names:
        return value  # type: ignore[return-value]
    return "UTC"


def ensure_app_settings() -> AppSettings:
    """Create application settings with defaults when missing."""

    settings = AppSettings.query.first()
    changed = False

    if not settings:
        settings = AppSettings(timezone="UTC")
        db.session.add(settings)
        changed = True
    elif not settings.timezone:
        settings.timezone = "UTC"
        db.session.add(settings)
        changed = True

    if changed:
        db.session.commit()

    return settings


def get_app_settings() -> AppSettings:
    """Return the persisted application settings."""

    return ensure_app_settings()


def get_active_timezone_name() -> str:
    """Return the currently configured timezone identifier."""

    settings = ensure_app_settings()
    global _cached_timezone_name
    if _cached_timezone_name != settings.timezone:
        _cached_timezone_name = settings.timezone or "UTC"
    return _cached_timezone_name or "UTC"


def get_active_timezone() -> ZoneInfo:
    """Return the ZoneInfo instance for the active timezone."""

    name = get_active_timezone_name()
    return _resolve_zoneinfo(name)


def set_timezone(choice: str) -> AppSettings:
    """Persist a new timezone selection for the application."""

    settings = ensure_app_settings()
    settings.timezone = _normalize_timezone_choice(choice)
    db.session.add(settings)
    db.session.commit()

    # refresh cache so other components see the update immediately
    global _cached_timezone_name
    _cached_timezone_name = settings.timezone
    _resolve_zoneinfo(settings.timezone)  # prime cache with the updated timezone

    return settings


def _format_offset(delta: timedelta | None) -> str:
    """Return a printable UTC offset string."""

    if delta is None:
        return "UTC±00:00"
    minutes = int(delta.total_seconds() // 60)
    sign = "+" if minutes >= 0 else "-"
    minutes = abs(minutes)
    hours, remainder = divmod(minutes, 60)
    return f"UTC{sign}{hours:02d}:{remainder:02d}"


def get_timezone_options() -> list[TimezoneOption]:
    """Return curated timezone options for the settings interface."""

    now_utc = datetime.now(timezone.utc)
    options: List[TimezoneOption] = []
    for value, label in AVAILABLE_TIMEZONES:
        zone = _resolve_zoneinfo(value)
        offset = _format_offset(now_utc.astimezone(zone).utcoffset())
        options.append(TimezoneOption(value=value, label=label, offset=offset))
    return options


def describe_timezone(name: str | None) -> str:
    """Return a friendly label for the selected timezone."""

    if not name:
        name = "UTC"
    for value, label in AVAILABLE_TIMEZONES:
        if value == name:
            zone = _resolve_zoneinfo(name)
            now_utc = datetime.now(timezone.utc)
            offset = _format_offset(now_utc.astimezone(zone).utcoffset())
            return f"{label} ({offset})"
    zone = _resolve_zoneinfo(name)
    now_utc = datetime.now(timezone.utc)
    offset = _format_offset(now_utc.astimezone(zone).utcoffset())
    return f"{name} ({offset})"


def convert_to_active_timezone(value: datetime) -> datetime:
    """Convert a naive UTC datetime to the configured timezone."""

    if not isinstance(value, datetime):
        raise TypeError("Datetime objects are required for timezone conversion")

    zone = get_active_timezone()
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    else:
        value = value.astimezone(timezone.utc)
    return value.astimezone(zone)


def current_datetime() -> datetime:
    """Return the current datetime localized to the active timezone."""

    zone = get_active_timezone()
    return datetime.now(zone)


def current_date() -> date:
    """Return today's date in the configured timezone."""

    return current_datetime().date()


def format_datetime_for_display(value: datetime, fmt: str = "%b %d, %Y") -> str:
    """Return a formatted datetime string using the active timezone."""

    localized = convert_to_active_timezone(value)
    return localized.strftime(fmt)
