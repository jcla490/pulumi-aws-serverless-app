import datetime

from piccolo.columns import UUID, SmallInt, Text, Timestamptz
from piccolo.table import Table


class Reviews(Table):
    """
    Reviews table for reviews-api service
    """

    id = UUID(primary_key=True)
    title = Text(required=True)
    rating = SmallInt(required=True)
    body = Text()
    created_on = Timestamptz(default=datetime.datetime.now)
    modified_on = Timestamptz(auto_update=datetime.datetime.now)
    user_id = UUID(required=True)
