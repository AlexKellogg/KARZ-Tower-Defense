from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

MIGRATIONS = Path(__file__).parent/'migrations'
BASELINE = '0001'


def alembic_config(connection=None):
    config = Config()
    config.set_main_option('script_location', str(MIGRATIONS))
    if connection is not None:
        config.attributes['connection'] = connection
    return config


def upgrade_database(engine):
    with engine.begin() as connection:
        tables = set(inspect(connection).get_table_names())
        config = alembic_config(connection)
        if 'accounts' in tables and 'alembic_version' not in tables:
            command.stamp(config, BASELINE)
        command.upgrade(config, 'head')


def current_revision(engine):
    with engine.connect() as connection:
        if 'alembic_version' not in inspect(connection).get_table_names():
            return None
        return connection.exec_driver_sql('SELECT version_num FROM alembic_version').scalar()
