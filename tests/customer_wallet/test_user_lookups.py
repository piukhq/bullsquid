"""Tests for customer wallet API endpoints."""
import secrets
from datetime import datetime
from typing import Any

from fastapi import status
from fastapi.testclient import TestClient
from requests import Response

from bullsquid.customer_wallet.user_lookups.tables import UserLookup
from tests.customer_wallet.conftest import Factory


def user_json(user_lookup: UserLookup) -> dict[str, Any]:
    """Return the JSON representation of the `user` section of a user lookup request/response."""
    return {
        "user_id": user_lookup.user_id,
        "channel": user_lookup.channel,
        "display_text": user_lookup.display_text,
    }


def user_lookup_req_json(user_lookup: UserLookup) -> dict[str, Any]:
    """Return the JSON representation of a user lookup request."""
    return {
        "user": user_json(user_lookup),
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


def assert_lookup_was_upserted(user_lookup: UserLookup, json: dict) -> None:
    assert json["user"] == user_json(user_lookup)
    assert json["lookup"]["type"] == user_lookup.lookup_type
    assert datetime.fromisoformat(json["lookup"]["datetime"]) >= user_lookup.updated_at


async def test_list_user_lookups(
    user_lookup_factory: Factory[UserLookup],
    test_client: TestClient,
) -> None:
    auth_id = "test-authed-user-1"
    lookups = [await user_lookup_factory(auth_id=auth_id) for _ in range(5)]
    resp = test_client.get(
        "/api/v1/customer_wallet/user_lookups",
        headers={"user": auth_id},
    )
    assert resp.status_code == status.HTTP_200_OK

    expected = [user_lookup_resp_json(lookup) for lookup in reversed(lookups)]
    assert resp.json() == expected


async def test_list_user_lookups_custom_pagination(
    user_lookup_factory: Factory[UserLookup],
    test_client: TestClient,
) -> None:
    auth_id = "test-authed-user-1"
    lookups = [await user_lookup_factory(auth_id=auth_id) for _ in range(5)]
    resp = test_client.get(
        "/api/v1/customer_wallet/user_lookups",
        params={"n": 2, "p": 2},
        headers={"user": auth_id},
    )
    assert resp.status_code == status.HTTP_200_OK

    expected = [
        user_lookup_resp_json(lookup) for lookup in list(reversed(lookups))[2:4]
    ]
    assert resp.json() == expected


async def test_upsert_user_lookup(
    user_lookup_factory: Factory[UserLookup],
    test_client: TestClient,
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
            headers={"user": auth_id},
            json=user_lookup_req_json(lookup),
        )
        lookups.append(lookup)

    assert lookup is not None
    assert resp is not None

    assert resp.status_code == status.HTTP_201_CREATED

    # the most recent five should have been returned last.
    lookups = list(reversed(lookups))[:5]
    for json, lookup in zip(resp.json(), lookups):
        assert_lookup_was_upserted(lookup, json)


async def test_upsert_user_lookup_custom_pagination(
    user_lookup_factory: Factory[UserLookup],
    test_client: TestClient,
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
            headers={"user": auth_id},
            json=user_lookup_req_json(lookup),
        )
        lookups.append(lookup)

    assert lookup is not None
    assert resp is not None

    assert resp.status_code == status.HTTP_201_CREATED

    # the most recent 3 from page 2 should have been returned last.
    lookups = list(reversed(lookups))[3:6]
    for lookup, json in zip(lookups, resp.json()):
        assert_lookup_was_upserted(lookup, json)


async def test_upsert_user_lookup_user_header(
    user_lookup_factory: Factory[UserLookup],
    test_client: TestClient,
) -> None:
    lookup_1 = await user_lookup_factory(persist=False, auth_id="test-authed-user-1")
    lookup_2 = await user_lookup_factory(persist=False, auth_id="test-authed-user-2")

    resp = test_client.put(
        "/api/v1/customer_wallet/user_lookups",
        headers={"user": "test-authed-user-1"},
        json=user_lookup_req_json(lookup_1),
    )
    assert resp.status_code == status.HTTP_201_CREATED
    assert len(resp.json()) == 1
    assert resp.json()[0]["user"]["user_id"] == lookup_1.user_id

    resp = test_client.put(
        "/api/v1/customer_wallet/user_lookups",
        headers={"user": "test-authed-user-2"},
        json=user_lookup_req_json(lookup_2),
    )
    assert resp.status_code == status.HTTP_201_CREATED
    assert len(resp.json()) == 1
    assert resp.json()[0]["user"]["user_id"] == lookup_2.user_id


async def test_upsert_duplicate_lookup(
    user_lookup_factory: Factory[UserLookup],
    test_client: TestClient,
) -> None:
    lookup = await user_lookup_factory(persist=False)

    resp = test_client.put(
        "/api/v1/customer_wallet/user_lookups",
        headers={"user": lookup.auth_id},
        json=user_lookup_req_json(lookup),
    )

    assert resp.status_code == status.HTTP_201_CREATED

    resp = test_client.put(
        "/api/v1/customer_wallet/user_lookups",
        headers={"user": lookup.auth_id},
        json=user_lookup_req_json(lookup),
    )

    assert resp.status_code == status.HTTP_200_OK
