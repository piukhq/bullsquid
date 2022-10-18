import pytest
from pydantic import BaseModel, ValidationError

from bullsquid.merchant_data.validators import FlexibleUrl


class TestFlexibleUrl(BaseModel):
    url: FlexibleUrl


def test_url_without_protocol() -> None:
    example_outcome = TestFlexibleUrl(url="www.example.com")
    assert example_outcome.url == "https://www.example.com/"


def test_url_without_tld() -> None:
    example_outcome = TestFlexibleUrl(url="https://www.example")
    assert example_outcome.url == "https://www.example/"


def test_url_without_protocol_and_www() -> None:
    example_outcome = TestFlexibleUrl(url="example.com")
    assert example_outcome.url == "https://example.com/"


def test_invalid_url() -> None:
    with pytest.raises(ValidationError):
        TestFlexibleUrl(url="example")


def test_url_with_path() -> None:
    example_outcome = TestFlexibleUrl(url="https://www.example.com/icon.png")
    assert example_outcome.url == "https://www.example.com/icon.png"
