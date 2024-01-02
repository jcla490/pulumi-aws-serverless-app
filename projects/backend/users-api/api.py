from contextlib import asynccontextmanager
from typing import Any, Dict, Generator

from db.tables import Users
from fastapi import FastAPI, status
from piccolo.engine import engine_finder
from piccolo_api.fastapi.endpoints import FastAPIKwargs, FastAPIWrapper, PiccoloCRUD


async def open_database_connection_pool() -> None:
    try:
        engine = engine_finder()
        await engine.start_connection_pool()
    except Exception:
        print("Unable to connect to the database")


async def close_database_connection_pool() -> None:
    try:
        engine = engine_finder()
        await engine.close_connection_pool()
    except Exception:
        print("Unable to connect to the database")


@asynccontextmanager
async def lifespan(app: FastAPI) -> Generator[None, Any, None]:
    # Open db connection
    await open_database_connection_pool()
    yield
    # Close db connection
    await close_database_connection_pool()


api = FastAPI(lifespan=lifespan)


@api.get(
    "/health",
    tags=["Health"],
    response_description="Return HTTP Status Code 200 (OK)",
    status_code=status.HTTP_200_OK,
)
def get_health() -> Dict[str, str]:
    return {"status": "OK"}


FastAPIWrapper(
    "/users",
    fastapi_app=api,
    piccolo_crud=PiccoloCRUD(Users, read_only=False),
    fastapi_kwargs=FastAPIKwargs(
        all_routes={"tags": ["Users"]},
    ),
)
