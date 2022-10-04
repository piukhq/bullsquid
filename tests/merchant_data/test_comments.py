from uuid import UUID, uuid4

from fastapi import status
from fastapi.testclient import TestClient
from ward import test

from bullsquid.merchant_data.comments.tables import Comment
from bullsquid.merchant_data.enums import ResourceType
from bullsquid.merchant_data.merchants.tables import Merchant
from bullsquid.merchant_data.plans.tables import Plan
from tests.fixtures import database, test_client
from tests.helpers import assert_is_not_found_error, assert_is_value_error
from tests.merchant_data.factories import (
    comment_factory,
    identifier_factory,
    location_factory,
    merchant_factory,
    plan_factory,
    primary_mid_factory,
    secondary_mid_factory,
)


def comment_json(
    comment: Comment,
    *,
    plan: Plan | None,
    merchant: Merchant | None,
    subject_type: ResourceType,
    entity_ref: UUID,
) -> dict:
    return {
        "comment_ref": str(comment.pk),
        "created_at": comment.created_at.isoformat(),
        "created_by": comment.created_by,
        "is_edited": comment.is_edited,
        "is_deleted": comment.is_deleted,
        "subjects": [
            {
                "display_text": "string",
                "plan_ref": str(plan.pk) if plan else None,
                "merchant_ref": str(merchant.pk) if merchant else None,
                "subject_type": subject_type.value,
                "entity_ref": str(entity_ref),
                "icon_slug": None,
            }
        ],
        "metadata": {
            "comment_owner": str(comment.owner),
            "owner_type": comment.owner_type,
            "text": comment.text,
        },
        "responses": [],
    }


@test("can create a top-level comment on a plan")
async def _(_: None = database, test_client: TestClient = test_client) -> None:
    plan = await plan_factory()
    comment = await comment_factory(persist=False)

    resp = test_client.post(
        "/api/v1/directory_comments",
        json={
            "metadata": {
                "comment_owner": str(plan.pk),
                "owner_type": "plan",
                "text": comment.text,
            },
            "subjects": [str(plan.pk)],
            "subject_type": "plan",
        },
    )

    assert resp.status_code == status.HTTP_201_CREATED

    comment = await Comment.objects().get(Comment.pk == resp.json()["comment_ref"])
    assert comment is not None

    assert resp.json() == comment_json(
        comment,
        plan=plan,
        merchant=None,
        subject_type=ResourceType.PLAN,
        entity_ref=plan.pk,
    )


@test("can create a top-level comment on a merchant")
async def _(_: None = database, test_client: TestClient = test_client) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    comment = await comment_factory(persist=False)

    resp = test_client.post(
        "/api/v1/directory_comments",
        json={
            "metadata": {
                "comment_owner": str(plan.pk),
                "owner_type": "plan",
                "text": comment.text,
            },
            "subjects": [str(merchant.pk)],
            "subject_type": "merchant",
        },
    )

    assert resp.status_code == status.HTTP_201_CREATED

    comment = await Comment.objects().get(Comment.pk == resp.json()["comment_ref"])
    assert comment is not None

    assert resp.json() == comment_json(
        comment,
        plan=plan,
        merchant=merchant,
        subject_type=ResourceType.MERCHANT,
        entity_ref=merchant.pk,
    )


@test("can create a top-level comment on a location")
async def _(_: None = database, test_client: TestClient = test_client) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    location = await location_factory(merchant=merchant)
    comment = await comment_factory(persist=False)

    resp = test_client.post(
        "/api/v1/directory_comments",
        json={
            "metadata": {
                "comment_owner": str(merchant.pk),
                "owner_type": "merchant",
                "text": comment.text,
            },
            "subjects": [str(location.pk)],
            "subject_type": "location",
        },
    )

    assert resp.status_code == status.HTTP_201_CREATED

    comment = await Comment.objects().get(Comment.pk == resp.json()["comment_ref"])
    assert comment is not None

    assert resp.json() == comment_json(
        comment,
        plan=plan,
        merchant=merchant,
        subject_type=ResourceType.LOCATION,
        entity_ref=location.pk,
    )


@test("can create a top-level comment on a primary mid")
async def _(_: None = database, test_client: TestClient = test_client) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    primary_mid = await primary_mid_factory(merchant=merchant)
    comment = await comment_factory(persist=False)

    resp = test_client.post(
        "/api/v1/directory_comments",
        json={
            "metadata": {
                "comment_owner": str(merchant.pk),
                "owner_type": "merchant",
                "text": comment.text,
            },
            "subjects": [str(primary_mid.pk)],
            "subject_type": "mid",
        },
    )

    assert resp.status_code == status.HTTP_201_CREATED, resp.text

    comment = await Comment.objects().get(Comment.pk == resp.json()["comment_ref"])
    assert comment is not None

    assert resp.json() == comment_json(
        comment,
        plan=plan,
        merchant=merchant,
        subject_type=ResourceType.PRIMARY_MID,
        entity_ref=primary_mid.pk,
    )


@test("can create a top-level comment on a secondary mid")
async def _(_: None = database, test_client: TestClient = test_client) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    secondary_mid = await secondary_mid_factory(merchant=merchant)
    comment = await comment_factory(persist=False)

    resp = test_client.post(
        "/api/v1/directory_comments",
        json={
            "metadata": {
                "comment_owner": str(merchant.pk),
                "owner_type": "merchant",
                "text": comment.text,
            },
            "subjects": [str(secondary_mid.pk)],
            "subject_type": "secondary_mid",
        },
    )

    assert resp.status_code == status.HTTP_201_CREATED, resp.text

    comment = await Comment.objects().get(Comment.pk == resp.json()["comment_ref"])
    assert comment is not None

    assert resp.json() == comment_json(
        comment,
        plan=plan,
        merchant=merchant,
        subject_type=ResourceType.SECONDARY_MID,
        entity_ref=secondary_mid.pk,
    )


@test("can create a top-level comment on a PSIMI")
async def _(_: None = database, test_client: TestClient = test_client) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    psimi = await identifier_factory(merchant=merchant)
    comment = await comment_factory(persist=False)

    resp = test_client.post(
        "/api/v1/directory_comments",
        json={
            "metadata": {
                "comment_owner": str(merchant.pk),
                "owner_type": "merchant",
                "text": comment.text,
            },
            "subjects": [str(psimi.pk)],
            "subject_type": "psimi",
        },
    )

    assert resp.status_code == status.HTTP_201_CREATED, resp.text

    comment = await Comment.objects().get(Comment.pk == resp.json()["comment_ref"])
    assert comment is not None

    assert resp.json() == comment_json(
        comment,
        plan=plan,
        merchant=merchant,
        subject_type=ResourceType.PSIMI,
        entity_ref=psimi.pk,
    )


@test("creating a comment with a non-existent plan owner returns a ref error")
async def _(_: None = database, test_client: TestClient = test_client) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    comment = await comment_factory(persist=False)

    resp = test_client.post(
        "/api/v1/directory_comments",
        json={
            "metadata": {
                "comment_owner": str(uuid4()),
                "owner_type": "plan",
                "text": comment.text,
            },
            "subjects": [str(merchant.pk)],
            "subject_type": "merchant",
        },
    )

    assert_is_not_found_error(resp, loc=["body", "plan_ref"])


@test("creating a comment with a non-existent merchant owner returns a ref error")
async def _(_: None = database, test_client: TestClient = test_client) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    comment = await comment_factory(persist=False)

    resp = test_client.post(
        "/api/v1/directory_comments",
        json={
            "metadata": {
                "comment_owner": str(uuid4()),
                "owner_type": "merchant",
                "text": comment.text,
            },
            "subjects": [str(merchant.pk)],
            "subject_type": "merchant",
        },
    )

    assert_is_not_found_error(resp, loc=["body", "merchant_ref"])


@test(
    "creating a comment with an owner type that isn't plan or merchant returns a value error"
)
async def _(_: None = database, test_client: TestClient = test_client) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    primary_mid = await primary_mid_factory(merchant=merchant)
    comment = await comment_factory(persist=False)

    resp = test_client.post(
        "/api/v1/directory_comments",
        json={
            "metadata": {
                "comment_owner": str(primary_mid.pk),
                "owner_type": "mid",
                "text": comment.text,
            },
            "subjects": [str(merchant.pk)],
            "subject_type": "merchant",
        },
    )

    assert_is_value_error(resp, loc=["body", "metadata", "owner_type"])


@test("can create a comment reply on a plan")
async def _(_: None = database, test_client: TestClient = test_client) -> None:
    plan = await plan_factory()
    comment = await comment_factory(persist=False)
    parent_comment = await comment_factory()

    resp = test_client.post(
        f"/api/v1/directory_comments/{parent_comment.pk}",
        json={
            "metadata": {
                "comment_owner": str(plan.pk),
                "owner_type": "plan",
                "text": comment.text,
            },
            "subjects": [str(plan.pk)],
            "subject_type": "plan",
        },
    )
    assert resp.status_code == status.HTTP_201_CREATED

    comment = await Comment.objects().get(Comment.pk == resp.json()["comment_ref"])
    assert comment is not None
    assert comment.parent == parent_comment.pk

    assert resp.json() == comment_json(
        comment,
        plan=plan,
        merchant=None,
        subject_type=ResourceType.PLAN,
        entity_ref=plan.pk,
    )


@test("can't reply to a comment that does not exist")
async def _(_: None = database, test_client: TestClient = test_client) -> None:
    plan = await plan_factory()
    comment = await comment_factory(persist=False)
    parent_comment = await comment_factory()

    resp = test_client.post(
        f"/api/v1/directory_comments/{uuid4()}",
        json={
            "metadata": {
                "comment_owner": str(plan.pk),
                "owner_type": "plan",
                "text": comment.text,
            },
            "subjects": [str(plan.pk)],
            "subject_type": "plan",
        },
    )

    assert_is_not_found_error(resp, loc=["path", "comment_ref"])
