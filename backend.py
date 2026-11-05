import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from numbers import Real

DIFFICULTY_NAMES = ('Easy', 'Medium', 'Hard', 'Impossible')
ROLES = ('user', 'admin')
LEADERBOARD_KINDS = ('score', 'time', 'lives', 'waves')
MODES = ('regular', 'sandbox')
LEADERBOARD_SIZE = 25


class AccountError(ValueError):
    pass


class AccessDenied(PermissionError):
    pass


class ScoreQueued(AccountError):
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
    sandbox: bool = False

    @property
    def mode(self):
        return 'sandbox' if self.sandbox else 'regular'


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


CHECKPOINT_VERSION = 1
MAX_CHECKPOINT_BYTES = 20_000
MAX_CHECKPOINT_TOWERS = 300
CHECKPOINT_NUMBERS = {'wave': (1, 1000), 'lives': (0, 1000), 'kills': (0, 10**7), 'leaked': (0, 10**7),
                      'money': (0, 10**9), 'elapsed': (0, 10**7)}


def checkpoint_json(difficulty, mode, state):
    if difficulty not in DIFFICULTY_NAMES:
        raise AccountError('Unknown difficulty.')
    if mode not in MODES:
        raise AccountError('Unknown mode.')
    invalid = AccountError('Saved game is invalid.')
    if not isinstance(state, dict) or state.get('version') != CHECKPOINT_VERSION:
        raise invalid
    for key, (low, high) in CHECKPOINT_NUMBERS.items():
        value = state.get(key)
        if isinstance(value, bool) or not isinstance(value, Real) or not low <= value <= high:
            raise invalid
    towers = state.get('towers')
    if not isinstance(towers, list) or len(towers) > MAX_CHECKPOINT_TOWERS:
        raise invalid
    for tower in towers:
        if not isinstance(tower, dict) or set(tower) != {'x', 'y', 'level'}:
            raise invalid
        if not all(isinstance(tower[k], Real) and not isinstance(tower[k], bool) for k in tower):
            raise invalid
        if not (0 <= tower['x'] <= 960 and 0 <= tower['y'] <= 576 and 0 <= tower['level'] <= 10):
            raise invalid
    text = json.dumps(state, sort_keys=True)
    if len(text) > MAX_CHECKPOINT_BYTES:
        raise invalid
    return text


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
    def leaderboard(self, kind, difficulty=None, limit=LEADERBOARD_SIZE, mode='regular'):
        """kind is 'score', 'time', 'lives' or 'waves'; mode is 'regular' or 'sandbox'. One entry per player (their best)."""

    @abstractmethod
    def list_accounts(self, requester):
        """Admins only. Returns list of AccountSummary. Raises AccessDenied for regular users."""

    @abstractmethod
    def set_role(self, requester, account_id, role):
        """Admins only. Returns the updated Account. Raises AccessDenied."""

    @abstractmethod
    def save_checkpoint(self, account, difficulty, mode, state):
        """Keeps the game state reached after a cleared wave, replacing any earlier one for that level and mode."""

    @abstractmethod
    def load_checkpoint(self, account, difficulty, mode):
        """Returns the saved state dict, or None."""

    @abstractmethod
    def clear_checkpoint(self, account, difficulty, mode):
        """Removes the saved state for that level and mode, if any."""
