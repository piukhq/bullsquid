"""
Sets up the ASGI application.
Running this file directly also starts uvicorn for local development.
"""
import sentry_sdk

from bullsquid import __version__
from bullsquid.api.app import create_app
from bullsquid.log_conf import set_loguru_intercept
from bullsquid.settings import settings

# redirect all logging into loguru.
set_loguru_intercept()

if settings.sentry.dsn:
    sentry_sdk.init(
        dsn=settings.sentry.dsn,
        release=__version__,
        environment=settings.sentry.env,
    )

# initialise the asgi app instance.
app = create_app()

# serve up the app locally for development purposes.
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("asgi:app", reload=True, port=6502, reload_excludes=[".venv"])
