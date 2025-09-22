"""Blueprint for global Lifesim settings."""
from __future__ import annotations

from flask import Blueprint

bp = Blueprint(
    "settings",
    __name__,
    template_folder="templates",
    static_folder="static",
)
