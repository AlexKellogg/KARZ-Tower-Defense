from abc import ABC, abstractmethod
from dataclasses import dataclass

DIFFICULTY_NAMES = ('Easy', 'Medium', 'Hard', 'Impossible')
ROLES = ('user', 'admin')
LEADERBOARD_KINDS = ('score', 'time', 'lives')
LEADERBOARD_SIZE = 25


class AccountError(ValueError):
    pass


class AccessDenied(PermissionError):
    pass


@dataclass(frozen=True)
class Account:
    id: int
    name: str
    username: str
    email: str
    role: str = 'user'

    @property
    def is_admin(self):
        return self.role == 'admin'


@dataclass(frozen=True)
class RunResult:
    difficulty: str
    won: bool
    score: int
    time_seconds: float
    lives_lost: int
    waves_cleared: int
    kills: int


@dataclass(frozen=True)
class AccountSummary:
    account: Account
    unlocked: tuple
    best_score: int
    games_played: int
    joined: str


@dataclass(frozen=True)
class LeaderboardEntry:
    rank: int
    username: str
    value: float
    difficulty: str
    played_at: str


def unlocked_for(role, highest_won_index):
    if role == 'admin':
        return DIFFICULTY_NAMES
    return DIFFICULTY_NAMES[:min(len(DIFFICULTY_NAMES), highest_won_index+2)]


class Backend(ABC):
    @abstractmethod
    def sign_up(self, name, username, email, password):
        """Create a regular user. Returns Account. Raises AccountError."""

    @abstractmethod
    def log_in(self, email, password):
        """Returns Account. Raises AccountError."""

    @abstractmethod
    def update_account(self, account, current_password, name, username, email, new_password=''):
        """Returns the updated Account. Raises AccountError."""

    @abstractmethod
    def unlocked_difficulties(self, account):
        """Returns the difficulty names this account may play, in order."""

    @abstractmethod
    def record_run(self, account, result):
        """Saves a finished game. Returns the names of difficulties newly unlocked by it. Raises AccessDenied."""

    @abstractmethod
    def leaderboard(self, kind, difficulty=None, limit=LEADERBOARD_SIZE):
        """kind is 'score', 'time', or 'lives'. One entry per player (their best). Returns list of LeaderboardEntry."""

    @abstractmethod
    def list_accounts(self, requester):
        """Admins only. Returns list of AccountSummary. Raises AccessDenied for regular users."""

    @abstractmethod
    def set_role(self, requester, account_id, role):
        """Admins only. Returns the updated Account. Raises AccessDenied."""
