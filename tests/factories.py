"""Model factories that clear the table after each test."""
from typing import Any, Mapping

from piccolo.testing.model_builder import ModelBuilder
from ward import fixture

from bullsquid.merchant_data.tables import Merchant, PaymentScheme, Plan, PrimaryMID
from tests.fixtures import database


async def plan_factory(*, persist: bool = True, **defaults: Mapping[str, Any]) -> Plan:
    """Creates and returns a plan."""
    return await ModelBuilder.build(
        Plan,
        defaults={
            "icon_url": "https://example.com/icon.png",
            **defaults,  # type: ignore
        },
        persist=persist,
    )


async def merchant_factory(
    *, persist: bool = True, **defaults: Mapping[str, Any]
) -> Merchant:
    """Creates and returns a merchant."""
    return await ModelBuilder.build(
        Merchant,
        defaults={
            "icon_url": "https://example.com/icon.png",
            **defaults,  # type: ignore
        },
        persist=persist,
    )


async def primary_mid_factory(
    *, persist: bool = True, **defaults: Mapping[str, Any]
) -> Merchant:
    """Creates and returns a primary MID."""
    return await ModelBuilder.build(
        PrimaryMID,
        defaults=defaults,  # type: ignore
        persist=persist,
    )


@fixture
async def plan(_: None = database) -> Plan:
    """Creates and returns a plan."""
    return await plan_factory()


@fixture
async def three_plans(_: None = database) -> list[Plan]:
    """Creates and returns three plans with the given defaults."""
    return [await plan_factory() for _ in range(3)]


@fixture
async def merchant(_: None = database) -> Merchant:
    """Creates and returns a merchant."""
    return await merchant_factory()


@fixture
async def three_merchants(_: None = database) -> list[Merchant]:
    """Creates and returns three merchants."""
    return [await merchant_factory() for _ in range(3)]


@fixture
async def primary_mid(_: None = database) -> PrimaryMID:
    """Creates and returns a primary MID."""
    return await primary_mid_factory()


@fixture
async def payment_schemes(_: None = database) -> list[PaymentScheme]:
    """Creates and returns some default payment schemes."""
    return [
        await ModelBuilder.build(
            PaymentScheme,
            defaults={
                "slug": "visa",
                "label": "VISA",
                "code": 1,
            },
        ),
        await ModelBuilder.build(
            PaymentScheme,
            defaults={
                "slug": "mastercard",
                "label": "MASTERCARD",
                "code": 2,
            },
        ),
        await ModelBuilder.build(
            PaymentScheme,
            defaults={
                "slug": "amex",
                "label": "AMEX",
                "code": 3,
            },
        ),
    ]
