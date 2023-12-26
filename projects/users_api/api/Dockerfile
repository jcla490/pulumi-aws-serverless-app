FROM python:3.10-slim

RUN pip install litestar[standard]

COPY . ./

CMD [ "uvicorn", "api:api", "--host", "0.0.0.0", "--port", "80"]
