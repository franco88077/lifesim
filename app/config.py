"""Configuration settings for Lifesim."""
from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class Config:
    """Base configuration class."""

    SECRET_KEY = os.environ.get("LIFESIM_SECRET_KEY", "lifesim-dev-key")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "LIFESIM_DATABASE_URI", f"sqlite:///{BASE_DIR / 'lifesim.db'}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    ENVIRONMENT = os.environ.get("LIFESIM_ENV", "development")
    LOG_RETENTION = int(os.environ.get("LIFESIM_LOG_RETENTION", 200))
