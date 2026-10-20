import hashlib
import hmac
import re
import secrets
import sqlite3
from dataclasses import dataclass
from pathlib import Path

# Local stand-in for the FastAPI accounts backend, swap out once the server exists - alex
DEFAULT_DB = Path.home()/'.karz_td'/'accounts.db'
EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
MIN_PASSWORD = 8


class AccountError(ValueError):
    pass


@dataclass
class Account:
    id: int
    name: str
    username: str
    email: str


def _hash(password, salt):
    return hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 200_000)


class AccountStore:
    def __init__(self, path=DEFAULT_DB):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.execute('''CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            username TEXT NOT NULL UNIQUE COLLATE NOCASE,
            email TEXT NOT NULL UNIQUE COLLATE NOCASE,
            salt BLOB NOT NULL,
            password_hash BLOB NOT NULL)''')
        self.db.commit()

    def close(self):
        self.db.close()

    def _validate(self, name, username, email, password=None, ignore_id=None):
        if not name.strip():
            raise AccountError('Enter your name.')
        if not re.fullmatch(r'[A-Za-z0-9_.]{3,20}', username):
            raise AccountError('Username must be 3-20 letters, numbers, _ or .')
        if not EMAIL_RE.match(email):
            raise AccountError('Enter a valid email address.')
        if password is not None and len(password) < MIN_PASSWORD:
            raise AccountError(f'Password must be at least {MIN_PASSWORD} characters.')
        for column, value, label in (('username', username, 'username'), ('email', email, 'email')):
            row = self.db.execute(f'SELECT id FROM accounts WHERE {column} = ?', (value,)).fetchone()
            if row and row[0] != ignore_id:
                raise AccountError(f'That {label} is already taken.')

    def _get(self, account_id):
        row = self.db.execute('SELECT id, name, username, email FROM accounts WHERE id = ?', (account_id,)).fetchone()
        return Account(*row)

    def sign_up(self, name, username, email, password):
        name, username, email = name.strip(), username.strip(), email.strip().lower()
        self._validate(name, username, email, password)
        salt = secrets.token_bytes(16)
        cur = self.db.execute(
            'INSERT INTO accounts (name, username, email, salt, password_hash) VALUES (?, ?, ?, ?, ?)',
            (name, username, email, salt, _hash(password, salt)))
        self.db.commit()
        return self._get(cur.lastrowid)

    def _check_password(self, account_id, password):
        salt, stored = self.db.execute('SELECT salt, password_hash FROM accounts WHERE id = ?', (account_id,)).fetchone()
        return hmac.compare_digest(_hash(password, salt), stored)

    def log_in(self, email, password):
        row = self.db.execute('SELECT id FROM accounts WHERE email = ?', (email.strip().lower(),)).fetchone()
        if row is None or not self._check_password(row[0], password):
            raise AccountError('Incorrect email or password.')
        return self._get(row[0])

    def update(self, account_id, current_password, name, username, email, new_password=''):
        if not self._check_password(account_id, current_password):
            raise AccountError('Current password is incorrect.')
        name, username, email = name.strip(), username.strip(), email.strip().lower()
        self._validate(name, username, email, new_password or None, ignore_id=account_id)
        self.db.execute('UPDATE accounts SET name = ?, username = ?, email = ? WHERE id = ?',
                        (name, username, email, account_id))
        if new_password:
            salt = secrets.token_bytes(16)
            self.db.execute('UPDATE accounts SET salt = ?, password_hash = ? WHERE id = ?',
                            (salt, _hash(new_password, salt), account_id))
        self.db.commit()
        return self._get(account_id)