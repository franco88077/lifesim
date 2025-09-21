"""Routes for the Lifesim home hub."""
from __future__ import annotations

from flask import render_template

from ..banking.services import (
    decimal_to_number,
    ensure_bank_defaults,
    fetch_accounts,
    format_currency,
    get_bank_settings,
)
from ..logging_service import log_manager
from . import bp


@bp.route("/")
def home():
    """Render the main dashboard hub."""
    ensure_bank_defaults()
    settings = get_bank_settings()
    accounts = fetch_accounts()

    cash_account = next((account for account in accounts if account.slug == "hand"), None)
    cash_balance = cash_account.balance if cash_account else 0
    available_cash = format_currency(cash_balance)
    available_cash_value = decimal_to_number(cash_balance)
    account_slugs = {account.slug for account in accounts if account.slug != "hand"}
    missing_accounts = [slug for slug in ("checking", "savings") if slug not in account_slugs]
    has_any_accounts = bool(account_slugs)

    log_manager.record(
        component="Home",
        action="view",
        level="info",
        result="success",
        title="Homepage accessed",
        user_summary="Dashboard hub loaded successfully.",
        technical_details="index.home endpoint served Lifesim hub without issues.",
    )
    quick_metrics = {
        "balance": 12500,
        "credit_score": 720,
        "properties": 1,
        "job_hours": 12,
    }
    return render_template(
        "index/home.html",
        title="Lifesim — Home",
        metrics=quick_metrics,
        bank_settings=settings,
        available_cash=available_cash,
        available_cash_value=available_cash_value,
        has_bank_accounts=has_any_accounts,
        missing_accounts=missing_accounts,
        account_opening_requirements={
            "checking": format_currency(settings.checking_opening_deposit),
            "savings": format_currency(settings.savings_opening_deposit),
        },
        account_opening_requirements_value={
            "checking": decimal_to_number(settings.checking_opening_deposit),
            "savings": decimal_to_number(settings.savings_opening_deposit),
        },
        active_nav="home",
    )
