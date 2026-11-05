import os

from alembic import context
from sqlalchemy import create_engine

from server.sql_backend import DEFAULT_URL, Base, normalize_url

config = context.config
target_metadata = Base.metadata


def run(connection):
    context.configure(connection=connection, target_metadata=target_metadata,
                      render_as_batch=connection.dialect.name == 'sqlite')
    with context.begin_transaction():
        context.run_migrations()


connection = config.attributes.get('connection')
if connection is not None:
    run(connection)
else:
    engine = create_engine(normalize_url(os.environ.get('DATABASE_URL', DEFAULT_URL)))
    with engine.connect() as conn:
        run(conn)
    engine.dispose()
