"""
Generate Kubernetes manifests for the Bullsquid API.

Usage:
    bullsquid-kubefest service-profile
    bullsquid-kubefest (-h | --help)
    bullsquid-kubefest --version

Options:
    -h --help   Show this screen.
    --version   Show version.
"""
import re

import yaml
from docopt import docopt
from pydantic import BaseModel

from bullsquid.api.app import create_app

from . import __version__

NAMESPACE = "default"
LINKERD_API_VERSION = "linkerd.io/v1alpha2"
METADATA_NAME = f"bullsquid-api.{NAMESPACE}.svc.cluster.local"

PATH_PARAM_PATTERN = re.compile(r"\{.*?\}")
PATH_PARAM_REPLACEMENT = r"[^/]*"


class APIEndpoint(BaseModel):
    """A HTTP method and path for a single endpoint in the API."""

    name: str
    method: str
    path: str


def to_path_regex(path: str) -> str:
    """
    Converts an OpenAPI path to a service profile path regex by replacing
    {parameters} with [^/]* patterns.
    """
    return PATH_PARAM_PATTERN.sub(PATH_PARAM_REPLACEMENT, path)


def service_profile_header() -> dict:
    """Return the Linkerd service profile header."""
    return {
        "apiVersion": LINKERD_API_VERSION,
        "kind": "ServiceProfile",
        "metadata": {
            "name": METADATA_NAME,
            "namespace": NAMESPACE,
        },
    }


def to_route_spec(endpoint: APIEndpoint) -> dict:
    """Convert an APIEndpoint to a Linkerd route spec."""
    return {
        "condition": {
            "method": endpoint.method,
            "pathRegex": to_path_regex(endpoint.path),
        },
        "name": f"{endpoint.method} {endpoint.path} ({endpoint.name})",
        "isRetryable": True,
        "timeout": "2000ms",
    }


def generate_service_profile(endpoints: list[APIEndpoint]) -> dict:
    """
    Generate a full Linkerd service profile structure from the given endpoints.
    """
    return service_profile_header() | {
        "spec": {"routes": [to_route_spec(endpoint) for endpoint in endpoints]}
    }


def get_api_spec() -> dict:
    """Return the OpenAPI spec from the Bullsquid FastAPI app."""
    app = create_app()
    return app.openapi()


def get_endpoints(api_spec: dict) -> list[APIEndpoint]:
    """Parse a list of APIEndpoint objects from the given OpenAPI spec dictionary."""
    return [
        APIEndpoint(method=method.upper(), path=path, name=route_config["summary"])
        for path, config in api_spec["paths"].items()
        for method, route_config in config.items()
    ]


def main() -> None:
    """Parse arguments and run the application."""
    args = docopt(__doc__, version=f"bullsquid-kubefest {__version__}")

    spec = get_api_spec()
    endpoints = get_endpoints(spec)
    if args["service-profile"]:
        service_profile = generate_service_profile(endpoints)
        print(yaml.dump(service_profile, explicit_start=True, sort_keys=False))


if __name__ == "__main__":
    main()
