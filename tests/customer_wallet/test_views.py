"""Tests for customer wallet API endpoints."""
import secrets
from typing import Any

from fastapi import status
from fastapi.testclient import TestClient
from requests import Response
from ward import test

from bullsquid.customer_wallet.user_lookups.tables import UserLookup
from tests.customer_wallet.factories import user_lookup_factory
from tests.fixtures import auth_header, database, test_client


def user_lookup_req_json(user_lookup: UserLookup) -> dict[str, Any]:
    """Return the JSON representation of a user lookup request."""
    return {
        "user": {
            "user_id": user_lookup.user_id,
            "channel": user_lookup.channel,
            "display_text": user_lookup.display_text,
        },
        "lookup": {
            "type": user_lookup.lookup_type,
            "criteria": user_lookup.criteria,
        },
    }


def user_lookup_resp_json(user_lookup: UserLookup) -> dict[str, Any]:
    """Return the JSON representation of a user lookup request."""
    json = user_lookup_req_json(user_lookup)
    json["lookup"]["datetime"] = user_lookup.updated_at.isoformat()
    return json


@test("can list user lookups with default pagination")
async def _(
    _db: None = database,
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
) -> None:
    auth_id = "test-authed-user-1"
    lookups = [await user_lookup_factory(auth_id=auth_id) for _ in range(5)]
    lookups = [
        await UserLookup.objects()
        .get(UserLookup.id == lookup.id)
        .output(load_json=True)
        for lookup in lookups
    ]
    resp = test_client.get(
        "/api/v1/customer_wallet/user_lookups",
        headers={"user": auth_id, **auth_header},
    )
    assert resp.status_code == status.HTTP_200_OK

    expected = [user_lookup_resp_json(lookup) for lookup in reversed(lookups)]
    assert resp.json() == expected


@test("can list user lookups with custom pagination")
async def _(
    _db: None = database,
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
) -> None:
    auth_id = "test-authed-user-1"
    lookups = [await user_lookup_factory(auth_id=auth_id) for _ in range(5)]
    lookups = [
        await UserLookup.objects()
        .get(UserLookup.id == lookup.id)
        .output(load_json=True)
        for lookup in lookups
    ]
    resp = test_client.get(
        "/api/v1/customer_wallet/user_lookups",
        params={"n": 2, "p": 2},
        headers={"user": auth_id, **auth_header},
    )
    assert resp.status_code == status.HTTP_200_OK

    expected = [
        user_lookup_resp_json(lookup) for lookup in list(reversed(lookups))[2:4]
    ]
    assert resp.json() == expected


@test("can upsert customer lookups with default pagination")
async def _(
    _db: None = database,
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
) -> None:
    auth_id = "test-authed-user-1"
    lookups = []

    resp: Response | None = None
    lookup: UserLookup | None = None
    for _ in range(10):
        user_id = secrets.token_urlsafe()
        lookup = await user_lookup_factory(persist=False, user_id=user_id)
        resp = test_client.put(
            "/api/v1/customer_wallet/user_lookups",
            headers={
                "user": auth_id,
                **auth_header,
            },
            json=user_lookup_req_json(lookup),
        )

        lookups.append(
            await UserLookup.objects()
            .where(UserLookup.auth_id == auth_id, UserLookup.user_id == user_id)
            .first()
            .output(load_json=True)
        )

    assert lookup is not None
    assert resp is not None

    assert resp.status_code == status.HTTP_201_CREATED

    # the most recent five should have been returned last.
    lookups = list(reversed(lookups))[:5]
    assert resp.json() == [user_lookup_resp_json(lookup) for lookup in lookups]


@test("can upsert customer lookups with custom pagination")
async def _(
    _db: None = database,
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
) -> None:
    auth_id = "test-authed-user-1"
    lookups = []

    resp: Response | None = None
    lookup: UserLookup | None = None
    for _ in range(10):
        user_id = secrets.token_urlsafe()
        lookup = await user_lookup_factory(persist=False, user_id=user_id)
        resp = test_client.put(
            "/api/v1/customer_wallet/user_lookups",
            params={"n": 3, "p": 2},
            headers={
                "user": auth_id,
                **auth_header,
            },
            json=user_lookup_req_json(lookup),
        )

        lookups.append(
            await UserLookup.objects()
            .where(UserLookup.auth_id == auth_id, UserLookup.user_id == user_id)
            .first()
            .output(load_json=True)
        )

    assert lookup is not None
    assert resp is not None

    assert resp.status_code == status.HTTP_201_CREATED

    # the most recent 3 from page 2 should have been returned last.
    lookups = list(reversed(lookups))[3:6]
    assert resp.json() == [user_lookup_resp_json(lookup) for lookup in lookups]


@test("lookups returned from the PUT endpoint are separated by the user header")
async def _(
    _db: None = database,
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
) -> None:
    lookup_1 = await user_lookup_factory(persist=False, auth_id="test-authed-user-1")
    lookup_2 = await user_lookup_factory(persist=False, auth_id="test-authed-user-2")

    resp = test_client.put(
        "/api/v1/customer_wallet/user_lookups",
        headers={"user": "test-authed-user-1", **auth_header},
        json=user_lookup_req_json(lookup_1),
    )
    assert resp.status_code == status.HTTP_201_CREATED
    assert len(resp.json()) == 1
    assert resp.json()[0]["user"]["user_id"] == lookup_1.user_id

    resp = test_client.put(
        "/api/v1/customer_wallet/user_lookups",
        headers={"user": "test-authed-user-2", **auth_header},
        json=user_lookup_req_json(lookup_2),
    )
    assert resp.status_code == status.HTTP_201_CREATED
    assert len(resp.json()) == 1
    assert resp.json()[0]["user"]["user_id"] == lookup_2.user_id


@test("upserting the same lookup twice returns a 201 followed by a 200")
async def _(
    _db: None = database,
    test_client: TestClient = test_client,
    auth_header: dict = auth_header,
) -> None:
    lookup = await user_lookup_factory(persist=False)

    resp = test_client.put(
        "/api/v1/customer_wallet/user_lookups",
        headers={
            "user": lookup.auth_id,
            **auth_header,
        },
        json=user_lookup_req_json(lookup),
    )

    assert resp.status_code == status.HTTP_201_CREATED

    resp = test_client.put(
        "/api/v1/customer_wallet/user_lookups",
        headers={
            "user": lookup.auth_id,
            **auth_header,
        },
        json=user_lookup_req_json(lookup),
    )

    assert resp.status_code == status.HTTP_200_OK
