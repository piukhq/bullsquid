#!/usr/bin/env python
"""
Shortcut for running the piccolo tester.
Works well as an entrypoint for IDE tests and debugging.
"""
import sys

from piccolo.apps.tester.commands.run import run


def main() -> None:
    """Invokes the piccolo tester's run function."""
    run(pytest_args=" ".join(sys.argv[1:]))


if __name__ == "__main__":
    main()
