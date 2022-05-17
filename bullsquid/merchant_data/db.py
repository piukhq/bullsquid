"""Database access layer."""
from datetime import datetime
from typing import Any, Mapping, TypedDict
from uuid import UUID

from bullsquid.merchant_data.tables import Merchant, PaymentScheme, Plan, PrimaryMID


class NoSuchRecord(Exception):
    """Raised when the requested record could not be found."""


async def get_plan(pk: UUID) -> Plan:
    """Return a plan by its primary key. Raises NoSuchRecord if `pk` is not found."""
    plan = await Plan.objects().get(Plan.pk == pk)
    if not plan:
        raise NoSuchRecord
    return plan


async def list_plans() -> list[Plan]:
    """Return a list of all plans."""
    return await Plan.objects()


async def create_plan(fields: Mapping[str, Any]) -> Plan:
    """Create a new plan with the given fields."""
    plan = Plan(**fields)
    await plan.save()
    return plan


async def update_plan(pk: UUID, fields: Mapping[str, Any]) -> Plan:
    """Update an existing merchant with the given fields."""
    plan = await get_plan(pk)
    for key, value in fields.items():
        setattr(plan, key, value)
    await plan.save()
    return plan


async def get_merchant(pk: UUID, *, plan_ref: UUID) -> Merchant:
    """Return a merchant by its primary key. Raises NoSuchRecord if `pk` is not found."""
    merchant = (
        await Merchant.objects()
        .where(Merchant.pk == pk, Merchant.plan == plan_ref)
        .first()
    )
    if not merchant:
        raise NoSuchRecord
    return merchant


async def list_merchants() -> list[Merchant]:
    """Return a list of all merchants."""
    return await Merchant.objects()


async def count_merchants(plan_ref: UUID) -> int:
    """Return a count of merchants in a plan."""
    return await Merchant.count().where(Merchant.plan == plan_ref)


async def create_merchant(fields: Mapping[str, Any], *, plan: Plan) -> Merchant:
    """Create a new merchant with the given fields."""
    merchant = Merchant(**fields, plan=plan)
    await merchant.save()
    return merchant


async def update_merchant(
    pk: UUID, fields: Mapping[str, Any], *, plan_ref: UUID
) -> Merchant:
    """Update an existing merchant with the given fields."""
    merchant = await get_merchant(pk, plan_ref=plan_ref)
    for key, value in fields.items():
        setattr(merchant, key, value)
    await merchant.save()
    return merchant


async def delete_merchant(pk: UUID, *, plan_ref: UUID) -> None:
    """Delete a merchant by its primary key. Raises NoSuchRecord if `pk` is not found."""
    merchant = await get_merchant(pk, plan_ref=plan_ref)
    await merchant.remove()


async def list_payment_schemes() -> list[PaymentScheme]:
    """Return a list of all payment schemes."""
    return await PaymentScheme.objects()


PrimaryMIDResult = TypedDict(
    "PrimaryMIDResult",
    {
        "pk": UUID,
        "payment_scheme.code": int,
        "mid": str,
        "visa_bin": str,
        "payment_enrolment_status": str,
        "date_added": datetime,
        "txm_status": str,
    },
)


async def list_primary_mids(
    *, plan_ref: UUID, merchant_ref: UUID
) -> list[PrimaryMIDResult]:
    """Return a list of all primary MIDs on the given merchant."""
    merchant = await get_merchant(merchant_ref, plan_ref=plan_ref)

    return await PrimaryMID.select(
        PrimaryMID.pk,
        PrimaryMID.payment_scheme.code,
        PrimaryMID.mid,
        PrimaryMID.visa_bin,
        PrimaryMID.payment_enrolment_status,
        PrimaryMID.date_added,
        PrimaryMID.txm_status,
    ).where(PrimaryMID.merchant == merchant)
