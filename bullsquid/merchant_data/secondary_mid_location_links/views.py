"""
Endpoints that operate on secondary MID location links.
"""
from fastapi import APIRouter, status
from pydantic import UUID4

from bullsquid.api.errors import ResourceNotFoundError
from bullsquid.db import NoSuchRecord
from bullsquid.merchant_data.secondary_mid_location_links import db

router = APIRouter(
    prefix="/plans/{plan_ref}/merchants/{merchant_ref}/secondary_mid_location_links"
)


@router.delete("/{link_ref}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_secondary_mid_location_link(
    plan_ref: UUID4, merchant_ref: UUID4, link_ref: UUID4
) -> None:
    """
    Delete the link between a secondary MID and a location.
    """

    try:
        await db.delete_secondary_mid_location_link(
            link_ref, plan_ref=plan_ref, merchant_ref=merchant_ref
        )
    except NoSuchRecord as ex:
        raise ResourceNotFoundError.from_no_such_record(ex, loc=["path"])
