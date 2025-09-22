"""Database models for Lifesim."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from .extensions import db
from .settings.services import convert_to_active_timezone


class SystemLog(db.Model):
    """Model representing a single system log entry."""

    id: int = db.Column(db.Integer, primary_key=True)
    timestamp: datetime = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    component: str = db.Column(db.String(64), nullable=False, index=True)
    action: str = db.Column(db.String(64), nullable=False)
    level: str = db.Column(db.String(16), nullable=False, index=True)
    result: str = db.Column(db.String(32), nullable=False)
    title: str = db.Column(db.String(120), nullable=False)
    user_summary: str = db.Column(db.Text, nullable=False)
    technical_details: str = db.Column(db.Text, nullable=False)
    correlation_id: Optional[str] = db.Column(db.String(36), index=True)
    environment: str = db.Column(db.String(20), default="development")

    def serialize(self) -> dict[str, str]:
        """Return a JSON-serializable representation of the log entry."""
        localized_timestamp = convert_to_active_timezone(self.timestamp)
        return {
            "id": self.id,
            "timestamp": localized_timestamp.isoformat(timespec="seconds"),
            "component": self.component,
            "action": self.action,
            "level": self.level,
            "result": self.result,
            "title": self.title,
            "user_summary": self.user_summary,
            "technical_details": self.technical_details,
            "correlation_id": self.correlation_id,
            "environment": self.environment,
        }

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"<SystemLog {self.level} {self.component} {self.action}>"
