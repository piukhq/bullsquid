# """Tests for endpoints that do CRUD operations on merchants."""
# from uuid import uuid4

# from fastapi.testclient import TestClient
# from starlette import status

# from bullsquid.merchant_data import models
# from bullsquid.merchant_data.tables import Location, Merchant
# from conftest import (
#     ModelFactory,
#     assert_is_missing_field_error,
#     assert_is_not_found_error,
#     assert_is_uniqueness_error,
#     merchant_factory,
#     ser,
# )


# def test_list_merchants(
#     test_client: TestClient, merchant_factory: ModelFactory, auth_header: dict
# ) -> None:
#     """Test listing a few merchants."""
#     num_merchants = 5
#     for _ in range(num_merchants):
#         merchant_factory.get()

#     resp = test_client.get("/merchant_data/v1/merchants", headers=auth_header)
#     assert resp.ok, resp.text

#     merchants = resp.json()
#     assert len(merchants) == Merchant.count().run_sync()


# def test_create_unique_merchant(
#     test_client: TestClient, merchant_factory: ModelFactory, auth_header: dict
# ) -> None:
#     """Test creating a merchant with a valid request."""
#     resp = test_client.post(
#         "/merchant_data/v1/merchants",
#         json=ser(merchant_factory.get(persist=False), models.Merchant),
#         headers=auth_header,
#     )
#     assert resp.ok, resp.text
#     assert Merchant.exists().where(Merchant.pk == resp.json()["pk"]).run_sync()


# def test_create_merchant_with_duplicate_name(
#     test_client: TestClient, merchant_factory: ModelFactory, auth_header: dict
# ) -> None:
#     """Test creating a merchant with a duplicate name."""
#     merchant = merchant_factory.get()
#     new_merchant = merchant_factory.get(persist=False, name=merchant.name)
#     resp = test_client.post(
#         "/merchant_data/v1/merchants",
#         json=ser(new_merchant, models.Merchant),
#         headers=auth_header,
#     )

#     assert_is_uniqueness_error(resp, loc=["body", "name"])
#     assert Merchant.count().where(Merchant.name == new_merchant.name).run_sync() == 1


# def test_create_merchant_with_duplicate_slug(
#     test_client: TestClient, merchant_factory: ModelFactory, auth_header: dict
# ) -> None:
#     """Test creating a merchant with a duplicate name."""
#     merchant = merchant_factory.get()
#     new_merchant = merchant_factory.get(persist=False, slug=merchant.slug)
#     resp = test_client.post(
#         "/merchant_data/v1/merchants",
#         json=ser(new_merchant, models.Merchant),
#         headers=auth_header,
#     )

#     assert_is_uniqueness_error(resp, loc=["body", "slug"])
#     assert Merchant.count().where(Merchant.slug == new_merchant.slug).run_sync() == 1


# def test_create_merchant_with_duplicate_plan_id(
#     test_client: TestClient, merchant_factory: ModelFactory, auth_header: dict
# ) -> None:
#     """Test creating a merchant with a duplicate plan ID."""
#     merchant = merchant_factory.get()
#     new_merchant = merchant_factory.get(persist=False, plan_id=merchant.plan_id)

#     resp = test_client.post(
#         "/merchant_data/v1/merchants",
#         json=ser(new_merchant, models.Merchant),
#         headers=auth_header,
#     )

#     assert_is_uniqueness_error(resp, loc=["body", "plan_id"])
#     assert (
#         Merchant.count().where(Merchant.plan_id == new_merchant.plan_id).run_sync() == 1
#     )


# def test_update_merchant(
#     test_client: TestClient, merchant_factory: ModelFactory, auth_header: dict
# ) -> None:
#     """Test updating a merchant with a valid request."""
#     merchant = merchant_factory.get()
#     new_merchant = merchant_factory.get(persist=False, name=merchant.name)
#     new_merchant_data = ser(new_merchant, models.Merchant)

#     resp = test_client.put(
#         f"/merchant_data/v1/merchants/{merchant.pk}",
#         json=new_merchant_data,
#         headers=auth_header,
#     )

#     assert resp.ok, resp.text
#     assert resp.json() == new_merchant_data | {"pk": str(merchant.pk)}
#     assert Merchant.select().where(
#         Merchant.pk == merchant.pk
#     ).first().run_sync() == new_merchant_data | {"pk": merchant.pk}


# def test_update_merchant_with_duplicate_details(
#     test_client: TestClient, merchant_factory: ModelFactory, auth_header: dict
# ) -> None:
#     """Test updating a merchant with duplicates of another merchant's fields."""
#     merchant = merchant_factory.get()
#     merchant2 = merchant_factory.get()
#     new_merchant = merchant_factory.get(persist=False, name=merchant2.name)
#     new_merchant_data = ser(new_merchant, models.Merchant)

#     resp = test_client.put(
#         f"/merchant_data/v1/merchants/{merchant.pk}",
#         json=new_merchant_data,
#         headers=auth_header,
#     )

#     assert_is_uniqueness_error(resp, loc=["body", "name"])
#     assert Merchant.count().where(Merchant.name == merchant2.name).run_sync() == 1


# def test_update_merchant_with_invalid_pk(
#     test_client: TestClient, merchant_factory: ModelFactory, auth_header: dict
# ) -> None:
#     """Test updating a merchant with an invalid pk."""
#     merchant = merchant_factory.get(persist=False)
#     pk = uuid4()
#     resp = test_client.put(
#         f"/merchant_data/v1/merchants/{pk}",
#         json=ser(merchant, models.Merchant),
#         headers=auth_header,
#     )
#     assert_is_not_found_error(resp, loc=["path", "merchant_ref"])
#     assert not Merchant.exists().where(Merchant.pk == pk).run_sync()


# def test_delete_merchant(
#     test_client: TestClient, merchant_factory: ModelFactory, auth_header: dict
# ) -> None:
#     """Test deleting an existing merchant."""
#     merchant = merchant_factory.get()
#     resp = test_client.delete(
#         f"/merchant_data/v1/merchants/{merchant.pk}", headers=auth_header
#     )
#     assert resp.ok, resp.text
#     assert resp.status_code == status.HTTP_204_NO_CONTENT
#     assert not Merchant.exists().where(Merchant.pk == merchant.pk).run_sync()


# def test_delete_merchant_with_invalid_pk(
#     test_client: TestClient, auth_header: dict
# ) -> None:
#     """Test deleting a merchant with an invalid pk."""
#     resp = test_client.delete(
#         f"/merchant_data/v1/merchants/{uuid4()}", headers=auth_header
#     )
#     assert_is_not_found_error(resp, loc=["path", "merchant_ref"])


# def test_create_unique_location(
#     test_client: TestClient,
#     auth_header: dict,
#     merchant_factory: ModelFactory,
#     location_factory: ModelFactory,
# ) -> None:
#     """Test creating a location with all valid fields."""
#     merchant = merchant_factory.get()
#     resp = test_client.post(
#         f"/merchant_data/v1/merchants/{merchant.pk}/locations",
#         json=ser(location_factory.get(persist=False), models.Location),
#         headers=auth_header,
#     )
#     assert resp.ok, resp.text
#     assert Location.exists().where(Location.pk == resp.json()["pk"]).run_sync()


# def test_create_duplicate_location(
#     test_client: TestClient,
#     auth_header: dict,
#     merchant_factory: ModelFactory,
#     location_factory: ModelFactory,
# ) -> None:
#     """Test creating a location with a duplication location ID."""
#     merchant = merchant_factory.get()
#     location = location_factory.get(merchant=merchant)
#     duplicate = location_factory.get(location_id=location.location_id)
#     resp = test_client.post(
#         f"/merchant_data/v1/merchants/{merchant.pk}/locations",
#         json=ser(duplicate, models.Location),
#         headers=auth_header,
#     )
#     assert_is_uniqueness_error(resp, loc=["body", "location_id"])
#     assert (
#         Location.count()
#         .where(
#             Location.merchant == merchant,
#             Location.location_id == location.location_id,
#         )
#         .run_sync()
#         == 1
#     )


# def test_create_physical_location_with_missing_address_line_1(
#     test_client: TestClient,
#     auth_header: dict,
#     merchant_factory: ModelFactory,
#     location_factory: ModelFactory,
# ) -> None:
#     """Test creating a physical location with a missing address_line_1 field."""
#     merchant = merchant_factory.get()
#     location = location_factory.get(
#         merchant=merchant, is_physical_location=True, persist=False
#     )
#     json = ser(location, models.Location)
#     json["is_physical_location"] = True
#     json["address_line_1"] = None

#     resp = test_client.post(
#         f"/merchant_data/v1/merchants/{merchant.pk}/locations",
#         json=json,
#         headers=auth_header,
#     )
#     assert_is_missing_field_error(resp, loc=["body", "address_line_1"])
#     assert (
#         not Location.exists()
#         .where(
#             Location.merchant == merchant,
#             Location.location_id == location.location_id,
#         )
#         .run_sync()
#     )


# def test_create_location_with_invalid_merchant(
#     test_client: TestClient, auth_header: dict, location_factory: ModelFactory
# ) -> None:
#     """Test creating a location with a merchant ref that does not exist."""
#     location = location_factory.get(persist=False)
#     resp = test_client.post(
#         f"/merchant_data/v1/merchants/{uuid4()}/locations",
#         json=ser(location, models.Location),
#         headers=auth_header,
#     )
#     assert_is_not_found_error(resp, loc=["path", "merchant_ref"])


# def test_update_location(
#     test_client: TestClient,
#     auth_header: dict,
#     merchant_factory: ModelFactory,
#     location_factory: ModelFactory,
# ) -> None:
#     """Test updating an existing location with valid details."""
#     merchant = merchant_factory.get()
#     location = location_factory.get(merchant=merchant)

#     new_location = location_factory.get(persist=False)
#     new_location_data = ser(new_location, models.Location)

#     resp = test_client.put(
#         f"/merchant_data/v1/merchants/{merchant.pk}/locations/{location.pk}",
#         json=new_location_data,
#         headers=auth_header,
#     )

#     assert resp.ok, resp.text
#     assert resp.json() == new_location_data | {"pk": str(location.pk)}
#     assert Location.select().where(
#         Location.pk == location.pk
#     ).first().run_sync() == new_location_data | {
#         "pk": location.pk,
#         "merchant": merchant.pk,
#     }


# def test_update_location_invalid_merchant(
#     test_client: TestClient, auth_header: dict, location_factory: ModelFactory
# ) -> None:
#     """Test updating a location with a merchant that does not exist."""
#     location = location_factory.get()
#     resp = test_client.put(
#         f"/merchant_data/v1/merchants/{uuid4()}/locations/{location.pk}",
#         json=ser(location_factory.get(persist=False), models.Location),
#         headers=auth_header,
#     )
#     assert_is_not_found_error(resp, loc=["path", "merchant_ref"])


# def test_update_location_invalid_location(
#     test_client: TestClient,
#     auth_header: dict,
#     merchant_factory: ModelFactory,
#     location_factory: ModelFactory,
# ) -> None:
#     """Test updating a location with a merchant that does not exist."""
#     merchant = merchant_factory.get()
#     resp = test_client.put(
#         f"/merchant_data/v1/merchants/{merchant.pk}/locations/{uuid4()}",
#         json=ser(location_factory.get(persist=False), models.Location),
#         headers=auth_header,
#     )
#     assert_is_not_found_error(resp, loc=["path", "location_ref"])
