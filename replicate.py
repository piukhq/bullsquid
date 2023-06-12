import json
import secrets
import time
from typing import Generator
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from loguru import logger
from rich import print

# BASE_URL = "https://portal.staging.gb.bink.com"
BASE_URL = "http://localhost:6502"
PLAN_SLUG = "cl-test-plan"
SECONDARY_MID_PREFIX = "cl-test-secmid-"
ACCESS_TOKEN = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6IkNqWW15TmNON3Q5Mjh4X3JUZUp4RiJ9.eyJpc3MiOiJodHRwczovL2JpbmsuZXUuYXV0aDAuY29tLyIsInN1YiI6IndhYWR8WVJUeFpTTHRlQktoYlF0Q1hzQVlXN1R4Y0d6UjNpU2M5WllVWDBER2s3USIsImF1ZCI6Imh0dHBzOi8vcG9ydGFsLmJpbmsuY29tIiwiaWF0IjoxNjg2NTc2OTg3LCJleHAiOjE2ODY2NjMzODcsImF6cCI6IjRiQkgxTGFkR2hkemc3RnJtNUI4UjJCV2w1eERVc2dFIiwib3JnX2lkIjoib3JnX2hqZGE4WmtSTmQ4dzRaTlUiLCJwZXJtaXNzaW9ucyI6WyJjdXN0b21lcl93YWxsZXQ6cm8iLCJjdXN0b21lcl93YWxsZXQ6cnciLCJjdXN0b21lcl93YWxsZXQ6cndkIiwibWVyY2hhbnRfZGF0YTpybyIsIm1lcmNoYW50X2RhdGE6cnciLCJtZXJjaGFudF9kYXRhOnJ3ZCJdfQ.gyEd5I06xt3RcSUSXeTFbHX1L2PS0ACBJG0hs9pOR9RyTVNgQ0nuxRSE6qWHIMtT1hq7Sa99rYFMX848K7MCWvNurGfBS6DDGUHkS2gJHOc0LHEWWzoveD4gW12ucHccGENtasdI_O0vXhSlERmZYKAtAq9pF7ZdYzixpUYtqzUckrNW5Qdj12gW6tjiLiYgNXoJTPBRPIoANIpua7JqMhvz0wFVGAefC7JXtSGWBtfKcnyVF_gcyuxSG3RNW3Zr6ZF7K103jha2tYuQW7qaEeY86QL_WIZ4R8DvRznxLuzOYsyi0qNMiFAV0KOa52Yx3RdFK3I2HEh44ry6ApIhDQ"


class API:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url

    def _make_request(self, method: str, path: str, data: dict | None = None) -> dict:
        logger.debug(f"Making {method} request to {path}")

        headers = {
            "Authorization": f"Bearer {ACCESS_TOKEN}",
            "Content-Type": "application/json",
        }

        req = Request(self.base_url + path, method=method, headers=headers)
        if method == "POST":
            if data is not None:
                req.data = json.dumps(data).encode("utf-8")

        try:
            resp = urlopen(req, timeout=5)
        except HTTPError as e:
            resp_json = json.loads(e.read())
            logger.error(
                f"Request failed with status {e.status} {e.reason}: {resp_json}"
            )
            raise

        return json.loads(resp.read())

    def _paginate(self, path: str, page_size: int = 100) -> Generator[dict, None, None]:
        page = 1
        while True:
            resp = self.get(f"{path}?page={page}&page_size={page_size}")
            if not isinstance(resp, list):
                raise ValueError(
                    f"Expected list response from {path} for pagination, got {type(resp)}"
                )
            yield from resp
            if len(resp) < page_size:
                logger.debug(f"{len(resp)} items returned ({page_size=}), stopping")
                break
            page += 1

    def get(self, path: str) -> list | dict:
        return self._make_request("GET", path)

    def post(self, path: str, data: dict | None = None) -> dict:
        return self._make_request("POST", path, data)

    def list_plans(self) -> Generator[dict, None, None]:
        return self._paginate("/api/v1/plans")

    def create_plan(self, *, name: str, slug: str) -> dict:
        return self.post("/api/v1/plans", {"name": name, "slug": slug})

    def list_merchants(self, plan_ref: str) -> list[dict]:
        return self._paginate(f"/api/v1/plans/{plan_ref}/merchants")

    def create_merchant(self, *, plan_ref: str, name: str) -> dict:
        return self.post(
            f"/api/v1/plans/{plan_ref}/merchants",
            {"name": name, "location_label": "store"},
        )

    def list_secondary_mids(
        self, *, plan_ref: str, merchant_ref: str
    ) -> Generator[dict, None, None]:
        return self._paginate(
            f"/api/v1/plans/{plan_ref}/merchants/{merchant_ref}/secondary_mids"
        )

    def create_secondary_mid(
        self, *, plan_ref: str, merchant_ref: str, secondary_mid: str
    ) -> dict:
        return self.post(
            f"/api/v1/plans/{plan_ref}/merchants/{merchant_ref}/secondary_mids",
            {
                "secondary_mid_metadata": {
                    "payment_scheme_slug": "visa",
                    "secondary_mid": secondary_mid,
                },
                "onboard": True,
            },
        )

    def offboard_secondary_mid(
        self, *, plan_ref: str, merchant_ref: str, secondary_mid_ref: str
    ) -> dict:
        return self.post(
            f"/api/v1/plans/{plan_ref}/merchants/{merchant_ref}/secondary_mids/offboarding",
            data={"secondary_mid_refs": [secondary_mid_ref]},
        )


def main() -> None:
    api = API(BASE_URL)

    plans = api.list_plans()
    try:
        plan = next(p for p in plans if p["plan_metadata"]["slug"] == PLAN_SLUG)
    except StopIteration:
        plan = api.create_plan(name=PLAN_SLUG, slug=PLAN_SLUG)

    merchants = api.list_merchants(plan["plan_ref"])
    try:
        merchant = next(
            m for m in merchants if m["merchant_metadata"]["name"] == PLAN_SLUG
        )
    except StopIteration:
        merchant = api.create_merchant(plan_ref=plan["plan_ref"], name=PLAN_SLUG)

    secondary_mid = api.create_secondary_mid(
        plan_ref=plan["plan_ref"],
        merchant_ref=merchant["merchant_ref"],
        secondary_mid=f"{SECONDARY_MID_PREFIX}{secrets.token_urlsafe(8)}",
    )

    print(secondary_mid)

    print("\n\nDelaying for 3 seconds to allow MID to be onboarded...")
    time.sleep(3)
    print("\n\n")

    api.offboard_secondary_mid(
        plan_ref=plan["plan_ref"],
        merchant_ref=merchant["merchant_ref"],
        secondary_mid_ref=secondary_mid["secondary_mid_ref"],
    )

    print("\n\nDelaying for 3 seconds to allow MID to be offboarded...")
    time.sleep(3)
    print("\n\n")

    secondary_mids = list(
        api.list_secondary_mids(
            plan_ref=plan["plan_ref"], merchant_ref=merchant["merchant_ref"]
        )
    )
    print(secondary_mids)


if __name__ == "__main__":
    main()
