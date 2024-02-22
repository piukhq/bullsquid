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
import sentry_sdk

from bullsquid import __version__
from bullsquid.settings import settings
from bullsquid.log_conf import set_loguru_intercept


def main() -> None:
    """Executes the task worker."""
    docopt(__doc__, version=f"bullsquid-worker {__version__}")

    # importing these here allows --help and --version to finish a little quicker
    import asyncio

    from bullsquid.merchant_data.tasks import run_worker

    try:
        asyncio.run(run_worker())
    except KeyboardInterrupt:
        logger.info("Caught interrupt, exiting.")


if __name__ == "__main__":
    # redirect all logging into loguru.
    set_loguru_intercept()

    if settings.sentry.dsn:
        sentry_sdk.init(
            dsn=settings.sentry.dsn,
            release=__version__,
            environment=settings.sentry.env,
        )

    main()
