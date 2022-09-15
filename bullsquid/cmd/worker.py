"""
Run the task queue worker.

Usage:
    bullsquid-worker
    bullsquid-worker (-h | --help)
    bullsquid-worker --version

Options:
    -h --help   Show this screen.
    --version   Show version.
"""

from docopt import docopt
from loguru import logger

from bullsquid import __version__


def main() -> None:
    """Executes the task worker."""
    docopt(__doc__, version=f"bullsquid-worker {__version__}")

    # importing these here allows --help and --version to finish a little quicker
    import asyncio  # pylint: disable=import-outside-toplevel

    from bullsquid.tasks import run_worker  # pylint: disable=import-outside-toplevel

    try:
        asyncio.run(run_worker())
    except KeyboardInterrupt:
        logger.info("Caught interrupt, exiting.")


if __name__ == "__main__":
    main()
