from uuid import UUID, uuid4

from fastapi import status
from fastapi.testclient import TestClient
from ward import test

from bullsquid.merchant_data.comments.tables import Comment
from bullsquid.merchant_data.enums import ResourceType
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
    subject_ref: UUID,
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
                "subject_ref": str(subject_ref),
                "icon_slug": None,
            }
        ],
        "metadata": {
            "owner_ref": str(comment.owner),
            "owner_type": ResourceType(comment.owner_type).value,
            "text": comment.text,
        },
        "responses": [],
    }


@test("can list a single comment by subject ref")
async def _(_: None = database, test_client: TestClient = test_client) -> None:
    plan = await plan_factory()
    comment = await comment_factory(
        owner=plan.pk,
        owner_type=ResourceType.PLAN,
        subjects=[plan.pk],
        subject_type=ResourceType.PLAN,
    )

    resp = test_client.get("/api/v1/directory_comments", params={"ref": str(plan.pk)})

    assert resp.status_code == status.HTTP_200_OK, resp.text
    assert resp.json() == {
        "entity_comments": {
            "subject_type": "plan",
            "comments": [
                comment_json(
                    await Comment.objects().get(Comment.pk == comment.pk),
                    subject_ref=plan.pk,
                )
            ],
        },
        "lower_comments": [],
    }


@test("can list a single comment by owner ref")
async def _(_: None = database, test_client: TestClient = test_client) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    comment = await comment_factory(
        owner=plan.pk,
        owner_type=ResourceType.PLAN,
        subjects=[merchant.pk],
        subject_type=ResourceType.MERCHANT,
    )

    resp = test_client.get("/api/v1/directory_comments", params={"ref": str(plan.pk)})

    assert resp.status_code == status.HTTP_200_OK, resp.text
    assert resp.json() == {
        "entity_comments": None,
        "lower_comments": [
            {
                "subject_type": "merchant",
                "comments": [
                    comment_json(
                        await Comment.objects().get(Comment.pk == comment.pk),
                        subject_ref=merchant.pk,
                    )
                ],
            }
        ],
    }


@test("can list lower comments with multiple subject types")
async def _(_: None = database, test_client: TestClient = test_client) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    primary_mid = await primary_mid_factory(merchant=merchant)
    secondary_mid = await secondary_mid_factory(merchant=merchant)
    pm_comment = await comment_factory(
        owner=merchant.pk,
        owner_type=ResourceType.MERCHANT,
        subjects=[primary_mid.pk],
        subject_type=ResourceType.PRIMARY_MID,
    )
    sm_comment = await comment_factory(
        owner=merchant.pk,
        owner_type=ResourceType.MERCHANT,
        subjects=[secondary_mid.pk],
        subject_type=ResourceType.SECONDARY_MID,
    )

    resp = test_client.get(
        "/api/v1/directory_comments", params={"ref": str(merchant.pk)}
    )

    assert resp.status_code == status.HTTP_200_OK, resp.text
    assert resp.json() == {
        "entity_comments": None,
        "lower_comments": [
            {
                "subject_type": "mid",
                "comments": [
                    comment_json(
                        await Comment.objects().get(Comment.pk == pm_comment.pk),
                        subject_ref=primary_mid.pk,
                    )
                ],
            },
            {
                "subject_type": "secondary_mid",
                "comments": [
                    comment_json(
                        await Comment.objects().get(Comment.pk == sm_comment.pk),
                        subject_ref=secondary_mid.pk,
                    )
                ],
            },
        ],
    }


@test("can filter lower comments by subject type")
async def _(_: None = database, test_client: TestClient = test_client) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    primary_mid = await primary_mid_factory(merchant=merchant)
    secondary_mid = await secondary_mid_factory(merchant=merchant)
    await comment_factory(
        owner=merchant.pk,
        owner_type=ResourceType.MERCHANT,
        subjects=[primary_mid.pk],
        subject_type=ResourceType.PRIMARY_MID,
    )
    comment = await comment_factory(
        owner=merchant.pk,
        owner_type=ResourceType.MERCHANT,
        subjects=[secondary_mid.pk],
        subject_type=ResourceType.SECONDARY_MID,
    )

    resp = test_client.get(
        "/api/v1/directory_comments",
        params={"ref": str(merchant.pk), "subject_type": "secondary_mid"},
    )

    assert resp.status_code == status.HTTP_200_OK, resp.text
    assert resp.json() == {
        "entity_comments": None,
        "lower_comments": [
            {
                "subject_type": "secondary_mid",
                "comments": [
                    comment_json(
                        await Comment.objects().get(Comment.pk == comment.pk),
                        subject_ref=secondary_mid.pk,
                    )
                ],
            },
        ],
    }


@test("listing comments with replies returns the replies")
async def _(_: None = database, test_client: TestClient = test_client) -> None:
    plan = await plan_factory()
    comment = await comment_factory(
        owner=plan.pk,
        owner_type=ResourceType.PLAN,
        subjects=[plan.pk],
        subject_type=ResourceType.PLAN,
    )
    reply = await comment_factory(
        owner=plan.pk,
        owner_type=ResourceType.PLAN,
        subjects=[plan.pk],
        subject_type=ResourceType.PLAN,
        parent=comment,
    )

    resp = test_client.get("/api/v1/directory_comments", params={"ref": str(plan.pk)})

    assert resp.status_code == status.HTTP_200_OK, resp.text

    responses = resp.json()["entity_comments"]["comments"][0]["responses"]
    assert responses == [
        comment_json(
            await Comment.objects().get(Comment.pk == reply.pk), subject_ref=plan.pk
        )
    ]


@test("listing comments with an invalid ref returns no results")
async def _(_: None = database, test_client: TestClient = test_client) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    await comment_factory(
        owner=plan.pk,
        owner_type=ResourceType.PLAN,
        subjects=[merchant.pk],
        subject_type=ResourceType.MERCHANT,
    )

    resp = test_client.get("/api/v1/directory_comments", params={"ref": str(uuid4())})

    assert resp.status_code == status.HTTP_200_OK
    assert resp.json() == {
        "entity_comments": None,
        "lower_comments": [],
    }


@test("can create a top-level comment on a plan")
async def _(_: None = database, test_client: TestClient = test_client) -> None:
    plan = await plan_factory()
    comment = await comment_factory(persist=False)

    resp = test_client.post(
        "/api/v1/directory_comments",
        json={
            "metadata": {
                "owner_ref": str(plan.pk),
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
        subject_ref=plan.pk,
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
                "owner_ref": str(plan.pk),
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
        subject_ref=merchant.pk,
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
                "owner_ref": str(merchant.pk),
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
        subject_ref=location.pk,
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
                "owner_ref": str(merchant.pk),
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
        subject_ref=primary_mid.pk,
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
                "owner_ref": str(merchant.pk),
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
        subject_ref=secondary_mid.pk,
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
                "owner_ref": str(merchant.pk),
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
        subject_ref=psimi.pk,
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
                "owner_ref": str(uuid4()),
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
    location = await location_factory(merchant=merchant)
    comment = await comment_factory(persist=False)

    resp = test_client.post(
        "/api/v1/directory_comments",
        json={
            "metadata": {
                "owner_ref": str(uuid4()),
                "owner_type": "merchant",
                "text": comment.text,
            },
            "subjects": [str(location.pk)],
            "subject_type": "location",
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
                "owner_ref": str(primary_mid.pk),
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
                "owner_ref": str(plan.pk),
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
        subject_ref=plan.pk,
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
                "owner_ref": str(plan.pk),
                "owner_type": "plan",
                "text": comment.text,
            },
            "subjects": [str(plan.pk)],
            "subject_type": "plan",
        },
    )

    assert_is_not_found_error(resp, loc=["path", "comment_ref"])


@test("can't comment on a subject that doesn't exist")
async def _(_: None = database, test_client: TestClient = test_client) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    comment = await comment_factory(persist=False)

    resp = test_client.post(
        "/api/v1/directory_comments",
        json={
            "metadata": {
                "owner_ref": str(plan.pk),
                "owner_type": "plan",
                "text": comment.text,
            },
            "subjects": [
                str(merchant.pk),
                str(uuid4()),
            ],
            "subject_type": "merchant",
        },
    )

    assert_is_not_found_error(resp, loc=["body", "merchant_ref"])
    assert not await Comment.exists().where(Comment.owner == plan.pk)


@test("can't comment on a subject from another owner")
async def _(_: None = database, test_client: TestClient = test_client) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    merchant2 = await merchant_factory()
    comment = await comment_factory(persist=False)

    resp = test_client.post(
        "/api/v1/directory_comments",
        json={
            "metadata": {
                "owner_ref": str(plan.pk),
                "owner_type": "plan",
                "text": comment.text,
            },
            "subjects": [
                str(merchant.pk),
                str(merchant2.pk),
            ],
            "subject_type": "merchant",
        },
    )

    assert_is_not_found_error(resp, loc=["body", "merchant_ref"])
    assert not await Comment.exists().where(Comment.owner == plan.pk)


@test("can't comment on a subject with the wrong owner type")
async def _(_: None = database, test_client: TestClient = test_client) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    location = await location_factory(merchant=merchant)
    comment = await comment_factory(persist=False)

    resp = test_client.post(
        "/api/v1/directory_comments",
        json={
            "metadata": {
                "owner_ref": str(plan.pk),
                "owner_type": "plan",
                "text": comment.text,
            },
            "subjects": [
                str(location.pk),
            ],
            "subject_type": "location",
        },
    )

    assert_is_value_error(resp, loc=["body", "__root__"])
    assert not await Comment.exists().where(Comment.owner == plan.pk)
