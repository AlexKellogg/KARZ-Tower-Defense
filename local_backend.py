import hashlib
import hmac
import re
import secrets
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from backend import (DIFFICULTY_NAMES, LEADERBOARD_KINDS, LEADERBOARD_SIZE, ROLES, AccessDenied, Account,
                     AccountError, AccountSummary, Backend, LeaderboardEntry, unlocked_for)

# Local stand-in for the FastAPI backend, swap for the server version once it exists.
DEFAULT_DB = Path.home()/'.karz_td'/'accounts.db'
EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
MIN_PASSWORD = 8

LEADERBOARD_SQL = {
    'score': ('score', 'score DESC', ''),
    'time': ('time_seconds', 'time_seconds ASC', 'AND r.won = 1'),
    'lives': ('lives_lost', 'lives_lost ASC, time_seconds ASC', 'AND r.won = 1'),
}


def _hash(password, salt):
    return hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 200_000)


def _now():
    return datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')


class LocalBackend(Backend):
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
        columns = {row[1] for row in self.db.execute('PRAGMA table_info(accounts)')}
        if 'role' not in columns:
            self.db.execute("ALTER TABLE accounts ADD COLUMN role TEXT NOT NULL DEFAULT 'user'")
        if 'created_at' not in columns:
            self.db.execute('ALTER TABLE accounts ADD COLUMN created_at TEXT')
            self.db.execute('UPDATE accounts SET created_at = ? WHERE created_at IS NULL', (_now(),))
        self.db.execute('''CREATE TABLE IF NOT EXISTS runs (
            id INTEGER PRIMARY KEY,
            account_id INTEGER NOT NULL REFERENCES accounts(id),
            difficulty TEXT NOT NULL,
            won INTEGER NOT NULL,
            score INTEGER NOT NULL,
            time_seconds REAL NOT NULL,
            lives_lost INTEGER NOT NULL,
            waves_cleared INTEGER NOT NULL,
            kills INTEGER NOT NULL,
            played_at TEXT NOT NULL)''')
        self.db.commit()

    def close(self):
        self.db.close()

    def _get(self, account_id):
        row = self.db.execute('SELECT id, name, username, email, role FROM accounts WHERE id = ?', (account_id,)).fetchone()
        if row is None:
            raise AccountError('Account not found.')
        return Account(*row)

    def _require_admin(self, requester):
        if self._get(requester.id).role != 'admin':
            raise AccessDenied('Only admins can do that.')

    def _validate(self, name, username, email, password=None, ignore_id=None):
        if not name.strip():
            raise AccountError('Enter your name.')
        if not re.fullmatch(r'[A-Za-z0-9_.]{3,20}', username):
            raise AccountError('Username must be 3-20 letters, numbers, _ or .')
        if not EMAIL_RE.match(email):
            raise AccountError('Enter a valid email address.')
        if password is not None and len(password) < MIN_PASSWORD:
            raise AccountError(f'Password must be at least {MIN_PASSWORD} characters.')
        for column, value in (('username', username), ('email', email)):
            row = self.db.execute(f'SELECT id FROM accounts WHERE {column} = ?', (value,)).fetchone()
            if row and row[0] != ignore_id:
                raise AccountError(f'That {column} is already taken.')

    def _check_password(self, account_id, password):
        salt, stored = self.db.execute('SELECT salt, password_hash FROM accounts WHERE id = ?', (account_id,)).fetchone()
        return hmac.compare_digest(_hash(password, salt), stored)

    def sign_up(self, name, username, email, password):
        name, username, email = name.strip(), username.strip(), email.strip().lower()
        self._validate(name, username, email, password)
        salt = secrets.token_bytes(16)
        cur = self.db.execute(
            "INSERT INTO accounts (name, username, email, salt, password_hash, role, created_at) VALUES (?, ?, ?, ?, ?, 'user', ?)",
            (name, username, email, salt, _hash(password, salt), _now()))
        self.db.commit()
        return self._get(cur.lastrowid)

    def log_in(self, email, password):
        row = self.db.execute('SELECT id FROM accounts WHERE email = ?', (email.strip().lower(),)).fetchone()
        if row is None or not self._check_password(row[0], password):
            raise AccountError('Incorrect email or password.')
        return self._get(row[0])

    def update_account(self, account, current_password, name, username, email, new_password=''):
        if not self._check_password(account.id, current_password):
            raise AccountError('Current password is incorrect.')
        name, username, email = name.strip(), username.strip(), email.strip().lower()
        self._validate(name, username, email, new_password or None, ignore_id=account.id)
        self.db.execute('UPDATE accounts SET name = ?, username = ?, email = ? WHERE id = ?',
                        (name, username, email, account.id))
        if new_password:
            salt = secrets.token_bytes(16)
            self.db.execute('UPDATE accounts SET salt = ?, password_hash = ? WHERE id = ?',
                            (salt, _hash(new_password, salt), account.id))
        self.db.commit()
        return self._get(account.id)

    def _highest_won(self, account_id):
        won = {row[0] for row in self.db.execute('SELECT DISTINCT difficulty FROM runs WHERE account_id = ? AND won = 1', (account_id,))}
        return max((i for i, name in enumerate(DIFFICULTY_NAMES) if name in won), default=-1)

    def unlocked_difficulties(self, account):
        return unlocked_for(self._get(account.id).role, self._highest_won(account.id))

    def record_run(self, account, result):
        if result.difficulty not in DIFFICULTY_NAMES:
            raise AccountError('Unknown difficulty.')
        before = self.unlocked_difficulties(account)
        if result.difficulty not in before:
            raise AccessDenied(f'{result.difficulty} is locked for this account.')
        self.db.execute(
            '''INSERT INTO runs (account_id, difficulty, won, score, time_seconds, lives_lost, waves_cleared, kills, played_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (account.id, result.difficulty, int(result.won), int(result.score), float(result.time_seconds),
             int(result.lives_lost), int(result.waves_cleared), int(result.kills), _now()))
        self.db.commit()
        return tuple(name for name in self.unlocked_difficulties(account) if name not in before)

    def leaderboard(self, kind, difficulty=None, limit=LEADERBOARD_SIZE):
        if kind not in LEADERBOARD_KINDS:
            raise ValueError(f'Unknown leaderboard: {kind}')
        column, order, only_wins = LEADERBOARD_SQL[kind]
        where, params = '', []
        if difficulty is not None:
            where = 'AND r.difficulty = ?'
            params.append(difficulty)
        rows = self.db.execute(f'''
            SELECT username, {column}, difficulty, played_at FROM (
                SELECT a.username AS username, r.score AS score, r.time_seconds AS time_seconds,
                       r.lives_lost AS lives_lost, r.difficulty AS difficulty, r.played_at AS played_at, r.id AS run_id,
                       ROW_NUMBER() OVER (PARTITION BY r.account_id ORDER BY {order}, r.played_at, r.id) AS pick
                FROM runs r JOIN accounts a ON a.id = r.account_id
                WHERE 1 = 1 {only_wins} {where})
            WHERE pick = 1
            ORDER BY {order}, played_at, run_id
            LIMIT ?''', (*params, limit)).fetchall()
        return [LeaderboardEntry(i+1, *row) for i, row in enumerate(rows)]

    def list_accounts(self, requester):
        self._require_admin(requester)
        rows = self.db.execute('''
            SELECT a.id, a.name, a.username, a.email, a.role, COALESCE(MAX(r.score), 0), COUNT(r.id), a.created_at
            FROM accounts a LEFT JOIN runs r ON r.account_id = a.id
            GROUP BY a.id ORDER BY a.role = 'admin' DESC, a.username COLLATE NOCASE''').fetchall()
        return [AccountSummary(Account(*row[:5]), unlocked_for(row[4], self._highest_won(row[0])), row[5], row[6], row[7] or '')
                for row in rows]

    def set_role(self, requester, account_id, role):
        self._require_admin(requester)
        if role not in ROLES:
            raise AccountError('Unknown role.')
        if account_id == requester.id and role != 'admin':
            raise AccountError('You cannot remove your own admin role.')
        self._get(account_id)
        self.db.execute('UPDATE accounts SET role = ? WHERE id = ?', (role, account_id))
        self.db.commit()
        return self._get(account_id)

    def promote_by_email(self, email):
        row = self.db.execute('SELECT id FROM accounts WHERE email = ?', (email.strip().lower(),)).fetchone()
        if row is None:
            raise AccountError(f'No account with email {email}.')
        self.db.execute("UPDATE accounts SET role = 'admin' WHERE id = ?", (row[0],))
        self.db.commit()
        return self._get(row[0])
