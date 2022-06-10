"""Model factories that clear the table after each test."""
from typing import Any, Mapping

from piccolo.testing.model_builder import ModelBuilder
from ward import fixture

from bullsquid.merchant_data.enums import ResourceStatus
from bullsquid.merchant_data.identifiers.tables import Identifier
from bullsquid.merchant_data.merchants.tables import Merchant
from bullsquid.merchant_data.payment_schemes.tables import PaymentScheme
from bullsquid.merchant_data.plans.tables import Plan
from bullsquid.merchant_data.primary_mids.tables import PrimaryMID
from bullsquid.merchant_data.secondary_mids.tables import SecondaryMID
from tests.fixtures import database


async def plan_factory(*, persist: bool = True, **defaults: Mapping[str, Any]) -> Plan:
    """Creates and returns a plan."""
    return await ModelBuilder.build(
        Plan,
        defaults={
            "status": ResourceStatus.ACTIVE,
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
            "status": ResourceStatus.ACTIVE,
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
        defaults={
            "status": ResourceStatus.ACTIVE,
            **defaults,  # type: ignore
        },
        persist=persist,
    )


async def secondary_mid_factory(
    *, persist: bool = True, **defaults: Mapping[str, Any]
) -> Merchant:
    """Creates and returns a secondary MID."""
    return await ModelBuilder.build(
        SecondaryMID,
        defaults={
            "status": ResourceStatus.ACTIVE,
            **defaults,  # type: ignore
        },
        persist=persist,
    )


async def identifier_factory(
    *, persist: bool = True, **defaults: Mapping[str, Any]
) -> Identifier:
    """Creates and returns an identifier."""
    return await ModelBuilder.build(
        Identifier,
        defaults={
            "status": ResourceStatus.ACTIVE,
            **defaults,  # type: ignore
        },
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
async def three_primary_mids(_: None = database) -> list[PrimaryMID]:
    """Creates and returns three primary MIDs."""
    return [await primary_mid_factory() for _ in range(3)]


@fixture
async def secondary_mid(_: None = database) -> SecondaryMID:
    """Creates and returns a secondary MID."""
    return await secondary_mid_factory()


@fixture
async def three_secondary_mids(_: None = database) -> list[SecondaryMID]:
    """Creates and returns three secondary MIDs."""
    return [await secondary_mid_factory() for _ in range(3)]


@fixture
async def identifier(_: None = database) -> Identifier:
    """Creates and returns an identifier."""
    return await identifier_factory()


@fixture
async def three_identifiers(_: None = database) -> list[Identifier]:
    """Creates and returns three identifiers."""
    return [await identifier_factory() for _ in range(3)]


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
