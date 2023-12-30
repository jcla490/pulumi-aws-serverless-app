"""
A silly 'user' microservice using litestar
https://docs.litestar.dev/latest/
"""
from dataclasses import dataclass

from litestar import Litestar, delete, get, post
from litestar.exceptions import HTTPException


@dataclass
class User:
    user_id: int
    name: str
    age: int
    email: str


DUMMY_USER_STORE: list[User] = [
    User(user_id=1, name="John Doe", age=30, email="john.doe@example.com"),
    User(user_id=2, name="Jane Doe", age=25, email="jane.doe@example.com"),
]


@get(path="/health")
async def health_check() -> list[User]:
    """Health check for load balancer to ping"""
    return {"status": "ok"}


@post(path="/user")
async def create_user(data: User) -> User:
    """Create a user"""
    user = [u for u in DUMMY_USER_STORE if u.user_id == data.user_id]
    if len(user) > 0:
        return False
    else:
        DUMMY_USER_STORE.append(data)
        return data


@get(path="/users")
async def list_users() -> list[User]:
    """List all users"""
    return DUMMY_USER_STORE


@get(path="/user/{user_id:int}")
async def get_user(user_id: int) -> User:
    """Get user by user_id"""
    user = [u for u in DUMMY_USER_STORE if u.user_id == user_id]
    if len(user) == 0:
        raise HTTPException(
            status_code=400, detail=f"user with id [{user_id}] not found"
        )
    else:
        return user


@delete(path="/user/{user_id:int}")
async def delete_user(user_id: int) -> None:
    """Delete a user"""
    temp = DUMMY_USER_STORE.copy()
    DUMMY_USER_STORE.clear()
    for u in temp:
        if u.user_id != user_id:
            DUMMY_USER_STORE.append(u)
    return None


api = Litestar(
    route_handlers=[health_check, create_user, list_users, get_user, delete_user]
)
