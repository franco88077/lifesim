"""Database models for the banking system."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint

from ..extensions import db


class BankSettings(db.Model):
    """Persisted configuration for the banking system."""

    id: int = db.Column(db.Integer, primary_key=True)
    bank_name: str = db.Column(db.String(120), nullable=False, default="Lifesim Bank")
    standard_fee: Decimal = db.Column(
        db.Numeric(10, 2), nullable=False, default=Decimal("12.00")
    )
    savings_interest_rate: Decimal = db.Column(
        db.Numeric(5, 3), nullable=False, default=Decimal("2.000")
    )
    checking_minimum_balance: Decimal = db.Column(
        db.Numeric(10, 2), nullable=False, default=Decimal("1500.00")
    )
    checking_minimum_fee: Decimal = db.Column(
        db.Numeric(10, 2), nullable=False, default=Decimal("12.00")
    )
    checking_anchor_day: int = db.Column(db.Integer, nullable=False, default=25)
    savings_minimum_balance: Decimal = db.Column(
        db.Numeric(10, 2), nullable=False, default=Decimal("500.00")
    )
    savings_minimum_fee: Decimal = db.Column(
        db.Numeric(10, 2), nullable=False, default=Decimal("5.00")
    )
    savings_anchor_day: int = db.Column(db.Integer, nullable=False, default=1)
    checking_opening_deposit: Decimal = db.Column(
        db.Numeric(10, 2), nullable=False, default=Decimal("100.00")
    )
    savings_opening_deposit: Decimal = db.Column(
        db.Numeric(10, 2), nullable=False, default=Decimal("50.00")
    )
    created_at: datetime = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at: datetime = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class BankAccount(db.Model):
    """Represents a single bank account tracked by the player."""

    __table_args__ = (
        CheckConstraint("balance >= 0", name="ck_bank_account_balance_positive"),
    )

    id: int = db.Column(db.Integer, primary_key=True)
    slug: str = db.Column(db.String(32), unique=True, nullable=False, index=True)
    name: str = db.Column(db.String(120), nullable=False)
    category: str = db.Column(db.String(64), nullable=False)
    balance: Decimal = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    created_at: datetime = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at: datetime = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class BankTransaction(db.Model):
    """Ledger entry for money moving in or out of an account."""

    id: int = db.Column(db.Integer, primary_key=True)
    account_id: int = db.Column(db.Integer, db.ForeignKey("bank_account.id"), nullable=False)
    name: str = db.Column(db.String(120), nullable=False)
    description: str = db.Column(db.Text, nullable=False)
    direction: str = db.Column(db.String(16), nullable=False)
    amount: Decimal = db.Column(db.Numeric(12, 2), nullable=False)
    created_at: datetime = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    account = db.relationship("BankAccount", backref="transactions")

    __table_args__ = (
        CheckConstraint(
            "direction IN ('credit', 'debit')", name="ck_bank_transaction_direction"
        ),
    )
