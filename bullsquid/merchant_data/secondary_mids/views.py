"""SecondaryMID API views."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from bullsquid.api.auth import AccessLevel, JWTCredentials
from bullsquid.api.errors import ResourceNotFoundError, UniqueError
from bullsquid.db import NoSuchRecord, fields_are_unique
from bullsquid.merchant_data import tasks
from bullsquid.merchant_data.auth import require_access_level
from bullsquid.merchant_data.enums import ResourceStatus
from bullsquid.merchant_data.locations.tables import Location
from bullsquid.merchant_data.merchants.tables import Merchant
from bullsquid.merchant_data.plans.tables import Plan
from bullsquid.merchant_data.secondary_mid_location_links.db import (
    create_secondary_mid_location_links,
)
from bullsquid.merchant_data.secondary_mids import db
from bullsquid.merchant_data.secondary_mids.models import (
    AssociatedLocationResponse,
    CreateSecondaryMIDRequest,
    LocationLinkRequest,
    LocationLinkResponse,
    SecondaryMIDDeletionResponse,
    SecondaryMIDRefsRequest,
    SecondaryMIDResponse,
    UpdateSecondaryMIDRequest,
    UpdateSecondaryMIDs,
)
from bullsquid.merchant_data.secondary_mids.tables import SecondaryMID
from bullsquid.settings import settings

router = APIRouter(prefix="/plans/{plan_ref}/merchants/{merchant_ref}/secondary_mids")


@router.get("", response_model=list[SecondaryMIDResponse])
async def list_secondary_mids(
    plan_ref: UUID,
    merchant_ref: UUID,
    exclude_location: UUID | None = Query(default=None),
    n: int = Query(default=settings.default_page_size),
    p: int = Query(default=1),
    _credentials: JWTCredentials = Depends(require_access_level(AccessLevel.READ_ONLY)),
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
        ) from ex

    return secondary_mids


@router.patch("", response_model=list[SecondaryMIDResponse])
async def bulk_update_secondary_mids(
    plan_ref: UUID,
    merchant_ref: UUID,
    secondary_mid_data: UpdateSecondaryMIDs,
    _credentials: JWTCredentials = Depends(
        require_access_level(AccessLevel.READ_WRITE)
    ),
) -> list[SecondaryMIDResponse]:
    """Update a number of secondary MID's enrolment status"""
    try:
        mids = await db.bulk_update_secondary_mids(
            set(secondary_mid_data.secondary_mid_refs),
            secondary_mid_data.payment_enrolment_status,
            merchant_ref=merchant_ref,
            plan_ref=plan_ref,
        )
    except NoSuchRecord as ex:
        loc = ["path"] if ex.table in {Plan, Merchant} else ["body"]
        plural = ex.table is SecondaryMID
        raise ResourceNotFoundError.from_no_such_record(
            ex, loc=loc, plural=plural
        ) from ex

    return mids


@router.get("/{secondary_mid_ref}", response_model=SecondaryMIDResponse)
async def get_secondary_mid_details(
    plan_ref: UUID,
    merchant_ref: UUID,
    secondary_mid_ref: UUID,
    _credentials: JWTCredentials = Depends(require_access_level(AccessLevel.READ_ONLY)),
) -> SecondaryMIDResponse:
    """Returns details of a single secondary MID."""
    try:
        mid = await db.get_secondary_mid(
            secondary_mid_ref, plan_ref=plan_ref, merchant_ref=merchant_ref
        )
    except NoSuchRecord as ex:
        raise ResourceNotFoundError.from_no_such_record(ex, loc=["path"]) from ex

    return mid


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=SecondaryMIDResponse,
)
async def create_secondary_mid(
    plan_ref: UUID,
    merchant_ref: UUID,
    secondary_mid_data: CreateSecondaryMIDRequest,
    _credentials: JWTCredentials = Depends(
        require_access_level(AccessLevel.READ_WRITE)
    ),
) -> SecondaryMIDResponse:
    """Create a secondary MID for a merchant."""
    value = secondary_mid_data.secondary_mid_metadata.secondary_mid
    if not await fields_are_unique(
        SecondaryMID,
        {SecondaryMID.secondary_mid: value},
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
            if ex.table in (Plan, Merchant)
            else ["body", "secondary_mid_metadata"]
        )
        raise ResourceNotFoundError.from_no_such_record(ex, loc=loc) from ex

    if secondary_mid_data.onboard:
        await tasks.queue.push(
            tasks.OnboardSecondaryMIDs(
                secondary_mid_refs=[secondary_mid.secondary_mid_ref]
            )
        )

    return secondary_mid


@router.post("/onboarding", response_model=list[SecondaryMIDResponse])
async def onboard_secondary_mids(
    plan_ref: UUID,
    merchant_ref: UUID,
    data: SecondaryMIDRefsRequest,
    _credentials: JWTCredentials = Depends(
        require_access_level(AccessLevel.READ_WRITE)
    ),
) -> list[SecondaryMIDResponse]:
    """Onboard a number of secondary MIDs into Harmonia."""
    if not data.secondary_mid_refs:
        return []

    try:
        secondary_mids = await db.get_secondary_mids(
            set(data.secondary_mid_refs),
            plan_ref=plan_ref,
            merchant_ref=merchant_ref,
        )
    except NoSuchRecord as ex:
        raise ResourceNotFoundError.from_no_such_record(
            ex, loc=["body"], plural=True
        ) from ex

    await tasks.queue.push(
        tasks.OnboardSecondaryMIDs(
            secondary_mid_refs=[
                secondary_mid.secondary_mid_ref for secondary_mid in secondary_mids
            ]
        )
    )

    return secondary_mids


@router.post("/offboarding", response_model=list[SecondaryMIDResponse])
async def offboard_secondary_mids(
    plan_ref: UUID,
    merchant_ref: UUID,
    data: SecondaryMIDRefsRequest,
    _credentials: JWTCredentials = Depends(
        require_access_level(AccessLevel.READ_WRITE)
    ),
) -> list[SecondaryMIDResponse]:
    """Offboard a number of secondary MIDs from Harmonia."""
    if not data.secondary_mid_refs:
        return []

    try:
        secondary_mids = await db.get_secondary_mids(
            set(data.secondary_mid_refs),
            plan_ref=plan_ref,
            merchant_ref=merchant_ref,
        )
    except NoSuchRecord as ex:
        raise ResourceNotFoundError.from_no_such_record(
            ex, loc=["body"], plural=True
        ) from ex

    await tasks.queue.push(
        tasks.OffboardSecondaryMIDs(
            secondary_mid_refs=[
                secondary_mid.secondary_mid_ref for secondary_mid in secondary_mids
            ]
        )
    )

    return secondary_mids


@router.post(
    "/deletion",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=list[SecondaryMIDDeletionResponse],
)
async def delete_secondary_mids(
    plan_ref: UUID,
    merchant_ref: UUID,
    deletion: SecondaryMIDRefsRequest,
    _credentials: JWTCredentials = Depends(
        require_access_level(AccessLevel.READ_WRITE_DELETE)
    ),
) -> list[SecondaryMIDDeletionResponse]:
    """Remove a number of secondary MIDs from a merchant."""
    if not deletion.secondary_mid_refs:
        return []

    try:
        onboarded, not_onboarded = await db.filter_onboarded_secondary_mids(
            set(deletion.secondary_mid_refs),
            plan_ref=plan_ref,
            merchant_ref=merchant_ref,
        )
    except NoSuchRecord as ex:
        loc = ["body"] if ex.table == SecondaryMID else ["path"]
        plural = ex.table == SecondaryMID
        raise ResourceNotFoundError.from_no_such_record(
            ex, loc=loc, plural=plural
        ) from ex

    if onboarded:
        await db.update_secondary_mids_status(
            onboarded,
            status=ResourceStatus.PENDING_DELETION,
            plan_ref=plan_ref,
            merchant_ref=merchant_ref,
        )

        await tasks.queue.push(
            tasks.OffboardAndDeleteSecondaryMIDs(secondary_mid_refs=onboarded)
        )

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
            reason=None,
        )
        for secondary_mid_ref in onboarded
    ] + [
        SecondaryMIDDeletionResponse(
            secondary_mid_ref=secondary_mid_ref,
            status=ResourceStatus.DELETED,
            reason=None,
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
    _credentials: JWTCredentials = Depends(
        require_access_level(AccessLevel.READ_WRITE)
    ),
) -> JSONResponse:
    """
    Link a location to a secondary MID.
    """
    try:
        links, created = await create_secondary_mid_location_links(
            refs=[
                (secondary_mid_ref, location_ref)
                for location_ref in link_request.location_refs
            ],
            plan_ref=plan_ref,
            merchant_ref=merchant_ref,
        )
    except NoSuchRecord as ex:
        loc = ["body"] if ex.table == Location else ["path"]
        raise ResourceNotFoundError.from_no_such_record(ex, loc=loc) from ex

    content = jsonable_encoder(
        [
            LocationLinkResponse(
                link_ref=link.pk,
                location_ref=link.location.pk,
                location_title=link.location.display_text,
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
    n: int = Query(default=settings.default_page_size),
    p: int = Query(default=1),
    _credentials: JWTCredentials = Depends(require_access_level(AccessLevel.READ_ONLY)),
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
        raise ResourceNotFoundError.from_no_such_record(ex, loc=["path"]) from ex

    return links


@router.patch("/{secondary_mid_ref}", response_model=SecondaryMIDResponse)
async def update_secondary_mid(
    plan_ref: UUID,
    merchant_ref: UUID,
    secondary_mid_ref: UUID,
    secondary_mid_data: UpdateSecondaryMIDRequest,
    _credentials: JWTCredentials = Depends(
        require_access_level(AccessLevel.READ_WRITE)
    ),
) -> SecondaryMIDResponse:
    """Update a primary MID's editable fields."""
    try:
        mid = await db.update_secondary_mid(
            secondary_mid_ref,
            secondary_mid_data,
            merchant_ref=merchant_ref,
            plan_ref=plan_ref,
        )
    except NoSuchRecord as ex:
        raise ResourceNotFoundError.from_no_such_record(ex, loc=["path"]) from ex

    return mid
