"""Tests for banking routes covering account opening flows."""

from __future__ import annotations

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
