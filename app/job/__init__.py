"""Job tracker blueprint."""
from flask import Blueprint

bp = Blueprint(
    "job",
    __name__,
    template_folder="templates",
    static_folder="static",
)

from . import routes  # noqa: E402,F401
