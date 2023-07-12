from dataclasses import dataclass
from typing import BinaryIO, Generator
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from bullsquid.merchant_data.locations.tables import Location
from bullsquid.merchant_data.merchants.tables import Merchant
from bullsquid.merchant_data.plans.tables import Plan
from bullsquid.merchant_data.primary_mids.tables import PrimaryMID
from bullsquid.merchant_data.tasks import run_worker
from bullsquid.merchant_data.tasks.import_merchants import (
    InvalidRecord,
    import_merchant_file_record,
)
from tests.helpers import Factory


@pytest.fixture
def locations_file() -> Generator[BinaryIO, None, None]:
    """
    A locations ("long") file containing several merchants with an assortment
    of primary and secondary MIDs. Intentionally designed to hit as many code
    paths as possible on import.
    """
    with open("tests/merchant_data/fixtures/locations.csv", "rb") as f:
        yield f


@pytest.fixture
def locations_file_clean() -> Generator[BinaryIO, None, None]:
    """
    A copy of `locations_file` except the leading byte-order mark is removed.
    """
    with open("tests/merchant_data/fixtures/locations_clean.csv", "rb") as f:
        yield f


@pytest.fixture
def locations_file_no_merchant_name() -> Generator[BinaryIO, None, None]:
    """
    A locations ("long") file containing one merchant with no name provided.
    """
    with open("tests/merchant_data/fixtures/locations_no_merchant_name.csv", "rb") as f:
        yield f


@pytest.fixture
def locations_file_physical_no_address() -> Generator[BinaryIO, None, None]:
    """
    A locations ("long") file containing a location marked as `is_physical`,
    but with no address fields populated.
    """
    with open(
        "tests/merchant_data/fixtures/locations_physical_no_address.csv", "rb"
    ) as f:
        yield f


@pytest.fixture
def garbage_file() -> Generator[BinaryIO, None, None]:
    """
    A file containing purely random bytes.
    """
    with open("tests/merchant_data/fixtures/garbage_do_not_open.csv", "rb") as f:
        yield f


@pytest.fixture
def merchants_file() -> Generator[BinaryIO, None, None]:
    """
    A merchant details file containing several merchants.
    """
    with open("tests/merchant_data/fixtures/merchants.csv", "rb") as f:
        yield f


@pytest.fixture
def merchants_file_no_merchant_name() -> Generator[BinaryIO, None, None]:
    """
    A merchant details file missing the name column.
    """
    with open("tests/merchant_data/fixtures/merchants_no_merchant_name.csv", "rb") as f:
        yield f


@pytest.fixture
def identifiers_file() -> Generator[BinaryIO, None, None]:
    """
    A mids ("long") file containing several merchants with an assortment of
    primary and secondary MIDs. Intentionally designed to hit as many code
    paths as possible on import.
    """
    with open("tests/merchant_data/fixtures/identifiers.csv", "rb") as f:
        yield f


async def test_load_invalid_file_type(
    test_client: TestClient,
    locations_file: BinaryIO,
    plan_factory: Factory[Plan],
) -> None:
    plan = await plan_factory()
    resp = test_client.post(
        "/api/v1/plans/csv_upload",
        files={
            "file": locations_file,
        },
        data={
            "file_type": "fake file type for testing",
            "file_name": "locations.csv",
            "plan_ref": str(plan.pk),
        },
    )
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, resp.text


@pytest.mark.usefixtures("default_payment_schemes")
async def test_load_locations_file(
    test_client: TestClient,
    locations_file: BinaryIO,
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
) -> None:
    """Load a valid file with the correct merchants in place."""
    plan = await plan_factory()
    await merchant_factory(plan=plan, name="The Chester Mayfair")
    await merchant_factory(plan=plan, name="The Rubens at the Palace")
    await merchant_factory(plan=plan, name="100 Wardour St (Restaurant & Club)")
    resp = test_client.post(
        "/api/v1/plans/csv_upload",
        files={
            "file": locations_file,
        },
        data={
            "file_type": "locations",
            "file_name": "locations.csv",
            "plan_ref": str(plan.pk),
        },
    )

    assert resp.status_code == status.HTTP_202_ACCEPTED, resp.text
    await run_worker(burst=True)


@pytest.mark.usefixtures("default_payment_schemes")
async def test_load_locations_file_clean(
    test_client: TestClient,
    locations_file_clean: BinaryIO,
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
) -> None:
    """
    Load a valid file with no byte-order mark and with the correct merchants in place.
    """
    plan = await plan_factory()
    await merchant_factory(plan=plan, name="The Chester Mayfair")
    await merchant_factory(plan=plan, name="The Rubens at the Palace")
    await merchant_factory(plan=plan, name="100 Wardour St (Restaurant & Club)")
    resp = test_client.post(
        "/api/v1/plans/csv_upload",
        files={
            "file": locations_file_clean,
        },
        data={
            "file_type": "locations",
            "file_name": "locations.csv",
            "plan_ref": str(plan.pk),
        },
    )

    assert resp.status_code == status.HTTP_202_ACCEPTED, resp.text
    await run_worker(burst=True)


@pytest.mark.usefixtures("default_payment_schemes")
async def test_load_locations_file_with_merchant_ref(
    test_client: TestClient,
    locations_file: BinaryIO,
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
) -> None:
    """Load a valid file onto a specific merchant."""
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan, name="The Chester Mayfair")
    resp = test_client.post(
        "/api/v1/plans/csv_upload",
        files={
            "file": locations_file,
        },
        data={
            "file_type": "locations",
            "file_name": "locations.csv",
            "plan_ref": str(plan.pk),
            "merchant_ref": str(merchant.pk),
        },
    )

    assert resp.status_code == status.HTTP_202_ACCEPTED, resp.text
    await run_worker(burst=True)


@pytest.mark.usefixtures("default_payment_schemes")
async def test_load_locations_file_with_no_merchant_ref_or_name(
    test_client: TestClient,
    locations_file_no_merchant_name: BinaryIO,
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
) -> None:
    """Load a file with no merchant name, and without providing a merchant ref."""
    plan = await plan_factory()
    await merchant_factory(plan=plan, name="The Chester Mayfair")
    resp = test_client.post(
        "/api/v1/plans/csv_upload",
        files={
            "file": locations_file_no_merchant_name,
        },
        data={
            "file_type": "locations",
            "file_name": "locations.csv",
            "plan_ref": str(plan.pk),
        },
    )

    assert resp.status_code == status.HTTP_202_ACCEPTED, resp.text
    await run_worker(burst=True)


@pytest.mark.usefixtures("default_payment_schemes")
async def test_load_locations_file_no_merchants(
    test_client: TestClient,
    locations_file: BinaryIO,
    plan_factory: Factory[Plan],
) -> None:
    """
    Test loading a valid file without any of the required merchants in the database.
    """
    plan = await plan_factory()
    resp = test_client.post(
        "/api/v1/plans/csv_upload",
        files={
            "file": locations_file,
        },
        data={
            "file_type": "locations",
            "file_name": "locations.csv",
            "plan_ref": str(plan.pk),
        },
    )

    assert resp.status_code == status.HTTP_202_ACCEPTED, resp.text
    await run_worker(burst=True)


@pytest.mark.usefixtures("default_payment_schemes")
async def test_load_locations_file_physical_no_address(
    test_client: TestClient,
    locations_file_physical_no_address: BinaryIO,
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
) -> None:
    """Test loading a file containing a physical location with no address details."""
    plan = await plan_factory()
    await merchant_factory(plan=plan, name="The Chester Mayfair")
    resp = test_client.post(
        "/api/v1/plans/csv_upload",
        files={
            "file": locations_file_physical_no_address,
        },
        data={
            "file_type": "locations",
            "file_name": "locations.csv",
            "plan_ref": str(plan.pk),
        },
    )

    assert resp.status_code == status.HTTP_202_ACCEPTED, resp.text
    await run_worker(burst=True)


@pytest.mark.usefixtures("default_payment_schemes")
async def test_load_locations_file_duplicate_location(
    test_client: TestClient,
    locations_file: BinaryIO,
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
) -> None:
    """Test loading the same file twice."""
    plan = await plan_factory()
    await merchant_factory(plan=plan, name="The Chester Mayfair")
    await merchant_factory(plan=plan, name="The Rubens at the Palace")
    await merchant_factory(plan=plan, name="100 Wardour St (Restaurant & Club)")
    resp = test_client.post(
        "/api/v1/plans/csv_upload",
        files={
            "file": locations_file,
        },
        data={
            "file_type": "locations",
            "file_name": "locations.csv",
            "plan_ref": str(plan.pk),
        },
    )

    assert resp.status_code == status.HTTP_202_ACCEPTED, resp.text
    await run_worker(burst=True)

    # be kind, rewind
    locations_file.seek(0)

    resp = test_client.post(
        "/api/v1/plans/csv_upload",
        files={
            "file": locations_file,
        },
        data={
            "file_type": "locations",
            "file_name": "locations.csv",
            "plan_ref": str(plan.pk),
        },
    )

    assert resp.status_code == status.HTTP_202_ACCEPTED, resp.text
    await run_worker(burst=True)


@pytest.mark.usefixtures("default_payment_schemes")
async def test_load_locations_file_duplicate_primary_mid(
    test_client: TestClient,
    locations_file: BinaryIO,
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    primary_mid_factory: Factory[PrimaryMID],
) -> None:
    """Test loading a file containing a primary MID that already exists."""
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan, name="The Chester Mayfair")
    await merchant_factory(plan=plan, name="The Rubens at the Palace")
    await merchant_factory(plan=plan, name="100 Wardour St (Restaurant & Club)")
    await primary_mid_factory(merchant=merchant, payment_scheme="visa", mid="4005997")
    resp = test_client.post(
        "/api/v1/plans/csv_upload",
        files={
            "file": locations_file,
        },
        data={
            "file_type": "locations",
            "file_name": "locations.csv",
            "plan_ref": str(plan.pk),
        },
    )

    assert resp.status_code == status.HTTP_202_ACCEPTED, resp.text
    await run_worker(burst=True)


@pytest.mark.usefixtures("default_payment_schemes")
async def test_load_locations_file_duplicate_secondary_mid(
    test_client: TestClient,
    locations_file: BinaryIO,
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    secondary_mid_factory: Factory[PrimaryMID],
) -> None:
    """Test loading a file containing a secondary MID that already exists."""
    plan = await plan_factory()
    merchant = await merchant_factory(plan=plan, name="The Chester Mayfair")
    await merchant_factory(plan=plan, name="The Rubens at the Palace")
    await merchant_factory(plan=plan, name="100 Wardour St (Restaurant & Club)")
    await secondary_mid_factory(
        merchant=merchant, payment_scheme="visa", secondary_mid="4005997"
    )
    resp = test_client.post(
        "/api/v1/plans/csv_upload",
        files={
            "file": locations_file,
        },
        data={
            "file_type": "locations",
            "file_name": "locations.csv",
            "plan_ref": str(plan.pk),
        },
    )

    assert resp.status_code == status.HTTP_202_ACCEPTED, resp.text
    await run_worker(burst=True)


async def test_load_garbage_file(
    test_client: TestClient,
    garbage_file: BinaryIO,
    plan_factory: Factory[Plan],
) -> None:
    """Test loading a file containing random bytes."""
    plan = await plan_factory()
    resp = test_client.post(
        "/api/v1/plans/csv_upload",
        files={
            "file": garbage_file,
        },
        data={
            "file_type": "locations",
            "file_name": "locations.csv",
            "plan_ref": str(plan.pk),
        },
    )

    assert resp.status_code == status.HTTP_409_CONFLICT, resp.text


@pytest.mark.usefixtures("default_payment_schemes")
async def test_load_merchants_file(
    test_client: TestClient,
    merchants_file: BinaryIO,
    plan_factory: Factory[Plan],
) -> None:
    """Load a valid file with the correct plans in place."""
    plan = await plan_factory()
    resp = test_client.post(
        "/api/v1/plans/csv_upload",
        files={
            "file": merchants_file,
        },
        data={
            "file_type": "merchant_details",
            "file_name": "merchant_details.csv",
            "plan_ref": str(plan.pk),
        },
    )

    assert resp.status_code == status.HTTP_202_ACCEPTED, resp.text
    await run_worker(burst=True)


@pytest.mark.usefixtures("default_payment_schemes")
async def test_load_merchants_file_with_no_merchant_name(
    test_client: TestClient,
    merchants_file_no_merchant_name: BinaryIO,
    plan_factory: Factory[Plan],
) -> None:
    """Load a file with no merchant name, and without providing a merchant ref."""
    plan = await plan_factory()
    resp = test_client.post(
        "/api/v1/plans/csv_upload",
        files={
            "file": merchants_file_no_merchant_name,
        },
        data={
            "file_type": "merchant_details",
            "file_name": "merchant_details.csv",
            "plan_ref": str(plan.pk),
        },
    )

    assert resp.status_code == status.HTTP_409_CONFLICT, resp.text
    await run_worker(burst=True)


@pytest.mark.usefixtures("default_payment_schemes")
async def test_load_merchants_file_missing_plan(
    test_client: TestClient,
    merchants_file: BinaryIO,
) -> None:
    """Attempt to load a merchants file with a fake plan ref."""
    resp = test_client.post(
        "/api/v1/plans/csv_upload",
        files={
            "file": merchants_file,
        },
        data={
            "file_type": "merchant_details",
            "file_name": "merchant_details.csv",
            "plan_ref": str(uuid4()),
        },
    )

    assert resp.status_code == status.HTTP_202_ACCEPTED, resp.text
    await run_worker(burst=True)


@pytest.mark.usefixtures("default_payment_schemes")
async def test_process_invalid_merchant_file_record(
    plan_factory: Factory[Plan],
) -> None:
    """
    Ensure that the merchant file import task correctly validates the incoming
    data. We can't send a file to the API with these problems as it would be
    rejected outright. We can't put a bad record on the queue for the same
    reason. This uses a mock record to bypass pydantic's validation, and sends
    it directly to the task method.
    """

    @dataclass(frozen=True)
    class MerchantsFileRecord:
        name: str
        location_label: str = "stores"

    plan = await plan_factory()

    with pytest.raises(InvalidRecord):
        await import_merchant_file_record(
            MerchantsFileRecord(name=""),  # type: ignore
            plan_ref=plan.pk,
        )


@pytest.mark.usefixtures("default_payment_schemes")
async def test_load_locations_with_merchant_ref_file(
    test_client: TestClient,
    locations_file: BinaryIO,
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
) -> None:
    """Load a valid file with the correct merchants in place."""
    plan = await plan_factory()
    await merchant_factory(plan=plan, name="The Chester Mayfair")
    await merchant_factory(plan=plan, name="The Rubens at the Palace")
    merchant = await merchant_factory(
        plan=plan, name="100 Wardour St (Restaurant & Club)"
    )
    resp = test_client.post(
        "/api/v1/plans/csv_upload",
        files={
            "file": locations_file,
        },
        data={
            "file_type": "locations",
            "file_name": "locations.csv",
            "plan_ref": str(plan.pk),
            "merchant_ref": str(merchant.pk),
        },
    )

    assert resp.status_code == status.HTTP_202_ACCEPTED, resp.text
    await run_worker(burst=True)


@pytest.mark.usefixtures("default_payment_schemes")
async def test_load_identifiers_file(
    test_client: TestClient,
    identifiers_file: BinaryIO,
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    location_factory: Factory[Location],
) -> None:
    """Load a valid file with the correct mids in place."""
    plan = await plan_factory()
    merchant1 = await merchant_factory(plan=plan, name="2Wasabi")
    merchant2 = await merchant_factory(plan=plan, name="3Wasabi")
    await location_factory(merchant=merchant1, location_id="A037")
    await location_factory(merchant=merchant2, location_id="A038")
    resp = test_client.post(
        "/api/v1/plans/csv_upload",
        files={
            "file": identifiers_file,
        },
        data={
            "file_type": "identifiers",
            "file_name": "identifiers.csv",
            "plan_ref": str(plan.pk),
        },
    )

    assert resp.status_code == status.HTTP_202_ACCEPTED, resp.text
    await run_worker(burst=True)


@pytest.mark.usefixtures("default_payment_schemes")
async def test_load_identifiers_file_with_merchant_ref(
    test_client: TestClient,
    identifiers_file: BinaryIO,
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    location_factory: Factory[Location],
) -> None:
    """Load a valid file with the correct mids in place."""
    plan = await plan_factory()
    merchant1 = await merchant_factory(plan=plan, name="2Wasabi")
    merchant2 = await merchant_factory(plan=plan, name="3Wasabi")
    await location_factory(merchant=merchant1, location_id="A037")
    await location_factory(merchant=merchant2, location_id="A038")
    resp = test_client.post(
        "/api/v1/plans/csv_upload",
        files={
            "file": identifiers_file,
        },
        data={
            "file_type": "identifiers",
            "file_name": "identifiers.csv",
            "plan_ref": str(plan.pk),
            "merchant_ref": str(merchant1.pk),
        },
    )

    assert resp.status_code == status.HTTP_202_ACCEPTED, resp.text
    await run_worker(burst=True)


@pytest.mark.usefixtures("default_payment_schemes")
async def test_load_identifiers_file_missing_location(
    test_client: TestClient,
    identifiers_file: BinaryIO,
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    location_factory: Factory[Location],
) -> None:
    """Load a valid file with the correct mids in place."""
    plan = await plan_factory()
    await merchant_factory(plan=plan, name="2Wasabi")
    merchant2 = await merchant_factory(plan=plan, name="3Wasabi")
    await location_factory(merchant=merchant2, location_id="A038")
    resp = test_client.post(
        "/api/v1/plans/csv_upload",
        files={
            "file": identifiers_file,
        },
        data={
            "file_type": "identifiers",
            "file_name": "identifiers.csv",
            "plan_ref": str(plan.pk),
        },
    )

    assert resp.status_code == status.HTTP_202_ACCEPTED, resp.text
    await run_worker(burst=True)


@pytest.mark.usefixtures("default_payment_schemes")
async def test_load_identifiers_file_with_archive(
    test_client: TestClient,
    identifiers_file: BinaryIO,
    plan_factory: Factory[Plan],
    merchant_factory: Factory[Merchant],
    location_factory: Factory[Location],
) -> None:
    """Load a valid file with blob storage configured."""
    plan = await plan_factory()
    merchant1 = await merchant_factory(plan=plan, name="2Wasabi")
    merchant2 = await merchant_factory(plan=plan, name="3Wasabi")
    await location_factory(merchant=merchant1, location_id="A037")
    await location_factory(merchant=merchant2, location_id="A038")

    dsn = (
        "DefaultEndpointsProtocol=http;"
        "AccountName=testaccount;"
        "AccountKey=dGVzdGtleQo=;"
        "BlobEndpoint=http://testbink.com/testaccount;"
    )

    patch_dsn = patch(
        "bullsquid.merchant_data.csv_upload.views.settings.blob_storage.dsn",
        dsn,
    )
    patch_blob = patch("bullsquid.service.azure_storage.BlobServiceClient")
    with patch_dsn, patch_blob as mock_blob:
        resp = test_client.post(
            "/api/v1/plans/csv_upload",
            files={
                "file": identifiers_file,
            },
            data={
                "file_type": "identifiers",
                "file_name": "identifiers.csv",
                "plan_ref": str(plan.pk),
            },
        )

        mock_blob.from_connection_string.assert_called_once_with(dsn)
        mock_service_client = mock_blob.from_connection_string.return_value
        mock_service_client.get_blob_client.assert_called_once_with(
            container="portal-archive",
            blob="identifiers.csv",
        )

    assert resp.status_code == status.HTTP_202_ACCEPTED, resp.text
    await run_worker(burst=True)
