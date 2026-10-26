import os
import unittest

from fastapi.testclient import TestClient

import test_backend as contract
from backend import AccessDenied, Account, AccountError, RunResult
from remote_backend import OFFLINE, RemoteBackend
from server.app import create_app
from server.sql_backend import Base, SqlBackend, normalize_url

POSTGRES_URL = os.environ.get('KARZ_TEST_POSTGRES_URL', '')


class ServerFixture:
    def make_backend(self, folder):
        self.sql = SqlBackend(f'sqlite:///{folder/"server.db"}')
        self.http = TestClient(create_app(self.sql))
        return RemoteBackend('http://testserver', client=self.http)

    def tearDown(self):
        self.backend.close()
        self.sql.close()
        self.tmp.cleanup()

    def promote(self, email):
        return self.sql.promote_by_email(email)

    def password_hashes(self):
        return self.sql.stored_password_hashes()


class ServerAccountTests(ServerFixture, contract.AccountTests):
    pass


class ServerRoleTests(ServerFixture, contract.RoleTests):
    pass


class ServerUnlockTests(ServerFixture, contract.UnlockTests):
    pass


class ServerLeaderboardTests(ServerFixture, contract.LeaderboardTests):
    pass


class PostgresFixture(ServerFixture):
    def make_backend(self, folder):
        self.sql = SqlBackend(POSTGRES_URL)
        Base.metadata.drop_all(self.sql.engine)
        Base.metadata.create_all(self.sql.engine)
        self.http = TestClient(create_app(self.sql))
        return RemoteBackend('http://testserver', client=self.http)


needs_postgres = unittest.skipUnless(POSTGRES_URL, 'set KARZ_TEST_POSTGRES_URL to run against PostgreSQL')


@needs_postgres
class PostgresAccountTests(PostgresFixture, contract.AccountTests):
    pass


@needs_postgres
class PostgresRoleTests(PostgresFixture, contract.RoleTests):
    pass


@needs_postgres
class PostgresUnlockTests(PostgresFixture, contract.UnlockTests):
    pass


@needs_postgres
class PostgresLeaderboardTests(PostgresFixture, contract.LeaderboardTests):
    pass


class SqlBackendDirectTests(contract.BackendTestCase):
    def make_backend(self, folder):
        return SqlBackend('sqlite://')

    def password_hashes(self):
        return self.backend.stored_password_hashes()

    def test_score_board_and_unlocks_without_http(self):
        self.assertEqual(self.backend.record_run(self.zlata, contract.run('Easy', score=300)), ('Medium',))
        self.assertEqual([(e.username, e.value) for e in self.backend.leaderboard('score')], [('zlata_k', 300)])

    def test_username_uniqueness_ignores_case(self):
        with self.assertRaises(AccountError):
            self.backend.sign_up('Other', 'ZLATA_K', 'other@example.com', 'password123')


class HttpTests(ServerFixture, contract.BackendTestCase):
    def token(self, account):
        return {'Authorization': f'Bearer {self.backend.tokens[account.id]}'}

    def test_health_check(self):
        self.assertEqual(self.http.get('/health').json(), {'status': 'ok'})

    def test_protected_routes_need_a_valid_token(self):
        for method, path in (('GET', '/me'), ('GET', '/me/unlocked'), ('POST', '/me/runs'), ('GET', '/admin/accounts')):
            with self.subTest(path=path):
                self.assertEqual(self.http.request(method, path).status_code, 401)
                bad = self.http.request(method, path, headers={'Authorization': 'Bearer not-a-real-token'})
                self.assertEqual(bad.status_code, 401)

    def test_me_returns_the_logged_in_account_without_secrets(self):
        body = self.http.get('/me', headers=self.token(self.zlata)).json()
        self.assertEqual(body, {'id': self.zlata.id, 'name': 'Zlata', 'username': 'zlata_k',
                                'email': 'zlata@example.com', 'role': 'user'})

    def test_admin_listing_never_sends_passwords(self):
        admin = self.make_admin()
        text = self.http.get('/admin/accounts', headers=self.token(admin)).text
        for secret in ('password', 'salt', 'hash', 'correct-horse'):
            self.assertNotIn(secret, text)

    def test_logout_revokes_the_token(self):
        headers = self.token(self.zlata)
        self.backend.log_out(self.zlata)
        self.assertEqual(self.http.get('/me', headers=headers).status_code, 401)
        with self.assertRaises(AccountError):
            self.backend.unlocked_difficulties(self.zlata)

    def test_each_login_gets_its_own_token(self):
        first = self.backend.tokens[self.zlata.id]
        self.backend.log_in('zlata@example.com', 'correct-horse')
        self.assertNotEqual(self.backend.tokens[self.zlata.id], first)

    def test_cannot_act_as_an_account_you_never_logged_into(self):
        stranger = Account(999, 'Nobody', 'nobody', 'nobody@example.com', 'admin')
        with self.assertRaises(AccountError):
            self.backend.list_accounts(stranger)

    def test_cannot_post_scores_for_someone_else_by_changing_the_id(self):
        other = self.backend.sign_up('Reagan', 'reagan', 'reagan@example.com', 'password123')
        self.http.post('/me/runs', headers=self.token(self.zlata), json={
            'difficulty': 'Easy', 'won': True, 'score': 5, 'time_seconds': 1, 'lives_lost': 0, 'waves_cleared': 5,
            'kills': 1, 'account_id': other.id})
        board = self.backend.leaderboard('score')
        self.assertEqual([e.username for e in board], ['zlata_k'])

    def test_rejects_negative_or_malformed_runs(self):
        response = self.http.post('/me/runs', headers=self.token(self.zlata), json={
            'difficulty': 'Easy', 'won': True, 'score': -50, 'time_seconds': 1, 'lives_lost': 0, 'waves_cleared': 5,
            'kills': 1})
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()['error'], 'request')

    def test_leaderboard_is_public_and_limit_is_bounded(self):
        self.backend.record_run(self.zlata, RunResult('Easy', True, 10, 60.0, 0, 5, 3))
        self.assertEqual(len(self.http.get('/leaderboard/score').json()), 1)
        self.assertEqual(self.http.get('/leaderboard/score', params={'limit': 1000}).status_code, 422)

    def test_locked_level_is_refused_with_403(self):
        with self.assertRaises(AccessDenied):
            self.backend.record_run(self.zlata, contract.run('Hard'))


class OfflineTests(unittest.TestCase):
    def test_unreachable_server_gives_a_friendly_error(self):
        backend = RemoteBackend('http://127.0.0.1:9', timeout=0.5)
        try:
            with self.assertRaises(AccountError) as caught:
                backend.log_in('a@example.com', 'password123')
            self.assertEqual(str(caught.exception), OFFLINE)
            with self.assertRaises(AccountError):
                backend.leaderboard('score')
        finally:
            backend.close()


class UrlTests(unittest.TestCase):
    def test_hosted_postgres_urls_use_the_psycopg_driver(self):
        self.assertEqual(normalize_url('postgres://u:p@host/db'), 'postgresql+psycopg://u:p@host/db')
        self.assertEqual(normalize_url('postgresql://u:p@host/db'), 'postgresql+psycopg://u:p@host/db')
        self.assertEqual(normalize_url('sqlite:///karz.db'), 'sqlite:///karz.db')


if __name__ == '__main__':
    unittest.main()
