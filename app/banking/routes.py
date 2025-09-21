"""Routes for the Lifesim banking system."""
from __future__ import annotations

from copy import deepcopy
from typing import Iterable

from flask import render_template

from ..logging_service import log_manager
from . import bp

ACCOUNTS: list[dict[str, object]] = [
    {"id": "hand", "name": "Money on Hand", "balance": 280.50, "type": "Liquid Cash"},
    {
        "id": "checking",
        "name": "Checking Account",
        "balance": 5400.25,
        "type": "Daily Spending",
    },
    {
        "id": "savings",
        "name": "Savings Account",
        "balance": 8200.00,
        "type": "Emergency Fund",
    },
]

INITIAL_TRANSACTIONS: list[dict[str, object]] = [
    {
        "name": "Cash Allocation",
        "description": "Wallet deposit into Checking Account",
        "amount": 2650.00,
        "direction": "credit",
        "account": "checking",
    },
    {
        "name": "Cash Allocation",
        "description": "Wallet deposit into Savings Account",
        "amount": 500.00,
        "direction": "credit",
        "account": "savings",
    },
    {
        "name": "Cash Withdrawal",
        "description": "Funds moved from Checking Account to cash on hand",
        "amount": 150.00,
        "direction": "debit",
        "account": "checking",
    },
]

ACCOUNT_INSIGHTS: list[dict[str, object]] = [
    {
        "account": "Money on Hand",
        "details": [
            {
                "label": "Fees",
                "value": "No direct fees, but untracked spending can cause reconciliation drift.",
            },
            {
                "label": "Recommended buffer",
                "value": "Keep at least $200 available for daily cash needs.",
            },
        ],
    },
    {
        "account": "Checking Account",
        "details": [
            {
                "label": "Overdraft fee",
                "value": "$35 per occurrence when the balance dips below $0.",
            },
            {
                "label": "Monthly maintenance",
                "value": "$5 (waived with a $1,500 average daily balance).",
            },
            {
                "label": "ATM network",
                "value": "Four out-of-network withdrawals refunded each cycle; $3 thereafter.",
            },
        ],
    },
    {
        "account": "Savings Account",
        "details": [
            {
                "label": "Interest rate",
                "value": "2.10% APY calculated on the monthly average balance.",
            },
            {
                "label": "Transfer allowance",
                "value": "Three free transfers per month; $8 fee for additional moves.",
            },
            {
                "label": "Minimum balance",
                "value": "$300 minimum to avoid a $3 low-balance charge.",
            },
        ],
    },
]


def _account_snapshot() -> list[dict[str, object]]:
    """Return a copy of the configured account balances."""
    return deepcopy(ACCOUNTS)


def _build_banking_state(accounts: Iterable[dict[str, object]]) -> dict[str, object]:
    """Construct the state payload used by the transfer interface."""
    account_list = list(accounts)
    account_labels = {account["id"]: account["name"] for account in account_list}
    balances = {
        account["id"]: {"label": account["name"], "balance": account["balance"]}
        for account in account_list
    }
    return {
        "balances": balances,
        "transactions": deepcopy(INITIAL_TRANSACTIONS),
        "account_labels": account_labels,
    }


def _log_cash_health(accounts: Iterable[dict[str, object]]) -> None:
    """Emit warnings if liquid cash drops below the healthy threshold."""
    for account in accounts:
        if account.get("id") == "hand" and float(account.get("balance", 0)) < 150:
            log_manager.record(
                component="Banking",
                action="cash-check",
                level="warn",
                result="warn",
                title="Cash on hand trending low",
                user_summary=(
                    "Cash on hand fell below $150. Consider moving funds from checking or savings."
                ),
                technical_details=(
                    "banking.cash_monitor detected low liquidity in physical cash reserves."
                ),
            )
            break


@bp.route("/")
def home():
    """Display the banking overview and account information."""
    log_manager.record(
        component="Banking",
        action="view-home",
        level="info",
        result="success",
        title="Banking home opened",
        user_summary="Banking overview displayed for the player.",
        technical_details="banking.home rendered account balances and fee breakdowns.",
    )
    accounts = _account_snapshot()
    _log_cash_health(accounts)

    return render_template(
        "banking/home.html",
        title="Lifesim — Banking Home",
        accounts=accounts,
        account_insights=deepcopy(ACCOUNT_INSIGHTS),
        active_nav="banking",
        active_banking_tab="home",
    )


@bp.route("/transfer")
def transfer():
    """Surface the cash transfer workflow on a dedicated page."""
    log_manager.record(
        component="Banking",
        action="view-transfer",
        level="info",
        result="success",
        title="Banking transfer center opened",
        user_summary="Transfer interface loaded for cash and account movements.",
        technical_details="banking.transfer rendered cash movement forms and ledger.",
    )
    accounts = _account_snapshot()
    banking_state = _build_banking_state(accounts)
    _log_cash_health(accounts)

    return render_template(
        "banking/transfer.html",
        title="Lifesim — Banking Transfer",
        accounts=accounts,
        banking_state=banking_state,
        active_nav="banking",
        active_banking_tab="transfer",
    )
