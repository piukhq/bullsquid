"""Fixtures & factory functions for building merchant data objects."""
import random
from typing import Any

from piccolo.testing.model_builder import ModelBuilder

from bullsquid.merchant_data.enums import ResourceStatus, TXMStatus
from bullsquid.merchant_data.identifiers.tables import Identifier
from bullsquid.merchant_data.locations.tables import Location
from bullsquid.merchant_data.merchants.tables import Merchant
from bullsquid.merchant_data.payment_schemes.tables import PaymentScheme
from bullsquid.merchant_data.plans.tables import Plan
from bullsquid.merchant_data.primary_mids.tables import PrimaryMID
from bullsquid.merchant_data.secondary_mids.tables import SecondaryMID
from bullsquid.merchant_data.tables import LocationSecondaryMIDLink


async def plan_factory(*, persist: bool = True, **defaults: Any) -> Plan:
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


async def merchant_factory(*, persist: bool = True, **defaults: Any) -> Merchant:
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


async def location_factory(*, persist: bool = True, **defaults: Any) -> Location:
    """Creates and returns a location."""
    return await ModelBuilder.build(
        Location,
        defaults={
            "status": ResourceStatus.ACTIVE,
            **defaults,  # type: ignore
        },
        persist=persist,
    )


async def primary_mid_factory(*, persist: bool = True, **defaults: Any) -> PrimaryMID:
    """Creates and returns a primary MID."""
    payment_schemes = await default_payment_schemes()
    return await ModelBuilder.build(
        PrimaryMID,
        defaults={
            "status": ResourceStatus.ACTIVE,
            "txm_status": TXMStatus.NOT_ONBOARDED,
            "payment_scheme": random.choice(payment_schemes),
            **defaults,  # type: ignore
        },
        persist=persist,
    )


async def secondary_mid_factory(
    *, persist: bool = True, **defaults: Any
) -> SecondaryMID:
    """Creates and returns a secondary MID."""
    payment_schemes = await default_payment_schemes()
    return await ModelBuilder.build(
        SecondaryMID,
        defaults={
            "status": ResourceStatus.ACTIVE,
            "txm_status": TXMStatus.NOT_ONBOARDED,
            "payment_scheme": random.choice(payment_schemes),
            **defaults,  # type: ignore
        },
        persist=persist,
    )


async def identifier_factory(*, persist: bool = True, **defaults: Any) -> Identifier:
    """Creates and returns an identifier."""
    return await ModelBuilder.build(
        Identifier,
        defaults={
            "status": ResourceStatus.ACTIVE,
            "txm_status": TXMStatus.NOT_ONBOARDED,
            **defaults,  # type: ignore
        },
        persist=persist,
    )


async def location_secondary_mid_link_factory(
    *, persist: bool = True, **defaults: Any
) -> LocationSecondaryMIDLink:
    return await ModelBuilder.build(
        LocationSecondaryMIDLink,
        defaults=defaults,  # type: ignore
        persist=persist,
    )


async def default_payment_schemes() -> list[PaymentScheme]:
    return [
        await PaymentScheme.objects().get_or_create(
            PaymentScheme.slug == "visa",
            defaults={
                PaymentScheme.label: "VISA",
                PaymentScheme.code: 1,
            },
        ),
        await PaymentScheme.objects().get_or_create(
            PaymentScheme.slug == "mastercard",
            defaults={
                PaymentScheme.label: "MASTERCARD",
                PaymentScheme.code: 2,
            },
        ),
        await PaymentScheme.objects().get_or_create(
            PaymentScheme.slug == "amex",
            defaults={
                PaymentScheme.label: "AMEX",
                PaymentScheme.code: 3,
            },
        ),
    ]
