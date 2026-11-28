from math import hypot


# Placeholder enemy, replace with the real KARZ enemy later.
class PlaceholderEnemy:
    # Placeholder hp, speed, and reward values, change later.
    def __init__(self, waypoints, hp=30, speed=90, reward=5):
        if len(waypoints) < 2:
            raise ValueError('An enemy route needs at least two waypoints.')
        self.waypoints = [tuple(p) for p in waypoints]
        self.lengths = [hypot(bx-ax, by-ay) for (ax, ay), (bx, by) in zip(self.waypoints, self.waypoints[1:])]
        self.total = sum(self.lengths)
        self.max_hp = hp
        self.hp = hp
        self.speed = speed
        self.reward = reward
        self.progress = 0.0
        self.reached_end = False
        self.slow_factor = 1.0
        self.slow_remaining = 0.0

    def apply_slow(self, factor, duration):
        # Strongest effect wins; equal-strength hits refresh, never multiply slows.
        if self.slow_remaining <= 0 or factor < self.slow_factor:
            self.slow_factor, self.slow_remaining = factor, duration
        elif factor == self.slow_factor:
            self.slow_remaining = max(self.slow_remaining,duration)

    @property
    def alive(self):
        return self.hp > 0 and not self.reached_end

    @property
    def pos(self):
        remaining = self.progress
        for (ax, ay), (bx, by), length in zip(self.waypoints, self.waypoints[1:], self.lengths):
            if remaining <= length:
                t = remaining/length if length else 0
                return ax+(bx-ax)*t, ay+(by-ay)*t
            remaining -= length
        return self.waypoints[-1]

    def update(self, dt):
        if not self.alive:
            return
        slowed = min(dt,self.slow_remaining)
        distance = self.speed*(slowed*self.slow_factor+dt-slowed)
        self.slow_remaining = max(0.0,self.slow_remaining-dt)
        if self.slow_remaining == 0:
            self.slow_factor = 1.0
        self.progress = min(self.total, self.progress+distance)
        if self.progress >= self.total:
            self.reached_end = True

    def take_damage(self, amount):
        if not self.alive:
            return False
        self.hp = max(0, self.hp-amount)
        return self.hp == 0

