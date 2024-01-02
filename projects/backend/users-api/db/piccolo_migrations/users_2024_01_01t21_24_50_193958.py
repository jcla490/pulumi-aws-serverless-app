from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.columns.column_types import Timestamp, Timestamptz
from piccolo.columns.defaults.timestamp import TimestampNow
from piccolo.columns.defaults.timestamptz import TimestamptzNow

ID = "2024-01-01T21:24:50:193958"
VERSION = "1.2.0"
DESCRIPTION = ""


async def forwards():
    manager = MigrationManager(
        migration_id=ID, app_name="users", description=DESCRIPTION
    )

    manager.alter_column(
        table_class_name="Users",
        tablename="users",
        column_name="created_on",
        db_column_name="created_on",
        params={"default": TimestamptzNow()},
        old_params={"default": TimestampNow()},
        column_class=Timestamptz,
        old_column_class=Timestamp,
        schema=None,
    )

    manager.alter_column(
        table_class_name="Users",
        tablename="users",
        column_name="modified_on",
        db_column_name="modified_on",
        params={"default": TimestamptzNow()},
        old_params={"default": TimestampNow()},
        column_class=Timestamptz,
        old_column_class=Timestamp,
        schema=None,
    )

    return manager
