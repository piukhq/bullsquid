"""Fixtures & factory functions for building merchant data objects."""
import random
from typing import Any

import pytest
from piccolo.testing.model_builder import ModelBuilder

from bullsquid.merchant_data.comments.tables import Comment
from bullsquid.merchant_data.enums import ResourceStatus, TXMStatus
from bullsquid.merchant_data.identifiers.tables import Identifier
from bullsquid.merchant_data.locations.tables import Location
from bullsquid.merchant_data.merchants.tables import Merchant
from bullsquid.merchant_data.payment_schemes.tables import PaymentScheme
from bullsquid.merchant_data.plans.tables import Plan
from bullsquid.merchant_data.primary_mids.tables import PrimaryMID
from bullsquid.merchant_data.secondary_mid_location_links.tables import (
    SecondaryMIDLocationLink,
)
from bullsquid.merchant_data.secondary_mids.tables import SecondaryMID
from tests.helpers import Factory


@pytest.fixture
def plan_factory(database: None) -> Factory[Plan]:
    async def factory(*, persist: bool = True, **defaults: Any) -> Plan:
        return await ModelBuilder.build(
            Plan,
            defaults={
                "status": ResourceStatus.ACTIVE,
                "icon_url": "https://example.com/icon.png",
                **defaults,  # type: ignore
            },
            persist=persist,
        )

    return factory


@pytest.fixture
def merchant_factory(database: None) -> Factory[Merchant]:
    async def factory(*, persist: bool = True, **defaults: Any) -> Merchant:
        return await ModelBuilder.build(
            Merchant,
            defaults={
                "status": ResourceStatus.ACTIVE,
                "icon_url": "https://example.com/icon.png",
                **defaults,  # type: ignore
            },
            persist=persist,
        )

    return factory


@pytest.fixture
def location_factory(database: None) -> Factory[Location]:
    async def factory(*, persist: bool = True, **defaults: Any) -> Location:
        return await ModelBuilder.build(
            Location,
            defaults={
                "status": ResourceStatus.ACTIVE,
                **defaults,  # type: ignore
            },
            persist=persist,
        )

    return factory


@pytest.fixture
def primary_mid_factory(
    default_payment_schemes: list[PaymentScheme],
) -> Factory[PrimaryMID]:
    async def factory(*, persist: bool = True, **defaults: Any) -> PrimaryMID:
        return await ModelBuilder.build(
            PrimaryMID,
            defaults={
                "status": ResourceStatus.ACTIVE,
                "txm_status": TXMStatus.NOT_ONBOARDED,
                "payment_scheme": random.choice(default_payment_schemes),
                **defaults,  # type: ignore
            },
            persist=persist,
        )

    return factory


@pytest.fixture
def secondary_mid_factory(
    default_payment_schemes: list[PaymentScheme],
) -> Factory[SecondaryMID]:
    async def factory(*, persist: bool = True, **defaults: Any) -> SecondaryMID:
        return await ModelBuilder.build(
            SecondaryMID,
            defaults={
                "status": ResourceStatus.ACTIVE,
                "txm_status": TXMStatus.NOT_ONBOARDED,
                "payment_scheme": random.choice(default_payment_schemes),
                **defaults,  # type: ignore
            },
            persist=persist,
        )

    return factory


@pytest.fixture
def identifier_factory(database: None) -> Factory[Identifier]:
    async def factory(*, persist: bool = True, **defaults: Any) -> Identifier:
        return await ModelBuilder.build(
            Identifier,
            defaults={
                "status": ResourceStatus.ACTIVE,
                "txm_status": TXMStatus.NOT_ONBOARDED,
                **defaults,  # type: ignore
            },
            persist=persist,
        )

    return factory


@pytest.fixture
def secondary_mid_location_link_factory(
    database: None,
) -> Factory[SecondaryMIDLocationLink]:
    async def factory(
        *, persist: bool = True, **defaults: Any
    ) -> SecondaryMIDLocationLink:
        return await ModelBuilder.build(
            SecondaryMIDLocationLink,
            defaults=defaults,  # type: ignore
            persist=persist,
        )

    return factory


@pytest.fixture
def comment_factory(database: None) -> Factory[Comment]:
    async def factory(*, persist: bool = True, **defaults: Any) -> Comment:
        defaults = {
            "parent": None,  # FIXME: modelbuilder crashes on 'self' foreign keys
            **defaults,
        }
        return await ModelBuilder.build(Comment, defaults=defaults, persist=persist)  # type: ignore

    return factory


@pytest.fixture
async def default_payment_schemes(database: None) -> list[PaymentScheme]:
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