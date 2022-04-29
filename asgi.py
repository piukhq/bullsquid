"""
Sets up the ASGI application.
Running this file directly also starts uvicorn for local development.
"""
import sentry_sdk

from bullsquid.api.app import create_app
from bullsquid.log_conf import set_loguru_intercept

# redirect all logging into loguru.
set_loguru_intercept()

# use sentry's own environment variables to configure the connection.
# https://docs.sentry.io/platforms/python/configuration/options/#common-options
sentry_sdk.init()  # pylint: disable=abstract-class-instantiated

# initialise the asgi app instance.
app = create_app()

# serve up the app locally for development purposes.
if __name__ == "__main__":

    import uvicorn

    uvicorn.run("asgi:app", reload=True, port=6502, reload_excludes=[".venv"])
