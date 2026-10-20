import tempfile
import unittest
from pathlib import Path

from accounts import AccountError, AccountStore


class AccountTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = AccountStore(Path(self.tmp.name)/'test.db')
        self.zlata = self.store.sign_up('Zlata', 'zlata_k', 'Zlata@Example.com', 'correct-horse')

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_sign_up_normalizes_email(self):
        self.assertEqual(self.zlata.email, 'zlata@example.com')
        self.assertEqual(self.zlata.username, 'zlata_k')

    def test_log_in_with_email_and_password(self):
        self.assertEqual(self.store.log_in(' ZLATA@example.com ', 'correct-horse').id, self.zlata.id)
        with self.assertRaises(AccountError):
            self.store.log_in('zlata@example.com', 'wrong-password')
        with self.assertRaises(AccountError):
            self.store.log_in('nobody@example.com', 'correct-horse')

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
                self.store.sign_up(*case)

    def test_password_is_not_stored_in_plain_text(self):
        row = self.store.db.execute('SELECT password_hash FROM accounts').fetchone()
        self.assertNotIn(b'correct-horse', row[0])

    def test_update_requires_current_password(self):
        with self.assertRaises(AccountError):
            self.store.update(self.zlata.id, 'wrong', 'Z', 'zlata_k', 'zlata@example.com')
        updated = self.store.update(self.zlata.id, 'correct-horse', 'Zlata K', 'zlatak', 'z@example.com')
        self.assertEqual((updated.name, updated.username, updated.email), ('Zlata K', 'zlatak', 'z@example.com'))
        self.assertEqual(self.store.log_in('z@example.com', 'correct-horse').id, self.zlata.id)

    def test_update_changes_password(self):
        self.store.update(self.zlata.id, 'correct-horse', 'Zlata', 'zlata_k', 'zlata@example.com', 'new-password')
        self.store.log_in('zlata@example.com', 'new-password')
        with self.assertRaises(AccountError):
            self.store.log_in('zlata@example.com', 'correct-horse')

    def test_update_rejects_taken_username(self):
        self.store.sign_up('Reagan', 'reagan', 'reagan@example.com', 'password123')
        with self.assertRaises(AccountError):
            self.store.update(self.zlata.id, 'correct-horse', 'Zlata', 'Reagan', 'zlata@example.com')


if __name__ == '__main__':
    unittest.main()
