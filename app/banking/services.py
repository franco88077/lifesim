"""Helper utilities for banking data management."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from ..extensions import db
from .models import BankAccount, BankSettings, BankTransaction

DEFAULT_ACCOUNTS: tuple[dict[str, Any], ...] = (
    {
        "slug": "hand",
        "name": "Cash",
        "category": "Liquid Cash",
        "balance": Decimal("280.50"),
    },
    {
        "slug": "checking",
        "name": "Checking Account",
        "category": "Daily Spending",
        "balance": Decimal("5400.25"),
    },
    {
        "slug": "savings",
        "name": "Savings Account",
        "category": "Emergency Fund",
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

    settings = BankSettings.query.first()
    created = False

    if not settings:
        settings = BankSettings()
        db.session.add(settings)
        created = True

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
                created = True
        else:
            account = BankAccount(
                slug=config["slug"],
                name=config["name"],
                category=config["category"],
                balance=quantize_amount(config["balance"]),
            )
            db.session.add(account)
            accounts_by_slug[account.slug] = account
            created = True

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
        created = True

    if created:
        db.session.commit()

    return settings


def fetch_accounts() -> list[BankAccount]:
    """Return all bank accounts sorted by creation order."""

    return list(BankAccount.query.order_by(BankAccount.created_at.asc()).all())


def fetch_recent_transactions(limit: int = 20) -> list[BankTransaction]:
    """Return the most recent transactions including their related accounts."""

    statement = (
        select(BankTransaction)
        .options(joinedload(BankTransaction.account))
        .order_by(BankTransaction.created_at.desc())
        .limit(limit)
    )
    return list(db.session.execute(statement).scalars().all())


def build_banking_state(limit: int = 20) -> dict[str, Any]:
    """Return the structured state used by the transfer interface."""

    accounts = fetch_accounts()
    balances = {
        account.slug: {
            "label": account.name,
            "balance": decimal_to_number(account.balance),
        }
        for account in accounts
    }

    transactions = fetch_recent_transactions(limit)

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

    return {
        "balances": balances,
        "transactions": ledger,
        "account_labels": {account.slug: account.name for account in accounts},
    }


def build_account_insights(settings: BankSettings) -> list[dict[str, Any]]:
    """Construct insight content for the overview page."""

    fee_display = format_currency(settings.standard_fee)
    interest_display = f"{decimal_to_number(settings.savings_interest_rate):.2f}% APY"

    return [
        {
            "account": "Cash",
            "details": [
                {
                    "label": "Cash buffer",
                    "value": "Keep at least $200 to cover day-to-day expenses without dipping into accounts.",
                },
                {
                    "label": "Reconciliation",
                    "value": "Log every cash purchase so deposits back into checking stay accurate.",
                },
            ],
        },
        {
            "account": "Checking Account",
            "details": [
                {
                    "label": "Monthly service fee",
                    "value": f"A {fee_display} service charge applies when the balance falls under $1,500.",
                },
                {
                    "label": "Transaction guidance",
                    "value": "Schedule bill payments from checking to avoid surprise cash shortfalls.",
                },
            ],
        },
        {
            "account": "Savings Account",
            "details": [
                {
                    "label": "Interest rate",
                    "value": f"Savings grows at {interest_display} calculated on the average monthly balance.",
                },
                {
                    "label": "Transfer allowance",
                    "value": "Limit yourself to three outgoing transfers each month to avoid penalties.",
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
