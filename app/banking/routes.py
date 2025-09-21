"""Routes for the Lifesim banking system."""
from __future__ import annotations

from flask import render_template

from ..logging_service import log_manager
from . import bp


@bp.route("/")
def dashboard():
    """Display banking overview."""
    log_manager.record(
        component="Banking",
        action="view",
        level="info",
        result="success",
        title="Banking dashboard opened",
        user_summary="Banking overview displayed for the user.",
        technical_details="banking.dashboard rendered account summaries and goals.",
    )
    accounts = [
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
    account_labels = {account["id"]: account["name"] for account in accounts}
    transactions = [
        {
            "name": "Direct Deposit",
            "description": "Paycheck from Blue Sky Studios",
            "amount": 2650.00,
            "direction": "credit",
            "account": "checking",
        },
        {
            "name": "Emergency Fund Allocation",
            "description": "Monthly auto-transfer into savings buffer",
            "amount": 500.00,
            "direction": "credit",
            "account": "savings",
        },
        {
            "name": "Weekend Budget",
            "description": "Pulled cash from checking for discretionary spending",
            "amount": 150.00,
            "direction": "debit",
            "account": "checking",
        },
    ]
    banking_state = {
        "balances": {
            "hand": {"label": account_labels["hand"], "balance": accounts[0]["balance"]},
            "checking": {
                "label": account_labels["checking"],
                "balance": accounts[1]["balance"],
            },
            "savings": {
                "label": account_labels["savings"],
                "balance": accounts[2]["balance"],
            },
        },
        "transactions": transactions,
        "account_labels": account_labels,
    }
    goals = [
        {"goal": "Vacation Fund", "target": 2000, "current": 1200},
        {"goal": "Student Loan", "target": 15000, "current": 4500},
    ]
    for goal in goals:
        progress = goal['current'] / goal['target'] if goal['target'] else 0
        if progress < 0.5:
            log_manager.record(
                component="Banking",
                action="goal-check",
                level="warn",
                result="warn",
                title=f"Goal {goal['goal']} behind schedule",
                user_summary=f"{goal['goal']} is {progress * 100:.0f}% funded. Consider allocating more savings.",
                technical_details="Banking goals analysis flagged a low funding ratio under 50 percent.",
            )
    if accounts[0]["balance"] < 150:
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
                "banking.dashboard detected low liquidity in physical cash reserves."
            ),
        )

    return render_template(
        "banking/dashboard.html",
        title="Lifesim — Banking",
        accounts=accounts,
        goals=goals,
        banking_state=banking_state,
        active_nav="banking",
    )
