"""Tests for the merchant management API."""
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from requests import Response
from starlette import status

from bullsquid.merchant_data import models
from bullsquid.merchant_data.tables import Merchant, PaymentScheme
from conftest import ModelFactory, ModelFactoryFixture, ModelFactoryMaker, ser
from settings import settings

AUTH = {
    "Authorization": settings.api_key,
}


@pytest.fixture
def payment_scheme_factory(
    model_factory: ModelFactoryMaker,
) -> ModelFactoryFixture:
    """Returns a model factory for creating payment schemes."""
    yield from model_factory(PaymentScheme)


@pytest.fixture
def default_payment_schemes(
    payment_scheme_factory: ModelFactory,
) -> list[PaymentScheme]:
    """Creates default payment schemes."""
    return [
        payment_scheme_factory.get(slug="visa"),
        payment_scheme_factory.get(slug="amex"),
        payment_scheme_factory.get(slug="mastercard"),
    ]


@pytest.fixture
def merchant_factory(
    model_factory: ModelFactoryMaker,
) -> ModelFactoryFixture:
    """Returns a model factory for creating merchants."""
    yield from model_factory(Merchant, icon_url=None)


def assert_is_uniqueness_error(resp: Response, *, loc: list[str]) -> None:
    """Asserts that the response is a uniqueness error."""
    assert not resp.ok, resp.text
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    detail = resp.json()["detail"]
    assert len(detail) == 1
    assert detail[0]["loc"] == loc
    assert detail[0]["type"] == "unique_error"


def assert_is_not_found_error(resp: Response, *, loc: list[str]) -> None:
    """Asserts that the response is a not found error."""
    assert not resp.ok, resp.text
    assert resp.status_code == status.HTTP_404_NOT_FOUND

    detail = resp.json()["detail"]
    assert len(detail) == 1
    assert detail[0]["loc"] == loc
    assert detail[0]["type"] == "ref_error"


def test_list_merchants(
    test_client: TestClient, merchant_factory: ModelFactory
) -> None:
    """Test listening a few merchants."""
    num_merchants = 5
    for _ in range(num_merchants):
        merchant_factory.get()

    resp = test_client.get("/merchant_data/v1/merchants", headers=AUTH)
    assert resp.ok, resp.text

    merchants = resp.json()
    assert len(merchants) == num_merchants


def test_create_unique_merchant(
    test_client: TestClient,
    merchant_factory: ModelFactory,
) -> None:
    """Test creating a merchant with a valid request."""
    resp = test_client.post(
        "/merchant_data/v1/merchants",
        json=ser(merchant_factory.get(persist=False), models.Merchant),
        headers=AUTH,
    )
    assert resp.ok, resp.text


def test_create_merchant_with_duplicate_name(
    test_client: TestClient,
    merchant_factory: ModelFactory,
) -> None:
    """Test creating a merchant with a duplicate name."""
    merchant = merchant_factory.get()
    new_merchant = merchant_factory.get(persist=False, name=merchant.name)
    resp = test_client.post(
        "/merchant_data/v1/merchants",
        json=ser(new_merchant, models.Merchant),
        headers=AUTH,
    )

    assert_is_uniqueness_error(resp, loc=["body", "name"])
    assert Merchant.count().where(Merchant.name == new_merchant.name).run_sync() == 1


def test_create_merchant_with_duplicate_slug(
    test_client: TestClient,
    merchant_factory: ModelFactory,
) -> None:
    """Test creating a merchant with a duplicate name."""
    merchant = merchant_factory.get()
    new_merchant = merchant_factory.get(persist=False, slug=merchant.slug)
    resp = test_client.post(
        "/merchant_data/v1/merchants",
        json=ser(new_merchant, models.Merchant),
        headers=AUTH,
    )

    assert_is_uniqueness_error(resp, loc=["body", "slug"])
    assert Merchant.count().where(Merchant.slug == new_merchant.slug).run_sync() == 1


def test_create_merchant_with_duplicate_plan_id(
    test_client: TestClient,
    merchant_factory: ModelFactory,
) -> None:
    """Test creating a merchant with a duplicate plan ID."""
    merchant = merchant_factory.get()
    new_merchant = merchant_factory.get(persist=False, plan_id=merchant.plan_id)

    resp = test_client.post(
        "/merchant_data/v1/merchants",
        json=ser(new_merchant, models.Merchant),
        headers=AUTH,
    )

    assert_is_uniqueness_error(resp, loc=["body", "plan_id"])
    assert (
        Merchant.count().where(Merchant.plan_id == new_merchant.plan_id).run_sync() == 1
    )


def test_update_merchant(
    test_client: TestClient,
    merchant_factory: ModelFactory,
) -> None:
    """Test updating a merchant with a valid request."""
    merchant = merchant_factory.get()
    new_merchant = merchant_factory.get(persist=False, name=merchant.name)
    new_merchant_data = ser(new_merchant, models.Merchant)

    resp = test_client.put(
        f"/merchant_data/v1/merchants/{merchant.pk}",
        json=new_merchant_data,
        headers=AUTH,
    )

    assert resp.ok, resp.text
    assert resp.json() == new_merchant_data | {"pk": str(merchant.pk)}


def test_update_merchant_with_duplicate_details(
    test_client: TestClient,
    merchant_factory: ModelFactory,
) -> None:
    """Test updating a merchant with duplicates of another merchant's fields."""
    merchant = merchant_factory.get()
    merchant2 = merchant_factory.get()
    new_merchant = merchant_factory.get(persist=False, name=merchant2.name)
    new_merchant_data = ser(new_merchant, models.Merchant)

    resp = test_client.put(
        f"/merchant_data/v1/merchants/{merchant.pk}",
        json=new_merchant_data,
        headers=AUTH,
    )

    assert_is_uniqueness_error(resp, loc=["body", "name"])


def test_update_merchant_with_invalid_pk(
    test_client: TestClient,
    merchant_factory: ModelFactory,
) -> None:
    """Test updating a merchant with an invalid pk."""
    merchant = merchant_factory.get(persist=False)
    resp = test_client.put(
        f"/merchant_data/v1/merchants/{uuid4()}",
        json=ser(merchant, models.Merchant),
        headers=AUTH,
    )
    assert_is_not_found_error(resp, loc=["path", "merchant_ref"])


def test_delete_merchant(
    test_client: TestClient,
    merchant_factory: ModelFactory,
) -> None:
    """Test deleting an existing merchant."""
    merchant = merchant_factory.get()
    resp = test_client.delete(
        f"/merchant_data/v1/merchants/{merchant.pk}", headers=AUTH
    )
    assert resp.ok, resp.text
    assert resp.status_code == status.HTTP_204_NO_CONTENT
    assert not Merchant.exists().where(Merchant.pk == merchant.pk).run_sync()


def test_delete_merchant_with_invalid_pk(test_client: TestClient) -> None:
    """Test deleting a merchant with an invalid pk."""
    resp = test_client.delete(f"/merchant_data/v1/merchants/{uuid4()}", headers=AUTH)
    assert_is_not_found_error(resp, loc=["path", "merchant_ref"])
