"""Model factories that clear the table after each test."""
from piccolo.testing.model_builder import ModelBuilder
from ward import fixture

from bullsquid.merchant_data.tables import Merchant, PaymentScheme, Plan
from tests.fixtures import database


async def plan_factory(persist: bool = True) -> Plan:
    """Creates and returns a plan."""
    return await ModelBuilder.build(
        Plan,
        defaults={"icon_url": "https://example.com/icon.png"},
        persist=persist,
    )


async def merchant_factory(persist: bool = True) -> Merchant:
    """Creates and returns a merchant."""
    return await ModelBuilder.build(
        Merchant,
        defaults={"icon_url": "https://example.com/icon.png"},
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
    """Creates and returns three merchants with the given defaults."""
    return [await merchant_factory() for _ in range(3)]


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
