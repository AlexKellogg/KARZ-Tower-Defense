import os
import unittest

from fastapi.testclient import TestClient

import test_backend as contract
import httpx

from backend import AccessDenied, Account, AccountError, RunResult, ScoreQueued
from remote_backend import EXPIRED, OFFLINE, QUEUED, RemoteBackend
from server.app import create_app
from sqlalchemy import create_engine

from server.sql_backend import SqlBackend, normalize_url

POSTGRES_URL = os.environ.get('KARZ_TEST_POSTGRES_URL', '')


class ServerFixture:
    def make_backend(self, folder):
        self.sql = SqlBackend(f'sqlite:///{folder/"server.db"}')
        self.http = TestClient(create_app(self.sql))
        return RemoteBackend('http://testserver', client=self.http, pending_path=folder/'pending.json')

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


def reset_postgres():
    engine = create_engine(normalize_url(POSTGRES_URL))
    with engine.begin() as connection:
        connection.exec_driver_sql('DROP SCHEMA public CASCADE')
        connection.exec_driver_sql('CREATE SCHEMA public')
    engine.dispose()


class PostgresFixture(ServerFixture):
    def make_backend(self, folder):
        reset_postgres()
        self.sql = SqlBackend(POSTGRES_URL)
        self.http = TestClient(create_app(self.sql))
        return RemoteBackend('http://testserver', client=self.http, pending_path=folder/'pending.json')


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


class ServerModeTests(ServerFixture, contract.ModeTests):
    pass


@needs_postgres
class PostgresModeTests(PostgresFixture, contract.ModeTests):
    pass


class ServerCheckpointTests(ServerFixture, contract.CheckpointTests):
    pass


@needs_postgres
class PostgresCheckpointTests(PostgresFixture, contract.CheckpointTests):
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


class FlakyClient(TestClient):
    down = False

    def request(self, *args, **kwargs):
        if self.down:
            raise httpx.ConnectError('server is down')
        return super().request(*args, **kwargs)


class QueueFixture(ServerFixture):
    def make_backend(self, folder):
        self.folder = folder
        self.sql = SqlBackend(f'sqlite:///{folder/"server.db"}')
        self.http = FlakyClient(create_app(self.sql))
        return RemoteBackend('http://testserver', client=self.http, pending_path=folder/'pending.json')

    def server_runs(self):
        return len(self.sql.leaderboard('score', limit=100))

    def win(self, difficulty='Easy', score=500):
        return contract.run(difficulty, score=score)


class QueueTests(QueueFixture, contract.BackendTestCase):
    def test_score_finished_while_offline_is_kept_not_lost(self):
        self.http.down = True
        with self.assertRaises(ScoreQueued) as caught:
            self.backend.record_run(self.zlata, self.win())
        self.assertEqual(str(caught.exception), QUEUED)
        self.assertEqual(self.backend.pending_runs(self.zlata), [self.win()])
        self.http.down = False
        self.assertEqual(self.server_runs(), 0)

    def test_queued_score_uploads_once_when_the_server_is_back(self):
        self.http.down = True
        with self.assertRaises(ScoreQueued):
            self.backend.record_run(self.zlata, self.win())
        self.http.down = False
        self.assertEqual(self.backend.unlocked_difficulties(self.zlata), ('Easy', 'Medium'))
        self.assertEqual(self.backend.pending_runs(self.zlata), [])
        self.assertEqual([(e.username, e.value) for e in self.backend.leaderboard('score')], [('zlata_k', 500)])
        self.backend.unlocked_difficulties(self.zlata)
        self.assertEqual(self.sql.list_accounts(self.sql.promote_by_email('zlata@example.com'))[0].games_played, 1)

    def test_next_game_sends_the_queued_one_first_and_reports_both_unlocks(self):
        self.http.down = True
        with self.assertRaises(ScoreQueued):
            self.backend.record_run(self.zlata, self.win('Easy'))
        self.http.down = False
        self.assertEqual(self.backend.record_run(self.zlata, self.win('Medium')), ('Medium', 'Hard'))

    def test_queue_survives_closing_the_game(self):
        self.http.down = True
        with self.assertRaises(ScoreQueued):
            self.backend.record_run(self.zlata, self.win(score=321))
        self.http.down = False
        fresh = RemoteBackend('http://testserver', client=self.http, pending_path=self.folder/'pending.json')
        fresh.log_in('zlata@example.com', 'correct-horse')
        self.assertEqual([(e.username, e.value) for e in fresh.leaderboard('score')], [('zlata_k', 321)])
        self.assertEqual(fresh.pending_runs(self.zlata), [])

    def test_two_identical_queued_scores_both_upload(self):
        self.http.down = True
        for _ in range(2):
            with self.assertRaises(ScoreQueued):
                self.backend.record_run(self.zlata, self.win())
        self.http.down = False
        self.backend.unlocked_difficulties(self.zlata)
        admin = self.sql.promote_by_email('zlata@example.com')
        self.assertEqual(self.sql.list_accounts(admin)[0].games_played, 2)

    def test_a_queued_score_the_server_refuses_is_dropped_not_stuck(self):
        self.http.down = True
        with self.assertRaises(ScoreQueued):
            self.backend.record_run(self.zlata, self.win('Hard'))
        self.http.down = False
        self.assertEqual(self.backend.unlocked_difficulties(self.zlata), ('Easy',))
        self.assertEqual(self.backend.pending_runs(self.zlata), [])
        self.assertEqual(self.server_runs(), 0)

    def test_queued_scores_only_upload_for_their_own_account(self):
        other = self.backend.sign_up('Reagan', 'reagan', 'reagan@example.com', 'password123')
        self.http.down = True
        with self.assertRaises(ScoreQueued):
            self.backend.record_run(self.zlata, self.win(score=111))
        self.http.down = False
        self.backend.unlocked_difficulties(other)
        self.assertEqual(self.server_runs(), 0)
        self.assertEqual(len(self.backend.pending_runs(self.zlata)), 1)

    def test_server_dropping_again_mid_upload_keeps_the_rest(self):
        self.http.down = True
        for score in (1, 2):
            with self.assertRaises(ScoreQueued):
                self.backend.record_run(self.zlata, self.win(score=score))
        self.http.down = False
        calls = []
        real = FlakyClient.request

        def drop_after_first(client, *args, **kwargs):
            if args[0] == 'POST' and args[1] == '/me/runs':
                calls.append(1)
                if len(calls) == 2:
                    raise httpx.ConnectError('dropped')
            return real(client, *args, **kwargs)

        FlakyClient.request = drop_after_first
        try:
            self.backend.unlocked_difficulties(self.zlata)
        except AccountError:
            pass
        finally:
            FlakyClient.request = real
        self.assertEqual([r.score for r in self.backend.pending_runs(self.zlata)], [2])
        self.backend.unlocked_difficulties(self.zlata)
        self.assertEqual(self.backend.pending_runs(self.zlata), [])

    def test_expired_login_also_keeps_the_score(self):
        self.backend.tokens[self.zlata.id] = 'expired-token'
        with self.assertRaises(ScoreQueued) as caught:
            self.backend.record_run(self.zlata, self.win(score=77))
        self.assertEqual(str(caught.exception), EXPIRED)
        self.backend.log_in('zlata@example.com', 'correct-horse')
        self.assertEqual([(e.username, e.value) for e in self.backend.leaderboard('score')], [('zlata_k', 77)])


class CheckpointQueueTests(QueueFixture, contract.BackendTestCase):
    def test_checkpoint_saved_while_offline_reaches_the_server_later(self):
        self.http.down = True
        self.backend.save_checkpoint(self.zlata, 'Easy', 'regular', contract.state(wave=3))
        self.assertEqual(len(self.backend.pending_checkpoints(self.zlata)), 1)
        self.http.down = False
        self.assertEqual(self.backend.load_checkpoint(self.zlata, 'Easy', 'regular')['wave'], 3)
        self.assertEqual(self.backend.pending_checkpoints(self.zlata), [])

    def test_offline_save_then_finish_ends_with_no_checkpoint_and_the_score_kept(self):
        self.http.down = True
        self.backend.save_checkpoint(self.zlata, 'Easy', 'regular', contract.state(wave=4))
        with self.assertRaises(ScoreQueued):
            self.backend.record_run(self.zlata, self.win(score=650))
        self.backend.clear_checkpoint(self.zlata, 'Easy', 'regular')
        self.http.down = False
        self.assertIsNone(self.backend.load_checkpoint(self.zlata, 'Easy', 'regular'))
        self.assertEqual([(e.username, e.value) for e in self.backend.leaderboard('score')], [('zlata_k', 650)])

    def test_later_checkpoint_waits_behind_an_earlier_queued_one(self):
        self.http.down = True
        self.backend.save_checkpoint(self.zlata, 'Easy', 'regular', contract.state(wave=2))
        self.http.down = False
        calls = []
        real = FlakyClient.request

        def count(client, *args, **kwargs):
            if args[0] == 'PUT':
                calls.append(kwargs['json']['state']['wave'])
            return real(client, *args, **kwargs)

        FlakyClient.request = count
        try:
            self.backend.save_checkpoint(self.zlata, 'Easy', 'regular', contract.state(wave=3))
        finally:
            FlakyClient.request = real
        self.assertEqual(calls, [2, 3])
        self.assertEqual(self.backend.load_checkpoint(self.zlata, 'Easy', 'regular')['wave'], 3)

    def test_old_queue_files_without_a_kind_still_upload_as_scores(self):
        import json
        (self.folder/'pending.json').write_text(json.dumps([{'server': 'http://testserver', 'account_id': self.zlata.id,
                                                             'result': {'difficulty': 'Easy', 'won': True, 'score': 42,
                                                                        'time_seconds': 9.0, 'lives_lost': 0,
                                                                        'waves_cleared': 5, 'kills': 3}}]))
        self.backend.unlocked_difficulties(self.zlata)
        self.assertEqual([e.value for e in self.backend.leaderboard('score')], [42])

    def test_checkpoint_endpoints_need_a_login(self):
        for method in ('GET', 'PUT', 'DELETE'):
            response = self.http.request(method, '/me/checkpoints/Easy/regular', json={'state': contract.state()})
            self.assertEqual(response.status_code, 401)


class OfflineTests(unittest.TestCase):
    def test_unreachable_server_gives_a_friendly_error(self):
        import tempfile
        from pathlib import Path
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        backend = RemoteBackend('http://127.0.0.1:9', timeout=0.5, pending_path=Path(self.tmp.name)/'p.json')
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
