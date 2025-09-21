"""Helper utilities for banking data management."""
from __future__ import annotations

import calendar
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Iterable

from sqlalchemy import func, inspect, select, text
from sqlalchemy.orm import joinedload

from ..extensions import db
from .models import BankAccount, BankSettings, BankTransaction

DEFAULT_ACCOUNTS: tuple[dict[str, Any], ...] = (
    {
        "slug": "hand",
        "name": "Cash",
        "category": "",
        "balance": Decimal("280.50"),
    },
    {
        "slug": "checking",
        "name": "Checking Account",
        "category": "",
        "balance": Decimal("5400.25"),
    },
    {
        "slug": "savings",
        "name": "Savings Account",
        "category": "",
        "balance": Decimal("8200.00"),
    },
)

DEFAULT_TRANSACTIONS: tuple[dict[str, Any], ...] = (
    {
        "name": "Cash Allocation",
        "description": "Wallet deposit into Checking Account",
        "amount": Decimal("2650.00"),
        "direction": "credit",
        "account_slug": "checking",
    },
    {
        "name": "Cash Allocation",
        "description": "Wallet deposit into Savings Account",
        "amount": Decimal("500.00"),
        "direction": "credit",
        "account_slug": "savings",
    },
    {
        "name": "Cash Withdrawal",
        "description": "Funds moved from Checking Account to Cash",
        "amount": Decimal("150.00"),
        "direction": "debit",
        "account_slug": "checking",
    },
)


def ensure_bank_settings_schema() -> None:
    """Add newly introduced columns to the bank_settings table when missing."""

    inspector = inspect(db.engine)
    if not inspector.has_table("bank_settings"):
        return

    existing_columns = {column["name"] for column in inspector.get_columns("bank_settings")}
    alterations: list[str] = []

    def queue(column: str, ddl: str) -> None:
        if column not in existing_columns:
            alterations.append(ddl)

    queue(
        "checking_minimum_balance",
        "ALTER TABLE bank_settings ADD COLUMN checking_minimum_balance NUMERIC(10, 2) NOT NULL DEFAULT 1500.00",
    )
    queue(
        "checking_minimum_fee",
        "ALTER TABLE bank_settings ADD COLUMN checking_minimum_fee NUMERIC(10, 2) NOT NULL DEFAULT 12.00",
    )
    queue(
        "checking_anchor_day",
        "ALTER TABLE bank_settings ADD COLUMN checking_anchor_day INTEGER NOT NULL DEFAULT 25",
    )
    queue(
        "savings_minimum_balance",
        "ALTER TABLE bank_settings ADD COLUMN savings_minimum_balance NUMERIC(10, 2) NOT NULL DEFAULT 500.00",
    )
    queue(
        "savings_minimum_fee",
        "ALTER TABLE bank_settings ADD COLUMN savings_minimum_fee NUMERIC(10, 2) NOT NULL DEFAULT 5.00",
    )
    queue(
        "savings_anchor_day",
        "ALTER TABLE bank_settings ADD COLUMN savings_anchor_day INTEGER NOT NULL DEFAULT 1",
    )

    if not alterations:
        return

    for statement in alterations:
        db.session.execute(text(statement))
    db.session.commit()


def quantize_amount(value: Decimal | float | str) -> Decimal:
    """Normalize values to two decimal places."""

    if isinstance(value, Decimal):
        amount = value
    else:
        try:
            amount = Decimal(str(value))
        except (InvalidOperation, TypeError) as exc:  # pragma: no cover - defensive
            raise ValueError("Invalid numeric value") from exc
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def decimal_to_number(value: Decimal | float | int) -> float:
    """Convert decimals to floats for JSON serialization."""

    if isinstance(value, Decimal):
        return float(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    return float(value)


def ensure_bank_defaults() -> BankSettings:
    """Ensure banking defaults exist before interacting with the system."""

    ensure_bank_settings_schema()

    settings = BankSettings.query.first()
    changed = False

    if not settings:
        settings = BankSettings()
        db.session.add(settings)
        changed = True

    defaults: tuple[tuple[str, Decimal | int], ...] = (
        ("checking_minimum_balance", Decimal("1500.00")),
        ("checking_minimum_fee", Decimal("12.00")),
        ("checking_anchor_day", 25),
        ("savings_minimum_balance", Decimal("500.00")),
        ("savings_minimum_fee", Decimal("5.00")),
        ("savings_anchor_day", 1),
    )

    for attribute, default_value in defaults:
        if getattr(settings, attribute, None) is None:
            setattr(settings, attribute, default_value)
            changed = True

    accounts_by_slug = {account.slug: account for account in BankAccount.query.all()}

    for config in DEFAULT_ACCOUNTS:
        existing = accounts_by_slug.get(config["slug"])
        if existing:
            updated = False
            if existing.name != config["name"]:
                existing.name = config["name"]
                updated = True
            if existing.category != config["category"]:
                existing.category = config["category"]
                updated = True
            if updated:
                db.session.add(existing)
                changed = True
        else:
            account = BankAccount(
                slug=config["slug"],
                name=config["name"],
                category=config["category"],
                balance=quantize_amount(config["balance"]),
            )
            db.session.add(account)
            accounts_by_slug[account.slug] = account
            changed = True

    if BankTransaction.query.count() == 0:
        for entry in DEFAULT_TRANSACTIONS:
            account = accounts_by_slug.get(entry["account_slug"])
            if not account:
                continue
            transaction = BankTransaction(
                account=account,
                name=entry["name"],
                description=entry["description"],
                amount=quantize_amount(entry["amount"]),
                direction=entry["direction"],
            )
            db.session.add(transaction)
        changed = True

    if changed:
        db.session.commit()

    return settings


def fetch_accounts() -> list[BankAccount]:
    """Return all bank accounts sorted by creation order."""

    return list(BankAccount.query.order_by(BankAccount.created_at.asc()).all())


def fetch_recent_transactions(
    limit: int = 20, *, include_cash: bool = False
) -> list[BankTransaction]:
    """Return the most recent transactions including their related accounts."""

    statement = (
        select(BankTransaction)
        .options(joinedload(BankTransaction.account))
        .join(BankTransaction.account)
        .order_by(BankTransaction.created_at.desc())
    )

    if not include_cash:
        statement = statement.where(BankAccount.slug != "hand")

    if limit:
        statement = statement.limit(limit)

    return list(db.session.execute(statement).scalars().all())


def paginate_transactions(
    page: int, per_page: int, *, include_cash: bool = False
) -> dict[str, Any]:
    """Return a paginated set of transactions for the ledger view."""

    base_query = (
        select(BankTransaction)
        .options(joinedload(BankTransaction.account))
        .join(BankTransaction.account)
    )

    if not include_cash:
        base_query = base_query.where(BankAccount.slug != "hand")

    count_statement = select(func.count()).select_from(BankTransaction).join(BankTransaction.account)
    if not include_cash:
        count_statement = count_statement.where(BankAccount.slug != "hand")

    total = db.session.execute(count_statement).scalar_one()

    per_page = max(per_page, 1)
    total_pages = max((total + per_page - 1) // per_page, 1) if total else 1
    page = min(max(page, 1), total_pages)
    offset = (page - 1) * per_page if total else 0

    statement = (
        base_query.order_by(BankTransaction.created_at.desc())
        .limit(per_page)
        .offset(offset)
    )

    items = list(db.session.execute(statement).scalars().all())

    return {
        "items": items,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": total_pages,
    }


def build_banking_state(
    limit: int = 20,
    *,
    include_cash: bool = False,
    settings: BankSettings | None = None,
) -> dict[str, Any]:
    """Return the structured state used by the transfer interface."""

    accounts = fetch_accounts()
    balances = {
        account.slug: {
            "label": account.name,
            "balance": decimal_to_number(account.balance),
        }
        for account in accounts
    }

    transactions = fetch_recent_transactions(limit, include_cash=include_cash)

    ledger = [
        {
            "name": transaction.name,
            "description": transaction.description,
            "amount": decimal_to_number(transaction.amount),
            "direction": transaction.direction,
            "account": transaction.account.slug,
        }
        for transaction in transactions
    ]

    payload: dict[str, Any] = {
        "balances": balances,
        "transactions": ledger,
        "account_labels": {account.slug: account.name for account in accounts},
    }

    if settings:
        payload["requirements"] = {
            "checking": {
                "minimum_balance": decimal_to_number(settings.checking_minimum_balance),
                "fee": decimal_to_number(settings.checking_minimum_fee),
                "anchor_day": settings.checking_anchor_day,
            },
            "savings": {
                "minimum_balance": decimal_to_number(settings.savings_minimum_balance),
                "fee": decimal_to_number(settings.savings_minimum_fee),
                "anchor_day": settings.savings_anchor_day,
            },
        }

    return payload


def compute_next_anchor_date(anchor_day: int, *, today: date | None = None) -> date:
    """Return the next anchor date for the given day of the month."""

    today = today or date.today()
    year, month = today.year, today.month
    max_day = calendar.monthrange(year, month)[1]
    day = min(max(anchor_day, 1), max_day)
    anchor = date(year, month, day)

    if anchor <= today:
        month += 1
        if month > 12:
            month = 1
            year += 1
        max_day = calendar.monthrange(year, month)[1]
        day = min(max(anchor_day, 1), max_day)
        anchor = date(year, month, day)

    return anchor


def compute_previous_anchor_date(anchor_day: int, *, today: date | None = None) -> date:
    """Return the most recent anchor date on or before today."""

    today = today or date.today()
    year, month = today.year, today.month
    max_day = calendar.monthrange(year, month)[1]
    day = min(max(anchor_day, 1), max_day)
    anchor = date(year, month, day)

    if anchor > today:
        month -= 1
        if month < 1:
            month = 12
            year -= 1
        max_day = calendar.monthrange(year, month)[1]
        day = min(max(anchor_day, 1), max_day)
        anchor = date(year, month, day)

    return anchor


def ordinal(day: int) -> str:
    """Return an ordinal string (1st, 2nd, 3rd) for the provided day."""

    if day <= 0:
        return str(day)
    remainder = day % 100
    if 10 <= remainder <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
    return f"{day}{suffix}"


def estimate_interest_payout(
    balance: Decimal, rate: Decimal, anchor_day: int, *, today: date | None = None
) -> Decimal:
    """Estimate the interest accrued for the current cycle using daily accrual."""

    today = today or date.today()
    next_anchor = compute_next_anchor_date(anchor_day, today=today)
    previous_anchor = compute_previous_anchor_date(anchor_day, today=today)

    cycle_days = max((next_anchor - previous_anchor).days, 1)
    daily_rate = Decimal(rate) / Decimal("100") / Decimal("365")
    interest = balance * daily_rate * Decimal(cycle_days)
    return quantize_amount(interest)


def build_account_insights(
    settings: BankSettings, accounts: Iterable[BankAccount]
) -> list[dict[str, Any]]:
    """Construct insight content for the overview page."""

    account_balances = {account.slug: account.balance for account in accounts}
    savings_balance = account_balances.get("savings", Decimal("0"))

    checking_anchor = compute_next_anchor_date(settings.checking_anchor_day)
    savings_anchor = compute_next_anchor_date(settings.savings_anchor_day)
    savings_interest = estimate_interest_payout(
        savings_balance, settings.savings_interest_rate, settings.savings_anchor_day
    )
    checking_anchor_day_display = ordinal(settings.checking_anchor_day)
    savings_anchor_day_display = ordinal(settings.savings_anchor_day)

    checking_minimum_display = format_currency(settings.checking_minimum_balance)
    checking_fee_display = format_currency(settings.checking_minimum_fee)
    savings_minimum_display = format_currency(settings.savings_minimum_balance)
    savings_fee_display = format_currency(settings.savings_minimum_fee)
    interest_display = format_currency(savings_interest)
    apy_display = f"{decimal_to_number(settings.savings_interest_rate):.2f}% APY"

    return [
        {
            "account": "Cash",
            "details": [
                {
                    "label": "Liquidity guidance",
                    "value": "Hold a flexible cushion for impulse purchases; cash activity is kept off the ledger for clarity.",
                },
                {
                    "label": "Reconciliation",
                    "value": "Document cash spends manually so deposits back to checking remain accurate.",
                },
            ],
        },
        {
            "account": "Checking Account",
            "details": [
                {
                    "label": "Anchor date",
                    "value": (
                        f"{checking_anchor:%b %d, %Y} — monthly service review posts; if the"
                        f" {checking_anchor_day_display} is missing in a month, the evaluation runs on the final day."
                    ),
                },
                {
                    "label": "Next evaluation",
                    "value": (
                        f"Maintain at least {checking_minimum_display}; otherwise a {checking_fee_display} fee applies"
                        " on the anchor date."
                    ),
                },
                {
                    "label": "Cash flow tip",
                    "value": "Route bill payments here to keep savings untouched and rebuild cash with targeted transfers.",
                },
            ],
        },
        {
            "account": "Savings Account",
            "details": [
                {
                    "label": "Anchor date",
                    "value": (
                        f"{savings_anchor:%b %d, %Y} — accrued interest credits and the cycle resets; if the"
                        f" {savings_anchor_day_display} does not occur in the month, interest posts on the last day."
                    ),
                },
                {
                    "label": "Projected payout",
                    "value": (
                        f"Interest accrues daily at {apy_display}; expect {interest_display} on the next anchor date"
                        " if the balance holds steady."
                    ),
                },
                {
                    "label": "Balance requirements",
                    "value": (
                        f"Keep at least {savings_minimum_display}; falling short can trigger a {savings_fee_display}"
                        " maintenance fee."
                    ),
                },
            ],
        },
    ]


def format_currency(amount: Decimal | float | str) -> str:
    """Return a currency formatted string for display content."""

    quantized = quantize_amount(amount)
    return f"${quantized:,.2f}"


def find_account(slug: str) -> BankAccount | None:
    """Return the requested account, if it exists."""

    if not slug:
        return None
    return BankAccount.query.filter_by(slug=slug).first()


def update_account_balance(account: BankAccount, amount: Decimal) -> None:
    """Persist a new balance for the provided account."""

    account.balance = quantize_amount(amount)
    db.session.add(account)


def normalize_interest_rate(value: Decimal | float | str) -> Decimal:
    """Normalize interest rate inputs to three decimal places."""

    if isinstance(value, Decimal):
        rate = value
    else:
        try:
            rate = Decimal(str(value))
        except (InvalidOperation, TypeError) as exc:  # pragma: no cover - defensive
            raise ValueError("Invalid numeric value") from exc
    return rate.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)

def get_bank_settings() -> BankSettings:
    """Retrieve banking settings ensuring defaults are initialized."""

    ensure_bank_defaults()
    return BankSettings.query.first()
