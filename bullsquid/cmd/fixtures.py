"""
Create some preset merchants and locations via the API.

Usage:
    bullsquid-fixtures [--url=<url>] [--api-key=<api-key>]
    bullsquid-fixtures (-h | --help)
    bullsquid-fixtures --version

Options:
    -h --help            Show this screen.
    --version            Show version.
    -u --url=<url>       URL of the API server. [default: http://localhost:6502]
    --api-key=<api-key>  API key to authenticate with. (env: API_KEY)
"""
import colorama
import requests
from amazing_printer import ap
from colorama import Fore, Style
from docopt import docopt
from fastapi import status

from bullsquid.merchant_data.models import Merchant
from settings import settings

from . import __version__

MERCHANTS = [
    Merchant(
        name="Iceland",
        slug="iceland-bonus-card",
        payment_schemes=["visa", "amex", "mastercard"],
        plan_id=105,
        location_label="stores",
    ),
    Merchant(
        name="Harvey Nichols",
        slug="harvey-nichols",
        payment_schemes=["visa", "amex", "mastercard"],
        plan_id=124,
        location_label="stores",
    ),
    Merchant(
        name="Squaremeal",
        slug="squaremeal",
        payment_schemes=["visa", "amex", "mastercard"],
        plan_id=216,
        location_label="restaurants",
    ),
    Merchant(
        name="Wasabi",
        slug="wasabi-club",
        payment_schemes=["visa", "amex", "mastercard"],
        plan_id=215,
        location_label="restaurants",
    ),
    Merchant(
        name="ASOS",
        slug="bpl-asos",
        payment_schemes=["visa", "amex", "mastercard"],
        plan_id=251,
        location_label="stores",
    ),
]


def tag(tag: str, *, colour: int) -> str:
    """Generates a [tag] with the given colour."""
    return f"[{colour}{Style.BRIGHT}{tag}{Style.RESET_ALL}]"


def success() -> str:
    """Generates a success tag."""
    return tag("o", colour=Fore.GREEN)


def info() -> str:
    """Generates an info tag."""
    return tag("i", colour=Fore.BLUE)


def error() -> str:
    """Generates an error tag."""
    return tag("!", colour=Fore.RED)


def create_fixtures(*, url: str, api_key: str) -> None:
    """Post fixture data to the given URL."""
    headers = {"Authorization": f"token {api_key}"}
    for merchant in MERCHANTS:
        resp = requests.post(
            f"{url}/merchant_data/v1/merchants", json=merchant.dict(), headers=headers
        )

        if resp.ok:
            print(
                f"{success()} Created merchant {Fore.CYAN}{merchant.name}{Style.RESET_ALL}"
            )
        elif resp.status_code == status.HTTP_409_CONFLICT:
            print(
                f"{info()} Merchant {Fore.CYAN}{merchant.name}{Style.RESET_ALL} already exists, skipping."
            )
        elif not resp.ok:
            print(
                f"{error()} Failed to create merchant {Fore.CYAN}{merchant.name}{Style.RESET_ALL}"
            )
            ap(resp.json())
            return


def main() -> None:
    """Parse arguments and run the program."""
    args = docopt(__doc__, version=f"bullsquid-fixtures {__version__}")
    colorama.init()
    create_fixtures(url=args["--url"], api_key=args["--api-key"] or settings.api_key)


if __name__ == "__main__":
    main()
