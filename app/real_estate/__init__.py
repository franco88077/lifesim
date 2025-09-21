"""Real estate management blueprint."""
from flask import Blueprint

bp = Blueprint(
    "real_estate",
    __name__,
    template_folder="templates",
    static_folder="static",
)

from . import routes  # noqa: E402,F401
