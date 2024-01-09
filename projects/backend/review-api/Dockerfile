FROM python:3.10-slim

COPY pyproject.toml poetry.lock ./

RUN pip install poetry

RUN poetry config virtualenvs.create false \
    && poetry export -f requirements.txt --without-hashes > requirements.txt \
    && pip install -r requirements.txt

COPY / ./

CMD piccolo migrations new reviews --auto && \
    piccolo migrations forwards reviews && \
    uvicorn api:api --host "0.0.0.0" --port "80"
