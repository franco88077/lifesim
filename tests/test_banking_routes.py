"""Tests for banking routes covering account opening flows."""

from __future__ import annotations

from pathlib import Path
import sys

import pytest
from sqlalchemy.pool import StaticPool

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app
from app.config import Config
from app.extensions import db


class TestingConfig(Config):
    """Configuration tuned for isolated unit tests."""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_ENGINE_OPTIONS = {
        "connect_args": {"check_same_thread": False},
        "poolclass": StaticPool,
    }


@pytest.fixture()
def app():
    """Create a Flask app instance backed by an in-memory database."""

    application = create_app(TestingConfig)
    yield application
    with application.app_context():
        db.drop_all()
        db.session.remove()


@pytest.fixture()
def client(app):
    """Provide a Flask test client for request assertions."""

    return app.test_client()


def test_api_open_accounts_accepts_valid_payload(client):
    """Valid account opening requests should succeed and return updated balances."""

    payload = {
        "accounts": {
            "checking": {"deposit": "100.00"},
            "savings": {"deposit": "50"},
        }
    }

    response = client.post("/banking/api/accounts/open", json=payload)

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert (
        data["message"]
        == "Opened Checking Account, Savings Account with $150.00 transferred from cash."
    )
    assert data["cash_balance"] == "$350.00"
    account_names = {account["name"] for account in data["accounts"]}
    assert {"Checking Account", "Savings Account"} <= account_names
