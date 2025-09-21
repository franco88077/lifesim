"""Routes for the Lifesim banking system backed by the database."""
from __future__ import annotations

from decimal import Decimal
from typing import Iterable

from flask import jsonify, render_template, request
from sqlalchemy.exc import SQLAlchemyError

from ..extensions import db
from ..logging_service import log_manager
from . import bp
from .models import BankAccount, BankTransaction
from .services import (
    build_account_insights,
    build_banking_state,
    ensure_bank_defaults,
    fetch_accounts,
    fetch_recent_transactions,
    find_account,
    format_currency,
    get_bank_settings,
    normalize_interest_rate,
    quantize_amount,
    update_account_balance,
)


def _serialize_account(account: BankAccount) -> dict[str, object]:
    """Prepare account details for template rendering."""

    return {
        "id": account.slug,
        "name": account.name,
        "type": account.category,
        "balance": float(quantize_amount(account.balance)),
        "display_balance": format_currency(account.balance),
    }


def _serialize_transaction(transaction: BankTransaction) -> dict[str, object]:
    """Prepare transaction details for account activity listings."""

    account_name = transaction.account.name if transaction.account else "Unknown account"
    sign = "+" if transaction.direction == "credit" else "−"
    timestamp = transaction.created_at.strftime("%b %d, %Y")

    return {
        "id": transaction.id,
        "name": transaction.name,
        "description": transaction.description,
        "account_name": account_name,
        "direction": transaction.direction,
        "amount_display": f"{sign}{format_currency(transaction.amount)}",
        "timestamp": timestamp,
    }


def _log_cash_health(accounts: Iterable[BankAccount]) -> None:
    """Emit warnings if liquid cash drops below the healthy threshold."""

    for account in accounts:
        if account.slug == "hand" and account.balance < Decimal("150"):
            log_manager.record(
                component="Banking",
                action="cash-check",
                level="warn",
                result="warn",
                title="Cash balance trending low",
                user_summary=(
                    "Cash balance fell below $150. Consider moving funds from checking or savings."
                ),
                technical_details=(
                    "banking.cash_monitor detected low liquidity in cash reserves."
                ),
            )
            break


def _json_response(payload: dict[str, object], *, status: int = 200):
    """Return a JSON response with a consistent structure."""

    response = jsonify(payload)
    response.status_code = status
    return response


def _json_error(message: str, *, status: int = 400):
    """Return a JSON error payload with the supplied status."""

    return _json_response({"success": False, "message": message}, status=status)


@bp.route("/")
def home():
    """Display the banking overview and account information."""

    ensure_bank_defaults()
    settings = get_bank_settings()
    accounts = fetch_accounts()
    _log_cash_health(accounts)

    log_manager.record(
        component="Banking",
        action="view-home",
        level="info",
        result="success",
        title="Banking home opened",
        user_summary="Banking overview displayed for the player.",
        technical_details="banking.home rendered account balances and recent transactions.",
    )

    serialized_accounts = [_serialize_account(account) for account in accounts]
    transactions = fetch_recent_transactions(limit=12)
    serialized_transactions = [_serialize_transaction(tx) for tx in transactions]

    return render_template(
        "banking/home.html",
        title="Lifesim — Banking Home",
        accounts=serialized_accounts,
        recent_transactions=serialized_transactions,
        bank_settings=settings,
        active_nav="banking",
        active_banking_tab="home",
    )


@bp.route("/insights")
def insights():
    """Display account insight and fee information on a dedicated page."""

    ensure_bank_defaults()
    settings = get_bank_settings()

    log_manager.record(
        component="Banking",
        action="view-insights",
        level="info",
        result="success",
        title="Banking insights opened",
        user_summary="Account insight and fee guidance displayed for the player.",
        technical_details="banking.insights rendered the insight cards and policy notes.",
    )

    insights = build_account_insights(settings)

    return render_template(
        "banking/insights.html",
        title="Lifesim — Banking Insights",
        account_insights=insights,
        bank_settings=settings,
        active_nav="banking",
        active_banking_tab="insights",
    )


@bp.route("/transfer")
def transfer():
    """Surface the cash transfer workflow on a dedicated page."""

    ensure_bank_defaults()
    settings = get_bank_settings()
    accounts = fetch_accounts()
    banking_state = build_banking_state()
    _log_cash_health(accounts)

    log_manager.record(
        component="Banking",
        action="view-transfer",
        level="info",
        result="success",
        title="Banking transfer center opened",
        user_summary="Transfer interface loaded for cash and account movements.",
        technical_details="banking.transfer rendered cash movement forms and balance overview.",
    )

    serialized_accounts = [_serialize_account(account) for account in accounts]

    return render_template(
        "banking/transfer.html",
        title="Lifesim — Banking Transfer",
        accounts=serialized_accounts,
        banking_state=banking_state,
        bank_settings=settings,
        active_nav="banking",
        active_banking_tab="transfer",
    )


@bp.post("/api/transfer/deposit")
def api_deposit():
    """Move money from cash into a selected account."""

    ensure_bank_defaults()
    payload = request.get_json(silent=True) or {}
    destination_slug = (payload.get("destination") or "").strip()
    amount_raw = payload.get("amount")

    try:
        amount = quantize_amount(amount_raw)
    except (ValueError, TypeError):
        log_manager.record(
            component="Banking",
            action="deposit",
            level="error",
            result="error",
            title="Deposit rejected — invalid amount",
            user_summary="Transfer could not be processed because the amount was invalid.",
            technical_details="banking.api_deposit rejected payload due to invalid numeric input.",
        )
        return _json_error("Enter a valid deposit amount.")

    if amount <= 0:
        log_manager.record(
            component="Banking",
            action="deposit",
            level="warn",
            result="error",
            title="Deposit rejected — non-positive amount",
            user_summary="Transfer amount must be greater than zero.",
            technical_details="banking.api_deposit received a non-positive amount.",
        )
        return _json_error("Deposit amount must be greater than zero.")

    destination = find_account(destination_slug)
    hand = find_account("hand")

    if not destination:
        log_manager.record(
            component="Banking",
            action="deposit",
            level="error",
            result="error",
            title="Deposit rejected — unknown destination",
            user_summary="Select a valid account to receive the deposit.",
            technical_details=f"banking.api_deposit failed because destination '{destination_slug}' was missing.",
        )
        return _json_error("Select a valid destination account.")

    if not hand:
        log_manager.record(
            component="Banking",
            action="deposit",
            level="error",
            result="error",
            title="Deposit rejected — cash account missing",
            user_summary="Cash account is unavailable.",
            technical_details="banking.api_deposit could not locate the cash account.",
        )
        return _json_error("Cash balance is unavailable.")

    if amount > hand.balance:
        available = format_currency(hand.balance)
        log_manager.record(
            component="Banking",
            action="deposit",
            level="warn",
            result="error",
            title="Deposit rejected — insufficient cash",
            user_summary=f"Only {available} available in cash.",
            technical_details="banking.api_deposit prevented overdrawing the cash account.",
        )
        return _json_error(f"Only {available} available in cash.")

    description = f"Wallet deposit into {destination.name}"

    try:
        with db.session.begin():
            hand.balance = quantize_amount(hand.balance - amount)
            destination.balance = quantize_amount(destination.balance + amount)
            db.session.add(hand)
            db.session.add(destination)
            db.session.add(
                BankTransaction(
                    account=destination,
                    name="Cash Allocation",
                    description=description,
                    direction="credit",
                    amount=amount,
                )
            )
    except SQLAlchemyError as exc:
        db.session.rollback()
        log_manager.record(
            component="Banking",
            action="deposit",
            level="error",
            result="error",
            title="Deposit failed — database error",
            user_summary="The deposit could not be saved. Try again shortly.",
            technical_details=f"banking.api_deposit encountered {exc.__class__.__name__}: {exc}",
        )
        return _json_error("Unable to complete the deposit at this time.", status=500)

    state = build_banking_state()
    _log_cash_health(fetch_accounts())

    log_manager.record(
        component="Banking",
        action="deposit",
        level="info",
        result="success",
        title="Cash deposited",
        user_summary=f"Moved {format_currency(amount)} to {destination.name}.",
        technical_details=(
            "banking.api_deposit updated account balances and created a credit transaction entry."
        ),
    )

    message = f"Transferred {format_currency(amount)} to {destination.name}."
    return _json_response({"success": True, "message": message, "state": state})


@bp.post("/api/transfer/withdraw")
def api_withdraw():
    """Move money from an account back into cash."""

    ensure_bank_defaults()
    payload = request.get_json(silent=True) or {}
    source_slug = (payload.get("source") or "").strip()
    amount_raw = payload.get("amount")

    try:
        amount = quantize_amount(amount_raw)
    except (ValueError, TypeError):
        log_manager.record(
            component="Banking",
            action="withdraw",
            level="error",
            result="error",
            title="Withdrawal rejected — invalid amount",
            user_summary="Transfer could not be processed because the amount was invalid.",
            technical_details="banking.api_withdraw rejected payload due to invalid numeric input.",
        )
        return _json_error("Enter a valid withdrawal amount.")

    if amount <= 0:
        log_manager.record(
            component="Banking",
            action="withdraw",
            level="warn",
            result="error",
            title="Withdrawal rejected — non-positive amount",
            user_summary="Transfer amount must be greater than zero.",
            technical_details="banking.api_withdraw received a non-positive amount.",
        )
        return _json_error("Withdrawal amount must be greater than zero.")

    source = find_account(source_slug)
    hand = find_account("hand")

    if not source:
        log_manager.record(
            component="Banking",
            action="withdraw",
            level="error",
            result="error",
            title="Withdrawal rejected — unknown source",
            user_summary="Select a valid account to withdraw from.",
            technical_details=f"banking.api_withdraw failed because source '{source_slug}' was missing.",
        )
        return _json_error("Select a valid source account.")

    if not hand:
        log_manager.record(
            component="Banking",
            action="withdraw",
            level="error",
            result="error",
            title="Withdrawal rejected — cash account missing",
            user_summary="Cash account is unavailable.",
            technical_details="banking.api_withdraw could not locate the cash account.",
        )
        return _json_error("Cash balance is unavailable.")

    if amount > source.balance:
        available = format_currency(source.balance)
        log_manager.record(
            component="Banking",
            action="withdraw",
            level="warn",
            result="error",
            title="Withdrawal rejected — insufficient funds",
            user_summary=f"{source.name} only has {available} available.",
            technical_details="banking.api_withdraw prevented overdrawing the source account.",
        )
        return _json_error(f"{source.name} only has {available} available.")

    description = f"Funds moved from {source.name} to cash"

    try:
        with db.session.begin():
            source.balance = quantize_amount(source.balance - amount)
            hand.balance = quantize_amount(hand.balance + amount)
            db.session.add(source)
            db.session.add(hand)
            db.session.add(
                BankTransaction(
                    account=source,
                    name="Cash Withdrawal",
                    description=description,
                    direction="debit",
                    amount=amount,
                )
            )
    except SQLAlchemyError as exc:
        db.session.rollback()
        log_manager.record(
            component="Banking",
            action="withdraw",
            level="error",
            result="error",
            title="Withdrawal failed — database error",
            user_summary="The withdrawal could not be saved. Try again shortly.",
            technical_details=f"banking.api_withdraw encountered {exc.__class__.__name__}: {exc}",
        )
        return _json_error("Unable to complete the withdrawal at this time.", status=500)

    state = build_banking_state()
    _log_cash_health(fetch_accounts())

    log_manager.record(
        component="Banking",
        action="withdraw",
        level="info",
        result="success",
        title="Cash withdrawn",
        user_summary=f"Moved {format_currency(amount)} from {source.name} to cash.",
        technical_details=(
            "banking.api_withdraw updated account balances and created a debit transaction entry."
        ),
    )

    message = f"Moved {format_currency(amount)} from {source.name} to cash."
    return _json_response({"success": True, "message": message, "state": state})


@bp.route("/settings", methods=["GET", "POST"])
def settings():
    """Allow administrators to adjust bank configuration and balances."""

    ensure_bank_defaults()
    settings = get_bank_settings()
    accounts = fetch_accounts()
    feedback: dict[str, str] | None = None

    if request.method == "GET":
        log_manager.record(
            component="Banking",
            action="view-settings",
            level="info",
            result="success",
            title="Banking settings opened",
            user_summary="Bank configuration interface displayed for adjustments.",
            technical_details="banking.settings rendered configuration and balance controls.",
        )

    if request.method == "POST":
        intent = request.form.get("intent")

        if intent == "update-settings":
            feedback = _handle_settings_update(settings)
        elif intent == "update-balance":
            feedback = _handle_balance_update(accounts)
        elif intent == "reset-balance":
            feedback = _handle_balance_reset(accounts)
        else:
            feedback = {
                "type": "error",
                "message": "Unsupported action requested.",
            }

        settings = get_bank_settings()
        accounts = fetch_accounts()

    _log_cash_health(accounts)

    serialized_accounts = [_serialize_account(account) for account in accounts]

    return render_template(
        "banking/settings.html",
        title="Lifesim — Banking Settings",
        bank_settings=settings,
        accounts=serialized_accounts,
        feedback=feedback,
        active_nav="banking",
        active_banking_tab="settings",
    )


def _handle_settings_update(settings) -> dict[str, str]:
    """Persist updates to the bank name, fee, and interest rate."""

    bank_name = (request.form.get("bank_name") or "").strip()
    fee_raw = request.form.get("standard_fee")
    interest_raw = request.form.get("savings_interest_rate")

    errors: list[str] = []

    if not bank_name:
        errors.append("Provide a name for the banking system.")

    try:
        fee_amount = quantize_amount(fee_raw)
        if fee_amount < 0:
            raise ValueError
    except (ValueError, TypeError):
        errors.append("Enter a valid, non-negative fee amount.")
        fee_amount = settings.standard_fee

    try:
        interest_rate = normalize_interest_rate(interest_raw)
        if interest_rate < 0:
            raise ValueError
    except (ValueError, TypeError):
        errors.append("Enter a valid, non-negative savings interest rate.")
        interest_rate = settings.savings_interest_rate

    if errors:
        return {"type": "error", "message": " ".join(errors)}

    try:
        settings.bank_name = bank_name
        settings.standard_fee = fee_amount
        settings.savings_interest_rate = interest_rate
        db.session.add(settings)
        db.session.commit()
    except SQLAlchemyError as exc:
        db.session.rollback()
        log_manager.record(
            component="Banking",
            action="update-settings",
            level="error",
            result="error",
            title="Settings update failed",
            user_summary="Bank settings could not be saved.",
            technical_details=f"banking._handle_settings_update encountered {exc.__class__.__name__}: {exc}",
        )
        return {"type": "error", "message": "Unable to update settings at this time."}

    log_manager.record(
        component="Banking",
        action="update-settings",
        level="info",
        result="success",
        title="Bank settings updated",
        user_summary=f"Bank renamed to {bank_name} with fee {format_currency(fee_amount)} and interest {interest_rate:.3f}%.",
        technical_details="banking._handle_settings_update committed new configuration values.",
    )

    return {
        "type": "success",
        "message": "Bank settings saved successfully.",
    }


def _handle_balance_update(accounts: Iterable[BankAccount]) -> dict[str, str]:
    """Update an individual account balance based on form data."""

    account_slug = request.form.get("account_id")
    amount_raw = request.form.get("amount")

    target = next((acc for acc in accounts if acc.slug == account_slug), None)
    if not target:
        return {"type": "error", "message": "Select a valid account to update."}

    try:
        amount = quantize_amount(amount_raw)
        if amount < 0:
            raise ValueError
    except (ValueError, TypeError):
        return {"type": "error", "message": "Enter a valid, non-negative amount."}

    try:
        update_account_balance(target, amount)
        db.session.commit()
    except SQLAlchemyError as exc:
        db.session.rollback()
        log_manager.record(
            component="Banking",
            action="update-balance",
            level="error",
            result="error",
            title="Balance update failed",
            user_summary=f"Could not update {target.name} balance.",
            technical_details=f"banking._handle_balance_update encountered {exc.__class__.__name__}: {exc}",
        )
        return {"type": "error", "message": "Unable to update the balance at this time."}

    log_manager.record(
        component="Banking",
        action="update-balance",
        level="info",
        result="success",
        title="Account balance updated",
        user_summary=f"Set {target.name} to {format_currency(amount)}.",
        technical_details="banking._handle_balance_update committed a manual balance change.",
    )

    return {
        "type": "success",
        "message": f"{target.name} updated to {format_currency(amount)}.",
    }


def _handle_balance_reset(accounts: Iterable[BankAccount]) -> dict[str, str]:
    """Reset an account balance to zero."""

    account_slug = request.form.get("account_id")
    target = next((acc for acc in accounts if acc.slug == account_slug), None)
    if not target:
        return {"type": "error", "message": "Select a valid account to reset."}

    try:
        update_account_balance(target, Decimal("0"))
        db.session.commit()
    except SQLAlchemyError as exc:
        db.session.rollback()
        log_manager.record(
            component="Banking",
            action="reset-balance",
            level="error",
            result="error",
            title="Balance reset failed",
            user_summary=f"Could not reset {target.name}.",
            technical_details=f"banking._handle_balance_reset encountered {exc.__class__.__name__}: {exc}",
        )
        return {"type": "error", "message": "Unable to reset the balance at this time."}

    log_manager.record(
        component="Banking",
        action="reset-balance",
        level="info",
        result="success",
        title="Account balance reset",
        user_summary=f"Reset {target.name} to $0.00.",
        technical_details="banking._handle_balance_reset committed a zero-balance update.",
    )

    return {
        "type": "success",
        "message": f"{target.name} reset to $0.00.",
    }
