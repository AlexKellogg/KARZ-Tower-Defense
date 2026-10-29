from dataclasses import dataclass
from math import hypot


@dataclass(frozen=True)
class TowerLevel:
    range: float
    damage: float
    fire_rate: float


# Placeholder stats, tune after playtesting. Upgrades are free for now; add costs once the economy exists.
BASE_TOWER_LEVELS = (
    TowerLevel(range=110, damage=5, fire_rate=1.5),
    TowerLevel(range=130, damage=8, fire_rate=2.0),
    TowerLevel(range=150, damage=12, fire_rate=2.5),
)


class Tower:
    def __init__(self, x, y, radius=16, levels=BASE_TOWER_LEVELS):
        self.x, self.y, self.radius = x, y, radius
        self.levels = levels
        self.level = 0
        self.cooldown = 0.0
        self.target = None
        self.aim = (1.0, 0.0)

    @property
    def stats(self):
        return self.levels[self.level]

    @property
    def footprint(self):
        return self.x, self.y, self.radius

    @property
    def can_upgrade(self):
        return self.level < len(self.levels)-1

    def upgrade(self):
        if not self.can_upgrade:
            return False
        self.level += 1
        return True

    def contains(self, px, py):
        return hypot(px-self.x, py-self.y) <= self.radius

    def in_range(self, enemy):
        ex, ey = enemy.pos
        return hypot(ex-self.x, ey-self.y) <= self.stats.range

    def pick_target(self, enemies, targetable=None):
        candidates = [e for e in enemies if e.alive and self.in_range(e)
                      and (targetable is None or targetable(e))]
        return max(candidates, key=lambda e: e.progress, default=None)

    def update(self, dt, enemies, targetable=None):
        self.cooldown = max(0.0, self.cooldown-dt)
        self.target = self.pick_target(enemies, targetable)
        if self.target is None:
            return None
        ex, ey = self.target.pos
        dist = hypot(ex-self.x, ey-self.y)
        if dist:
            self.aim = ((ex-self.x)/dist, (ey-self.y)/dist)
        if self.cooldown > 0:
            return None
        self.cooldown = 1/self.stats.fire_rate
        self.target.take_damage(self.stats.damage)
        return self.target
