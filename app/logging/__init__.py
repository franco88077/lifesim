"""Blueprint exposing log endpoints."""
from flask import Blueprint

bp = Blueprint(
    "logging",
    __name__,
    template_folder="templates",
    static_folder="static",
)

from . import routes  # noqa: E402,F401
