import hashlib
import hmac
import re
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import Boolean, Float, ForeignKey, Integer, LargeBinary, String, create_engine, func, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column
from sqlalchemy.pool import StaticPool

from backend import (DIFFICULTY_NAMES, LEADERBOARD_KINDS, LEADERBOARD_SIZE, ROLES, AccessDenied, Account,
                     AccountError, AccountSummary, Backend, LeaderboardEntry, unlocked_for)
from local_backend import EMAIL_RE, MIN_PASSWORD, _hash

DEFAULT_URL = 'sqlite:///karz_server.db'
TOKEN_LIFETIME = timedelta(days=30)
TIME_FORMAT = '%Y-%m-%d %H:%M:%S'


def _now():
    return datetime.now(timezone.utc).strftime(TIME_FORMAT)


def normalize_url(url):
    for prefix in ('postgres://', 'postgresql://'):
        if url.startswith(prefix):
            return 'postgresql+psycopg://'+url[len(prefix):]
    return url


def _token_key(token):
    return hashlib.sha256(token.encode()).hexdigest()


class Base(DeclarativeBase):
    pass


class AccountRow(Base):
    __tablename__ = 'accounts'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    username: Mapped[str] = mapped_column(String(20))
    username_key: Mapped[str] = mapped_column(String(20), unique=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    salt: Mapped[bytes] = mapped_column(LargeBinary)
    password_hash: Mapped[bytes] = mapped_column(LargeBinary)
    role: Mapped[str] = mapped_column(String(10), default='user')
    created_at: Mapped[str] = mapped_column(String(19))

    def to_account(self):
        return Account(self.id, self.name, self.username, self.email, self.role)


class RunRow(Base):
    __tablename__ = 'runs'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey('accounts.id'), index=True)
    difficulty: Mapped[str] = mapped_column(String(20), index=True)
    won: Mapped[bool] = mapped_column(Boolean)
    score: Mapped[int] = mapped_column(Integer)
    time_seconds: Mapped[float] = mapped_column(Float)
    lives_lost: Mapped[int] = mapped_column(Integer)
    waves_cleared: Mapped[int] = mapped_column(Integer)
    kills: Mapped[int] = mapped_column(Integer)
    played_at: Mapped[str] = mapped_column(String(19))


class TokenRow(Base):
    __tablename__ = 'tokens'
    token_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey('accounts.id'), index=True)
    created_at: Mapped[str] = mapped_column(String(19))


LEADERBOARD_ORDER = {
    'score': ('score', (('score', True),), False),
    'time': ('time_seconds', (('time_seconds', False),), True),
    'lives': ('lives_lost', (('lives_lost', False), ('time_seconds', False)), True),
}


class SqlBackend(Backend):
    def __init__(self, url=DEFAULT_URL):
        url = normalize_url(url)
        options = {}
        if url.startswith('sqlite'):
            options['connect_args'] = {'check_same_thread': False}
            if url in ('sqlite://', 'sqlite:///:memory:'):
                options['poolclass'] = StaticPool
        self.engine = create_engine(url, **options)
        Base.metadata.create_all(self.engine)

    def close(self):
        self.engine.dispose()

    def _session(self):
        return Session(self.engine, expire_on_commit=False)

    def _row(self, db, account_id):
        row = db.get(AccountRow, account_id)
        if row is None:
            raise AccountError('Account not found.')
        return row

    def _get(self, account_id):
        with self._session() as db:
            return self._row(db, account_id).to_account()

    def _require_admin(self, db, requester):
        if self._row(db, requester.id).role != 'admin':
            raise AccessDenied('Only admins can do that.')

    def _validate(self, db, name, username, email, password=None, ignore_id=None):
        if not name.strip():
            raise AccountError('Enter your name.')
        if not re.fullmatch(r'[A-Za-z0-9_.]{3,20}', username):
            raise AccountError('Username must be 3-20 letters, numbers, _ or .')
        if not EMAIL_RE.match(email):
            raise AccountError('Enter a valid email address.')
        if password is not None and len(password) < MIN_PASSWORD:
            raise AccountError(f'Password must be at least {MIN_PASSWORD} characters.')
        for label, column, value in (('username', AccountRow.username_key, username.lower()),
                                     ('email', AccountRow.email, email)):
            found = db.scalar(select(AccountRow.id).where(column == value))
            if found is not None and found != ignore_id:
                raise AccountError(f'That {label} is already taken.')

    def _check_password(self, row, password):
        return hmac.compare_digest(_hash(password, row.salt), row.password_hash)

    def sign_up(self, name, username, email, password):
        name, username, email = name.strip(), username.strip(), email.strip().lower()
        with self._session() as db:
            self._validate(db, name, username, email, password)
            salt = secrets.token_bytes(16)
            row = AccountRow(name=name, username=username, username_key=username.lower(), email=email, salt=salt,
                             password_hash=_hash(password, salt), role='user', created_at=_now())
            db.add(row)
            db.commit()
            return row.to_account()

    def log_in(self, email, password):
        with self._session() as db:
            row = db.scalar(select(AccountRow).where(AccountRow.email == email.strip().lower()))
            if row is None or not self._check_password(row, password):
                raise AccountError('Incorrect email or password.')
            return row.to_account()

    def update_account(self, account, current_password, name, username, email, new_password=''):
        with self._session() as db:
            row = self._row(db, account.id)
            if not self._check_password(row, current_password):
                raise AccountError('Current password is incorrect.')
            name, username, email = name.strip(), username.strip(), email.strip().lower()
            self._validate(db, name, username, email, new_password or None, ignore_id=account.id)
            row.name, row.username, row.username_key, row.email = name, username, username.lower(), email
            if new_password:
                row.salt = secrets.token_bytes(16)
                row.password_hash = _hash(new_password, row.salt)
            db.commit()
            return row.to_account()

    def _highest_won(self, db, account_id):
        won = set(db.scalars(select(RunRow.difficulty).where(RunRow.account_id == account_id, RunRow.won.is_(True))))
        return max((i for i, name in enumerate(DIFFICULTY_NAMES) if name in won), default=-1)

    def _unlocked(self, db, account_id):
        return unlocked_for(self._row(db, account_id).role, self._highest_won(db, account_id))

    def unlocked_difficulties(self, account):
        with self._session() as db:
            return self._unlocked(db, account.id)

    def record_run(self, account, result):
        if result.difficulty not in DIFFICULTY_NAMES:
            raise AccountError('Unknown difficulty.')
        with self._session() as db:
            before = self._unlocked(db, account.id)
            if result.difficulty not in before:
                raise AccessDenied(f'{result.difficulty} is locked for this account.')
            db.add(RunRow(account_id=account.id, difficulty=result.difficulty, won=bool(result.won),
                          score=int(result.score), time_seconds=float(result.time_seconds),
                          lives_lost=int(result.lives_lost), waves_cleared=int(result.waves_cleared),
                          kills=int(result.kills), played_at=_now()))
            db.commit()
            return tuple(name for name in self._unlocked(db, account.id) if name not in before)

    def leaderboard(self, kind, difficulty=None, limit=LEADERBOARD_SIZE):
        if kind not in LEADERBOARD_KINDS:
            raise ValueError(f'Unknown leaderboard: {kind}')
        value_name, order, only_wins = LEADERBOARD_ORDER[kind]

        def ordering(table):
            cols = [table.c[name].desc() if desc else table.c[name].asc() for name, desc in order]
            return cols+[table.c.played_at.asc(), table.c.run_id.asc()]

        runs = select(AccountRow.username, RunRow.score, RunRow.time_seconds, RunRow.lives_lost, RunRow.difficulty,
                      RunRow.played_at, RunRow.id.label('run_id'), RunRow.account_id).join(
                          AccountRow, AccountRow.id == RunRow.account_id)
        if only_wins:
            runs = runs.where(RunRow.won.is_(True))
        if difficulty is not None:
            runs = runs.where(RunRow.difficulty == difficulty)
        runs = runs.subquery()
        ranked = select(runs, func.row_number().over(partition_by=runs.c.account_id,
                                                     order_by=ordering(runs)).label('pick')).subquery()
        query = (select(ranked.c.username, ranked.c[value_name], ranked.c.difficulty, ranked.c.played_at)
                 .where(ranked.c.pick == 1).order_by(*ordering(ranked)).limit(limit))
        with self._session() as db:
            rows = db.execute(query).all()
        return [LeaderboardEntry(i+1, *row) for i, row in enumerate(rows)]

    def list_accounts(self, requester):
        with self._session() as db:
            self._require_admin(db, requester)
            rows = db.execute(
                select(AccountRow, func.coalesce(func.max(RunRow.score), 0), func.count(RunRow.id))
                .outerjoin(RunRow, RunRow.account_id == AccountRow.id).group_by(AccountRow.id)
                .order_by((AccountRow.role == 'admin').desc(), AccountRow.username_key)).all()
            return [AccountSummary(row.to_account(), unlocked_for(row.role, self._highest_won(db, row.id)), best, played,
                                   row.created_at or '') for row, best, played in rows]

    def set_role(self, requester, account_id, role):
        with self._session() as db:
            self._require_admin(db, requester)
            if role not in ROLES:
                raise AccountError('Unknown role.')
            if account_id == requester.id and role != 'admin':
                raise AccountError('You cannot remove your own admin role.')
            row = self._row(db, account_id)
            row.role = role
            db.commit()
            return row.to_account()

    def promote_by_email(self, email):
        with self._session() as db:
            row = db.scalar(select(AccountRow).where(AccountRow.email == email.strip().lower()))
            if row is None:
                raise AccountError(f'No account with email {email}.')
            row.role = 'admin'
            db.commit()
            return row.to_account()

    def issue_token(self, account):
        token = secrets.token_urlsafe(32)
        with self._session() as db:
            db.add(TokenRow(token_key=_token_key(token), account_id=account.id, created_at=_now()))
            db.commit()
        return token

    def account_for_token(self, token):
        with self._session() as db:
            row = db.get(TokenRow, _token_key(token))
            if row is None:
                return None
            issued = datetime.strptime(row.created_at, TIME_FORMAT).replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc)-issued > TOKEN_LIFETIME:
                db.delete(row)
                db.commit()
                return None
            return self._row(db, row.account_id).to_account()

    def revoke_token(self, token):
        with self._session() as db:
            row = db.get(TokenRow, _token_key(token))
            if row is not None:
                db.delete(row)
                db.commit()

    def stored_password_hashes(self):
        with self._session() as db:
            return list(db.scalars(select(AccountRow.password_hash)))
