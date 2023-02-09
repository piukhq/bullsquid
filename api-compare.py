import sys
from operator import itemgetter
from typing import Any

import yaml

from bullsquid.api.app import create_app


def parse_routes(spec: dict[str, Any]) -> set[tuple[str, str]]:
    return {
        (method, path)
        for path, path_spec in spec["paths"].items()
        for method in path_spec
    }


def load_app_routes() -> set[tuple[str, str]]:
    spec = create_app().openapi()
    return parse_routes(spec)


def load_doc_routes() -> set[tuple[str, str]]:
    try:
        filename = sys.argv[1]
    except IndexError:
        print("Usage: python api-compare.py <openapi.yaml>")
        sys.exit(1)

    with open(filename) as f:
        spec = yaml.safe_load(f)

    routes = parse_routes(spec)

    return {(method, path.replace("{version}", "v1")) for method, path in routes}


def sort_routes(routes: set[tuple[str, str]]) -> list[tuple[str, str]]:
    return sorted(routes, key=itemgetter(1, 0))


def print_routes(routes: set[tuple[str, str]]) -> None:
    for method, path in sort_routes(routes):
        print(f" * {method.upper()} {path}")


if __name__ == "__main__":
    doc_routes = load_doc_routes()
    app_routes = load_app_routes()

    print("Routes in docs but not in app:")
    print_routes(doc_routes - app_routes)

    print("Routes in app but not in docs:")
    print_routes(app_routes - doc_routes)
