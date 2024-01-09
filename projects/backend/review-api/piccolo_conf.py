import json
import os

from piccolo.conf.apps import AppRegistry
from piccolo.engine.postgres import PostgresEngine

# These credentials are injected into our container via the ECS task definition
DB_CREDS = json.loads(os.environ["DATABASE_CREDENTIALS"])

DB = PostgresEngine(
    config={
        "database": DB_CREDS["DATABASE_NAME"],
        "user": DB_CREDS["USERNAME"],
        "password": DB_CREDS["PASSWORD"],
        "host": DB_CREDS["WRITER_ENDPOINT"],
        "port": DB_CREDS["PORT"],
    }
)

# Register our Reviews table configuration found in /db
APP_REGISTRY = AppRegistry(apps=["db.reviews_conf"])
