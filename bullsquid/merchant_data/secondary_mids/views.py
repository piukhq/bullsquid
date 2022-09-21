"""SecondaryMID API views."""
from uuid import UUID

from fastapi import APIRouter, Query, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from bullsquid.api.errors import ResourceNotFoundError, UniqueError
from bullsquid.db import NoSuchRecord, field_is_unique
from bullsquid.merchant_data.db import create_location_secondary_mid_links
from bullsquid.merchant_data.enums import ResourceStatus
from bullsquid.merchant_data.locations.tables import Location
from bullsquid.merchant_data.merchants.tables import Merchant
from bullsquid.merchant_data.plans.tables import Plan
from bullsquid.merchant_data.secondary_mids.tables import SecondaryMID

from . import db
from .models import (
    AssociatedLocationResponse,
    CreateSecondaryMIDRequest,
    LocationLinkRequest,
    LocationLinkResponse,
    SecondaryMIDDeletionRequest,
    SecondaryMIDDeletionResponse,
    SecondaryMIDMetadata,
    SecondaryMIDResponse,
)

router = APIRouter(prefix="/plans/{plan_ref}/merchants/{merchant_ref}/secondary_mids")


def create_secondary_mid_response(
    secondary_mid: db.SecondaryMIDResult,
) -> SecondaryMIDResponse:
    """Creates a SecondaryMIDResponse instance from the given secondary MID."""
    return SecondaryMIDResponse(
        secondary_mid_ref=secondary_mid["pk"],
        secondary_mid_metadata=SecondaryMIDMetadata(
            payment_scheme_code=secondary_mid["payment_scheme.code"],
            secondary_mid=secondary_mid["secondary_mid"],
            payment_scheme_store_name=secondary_mid["payment_scheme_store_name"],
            payment_enrolment_status=secondary_mid["payment_enrolment_status"],
        ),
        secondary_mid_status=secondary_mid["status"],
        date_added=secondary_mid["date_added"],
        txm_status=secondary_mid["txm_status"],
    )


@router.get("", response_model=list[SecondaryMIDResponse])
async def list_secondary_mids(
    plan_ref: UUID,
    merchant_ref: UUID,
    exclude_location: UUID | None = Query(default=None),
    n: int = Query(default=10),
    p: int = Query(default=1),
) -> list[SecondaryMIDResponse]:
    """Lists all secondary MIDs for a merchant."""
    try:
        secondary_mids = await db.list_secondary_mids(
            plan_ref=plan_ref,
            merchant_ref=merchant_ref,
            exclude_location=exclude_location,
            n=n,
            p=p,
        )
    except NoSuchRecord as ex:
        loc = ["query"] if ex.table == Location else ["path"]
        override_field_name = "exclude_location" if ex.table == Location else None
        raise ResourceNotFoundError.from_no_such_record(
            ex, loc=loc, override_field_name=override_field_name
        )

    return [create_secondary_mid_response(mid) for mid in secondary_mids]


@router.get("/{secondary_mid_ref}", response_model=SecondaryMIDResponse)
async def get_secondary_mid_details(
    plan_ref: UUID, merchant_ref: UUID, secondary_mid_ref: UUID
) -> SecondaryMIDResponse:
    """Returns details of a single secondary MID."""
    try:
        mid = await db.get_secondary_mid(
            secondary_mid_ref, plan_ref=plan_ref, merchant_ref=merchant_ref
        )
    except NoSuchRecord as ex:
        raise ResourceNotFoundError.from_no_such_record(ex, loc=["path"])

    return create_secondary_mid_response(mid)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=SecondaryMIDResponse,
)
async def create_secondary_mid(
    plan_ref: UUID,
    merchant_ref: UUID,
    secondary_mid_data: CreateSecondaryMIDRequest,
) -> SecondaryMIDResponse:
    """Create a secondary MID for a merchant."""

    if not await field_is_unique(
        SecondaryMID,
        "secondary_mid",
        secondary_mid_data.secondary_mid_metadata.secondary_mid,
    ):
        raise UniqueError(loc=["body", "secondary_mid_metadata", "secondary_mid"])

    try:
        secondary_mid = await db.create_secondary_mid(
            secondary_mid_data.secondary_mid_metadata,
            plan_ref=plan_ref,
            merchant_ref=merchant_ref,
        )
    except NoSuchRecord as ex:
        loc = (
            ["path"]
            if ex.table in [Plan, Merchant]
            else ["body", "secondary_mid_metadata"]
        )
        raise ResourceNotFoundError.from_no_such_record(ex, loc=loc)

    if secondary_mid_data.onboard:
        # TODO: implement once harmonia has support for secondary MID onboarding.
        # await tasks.queue.push(
        #     tasks.OnboardSecondaryMIDs(secondary_mid_refs=[secondary_mid["pk"]])
        # )
        ...

    return create_secondary_mid_response(secondary_mid)


@router.post(
    "/deletion",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=list[SecondaryMIDDeletionResponse],
)
async def delete_secondary_mids(
    plan_ref: UUID, merchant_ref: UUID, deletion: SecondaryMIDDeletionRequest
) -> list[SecondaryMIDDeletionResponse]:
    """Remove a number of secondary MIDs from a merchant."""
    if not deletion.secondary_mid_refs:
        return []

    try:
        onboarded, not_onboarded = await db.filter_onboarded_secondary_mids(
            deletion.secondary_mid_refs, plan_ref=plan_ref, merchant_ref=merchant_ref
        )
    except NoSuchRecord as ex:
        loc = ["body"] if ex.table == SecondaryMID else ["path"]
        plural = ex.table == SecondaryMID
        raise ResourceNotFoundError.from_no_such_record(ex, loc=loc, plural=plural)

    if onboarded:
        await db.update_secondary_mids_status(
            onboarded,
            status=ResourceStatus.PENDING_DELETION,
            plan_ref=plan_ref,
            merchant_ref=merchant_ref,
        )
        # TODO: implement once Harmonia has secondary MID support.
        # await tasks.queue.push(tasks.OffboardAndDeleteSecondaryMIDs(secondary_mid_refs=onboarded))

    if not_onboarded:
        await db.update_secondary_mids_status(
            not_onboarded,
            status=ResourceStatus.DELETED,
            plan_ref=plan_ref,
            merchant_ref=merchant_ref,
        )

    return [
        SecondaryMIDDeletionResponse(
            secondary_mid_ref=secondary_mid_ref,
            status=ResourceStatus.PENDING_DELETION,
        )
        for secondary_mid_ref in onboarded
    ] + [
        SecondaryMIDDeletionResponse(
            secondary_mid_ref=secondary_mid_ref, status=ResourceStatus.DELETED
        )
        for secondary_mid_ref in not_onboarded
    ]


@router.post(
    "/{secondary_mid_ref}/secondary_mid_location_links",
    responses={
        status.HTTP_200_OK: {"model": list[LocationLinkResponse]},
        status.HTTP_201_CREATED: {"model": list[LocationLinkResponse]},
    },
)
async def link_secondary_mid_to_location(
    plan_ref: UUID,
    merchant_ref: UUID,
    secondary_mid_ref: UUID,
    link_request: LocationLinkRequest,
) -> JSONResponse:
    """
    Link a location to a secondary MID.
    """
    try:
        links, created = await create_location_secondary_mid_links(
            refs=[
                (location_ref, secondary_mid_ref)
                for location_ref in link_request.location_refs
            ],
            plan_ref=plan_ref,
            merchant_ref=merchant_ref,
        )
    except NoSuchRecord as ex:
        loc = ["body"] if ex.table == Location else ["path"]
        raise ResourceNotFoundError.from_no_such_record(ex, loc=loc)

    content = jsonable_encoder(
        [
            LocationLinkResponse(
                link_ref=link.pk,
                location_ref=link.location.pk,
                location_title=link.location.title,
            )
            for link in links
        ]
    )

    return JSONResponse(
        content=content,
        status_code=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
    )


@router.get(
    "/{secondary_mid_ref}/secondary_mid_location_links",
    response_model=list[AssociatedLocationResponse],
)
async def list_location_secondary_mids(
    plan_ref: UUID,
    merchant_ref: UUID,
    secondary_mid_ref: UUID,
    n: int = Query(default=10),
    p: int = Query(default=1),
) -> list[AssociatedLocationResponse]:
    """List Secondary MIDs associated with location."""
    try:
        links = await db.list_associated_locations(
            plan_ref=plan_ref,
            merchant_ref=merchant_ref,
            secondary_mid_ref=secondary_mid_ref,
            n=n,
            p=p,
        )
    except NoSuchRecord as ex:
        raise ResourceNotFoundError.from_no_such_record(ex, loc=["path"])

    return [
        AssociatedLocationResponse(
            link_ref=link["pk"],
            location_ref=link["location"],
            location_title=Location.make_title(
                link["location.name"],
                link["location.address_line_1"],
                link["location.town_city"],
                link["location.postcode"],
            ),
        )
        for link in links
    ]
