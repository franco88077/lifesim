"""Database models for global Lifesim settings."""
from __future__ import annotations

from datetime import datetime

from ..extensions import db


class AppSettings(db.Model):
    """Persisted configuration shared across the entire application."""

    id: int = db.Column(db.Integer, primary_key=True)
    timezone: str = db.Column(db.String(64), nullable=False, default="UTC")
    created_at: datetime = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at: datetime = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"<AppSettings timezone={self.timezone}>"
