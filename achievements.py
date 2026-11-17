"""Achievement definitions and the per-game tracker that decides when they unlock.

Achievements only unlock in regular games: sandbox towers are free and money is infinite,
so tower and gold goals would be meaningless there.
"""
from dataclasses import dataclass, field

HARD_DIFFICULTIES = ('Hard', 'Impossible')


@dataclass(frozen=True)
class Achievement:
    id: str
    name: str
    description: str
    stat: str
    goal: int = 1


# Placeholder goals, tune after playtesting. Ids are saved in the database, so never rename one.
ACHIEVEMENTS = (
    Achievement('first_win', 'First Victory', 'Win your first game.', 'wins'),
    Achievement('flawless', 'Untouchable', 'Clear every wave on a map without losing a life.', 'flawless_wins'),
    Achievement('hard_win', 'Razorback Conqueror', 'Beat a Hard map.', 'hard_wins'),
    Achievement('survivor', 'Survivor', 'Clear 5 waves in one game.', 'waves_cleared', 5),
    Achievement('builder', 'Builder', 'Have 10 towers on the map at once.', 'towers_on_map', 10),
    Achievement('fully_loaded', 'Fully Loaded', 'Upgrade a tower to its max level.', 'max_tower_level', 3),
    Achievement('gold_rush', 'Gold Rush', 'Earn $400 from kills in one game.', 'gold_earned', 400),
    Achievement('big_spender', 'Big Spender', 'Spend $500 in one game.', 'gold_spent', 500),
)
ACHIEVEMENT_IDS = tuple(a.id for a in ACHIEVEMENTS)
BY_ID = {a.id: a for a in ACHIEVEMENTS}


@dataclass
class Progress:
    towers_on_map: int = 0
    max_tower_level: int = 0
    waves_cleared: int = 0
    gold_earned: int = 0
    gold_spent: int = 0
    wins: int = 0
    flawless_wins: int = 0
    hard_wins: int = 0


@dataclass
class AchievementTracker:
    """Watches one game. `already` holds ids the player unlocked before; `new` collects ones unlocked this game."""
    already: frozenset = frozenset()
    enabled: bool = True
    progress: Progress = field(default_factory=Progress)
    new: list = field(default_factory=list)

    def __post_init__(self):
        self.already = frozenset(self.already)

    @property
    def unlocked(self):
        return self.already | {a.id for a in self.new}

    def _check(self):
        if not self.enabled:
            return []
        found = [a for a in ACHIEVEMENTS
                 if a.id not in self.unlocked and getattr(self.progress, a.stat) >= a.goal]
        self.new.extend(found)
        return found

    # Hooks called by the game screen. Each returns the achievements it just unlocked.
    def tower_built(self, towers_on_map):
        self.progress.towers_on_map = max(self.progress.towers_on_map, towers_on_map)
        return self._check()

    def tower_upgraded(self, tower):
        self.progress.max_tower_level = max(self.progress.max_tower_level, tower.level+1)
        return self._check()

    def wave_cleared(self, waves_cleared):
        self.progress.waves_cleared = max(self.progress.waves_cleared, waves_cleared)
        return self._check()

    def economy_changed(self, economy):
        self.progress.gold_earned = economy.earned
        self.progress.gold_spent = economy.spent
        return self._check()

    def game_won(self, difficulty, lives_lost):
        self.progress.wins = 1
        if lives_lost == 0:
            self.progress.flawless_wins = 1
        if difficulty in HARD_DIFFICULTIES:
            self.progress.hard_wins = 1
        return self._check()
