"""Runtime logging utilities for Lifesim."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from uuid import uuid4

from flask import current_app

from .extensions import db
from .models import SystemLog
from .settings.services import convert_to_active_timezone


@dataclass(frozen=True)
class LogRecord:
    """Structured representation of a log message."""

    component: str
    action: str
    level: str
    result: str
    title: str
    user_summary: str
    technical_details: str
    correlation_id: str
    environment: str


class LogManager:
    """Manage structured logging for the application."""

    def __init__(self) -> None:
        self.app = None
        self.available_levels = ["info", "warn", "error"]
        self.available_components: list[str] = []

    def init_app(self, app) -> None:
        """Attach the log manager to the Flask app."""
        self.app = app

    def _ensure_component(self, component: str) -> None:
        if component not in self.available_components:
            self.available_components.append(component)
            self.available_components.sort()

    def register_component(self, component: str) -> None:
        """Explicitly register a component name."""
        self._ensure_component(component)

    def record(
        self,
        *,
        component: str,
        action: str,
        level: str = "info",
        result: str = "success",
        title: str,
        user_summary: str,
        technical_details: str,
        correlation_id: Optional[str] = None,
    ) -> LogRecord:
        """Persist a new log record."""
        if level not in self.available_levels:
            raise ValueError(f"Unsupported level '{level}'")

        self._ensure_component(component)
        environment = (self.app or current_app).config.get("ENVIRONMENT", "development")
        correlation = correlation_id or str(uuid4())

        entry = SystemLog(
            component=component,
            action=action,
            level=level,
            result=result,
            title=title,
            user_summary=user_summary,
            technical_details=technical_details,
            correlation_id=correlation,
            environment=environment,
        )
        db.session.add(entry)

        retention = (self.app or current_app).config.get("LOG_RETENTION", 200)
        self._trim_logs(retention)

        db.session.commit()

        return LogRecord(
            component=component,
            action=action,
            level=level,
            result=result,
            title=title,
            user_summary=user_summary,
            technical_details=technical_details,
            correlation_id=correlation,
            environment=environment,
        )

    def _trim_logs(self, retention: int) -> None:
        """Keep the number of stored logs under the configured retention."""
        total = SystemLog.query.count()
        if total <= retention:
            return
        # delete oldest entries beyond retention
        excess = total - retention
        oldest_ids = [
            entry.id
            for entry in SystemLog.query.order_by(SystemLog.timestamp).limit(excess)
        ]
        if oldest_ids:
            SystemLog.query.filter(SystemLog.id.in_(oldest_ids)).delete(synchronize_session=False)

    def fetch_logs(
        self,
        *,
        level: Optional[str] = None,
        component: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict[str, str]]:
        """Retrieve structured logs with optional filtering."""
        query = SystemLog.query.order_by(SystemLog.timestamp.desc())
        if level and level in self.available_levels:
            query = query.filter_by(level=level)
        if component:
            query = query.filter_by(component=component)
        if search:
            like_pattern = f"%{search}%"
            query = query.filter(
                (SystemLog.title.ilike(like_pattern))
                | (SystemLog.user_summary.ilike(like_pattern))
                | (SystemLog.technical_details.ilike(like_pattern))
                | (SystemLog.correlation_id.ilike(like_pattern))
            )
        records = query.limit(limit).all()
        return [record.serialize() for record in records]

    def latest_timestamp(self) -> Optional[str]:
        """Return ISO formatted timestamp of the most recent log entry."""
        record = SystemLog.query.order_by(SystemLog.timestamp.desc()).first()
        if not record:
            return None
        localized = convert_to_active_timezone(record.timestamp)
        return localized.isoformat(timespec="seconds")


log_manager = LogManager()
