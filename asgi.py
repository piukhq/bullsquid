"""Sets up the ASGI application. Running this file also starts uvicorn."""
from api.app import create_app

app = create_app()

if __name__ == "__main__":

    import uvicorn

    uvicorn.run("asgi:app", reload=True)
