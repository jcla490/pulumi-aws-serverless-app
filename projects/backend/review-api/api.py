from contextlib import asynccontextmanager
from typing import Any, Generator

from db.tables import Reviews
from fastapi import APIRouter, FastAPI, status
from piccolo.engine import engine_finder
from piccolo_api.fastapi.endpoints import FastAPIKwargs, FastAPIWrapper, PiccoloCRUD
from pydantic import BaseModel

# Very important, load balancer/service will cry if not this path
API_BASE_PATH = "/review"


# These are startup and shutdown events called in our lifespan func
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


# This is a lifespan event for the FastAPI instance
@asynccontextmanager
async def lifespan(app: FastAPI) -> Generator[None, Any, None]:
    # Open db connection
    await open_database_connection_pool()
    yield
    # Close db connection
    await close_database_connection_pool()


# API init
api = FastAPI(
    title="Review Service",
    description="A basic reviews service for orangejuice.reviews",
    openapi_url=API_BASE_PATH + "/openapi.json",
    docs_url=API_BASE_PATH + "/docs",
    redoc_url=API_BASE_PATH + "/redoc",
    lifespan=lifespan,
)

# We only need the router to configure a new base path
router = APIRouter(prefix=API_BASE_PATH)


class Health(BaseModel):
    """A simple model for the health endpoint"""

    status: str = "OK"


@router.get(
    "/health",
    tags=["Health"],
    response_description="Return OK (200) if API is healthy",
    response_model=Health,
    status_code=status.HTTP_200_OK,
)
def get_health() -> Health:
    """Health check for load balancer"""
    return Health


# A very convenient CRUD wrapper for our Reviews table
FastAPIWrapper(
    "/",
    fastapi_app=router,
    piccolo_crud=PiccoloCRUD(Reviews, read_only=False),
    fastapi_kwargs=FastAPIKwargs(
        all_routes={"tags": ["Review"]},
    ),
)

api.include_router(router)
