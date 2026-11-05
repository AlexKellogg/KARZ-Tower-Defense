import os
import tempfile
import unittest
from pathlib import Path

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect

from backend import RunResult
from server.migrate import BASELINE, alembic_config, current_revision, upgrade_database
from server.sql_backend import Base, SqlBackend, normalize_url

POSTGRES_URL = os.environ.get('KARZ_TEST_POSTGRES_URL', '')
HEAD = ScriptDirectory.from_config(alembic_config()).get_current_head()


def drift(engine):
    with engine.connect() as connection:
        return compare_metadata(MigrationContext.configure(connection), Base.metadata)


class SqliteMigrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.url = f'sqlite:///{Path(self.tmp.name)/"karz.db"}'
        self.engine = create_engine(self.url)

    def tearDown(self):
        self.engine.dispose()
        self.tmp.cleanup()

    def migrate_to(self, revision):
        with self.engine.begin() as connection:
            command.upgrade(alembic_config(connection), revision)

    def test_new_database_is_built_by_migrations_and_matches_the_models(self):
        backend = SqlBackend(self.url)
        backend.close()
        self.assertEqual(current_revision(self.engine), HEAD)
        self.assertEqual(drift(self.engine), [])

    def test_database_from_before_migrations_keeps_its_data(self):
        self.migrate_to(BASELINE)
        with self.engine.begin() as connection:
            connection.exec_driver_sql('DROP TABLE alembic_version')
        self.assertIsNone(current_revision(self.engine))
        with self.engine.begin() as connection:
            connection.exec_driver_sql(
                "INSERT INTO accounts (id, name, username, username_key, email, salt, password_hash, role, created_at) "
                "VALUES (1, 'Old', 'olduser', 'olduser', 'old@example.com', X'00', X'00', 'user', '2026-10-01 00:00:00')")
            connection.exec_driver_sql(
                "INSERT INTO runs (account_id, difficulty, won, score, time_seconds, lives_lost, waves_cleared, kills, played_at) "
                "VALUES (1, 'Easy', 1, 700, 90.0, 2, 5, 60, '2026-10-01 00:00:00')")
        backend = SqlBackend(self.url)
        self.assertEqual(current_revision(backend.engine), HEAD)
        self.assertEqual([(e.username, e.value) for e in backend.leaderboard('score')], [('olduser', 700)])
        account = backend._get(1)
        self.assertEqual(backend.unlocked_difficulties(account), ('Easy', 'Medium'))
        backend.close()
        self.assertEqual(drift(self.engine), [])

    def test_running_migrations_twice_changes_nothing(self):
        SqlBackend(self.url).close()
        upgrade_database(self.engine)
        self.assertEqual(current_revision(self.engine), HEAD)

    def test_every_migration_can_be_undone_and_redone(self):
        SqlBackend(self.url).close()
        with self.engine.begin() as connection:
            command.downgrade(alembic_config(connection), 'base')
        self.assertEqual(set(inspect(self.engine).get_table_names()) - {'alembic_version'}, set())
        upgrade_database(self.engine)
        self.assertEqual(drift(self.engine), [])

    def test_data_survives_each_step(self):
        backend = SqlBackend(self.url)
        account = backend.sign_up('Kaden', 'kaden', 'kaden@example.com', 'password123')
        backend.record_run(account, RunResult('Easy', True, 900, 80.0, 0, 5, 60))
        backend.close()
        for _ in range(2):
            upgrade_database(self.engine)
        backend = SqlBackend(self.url)
        self.assertEqual(backend.log_in('kaden@example.com', 'password123').username, 'kaden')
        self.assertEqual([e.value for e in backend.leaderboard('score')], [900])
        backend.close()


@unittest.skipUnless(POSTGRES_URL, 'set KARZ_TEST_POSTGRES_URL to run against PostgreSQL')
class PostgresMigrationTests(unittest.TestCase):
    def setUp(self):
        from test_server import reset_postgres
        reset_postgres()
        self.engine = create_engine(normalize_url(POSTGRES_URL))

    def tearDown(self):
        self.engine.dispose()

    def test_new_database_matches_the_models(self):
        SqlBackend(POSTGRES_URL).close()
        self.assertEqual(current_revision(self.engine), HEAD)
        self.assertEqual(drift(self.engine), [])

    def test_every_migration_can_be_undone_and_redone(self):
        SqlBackend(POSTGRES_URL).close()
        with self.engine.begin() as connection:
            command.downgrade(alembic_config(connection), 'base')
        upgrade_database(self.engine)
        self.assertEqual(drift(self.engine), [])


if __name__ == '__main__':
    unittest.main()
