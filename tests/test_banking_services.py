"""Unit tests for banking service helpers."""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

from app.banking import services
from app.settings.services import ensure_app_settings


def test_build_period_series_collapses_daily_points(app):
    """Daily chart data should contain one entry per calendar day."""

    with app.app_context():
        ensure_app_settings()

        base = datetime(2024, 5, 1, 9, 0)
        series = [
            (base, Decimal("100.00")),
            (base + timedelta(hours=3), Decimal("120.00")),
            (base + timedelta(days=1), Decimal("150.00")),
            (base + timedelta(days=1, hours=2), Decimal("160.00")),
        ]

        dataset = services._build_period_series(series)

        daily_dates = [point["date"] for point in dataset["daily"]]
        daily_values = [point["value"] for point in dataset["daily"]]

        assert daily_dates == ["2024-05-01", "2024-05-02"]
        assert daily_values == [120.0, 160.0]


def test_interest_series_daily_points_are_aggregated(app):
    """Interest projections should aggregate multiple events on the same day."""

    with app.app_context():
        ensure_app_settings()

        base = datetime(2024, 2, 1, 8, 0)
        balance_series = [
            (base, Decimal("200.00")),
            (base + timedelta(hours=6), Decimal("250.00")),
        ]

        interest_data = services._build_interest_series(
            balance_series, Decimal("5.00")
        )

        daily_points = interest_data["daily"]

        assert len(daily_points) == 1
        day, value = daily_points[0]

        assert day.isoformat() == "2024-02-01"

        expected_interest = services.quantize_amount(
            Decimal("250.00") * Decimal("5.00") / Decimal("100") / Decimal("365")
        )
        assert value == expected_interest
