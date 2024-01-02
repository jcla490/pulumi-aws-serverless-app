import datetime

from piccolo.columns import UUID, Timestamptz, Varchar
from piccolo.table import Table


class Users(Table):
    """
    Users table for users-api service
    """

    id = UUID(primary_key=True)
    email = Varchar(unique=True, null=False)
    first_name = Varchar()
    last_name = Varchar()
    created_on = Timestamptz(default=datetime.datetime.now)
    modified_on = Timestamptz(auto_update=datetime.datetime.now)
