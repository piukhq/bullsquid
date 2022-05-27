from curses import noraw
from locale import normalize

from pydantic import BaseModel, ValidationError
from ward import raises, test

from bullsquid.merchant_data.validators import FlexibleUrl


class TestFlexibleUrl(BaseModel):
    url: FlexibleUrl


@test("URL is formatted correctly without 'https://'")
def _():
    example_outcome = TestFlexibleUrl(url="www.example.com")
    assert example_outcome.url == "https://www.example.com/"


@test("URL is formatted correctly without '.com'")
def _():
    example_outcome = TestFlexibleUrl(url="https://www.example")
    assert example_outcome.url == "https://www.example/"


@test("URL is formatted correctly without 'https://www.'")
def _():
    example_outcome = TestFlexibleUrl(url="example.com")
    assert example_outcome.url == "https://example.com/"


@test("URL is formatted incorrectly")
def _():
    with raises(ValidationError):
        example_outcome = TestFlexibleUrl(url="example")


@test("URL is formatted correctly with icon.png")
def _():
    example_outcome = TestFlexibleUrl(url="https://www.example.com/icon.png")
    assert example_outcome.url == "https://www.example.com/icon.png"
