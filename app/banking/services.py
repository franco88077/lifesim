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
        "balance": Decimal("500.00"),
    },
)

DEFAULT_TRANSACTIONS: tuple[dict[str, Any], ...] = ()


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
    queue(
        "checking_opening_deposit",
        "ALTER TABLE bank_settings ADD COLUMN checking_opening_deposit NUMERIC(10, 2) NOT NULL DEFAULT 100.00",
    )
    queue(
        "savings_opening_deposit",
        "ALTER TABLE bank_settings ADD COLUMN savings_opening_deposit NUMERIC(10, 2) NOT NULL DEFAULT 50.00",
    )
    queue(
        "bank_closure_fee",
        "ALTER TABLE bank_settings ADD COLUMN bank_closure_fee NUMERIC(10, 2) NOT NULL DEFAULT 35.00",
    )
    queue(
        "checking_closure_fee",
        "ALTER TABLE bank_settings ADD COLUMN checking_closure_fee NUMERIC(10, 2) NOT NULL DEFAULT 25.00",
    )
    queue(
        "savings_closure_fee",
        "ALTER TABLE bank_settings ADD COLUMN savings_closure_fee NUMERIC(10, 2) NOT NULL DEFAULT 15.00",
    )

    if not alterations:
        return

    for statement in alterations:
        db.session.execute(text(statement))
    db.session.commit()


def ensure_bank_account_schema() -> None:
    """Ensure the bank_account table includes lifecycle management fields."""

    inspector = inspect(db.engine)
    if not inspector.has_table("bank_account"):
        return

    existing_columns = {column["name"] for column in inspector.get_columns("bank_account")}

    if "is_closed" in existing_columns:
        return

    db.session.execute(
        text("ALTER TABLE bank_account ADD COLUMN is_closed BOOLEAN NOT NULL DEFAULT 0")
    )
    db.session.execute(text("UPDATE bank_account SET is_closed = 0"))
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
    ensure_bank_account_schema()

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
        ("checking_opening_deposit", Decimal("100.00")),
        ("savings_opening_deposit", Decimal("50.00")),
        ("bank_closure_fee", Decimal("35.00")),
        ("checking_closure_fee", Decimal("25.00")),
        ("savings_closure_fee", Decimal("15.00")),
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
                is_closed=False,
            )
            db.session.add(account)
            accounts_by_slug[account.slug] = account
            changed = True

    # Remove any pre-seeded transactions when the ledger is empty to reflect the
    # new onboarding flow where accounts begin closed.
    if BankTransaction.query.count() == 0 and DEFAULT_TRANSACTIONS:
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


def fetch_accounts(*, include_closed: bool = False) -> list[BankAccount]:
    """Return bank accounts sorted by creation order."""

    query = BankAccount.query.order_by(BankAccount.created_at.asc())
    if not include_closed:
        query = query.filter(BankAccount.is_closed.is_(False))
    return list(query.all())


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
                "opening_deposit": decimal_to_number(settings.checking_opening_deposit),
            },
            "savings": {
                "minimum_balance": decimal_to_number(settings.savings_minimum_balance),
                "fee": decimal_to_number(settings.savings_minimum_fee),
                "anchor_day": settings.savings_anchor_day,
                "opening_deposit": decimal_to_number(settings.savings_opening_deposit),
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


def build_account_due_items(
    settings: BankSettings, accounts: Iterable[BankAccount]
) -> list[dict[str, str]]:
    """Return due amount guidance for checking and savings accounts."""

    account_lookup = {account.slug: account for account in accounts}
    checking_account = account_lookup.get("checking")
    savings_account = account_lookup.get("savings")

    checking_balance = checking_account.balance if checking_account else Decimal("0.00")
    savings_balance = savings_account.balance if savings_account else Decimal("0.00")

    checking_anchor = compute_next_anchor_date(settings.checking_anchor_day)
    savings_anchor = compute_next_anchor_date(settings.savings_anchor_day)

    checking_deficit = quantize_amount(
        max(settings.checking_minimum_balance - checking_balance, Decimal("0.00"))
    )
    savings_deficit = quantize_amount(
        max(settings.savings_minimum_balance - savings_balance, Decimal("0.00"))
    )

    checking_fee = quantize_amount(settings.checking_minimum_fee)
    savings_fee = quantize_amount(settings.savings_minimum_fee)

    def format_date(value: date | None) -> str:
        if not value:
            return "—"
        return value.strftime("%B %d, %Y")

    def build_open_account_due(
        *,
        name: str,
        slug: str,
        deficit: Decimal,
        fee: Decimal,
        anchor: date | None,
        minimum: Decimal,
    ) -> dict[str, str]:
        formatted_anchor = format_date(anchor)

        if deficit > Decimal("0.00"):
            return {
                "slug": slug,
                "is_open": True,
                "name": name,
                "amount": format_currency(fee),
                "due_date": f"Fee posts on {formatted_anchor}",
                "tip": (
                    "Deposit {shortfall} before {anchor} to prevent the {fee} service fee."
                ).format(
                    shortfall=format_currency(deficit),
                    anchor=formatted_anchor,
                    fee=format_currency(fee),
                ),
            }

        return {
            "slug": slug,
            "is_open": True,
            "name": name,
            "amount": format_currency(Decimal("0.00")),
            "due_date": f"Review on {formatted_anchor}",
            "tip": (
                "Balance meets the {minimum} requirement. Keep it above the threshold to avoid fees."
            ).format(minimum=format_currency(minimum)),
        }

    due_items: list[dict[str, str]] = []

    if checking_account:
        due_items.append(
            build_open_account_due(
                name="Checking Account",
                slug="checking",
                deficit=checking_deficit,
                fee=checking_fee,
                anchor=checking_anchor,
                minimum=settings.checking_minimum_balance,
            )
        )
    else:
        due_items.append(
            {
                "slug": "checking",
                "is_open": False,
                "name": "Checking Account",
                "amount": format_currency(settings.checking_opening_deposit),
                "due_date": "Schedule after opening",
                "tip": (
                    "Open the checking account with at least "
                    f"{format_currency(settings.checking_opening_deposit)} to start tracking reviews."
                ),
            }
        )

    if savings_account:
        due_items.append(
            build_open_account_due(
                name="Savings Account",
                slug="savings",
                deficit=savings_deficit,
                fee=savings_fee,
                anchor=savings_anchor,
                minimum=settings.savings_minimum_balance,
            )
        )
    else:
        due_items.append(
            {
                "slug": "savings",
                "is_open": False,
                "name": "Savings Account",
                "amount": format_currency(settings.savings_opening_deposit),
                "due_date": "Schedule after opening",
                "tip": (
                    "Open the savings account with at least "
                    f"{format_currency(settings.savings_opening_deposit)} to begin earning interest."
                ),
            }
        )

    return due_items


def build_account_insights(
    settings: BankSettings, accounts: Iterable[BankAccount]
) -> dict[str, Any]:
    """Construct insight content for a professional overview layout."""

    account_lookup = {account.slug: account for account in accounts}
    checking_account = account_lookup.get("checking")
    savings_account = account_lookup.get("savings")

    checking_balance = checking_account.balance if checking_account else Decimal("0.00")
    savings_balance = savings_account.balance if savings_account else Decimal("0.00")

    savings_interest = estimate_interest_payout(
        savings_balance, settings.savings_interest_rate, settings.savings_anchor_day
    )

    def format_date(value: date | None) -> str:
        if not value:
            return "—"
        return value.strftime("%B %d, %Y")

    checking_info = {
        "slug": "checking",
        "is_open": checking_account is not None,
        "name": "Checking Account",
        "balance": format_currency(checking_balance),
        "opened": format_date(
            checking_account.created_at.date() if checking_account else None
        ),
        "next_anchor": format_date(
            compute_next_anchor_date(settings.checking_anchor_day)
        ),
        "minimum_balance": format_currency(settings.checking_minimum_balance),
        "fee": format_currency(settings.checking_minimum_fee),
    }

    savings_info = {
        "slug": "savings",
        "is_open": savings_account is not None,
        "name": "Savings Account",
        "balance": format_currency(savings_balance),
        "opened": format_date(
            savings_account.created_at.date() if savings_account else None
        ),
        "next_anchor": format_date(
            compute_next_anchor_date(settings.savings_anchor_day)
        ),
        "minimum_balance": format_currency(settings.savings_minimum_balance),
        "fee": format_currency(settings.savings_minimum_fee),
        "apy_rate": f"{decimal_to_number(settings.savings_interest_rate):.2f}% APY",
        "projected_interest": format_currency(savings_interest),
    }

    due_items = [
        item for item in build_account_due_items(settings, accounts) if item["is_open"]
    ]

    return {
        "checking": checking_info,
        "savings": savings_info,
        "accounts": [checking_info, savings_info],
        "due_items": due_items,
    }


def format_currency(amount: Decimal | float | str) -> str:
    """Return a currency formatted string for display content."""

    quantized = quantize_amount(amount)
    return f"${quantized:,.2f}"


def find_account(slug: str, *, include_closed: bool = False) -> BankAccount | None:
    """Return the requested account, if it exists."""

    if not slug:
        return None

    query = BankAccount.query.filter_by(slug=slug)
    if not include_closed:
        query = query.filter(BankAccount.is_closed.is_(False))
    return query.first()


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
