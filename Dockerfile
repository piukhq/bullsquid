FROM ghcr.io/binkhq/python:3.10 as build

WORKDIR /src
ADD . .

RUN pip install poetry==1.2.0a2
RUN poetry build

FROM ghcr.io/binkhq/python:3.10

WORKDIR /app
COPY --from=build /src/dist/bullsquid-0.0.0-py3-none-any.whl .
COPY --from=build /src/asgi.py .
COPY --from=build /src/piccolo_conf.py .
COPY --from=build /src/settings.py .
RUN pip install bullsquid-0.0.0-py3-none-any.whl

ENTRYPOINT [ "uvicorn" ]
CMD [ "asgi:app", "--host", "0.0.0.0", "--port", "9000" ]
