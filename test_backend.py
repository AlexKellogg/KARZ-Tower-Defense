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
        self.path = Path(self.tmp.name)/'test.db'
        self.backend = LocalBackend(self.path)
        self.zlata = self.backend.sign_up('Zlata', 'zlata_k', 'Zlata@Example.com', 'correct-horse')

    def tearDown(self):
        self.backend.close()
        self.tmp.cleanup()

    def make_admin(self):
        self.backend.sign_up('Admin', 'admin', 'admin@example.com', 'password123')
        return self.backend.promote_by_email('admin@example.com')


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
        row = self.backend.db.execute('SELECT password_hash FROM accounts').fetchone()
        self.assertNotIn(b'correct-horse', row[0])

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
