from uuid import UUID, uuid4

from fastapi import status
from fastapi.testclient import TestClient

from bullsquid.merchant_data.comments.models import CommentResponse, EditCommentRequest
from bullsquid.merchant_data.comments.tables import Comment
from bullsquid.merchant_data.enums import ResourceType
from bullsquid.merchant_data.identifiers.tables import Identifier
from bullsquid.merchant_data.locations.tables import Location
from bullsquid.merchant_data.merchants.tables import Merchant
from bullsquid.merchant_data.plans.tables import Plan
from bullsquid.merchant_data.primary_mids.tables import PrimaryMID
from bullsquid.merchant_data.secondary_mids.tables import SecondaryMID
from bullsquid.merchant_data.tables import TableWithPK
from tests.helpers import (
    Factory,
    assert_is_missing_field_error,
    assert_is_not_found_error,
    assert_is_value_error,
)


def comment_json(
    comment: Comment,
    *,
    subject: TableWithPK,
) -> dict:
    return {
        "comment_ref": str(comment.pk),
        "created_at": comment.created_at.isoformat(),
        "created_by": comment.created_by,
        "is_edited": comment.is_edited,
        "is_deleted": comment.is_deleted,
        "subjects": [
            {
                "display_text": subject.display_text,
                "subject_ref": str(subject.pk),
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


async def test_list_by_subject_ref(
    plan_factory: Factory[Plan],
    comment_factory: Factory[Comment],
    test_client: TestClient,
) -> None:
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
                    subject=plan,
                )
            ],
        },
        "lower_comments": [],
    }


async def test_list_by_owner_ref(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    comment_factory: Factory[Comment],
    test_client: TestClient,
) -> None:
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
                        subject=merchant,
                    )
                ],
            }
        ],
    }


async def test_list_lower_comments_multiple_subject_types(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    primary_mid_factory: Factory[PrimaryMID],
    secondary_mid_factory: Factory[SecondaryMID],
    comment_factory: Factory[Comment],
    test_client: TestClient,
) -> None:
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
                        subject=primary_mid,
                    )
                ],
            },
            {
                "subject_type": "secondary_mid",
                "comments": [
                    comment_json(
                        await Comment.objects().get(Comment.pk == sm_comment.pk),
                        subject=secondary_mid,
                    )
                ],
            },
        ],
    }


async def test_filter_lower_comments_by_subject_type(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    primary_mid_factory: Factory[PrimaryMID],
    secondary_mid_factory: Factory[SecondaryMID],
    comment_factory: Factory[Comment],
    test_client: TestClient,
) -> None:
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
                        subject=secondary_mid,
                    )
                ],
            },
        ],
    }


async def test_list_with_replies(
    plan_factory: Factory[Plan],
    comment_factory: Factory[Comment],
    test_client: TestClient,
) -> None:
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
        comment_json(await Comment.objects().get(Comment.pk == reply.pk), subject=plan)
    ]


async def test_list_only_returns_top_level_comments(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    comment_factory: Factory[Comment],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    comment = await comment_factory(
        owner=plan.pk,
        owner_type=ResourceType.PLAN,
        subjects=[merchant.pk],
        subject_type=ResourceType.MERCHANT,
    )
    reply = await comment_factory(
        owner=plan.pk,
        owner_type=ResourceType.PLAN,
        subjects=[merchant.pk],
        subject_type=ResourceType.MERCHANT,
        parent=comment,
    )

    resp = test_client.get(
        "/api/v1/directory_comments", params={"ref": str(merchant.pk)}
    )

    assert resp.status_code == status.HTTP_200_OK, resp.text

    assert len(resp.json()["entity_comments"]["comments"]) == 1
    responses = resp.json()["entity_comments"]["comments"][0]["responses"]
    assert responses == [
        comment_json(
            await Comment.objects().get(Comment.pk == reply.pk), subject=merchant
        )
    ]


async def test_list_invalid_ref(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    comment_factory: Factory[Comment],
    test_client: TestClient,
) -> None:
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


async def test_create_on_plan(
    plan_factory: Factory[Plan],
    comment_factory: Factory[Comment],
    test_client: TestClient,
) -> None:
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
        subject=plan,
    )


async def test_create_on_merchant(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    comment_factory: Factory[Comment],
    test_client: TestClient,
) -> None:
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
        subject=merchant,
    )


async def test_create_on_location(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    location_factory: Factory[Location],
    comment_factory: Factory[Comment],
    test_client: TestClient,
) -> None:
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
        subject=location,
    )


async def test_create_on_primary_mid(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    primary_mid_factory: Factory[PrimaryMID],
    comment_factory: Factory[Comment],
    test_client: TestClient,
) -> None:
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
        subject=primary_mid,
    )


async def test_create_on_secondary_mid(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    secondary_mid_factory: Factory[SecondaryMID],
    comment_factory: Factory[Comment],
    test_client: TestClient,
) -> None:
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
        subject=secondary_mid,
    )


async def test_create_on_psimi(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    identifier_factory: Factory[Identifier],
    comment_factory: Factory[Comment],
    test_client: TestClient,
) -> None:
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
        subject=psimi,
    )


async def test_create_on_nonexistent_plan(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    comment_factory: Factory[Comment],
    test_client: TestClient,
) -> None:
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


async def test_create_on_nonexistent_merchant(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    location_factory: Factory[Location],
    comment_factory: Factory[Comment],
    test_client: TestClient,
) -> None:
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


async def test_create_incorrect_owner_type(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    primary_mid_factory: Factory[PrimaryMID],
    comment_factory: Factory[Comment],
    test_client: TestClient,
) -> None:
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


async def test_create_reply_on_plan(
    plan_factory: Factory[Plan],
    comment_factory: Factory[Comment],
    test_client: TestClient,
) -> None:
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
        subject=plan,
    )


async def test_reply_to_nonexistent_comment(
    plan_factory: Factory[Plan],
    comment_factory: Factory[Comment],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    comment = await comment_factory(persist=False)

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


async def test_create_with_nonexistent_subject(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    comment_factory: Factory[Comment],
    test_client: TestClient,
) -> None:
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


async def test_create_with_wrong_owner(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    comment_factory: Factory[Comment],
    test_client: TestClient,
) -> None:
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


async def test_create_with_incorrect_owner_type(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    location_factory: Factory[Location],
    comment_factory: Factory[Comment],
    test_client: TestClient,
) -> None:
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


async def test_update_comment(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    comment_factory: Factory[Comment],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    comment = await comment_factory(
        owner_type=ResourceType.PLAN,
        owner=plan.pk,
        subject_type=ResourceType.MERCHANT,
        subjects=[merchant.pk],
    )
    resp = test_client.patch(
        f"/api/v1/directory_comments/{comment.pk}",
        json={
            "text": "test text",
        },
    )

    comment = await Comment.objects().get(Comment.pk == comment.pk)
    assert resp.status_code == status.HTTP_200_OK
    assert comment.text == "test text"
    assert comment.is_edited == True


async def test_comment_with_missing_text(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    comment_factory: Factory[Comment],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    comment = await comment_factory(
        owner_type=ResourceType.PLAN,
        owner=plan.pk,
        subject_type=ResourceType.MERCHANT,
        subjects=[merchant.pk],
    )
    resp = test_client.patch(
        f"/api/v1/directory_comments/{comment.pk}",
        json={
            "text": "",
        },
    )
    assert_is_value_error(resp, loc=["body", "text"])


async def test_edit_nonexistent_comment(
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    comment_factory: Factory[Comment],
    test_client: TestClient,
) -> None:
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan)
    comment = await comment_factory(persist=False)
    resp = test_client.patch(
        f"/api/v1/directory_comments/{uuid4()}",
        json={
            "text": "test text",
        },
    )

    assert_is_not_found_error(resp, loc=["path", "comment_ref"])
