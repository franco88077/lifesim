"""Routes for the Lifesim banking system backed by the database."""
from __future__ import annotations

from decimal import Decimal
from typing import Iterable

from flask import jsonify, render_template, request
from sqlalchemy.exc import SQLAlchemyError

from ..extensions import db
from ..logging_service import log_manager
from . import bp
from .models import BankAccount, BankSettings, BankTransaction
from .services import (
    decimal_to_number,
    build_account_due_items,
    build_account_insights,
    build_banking_state,
    ensure_bank_defaults,
    fetch_accounts,
    fetch_recent_transactions,
    find_account,
    format_currency,
    get_bank_settings,
    normalize_interest_rate,
    paginate_transactions,
    quantize_amount,
    update_account_balance,
)


def _serialize_account(account: BankAccount) -> dict[str, object]:
    """Prepare account details for template rendering."""

    return {
        "id": account.slug,
        "name": account.name,
        "type": account.category or None,
        "balance": float(quantize_amount(account.balance)),
        "display_balance": format_currency(account.balance),
        "is_closed": getattr(account, "is_closed", False),
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


def _create_transfer_entries(
    source: BankAccount, destination: BankAccount, amount: Decimal
) -> list[BankTransaction]:
    """Create ledger entries for the transfer while skipping cash movements."""

    amount = quantize_amount(amount)
    description = f"Funds moved from {source.name} to {destination.name}"
    entries: list[BankTransaction] = []

    if source.slug != "hand":
        source_description = (
            "Funds moved from {name} to cash".format(name=source.name)
            if destination.slug == "hand"
            else description
        )
        source_name = "Cash Withdrawal" if destination.slug == "hand" else "Account Transfer"
        entries.append(
            BankTransaction(
                account=source,
                name=source_name,
                description=source_description,
                direction="debit",
                amount=amount,
            )
        )

    if destination.slug != "hand":
        destination_description = (
            "Wallet deposit into {name}".format(name=destination.name)
            if source.slug == "hand"
            else description
        )
        destination_name = "Cash Allocation" if source.slug == "hand" else "Account Transfer"
        entries.append(
            BankTransaction(
                account=destination,
                name=destination_name,
                description=destination_description,
                direction="credit",
                amount=amount,
            )
        )

    return entries


def _apply_transfer(
    source: BankAccount, destination: BankAccount, amount: Decimal
) -> None:
    """Persist the transfer by updating balances and ledger entries."""

    amount = quantize_amount(amount)
    entries = _create_transfer_entries(source, destination, amount)

    source.balance = quantize_amount(source.balance - amount)
    destination.balance = quantize_amount(destination.balance + amount)

    db.session.add(source)
    db.session.add(destination)
    for entry in entries:
        db.session.add(entry)

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

    cash_account = next((account for account in accounts if account.slug == "hand"), None)
    cash_balance = cash_account.balance if cash_account else Decimal("0")
    available_cash = format_currency(cash_balance)
    available_cash_value = decimal_to_number(cash_balance)
    account_slugs = {account.slug for account in accounts if account.slug != "hand"}
    missing_accounts = [slug for slug in ("checking", "savings") if slug not in account_slugs]

    account_due_cards = build_account_due_items(settings, accounts)
    has_open_accounts = any(
        account.slug in {"checking", "savings"} for account in accounts
    )

    log_manager.record(
        component="Banking",
        action="view-home",
        level="info",
        result="success",
        title="Banking home opened",
        user_summary="Banking overview displayed for the player.",
        technical_details="banking.home rendered account balances and recent transactions.",
    )

    display_accounts = [account for account in accounts if account.slug != "hand"]
    serialized_accounts = [_serialize_account(account) for account in display_accounts]
    transactions = fetch_recent_transactions(limit=6)
    has_more_transactions = len(transactions) > 5
    serialized_transactions = [
        _serialize_transaction(transaction) for transaction in transactions[:5]
    ]

    account_opening_requirements = {
        "checking": format_currency(settings.checking_opening_deposit),
        "savings": format_currency(settings.savings_opening_deposit),
    }
    account_opening_requirements_value = {
        "checking": decimal_to_number(settings.checking_opening_deposit),
        "savings": decimal_to_number(settings.savings_opening_deposit),
    }

    return render_template(
        "banking/home.html",
        title="Lifesim — Banking Home",
        accounts=serialized_accounts,
        has_open_accounts=has_open_accounts,
        missing_accounts=missing_accounts,
        account_due_cards=account_due_cards,
        recent_transactions=serialized_transactions,
        has_more_transactions=has_more_transactions,
        bank_settings=settings,
        available_cash=available_cash,
        available_cash_value=available_cash_value,
        account_opening_requirements=account_opening_requirements,
        account_opening_requirements_value=account_opening_requirements_value,
        active_nav="banking",
        active_banking_tab="home",
    )


@bp.route("/insights")
def insights():
    """Display account insight and fee information on a dedicated page."""

    ensure_bank_defaults()
    settings = get_bank_settings()
    accounts = fetch_accounts()

    log_manager.record(
        component="Banking",
        action="view-insights",
        level="info",
        result="success",
        title="Banking insights opened",
        user_summary="Account insight and fee guidance displayed for the player.",
        technical_details="banking.insights rendered the insight cards and policy notes.",
    )

    insights = build_account_insights(settings, accounts)

    return render_template(
        "banking/insights.html",
        title="Lifesim — Banking Insights",
        account_insights=insights,
        bank_settings=settings,
        active_nav="banking",
        active_banking_tab="insights",
    )


@bp.route("/transactions")
def transactions():
    """Display the full banking ledger with pagination."""

    ensure_bank_defaults()
    settings = get_bank_settings()

    raw_page = request.args.get("page", default=1, type=int)
    raw_per_page = request.args.get("per_page", default=10, type=int)
    per_page = max(1, min(raw_per_page, 25))

    pagination = paginate_transactions(raw_page, per_page)
    serialized_transactions = [
        _serialize_transaction(transaction) for transaction in pagination["items"]
    ]

    if pagination["total"]:
        display_start = (pagination["page"] - 1) * pagination["per_page"] + 1
        display_end = min(pagination["page"] * pagination["per_page"], pagination["total"])
    else:
        display_start = 0
        display_end = 0

    pager = {
        "page": pagination["page"],
        "per_page": pagination["per_page"],
        "total": pagination["total"],
        "pages": pagination["pages"],
        "has_prev": pagination["page"] > 1,
        "has_next": pagination["page"] < pagination["pages"],
        "prev_page": pagination["page"] - 1 if pagination["page"] > 1 else None,
        "next_page": pagination["page"] + 1 if pagination["page"] < pagination["pages"] else None,
    }

    log_manager.record(
        component="Banking",
        action="view-transactions",
        level="info",
        result="success",
        title="Banking transactions opened",
        user_summary="Full banking ledger displayed with pagination controls.",
        technical_details="banking.transactions rendered the paginated transaction history.",
    )

    return render_template(
        "banking/transactions.html",
        title="Lifesim — Banking Transactions",
        transactions=serialized_transactions,
        pagination=pager,
        display_start=display_start,
        display_end=display_end,
        bank_settings=settings,
        active_nav="banking",
        active_banking_tab="home",
    )


@bp.route("/transfer")
def transfer():
    """Surface the cash transfer workflow on a dedicated page."""

    ensure_bank_defaults()
    settings = get_bank_settings()
    accounts = fetch_accounts()
    banking_state = build_banking_state(settings=settings)
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


@bp.post("/api/accounts/open")
def api_open_accounts():
    """Create new banking accounts with an initial deposit from cash."""

    ensure_bank_defaults()
    settings = get_bank_settings()
    accounts = fetch_accounts()
    cash_account = next((account for account in accounts if account.slug == "hand"), None)

    if not cash_account:
        return _json_error("Cash account is unavailable. Try again later.", status=500)

    payload = request.get_json(silent=True) or {}
    requested_accounts = payload.get("accounts")

    if not isinstance(requested_accounts, dict):
        return _json_error("Select at least one account to open.")

    account_configs = {
        "checking": {
            "name": "Checking Account",
            "category": "Checking",
            "minimum_deposit": settings.checking_opening_deposit,
        },
        "savings": {
            "name": "Savings Account",
            "category": "Savings",
            "minimum_deposit": settings.savings_opening_deposit,
        },
    }

    selections: list[tuple[str, Decimal, bool]] = []
    errors: list[str] = []

    for slug, config in account_configs.items():
        if slug not in requested_accounts:
            continue

        existing_account = find_account(slug, include_closed=True)

        if existing_account and not existing_account.is_closed:
            errors.append(f"{config['name']} is already open.")
            continue

        raw_deposit = (requested_accounts.get(slug) or {}).get("deposit")
        try:
            deposit_amount = quantize_amount(raw_deposit)
        except (ValueError, TypeError):
            errors.append(f"Provide a valid deposit for the {config['name'].lower()}.")
            continue

        minimum_required = quantize_amount(config["minimum_deposit"])
        if deposit_amount < minimum_required:
            errors.append(
                f"Deposit at least {format_currency(minimum_required)} to open the {config['name'].lower()}."
            )
            continue

        if deposit_amount <= 0:
            errors.append(f"Deposit a positive amount for the {config['name'].lower()}.")
            continue

        selections.append((slug, deposit_amount, bool(existing_account)))

    if errors:
        return _json_error(" ".join(errors))

    if not selections:
        return _json_error("Choose an account to open and include a starting deposit.")

    total_deposit = sum(amount for _, amount, _ in selections)
    if total_deposit > cash_account.balance:
        available = format_currency(cash_account.balance)
        return _json_error(
            f"Cash only has {available} available. Lower the deposits before opening accounts."
        )

    created_accounts: list[BankAccount] = []
    try:
        for slug, amount, is_reopening in selections:
            config = account_configs[slug]
            if is_reopening:
                account = find_account(slug, include_closed=True)
                if not account:
                    continue
                account.name = config["name"]
                account.category = config["category"]
                account.balance = quantize_amount(amount)
                account.is_closed = False
                db.session.add(account)
            else:
                account = BankAccount(
                    slug=slug,
                    name=config["name"],
                    category=config["category"],
                    balance=amount,
                    is_closed=False,
                )
                db.session.add(account)
                db.session.flush()
            db.session.add(
                BankTransaction(
                    account=account,
                    name="Initial Deposit",
                    description=f"Opening deposit for {config['name']}",
                    direction="credit",
                    amount=amount,
                )
            )
            created_accounts.append(account)

        cash_account.balance = quantize_amount(cash_account.balance - total_deposit)
        db.session.add(cash_account)
        db.session.commit()
    except SQLAlchemyError as exc:
        db.session.rollback()
        log_manager.record(
            component="Banking",
            action="open-account",
            level="error",
            result="error",
            title="Account opening failed",
            user_summary="The new accounts could not be created.",
            technical_details=f"banking.api_open_accounts encountered {exc.__class__.__name__}: {exc}",
        )
        return _json_error("Unable to open accounts right now. Please try again shortly.", status=500)

    created_labels = ", ".join(account.name for account in created_accounts)

    log_manager.record(
        component="Banking",
        action="open-account",
        level="info",
        result="success",
        title="Bank accounts opened",
        user_summary=f"Opened {created_labels} with {format_currency(total_deposit)} in deposits.",
        technical_details=(
            "banking.api_open_accounts created deposit accounts, recorded opening transactions, and "
            "decremented cash reserves."
        ),
    )

    refreshed_accounts = fetch_accounts()
    _log_cash_health(refreshed_accounts)

    serialized = [
        _serialize_account(account)
        for account in refreshed_accounts
        if account.slug not in {"hand"}
    ]
    response_message = (
        f"Opened {created_labels} with {format_currency(total_deposit)} transferred from cash."
    )

    return _json_response(
        {
            "success": True,
            "message": response_message,
            "accounts": serialized,
            "cash_balance": format_currency(cash_account.balance),
        }
    )


@bp.post("/api/transfer/move")
def api_move():
    """Move money between any two accounts using a unified workflow."""

    ensure_bank_defaults()
    settings = get_bank_settings()
    payload = request.get_json(silent=True) or {}

    source_slug = (payload.get("source") or "").strip()
    destination_slug = (payload.get("destination") or "").strip()
    amount_raw = payload.get("amount")

    try:
        amount = quantize_amount(amount_raw)
    except (ValueError, TypeError):
        log_manager.record(
            component="Banking",
            action="transfer-move",
            level="error",
            result="error",
            title="Transfer rejected — invalid amount",
            user_summary="Transfer could not be processed because the amount was invalid.",
            technical_details="banking.api_move rejected payload due to invalid numeric input.",
        )
        return _json_error("Enter a valid transfer amount.")

    if amount <= 0:
        log_manager.record(
            component="Banking",
            action="transfer-move",
            level="warn",
            result="error",
            title="Transfer rejected — non-positive amount",
            user_summary="Transfer amount must be greater than zero.",
            technical_details="banking.api_move received a non-positive amount.",
        )
        return _json_error("Transfer amount must be greater than zero.")

    if not source_slug or not destination_slug:
        log_manager.record(
            component="Banking",
            action="transfer-move",
            level="error",
            result="error",
            title="Transfer rejected — missing accounts",
            user_summary="Select a source and destination account to continue.",
            technical_details="banking.api_move received an incomplete transfer payload.",
        )
        return _json_error("Select both a source and destination account.")

    if source_slug == destination_slug:
        log_manager.record(
            component="Banking",
            action="transfer-move",
            level="warn",
            result="error",
            title="Transfer rejected — identical accounts",
            user_summary="Source and destination accounts must be different.",
            technical_details="banking.api_move prevented a self-transfer request.",
        )
        return _json_error("Choose two different accounts.")

    source = find_account(source_slug)
    destination = find_account(destination_slug)

    if not source or not destination:
        log_manager.record(
            component="Banking",
            action="transfer-move",
            level="error",
            result="error",
            title="Transfer rejected — unknown accounts",
            user_summary="Transfer failed because one of the accounts could not be found.",
            technical_details=(
                f"banking.api_move could not locate source '{source_slug}' or destination '{destination_slug}'."
            ),
        )
        return _json_error("Select valid accounts for the transfer.")

    if amount > source.balance:
        available = format_currency(source.balance)
        log_manager.record(
            component="Banking",
            action="transfer-move",
            level="warn",
            result="error",
            title="Transfer rejected — insufficient funds",
            user_summary=f"{source.name} only has {available} available.",
            technical_details="banking.api_move prevented overdrawing the source account.",
        )
        return _json_error(f"{source.name} only has {available} available.")

    try:
        _apply_transfer(source, destination, amount)
        db.session.commit()
    except SQLAlchemyError as exc:
        db.session.rollback()
        log_manager.record(
            component="Banking",
            action="transfer-move",
            level="error",
            result="error",
            title="Transfer failed — database error",
            user_summary="The transfer could not be saved. Try again shortly.",
            technical_details=f"banking.api_move encountered {exc.__class__.__name__}: {exc}",
        )
        return _json_error("Unable to complete the transfer at this time.", status=500)

    state = build_banking_state(settings=settings)
    _log_cash_health(fetch_accounts())

    if source.slug == "hand":
        message = f"Transferred {format_currency(amount)} from Cash to {destination.name}."
    elif destination.slug == "hand":
        message = f"Moved {format_currency(amount)} from {source.name} to Cash."
    else:
        message = f"Moved {format_currency(amount)} from {source.name} to {destination.name}."

    log_manager.record(
        component="Banking",
        action="transfer-move",
        level="info",
        result="success",
        title="Transfer completed",
        user_summary=message,
        technical_details="banking.api_move updated account balances and recorded ledger entries.",
    )

    return _json_response({"success": True, "message": message, "state": state})


@bp.post("/api/transfer/deposit")
def api_deposit():
    """Move money from cash into a selected account."""

    ensure_bank_defaults()
    settings = get_bank_settings()
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
        db.session.commit()
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

    state = build_banking_state(settings=settings)
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
    settings = get_bank_settings()
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
        db.session.commit()
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

    state = build_banking_state(settings=settings)
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
        elif intent == "close-accounts":
            feedback = _handle_account_closure(settings)
        else:
            feedback = {
                "type": "error",
                "message": "Unsupported action requested.",
            }

        settings = get_bank_settings()
        accounts = fetch_accounts(include_closed=True)

    _log_cash_health(accounts)

    serialized_accounts = [_serialize_account(account) for account in accounts]
    account_lookup = {account["id"]: account for account in serialized_accounts}

    return render_template(
        "banking/settings.html",
        title="Lifesim — Banking Settings",
        bank_settings=settings,
        accounts=serialized_accounts,
        account_lookup=account_lookup,
        feedback=feedback,
        active_nav="banking",
        active_banking_tab="settings",
    )


def _handle_settings_update(settings) -> dict[str, str]:
    """Persist updates to the bank name, fee, and interest rate."""

    bank_name = (request.form.get("bank_name") or "").strip()
    fee_raw = request.form.get("standard_fee")
    interest_raw = request.form.get("savings_interest_rate")
    checking_min_balance_raw = request.form.get("checking_minimum_balance")
    checking_min_fee_raw = request.form.get("checking_minimum_fee")
    checking_opening_raw = request.form.get("checking_opening_deposit")
    savings_min_balance_raw = request.form.get("savings_minimum_balance")
    savings_min_fee_raw = request.form.get("savings_minimum_fee")
    savings_opening_raw = request.form.get("savings_opening_deposit")
    bank_closure_fee_raw = request.form.get("bank_closure_fee")
    checking_closure_fee_raw = request.form.get("checking_closure_fee")
    savings_closure_fee_raw = request.form.get("savings_closure_fee")

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

    try:
        checking_minimum_balance = quantize_amount(checking_min_balance_raw)
        if checking_minimum_balance < 0:
            raise ValueError
    except (ValueError, TypeError):
        errors.append("Enter a valid, non-negative checking minimum balance.")
        checking_minimum_balance = settings.checking_minimum_balance

    try:
        checking_minimum_fee = quantize_amount(checking_min_fee_raw)
        if checking_minimum_fee < 0:
            raise ValueError
    except (ValueError, TypeError):
        errors.append("Enter a valid, non-negative checking fee amount.")
        checking_minimum_fee = settings.checking_minimum_fee

    try:
        savings_minimum_balance = quantize_amount(savings_min_balance_raw)
        if savings_minimum_balance < 0:
            raise ValueError
    except (ValueError, TypeError):
        errors.append("Enter a valid, non-negative savings minimum balance.")
        savings_minimum_balance = settings.savings_minimum_balance

    try:
        savings_minimum_fee = quantize_amount(savings_min_fee_raw)
        if savings_minimum_fee < 0:
            raise ValueError
    except (ValueError, TypeError):
        errors.append("Enter a valid, non-negative savings fee amount.")
        savings_minimum_fee = settings.savings_minimum_fee

    try:
        checking_opening_deposit = quantize_amount(checking_opening_raw)
        if checking_opening_deposit < 0:
            raise ValueError
    except (ValueError, TypeError):
        errors.append("Enter a valid, non-negative checking opening deposit.")
        checking_opening_deposit = settings.checking_opening_deposit

    try:
        savings_opening_deposit = quantize_amount(savings_opening_raw)
        if savings_opening_deposit < 0:
            raise ValueError
    except (ValueError, TypeError):
        errors.append("Enter a valid, non-negative savings opening deposit.")
        savings_opening_deposit = settings.savings_opening_deposit

    try:
        bank_closure_fee = quantize_amount(bank_closure_fee_raw)
        if bank_closure_fee < 0:
            raise ValueError
    except (ValueError, TypeError):
        errors.append("Enter a valid, non-negative bank closure fee.")
        bank_closure_fee = settings.bank_closure_fee

    try:
        checking_closure_fee = quantize_amount(checking_closure_fee_raw)
        if checking_closure_fee < 0:
            raise ValueError
    except (ValueError, TypeError):
        errors.append("Enter a valid, non-negative checking closure fee.")
        checking_closure_fee = settings.checking_closure_fee

    try:
        savings_closure_fee = quantize_amount(savings_closure_fee_raw)
        if savings_closure_fee < 0:
            raise ValueError
    except (ValueError, TypeError):
        errors.append("Enter a valid, non-negative savings closure fee.")
        savings_closure_fee = settings.savings_closure_fee

    if errors:
        return {"type": "error", "message": " ".join(errors)}

    try:
        settings.bank_name = bank_name
        settings.standard_fee = fee_amount
        settings.savings_interest_rate = interest_rate
        settings.checking_minimum_balance = checking_minimum_balance
        settings.checking_minimum_fee = checking_minimum_fee
        settings.savings_minimum_balance = savings_minimum_balance
        settings.savings_minimum_fee = savings_minimum_fee
        settings.checking_opening_deposit = checking_opening_deposit
        settings.savings_opening_deposit = savings_opening_deposit
        settings.bank_closure_fee = bank_closure_fee
        settings.checking_closure_fee = checking_closure_fee
        settings.savings_closure_fee = savings_closure_fee
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
        user_summary=(
            f"Bank renamed to {bank_name} with fee {format_currency(fee_amount)}, interest {interest_rate:.3f}%"
            f", checking minimum {format_currency(checking_minimum_balance)} ({format_currency(checking_minimum_fee)} fee)"
            f", savings minimum {format_currency(savings_minimum_balance)} ({format_currency(savings_minimum_fee)} fee)"
            f", checking opening deposit {format_currency(checking_opening_deposit)}"
            f", savings opening deposit {format_currency(savings_opening_deposit)}"
            f", bank closure fee {format_currency(bank_closure_fee)}"
            f", checking closure fee {format_currency(checking_closure_fee)}"
            f", savings closure fee {format_currency(savings_closure_fee)}."
        ),
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

    if getattr(target, "is_closed", False):
        return {
            "type": "error",
            "message": "Reopen the account before updating its balance.",
        }

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

    if getattr(target, "is_closed", False):
        return {
            "type": "error",
            "message": "Closed accounts already report a zero balance.",
        }

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


def _handle_account_closure(settings: BankSettings) -> dict[str, str]:
    """Close selected accounts and move balances to cash."""

    target = (request.form.get("target") or "").strip()
    valid_targets = {"all", "checking", "savings"}

    if target not in valid_targets:
        return {"type": "error", "message": "Choose a valid closure option."}

    cash_account = find_account("hand", include_closed=True)
    if not cash_account:
        return {"type": "error", "message": "Cash account is unavailable."}

    slug_to_name = {
        "checking": "Checking Account",
        "savings": "Savings Account",
    }
    requested_slugs = ("checking", "savings") if target == "all" else (target,)

    accounts_to_close: list[BankAccount] = []
    for slug in requested_slugs:
        account = find_account(slug)
        if account:
            accounts_to_close.append(account)

    if not accounts_to_close:
        if target == "all":
            message = "All accounts are already closed."
        else:
            message = f"{slug_to_name[target]} is already closed."
        return {"type": "error", "message": message}

    total_transfer = Decimal("0.00")
    closed_labels: list[str] = []

    try:
        for account in accounts_to_close:
            balance = quantize_amount(account.balance)
            closed_labels.append(account.name)

            if balance > 0:
                db.session.add(
                    BankTransaction(
                        account=account,
                        name="Account Closed",
                        description="Account closed and funds moved to cash.",
                        direction="debit",
                        amount=balance,
                    )
                )
                db.session.add(
                    BankTransaction(
                        account=cash_account,
                        name=f"{account.name} Closure Transfer",
                        description=f"Funds from {account.name} moved to cash during closure.",
                        direction="credit",
                        amount=balance,
                    )
                )
                total_transfer += balance

            account.balance = Decimal("0.00")
            account.is_closed = True
            db.session.add(account)

        if total_transfer > 0:
            cash_account.balance = quantize_amount(cash_account.balance + total_transfer)

        fee_lookup = {
            "all": quantize_amount(settings.bank_closure_fee),
            "checking": quantize_amount(settings.checking_closure_fee),
            "savings": quantize_amount(settings.savings_closure_fee),
        }
        fee_label_lookup = {
            "all": "Bank", 
            "checking": "Checking", 
            "savings": "Savings",
        }

        closure_fee = fee_lookup.get(target, Decimal("0.00"))
        collected_fee = Decimal("0.00")

        if closure_fee > 0:
            available_fee = min(quantize_amount(cash_account.balance), closure_fee)
            if available_fee > 0:
                cash_account.balance = quantize_amount(cash_account.balance - available_fee)
                collected_fee = available_fee
                db.session.add(
                    BankTransaction(
                        account=cash_account,
                        name="Closure Fee",
                        description=(
                            f"{fee_label_lookup[target]} closure fee collected during account closure."
                        ),
                        direction="debit",
                        amount=available_fee,
                    )
                )

        db.session.add(cash_account)
        db.session.commit()
    except SQLAlchemyError as exc:
        db.session.rollback()
        log_manager.record(
            component="Banking",
            action="close-accounts",
            level="error",
            result="error",
            title="Account closure failed",
            user_summary="Accounts could not be closed due to a database error.",
            technical_details=f"banking._handle_account_closure encountered {exc.__class__.__name__}: {exc}",
        )
        return {
            "type": "error",
            "message": "Unable to close accounts at this time.",
        }

    closed_summary = ", ".join(closed_labels)
    transfer_display = format_currency(total_transfer)

    if collected_fee > 0:
        fee_display = format_currency(collected_fee)
        fee_message = f" Collected a {fee_display} closure fee."
    else:
        fee_message = " No closure fee was applied."

    log_manager.record(
        component="Banking",
        action="close-accounts",
        level="info",
        result="success",
        title="Accounts closed",
        user_summary=(
            f"Closed {closed_summary} and moved {transfer_display} to cash.{fee_message}"
        ),
        technical_details="banking._handle_account_closure transferred balances and updated account status.",
    )

    message = (
        f"Closed {closed_summary} and moved {transfer_display} to cash.{fee_message}"
    )

    return {"type": "success", "message": message}
