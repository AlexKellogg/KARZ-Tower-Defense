from dataclasses import dataclass
from math import hypot


@dataclass(frozen=True)
class TowerLevel:
    range: float
    damage: float
    fire_rate: float
    slow_factor: float = 1.0
    slow_duration: float = 0.0
    splash_radius: float = 0.0


# Local playtest values; three simple linear upgrade paths.
BASE_TOWER_LEVELS = (
    TowerLevel(range=110, damage=5, fire_rate=1.5),
    TowerLevel(range=130, damage=8, fire_rate=2.0),
    TowerLevel(range=150, damage=12, fire_rate=2.5),
)


@dataclass(frozen=True)
class TowerType:
    name: str
    cost: int
    upgrade_costs: tuple
    description: str
    levels: tuple


TOWER_TYPES = {
    'cannon': TowerType('Cannon', 50, (40,70), 'Reliable single-target damage.', BASE_TOWER_LEVELS),
    'cryo': TowerType('Cryo', 60, (45,70), 'Slows targets; pair with damage towers.', (
        TowerLevel(120,2,1.5,.65,1.8), TowerLevel(140,3,1.8,.55,2.2), TowerLevel(155,5,2.0,.5,2.5))),
    'mortar': TowerType('Mortar', 80, (55,85), 'Slow shots damage nearby groups.', (
        TowerLevel(135,14,.75,splash_radius=48), TowerLevel(150,22,.9,splash_radius=58),
        TowerLevel(165,32,1.0,splash_radius=68))),
}


class Tower:
    def __init__(self, x, y, radius=16, levels=None, tower_type='cannon'):
        if tower_type not in TOWER_TYPES:
            raise ValueError('Unknown tower type')
        self.tower_type = tower_type
        self.spec = TOWER_TYPES[tower_type]
        self.x, self.y, self.radius = x, y, radius
        self.levels = self.spec.levels if levels is None else levels
        self.level = 0
        self.cooldown = 0.0
        self.target = None
        self.aim = (1.0, 0.0)
        self.last_hits = []

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
        return min(candidates, key=lambda e: (e.total-e.progress)/max(e.speed,1e-9), default=None)

    def update(self, dt, enemies, targetable=None):
        self.last_hits = []
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
        victims = [self.target]
        if self.stats.splash_radius:
            victims = [e for e in enemies if e.alive
                       and hypot(e.pos[0]-ex,e.pos[1]-ey) <= self.stats.splash_radius
                       and (targetable is None or targetable(e))]
        for enemy in victims:
            enemy.take_damage(self.stats.damage)
            if self.stats.slow_duration and enemy.alive:
                enemy.apply_slow(self.stats.slow_factor,self.stats.slow_duration)
        self.last_hits = victims
        return self.target
