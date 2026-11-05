import sqlite3
import tempfile
import unittest
from pathlib import Path

from backend import AccessDenied, AccountError, RunResult
from local_backend import LocalBackend, _hash


def run(difficulty, won=True, score=100, time_seconds=120.0, lives_lost=0):
    return RunResult(difficulty, won, score, time_seconds, lives_lost, waves_cleared=5 if won else 2, kills=10)


class BackendTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.backend = self.make_backend(Path(self.tmp.name))
        self.zlata = self.backend.sign_up('Zlata', 'zlata_k', 'Zlata@Example.com', 'correct-horse')

    def tearDown(self):
        self.backend.close()
        self.tmp.cleanup()

    def make_backend(self, folder):
        return LocalBackend(folder/'test.db')

    def promote(self, email):
        return self.backend.promote_by_email(email)

    def password_hashes(self):
        return [row[0] for row in self.backend.db.execute('SELECT password_hash FROM accounts')]

    def make_admin(self):
        self.backend.sign_up('Admin', 'admin', 'admin@example.com', 'password123')
        return self.promote('admin@example.com')


class AccountTests(BackendTestCase):
    def test_sign_up_normalizes_email_and_is_a_regular_user(self):
        self.assertEqual(self.zlata.email, 'zlata@example.com')
        self.assertEqual(self.zlata.role, 'user')
        self.assertFalse(self.zlata.is_admin)

    def test_log_in_with_email_and_password(self):
        self.assertEqual(self.backend.log_in(' ZLATA@example.com ', 'correct-horse').id, self.zlata.id)
        with self.assertRaises(AccountError):
            self.backend.log_in('zlata@example.com', 'wrong-password')
        with self.assertRaises(AccountError):
            self.backend.log_in('nobody@example.com', 'correct-horse')

    def test_rejects_duplicates_and_bad_input(self):
        cases = [
            ('A', 'ZLATA_K', 'new@example.com', 'password123'),
            ('A', 'someone', 'zlata@example.com', 'password123'),
            ('', 'someone', 'a@example.com', 'password123'),
            ('A', 'x', 'a@example.com', 'password123'),
            ('A', 'someone', 'not-an-email', 'password123'),
            ('A', 'someone', 'a@example.com', 'short'),
        ]
        for case in cases:
            with self.subTest(case=case), self.assertRaises(AccountError):
                self.backend.sign_up(*case)

    def test_password_is_not_stored_in_plain_text(self):
        hashes = self.password_hashes()
        self.assertEqual(len(hashes), 1)
        self.assertNotIn(b'correct-horse', hashes[0])

    def test_update_requires_current_password_and_can_change_password(self):
        with self.assertRaises(AccountError):
            self.backend.update_account(self.zlata, 'wrong', 'Z', 'zlata_k', 'zlata@example.com')
        updated = self.backend.update_account(self.zlata, 'correct-horse', 'Zlata K', 'zlatak', 'z@example.com', 'new-password')
        self.assertEqual((updated.name, updated.username, updated.email), ('Zlata K', 'zlatak', 'z@example.com'))
        self.backend.log_in('z@example.com', 'new-password')
        with self.assertRaises(AccountError):
            self.backend.log_in('z@example.com', 'correct-horse')

    def test_update_rejects_taken_username(self):
        self.backend.sign_up('Reagan', 'reagan', 'reagan@example.com', 'password123')
        with self.assertRaises(AccountError):
            self.backend.update_account(self.zlata, 'correct-horse', 'Zlata', 'Reagan', 'zlata@example.com')


class RoleTests(BackendTestCase):
    def test_users_cannot_list_accounts_but_admins_can(self):
        with self.assertRaises(AccessDenied):
            self.backend.list_accounts(self.zlata)
        admin = self.make_admin()
        summaries = self.backend.list_accounts(admin)
        self.assertEqual([s.account.username for s in summaries], ['admin', 'zlata_k'])
        self.assertTrue(all(not hasattr(s.account, 'password_hash') for s in summaries))

    def test_role_is_checked_in_the_database_not_trusted_from_the_client(self):
        fake_admin = type(self.zlata)(self.zlata.id, 'Zlata', 'zlata_k', 'zlata@example.com', role='admin')
        with self.assertRaises(AccessDenied):
            self.backend.list_accounts(fake_admin)

    def test_admin_can_change_roles_but_not_demote_themselves(self):
        admin = self.make_admin()
        self.assertTrue(self.backend.set_role(admin, self.zlata.id, 'admin').is_admin)
        self.assertFalse(self.backend.set_role(admin, self.zlata.id, 'user').is_admin)
        with self.assertRaises(AccountError):
            self.backend.set_role(admin, admin.id, 'user')
        with self.assertRaises(AccessDenied):
            self.backend.set_role(self.zlata, admin.id, 'user')


class UnlockTests(BackendTestCase):
    def test_new_user_only_has_easy(self):
        self.assertEqual(self.backend.unlocked_difficulties(self.zlata), ('Easy',))

    def test_admin_has_everything_immediately(self):
        self.assertEqual(self.backend.unlocked_difficulties(self.make_admin()), ('Easy', 'Medium', 'Hard', 'Impossible'))

    def test_losing_does_not_unlock_and_winning_unlocks_the_next_level(self):
        self.assertEqual(self.backend.record_run(self.zlata, run('Easy', won=False)), ())
        self.assertEqual(self.backend.unlocked_difficulties(self.zlata), ('Easy',))
        self.assertEqual(self.backend.record_run(self.zlata, run('Easy')), ('Medium',))
        self.assertEqual(self.backend.record_run(self.zlata, run('Easy')), ())
        self.assertEqual(self.backend.record_run(self.zlata, run('Medium')), ('Hard',))
        self.assertEqual(self.backend.record_run(self.zlata, run('Hard')), ('Impossible',))
        self.assertEqual(self.backend.record_run(self.zlata, run('Impossible')), ())
        self.assertEqual(self.backend.unlocked_difficulties(self.zlata), ('Easy', 'Medium', 'Hard', 'Impossible'))

    def test_users_cannot_record_runs_on_locked_levels(self):
        for name in ('Medium', 'Hard', 'Impossible'):
            with self.subTest(name=name), self.assertRaises(AccessDenied):
                self.backend.record_run(self.zlata, run(name))
        with self.assertRaises(AccountError):
            self.backend.record_run(self.zlata, run('Nightmare'))


class LeaderboardTests(BackendTestCase):
    def add_player(self, i):
        return self.backend.sign_up(f'Player {i}', f'player{i}', f'p{i}@example.com', 'password123')

    def test_score_board_keeps_each_players_best_and_includes_losses(self):
        self.backend.record_run(self.zlata, run('Easy', won=False, score=900))
        self.backend.record_run(self.zlata, run('Easy', score=400))
        other = self.add_player(1)
        self.backend.record_run(other, run('Easy', score=500))
        board = self.backend.leaderboard('score')
        self.assertEqual([(e.rank, e.username, e.value) for e in board], [(1, 'zlata_k', 900), (2, 'player1', 500)])

    def test_time_and_lives_boards_only_count_wins(self):
        self.backend.record_run(self.zlata, run('Easy', won=False, time_seconds=10, lives_lost=0))
        self.assertEqual(self.backend.leaderboard('time'), [])
        self.backend.record_run(self.zlata, run('Easy', time_seconds=95.5, lives_lost=3))
        other = self.add_player(1)
        self.backend.record_run(other, run('Easy', time_seconds=80.0, lives_lost=5))
        self.assertEqual([(e.username, e.value) for e in self.backend.leaderboard('time')], [('player1', 80.0), ('zlata_k', 95.5)])
        self.assertEqual([(e.username, e.value) for e in self.backend.leaderboard('lives')], [('zlata_k', 3), ('player1', 5)])

    def test_lives_ties_are_broken_by_faster_time(self):
        self.backend.record_run(self.zlata, run('Easy', time_seconds=200, lives_lost=0))
        other = self.add_player(1)
        self.backend.record_run(other, run('Easy', time_seconds=150, lives_lost=0))
        self.assertEqual([e.username for e in self.backend.leaderboard('lives')], ['player1', 'zlata_k'])

    def test_board_is_capped_at_25_players(self):
        for i in range(30):
            self.backend.record_run(self.add_player(i), run('Easy', score=i))
        board = self.backend.leaderboard('score')
        self.assertEqual(len(board), 25)
        self.assertEqual((board[0].value, board[-1].value), (29, 5))
        self.assertEqual([e.rank for e in board], list(range(1, 26)))

    def test_difficulty_filter(self):
        admin = self.make_admin()
        self.backend.record_run(admin, run('Hard', score=50))
        self.backend.record_run(self.zlata, run('Easy', score=999))
        self.assertEqual([e.username for e in self.backend.leaderboard('score', 'Hard')], ['admin'])
        with self.assertRaises(ValueError):
            self.backend.leaderboard('fastest')


def sandbox(waves, kills=30, difficulty='Easy', score=300, time_seconds=200.0, won=False):
    return RunResult(difficulty, won, score, time_seconds, 3, waves, kills, sandbox=True)


class ModeTests(BackendTestCase):
    def test_sandbox_games_are_saved_but_never_unlock_levels(self):
        self.assertEqual(self.backend.record_run(self.zlata, sandbox(12, won=True)), ())
        self.assertEqual(self.backend.unlocked_difficulties(self.zlata), ('Easy',))

    def test_sandbox_and_regular_boards_are_separate(self):
        self.backend.record_run(self.zlata, sandbox(12, score=5000))
        self.backend.record_run(self.zlata, run('Easy', score=400))
        self.assertEqual([(e.username, e.value) for e in self.backend.leaderboard('score')], [('zlata_k', 400)])
        self.assertEqual([(e.username, e.value) for e in self.backend.leaderboard('score', mode='sandbox')],
                         [('zlata_k', 5000)])

    def test_sandbox_board_ranks_by_most_waves_then_kills(self):
        reagan = self.backend.sign_up('Reagan', 'reagan', 'reagan@example.com', 'password123')
        alex = self.backend.sign_up('Alex', 'alex', 'alex@example.com', 'password123')
        self.backend.record_run(self.zlata, sandbox(8, kills=90))
        self.backend.record_run(self.zlata, sandbox(15, kills=200))
        self.backend.record_run(reagan, sandbox(15, kills=250))
        self.backend.record_run(alex, sandbox(3, kills=20))
        board = self.backend.leaderboard('waves', mode='sandbox')
        self.assertEqual([(e.rank, e.username, e.value) for e in board], [(1, 'reagan', 15), (2, 'zlata_k', 15), (3, 'alex', 3)])

    def test_sandbox_needs_the_level_unlocked(self):
        with self.assertRaises(AccessDenied):
            self.backend.record_run(self.zlata, sandbox(5, difficulty='Medium'))

    def test_sandbox_difficulty_filter(self):
        self.backend.record_run(self.zlata, run('Easy'))
        self.backend.record_run(self.zlata, sandbox(4, difficulty='Medium'))
        self.backend.record_run(self.zlata, sandbox(9, difficulty='Easy'))
        self.assertEqual([e.value for e in self.backend.leaderboard('waves', 'Medium', mode='sandbox')], [4])

    def test_admin_best_score_ignores_sandbox(self):
        admin = self.make_admin()
        self.backend.record_run(self.zlata, sandbox(30, score=99999))
        self.backend.record_run(self.zlata, run('Easy', score=500))
        summary = next(s for s in self.backend.list_accounts(admin) if s.account.id == self.zlata.id)
        self.assertEqual((summary.best_score, summary.games_played), (500, 2))

    def test_regular_waves_board_and_unknown_mode(self):
        self.backend.record_run(self.zlata, run('Easy', won=False))
        self.assertEqual([e.value for e in self.backend.leaderboard('waves')], [2])
        with self.assertRaises(ValueError):
            self.backend.leaderboard('waves', mode='hardcore')


def state(wave=3, money=210, towers=None, **extra):
    data = {'version': 1, 'wave': wave, 'lives': 18, 'kills': 40, 'leaked': 2, 'money': money, 'elapsed': 95.5,
            'towers': towers if towers is not None else [{'x': 150, 'y': 250, 'level': 2}, {'x': 230.5, 'y': 180, 'level': 0}]}
    data.update(extra)
    return data


class CheckpointTests(BackendTestCase):
    def test_nothing_saved_yet(self):
        self.assertIsNone(self.backend.load_checkpoint(self.zlata, 'Easy', 'regular'))

    def test_save_and_load_round_trip(self):
        self.backend.save_checkpoint(self.zlata, 'Easy', 'regular', state())
        self.assertEqual(self.backend.load_checkpoint(self.zlata, 'Easy', 'regular'), state())

    def test_newer_checkpoint_replaces_the_old_one(self):
        self.backend.save_checkpoint(self.zlata, 'Easy', 'regular', state(wave=2))
        self.backend.save_checkpoint(self.zlata, 'Easy', 'regular', state(wave=4))
        self.assertEqual(self.backend.load_checkpoint(self.zlata, 'Easy', 'regular')['wave'], 4)

    def test_each_level_and_mode_has_its_own_checkpoint(self):
        self.backend.record_run(self.zlata, run('Easy'))
        self.backend.save_checkpoint(self.zlata, 'Easy', 'regular', state(wave=2))
        self.backend.save_checkpoint(self.zlata, 'Easy', 'sandbox', state(wave=9))
        self.backend.save_checkpoint(self.zlata, 'Medium', 'regular', state(wave=1))
        self.assertEqual([self.backend.load_checkpoint(self.zlata, d, m)['wave'] for d, m in
                          (('Easy', 'regular'), ('Easy', 'sandbox'), ('Medium', 'regular'))], [2, 9, 1])

    def test_clear_removes_only_that_checkpoint(self):
        self.backend.save_checkpoint(self.zlata, 'Easy', 'regular', state())
        self.backend.save_checkpoint(self.zlata, 'Easy', 'sandbox', state())
        self.backend.clear_checkpoint(self.zlata, 'Easy', 'regular')
        self.backend.clear_checkpoint(self.zlata, 'Easy', 'regular')
        self.assertIsNone(self.backend.load_checkpoint(self.zlata, 'Easy', 'regular'))
        self.assertIsNotNone(self.backend.load_checkpoint(self.zlata, 'Easy', 'sandbox'))

    def test_players_only_see_their_own_checkpoints(self):
        reagan = self.backend.sign_up('Reagan', 'reagan', 'reagan@example.com', 'password123')
        self.backend.save_checkpoint(self.zlata, 'Easy', 'regular', state(wave=5))
        self.assertIsNone(self.backend.load_checkpoint(reagan, 'Easy', 'regular'))

    def test_cannot_save_on_a_locked_level(self):
        with self.assertRaises(AccessDenied):
            self.backend.save_checkpoint(self.zlata, 'Hard', 'regular', state())

    def test_invalid_checkpoints_are_refused(self):
        bad = [state(version=99), state(wave=0), state(money=-5), state(lives='lots'), state(towers='none'),
               state(towers=[{'x': 5000, 'y': 1, 'level': 0}]), state(towers=[{'x': 1, 'y': 1}]),
               state(towers=[{'x': 1, 'y': 1, 'level': 0}]*301), {'wave': 3}, ['not', 'a', 'dict']]
        for case in bad:
            with self.subTest(case=str(case)[:60]), self.assertRaises(AccountError):
                self.backend.save_checkpoint(self.zlata, 'Easy', 'regular', case)
        for difficulty, mode in (('Nightmare', 'regular'), ('Easy', 'hardcore')):
            with self.assertRaises(AccountError):
                self.backend.save_checkpoint(self.zlata, difficulty, mode, state())
        self.assertIsNone(self.backend.load_checkpoint(self.zlata, 'Easy', 'regular'))


class MigrationTests(unittest.TestCase):
    def test_old_database_from_the_previous_version_still_works(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'old.db'
            db = sqlite3.connect(path)
            db.execute('''CREATE TABLE accounts (id INTEGER PRIMARY KEY, name TEXT NOT NULL,
                username TEXT NOT NULL UNIQUE COLLATE NOCASE, email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                salt BLOB NOT NULL, password_hash BLOB NOT NULL)''')
            salt = b'0123456789abcdef'
            db.execute('INSERT INTO accounts (name, username, email, salt, password_hash) VALUES (?, ?, ?, ?, ?)',
                       ('Old', 'olduser', 'old@example.com', salt, _hash('password123', salt)))
            db.commit()
            db.close()
            backend = LocalBackend(path)
            account = backend.log_in('old@example.com', 'password123')
            self.assertEqual(account.role, 'user')
            self.assertEqual(backend.unlocked_difficulties(account), ('Easy',))
            self.assertEqual(backend.record_run(account, run('Easy')), ('Medium',))
            backend.close()


if __name__ == '__main__':
    unittest.main()
