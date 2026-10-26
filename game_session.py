from dataclasses import dataclass

from backend import RunResult

# Placeholder wave, lives, and scoring values, tune after playtesting.
STARTING_LIVES = 20
TOTAL_WAVES = 5
FIRST_WAVE_DELAY = 2.0
WAVE_BREAK = 3.0
SPAWN_GAP = 0.8
BASE_HP = 20
HP_PER_WAVE = 4
BASE_SPEED = 80
POINTS_PER_KILL = 10
POINTS_PER_LIFE_LEFT = 25
SPEEDS = (1, 2, 3)


@dataclass(frozen=True)
class WavePreview:
    wave: int
    count: int
    hp: int
    speed: float


@dataclass(frozen=True)
class DifficultyRules:
    hp_multiplier: float
    speed_multiplier: float
    score_multiplier: float


# Placeholder difficulty multipliers, tune after playtesting.
RULES = {
    'Easy': DifficultyRules(1.0, 1.0, 1.0),
    'Medium': DifficultyRules(1.4, 1.1, 1.5),
    'Hard': DifficultyRules(1.9, 1.2, 2.0),
    'Impossible': DifficultyRules(2.6, 1.35, 3.0),
}


def wave_size(wave):
    return 6+2*wave


def format_time(seconds):
    seconds = int(seconds)
    return f'{seconds//60}:{seconds % 60:02d}'


class GameSession:
    def __init__(self, difficulty, sandbox=False):
        self.difficulty = difficulty
        self.sandbox = sandbox
        self.rules = RULES[difficulty]
        self.lives = STARTING_LIVES
        self.wave = 0
        self.waves_cleared = 0
        self.to_spawn = 0
        self.spawn_timer = 0.0
        self.break_timer = FIRST_WAVE_DELAY
        self.elapsed = 0.0
        self.kills = 0
        self.leaked = 0
        self.status = 'playing'

    @property
    def finished(self):
        return self.status != 'playing'

    @property
    def between_waves(self):
        return not self.finished and self.to_spawn == 0 and self.wave == self.waves_cleared

    def enemy_stats(self, wave=None):
        wave = self.wave if wave is None else wave
        hp = round((BASE_HP+HP_PER_WAVE*wave)*self.rules.hp_multiplier)
        return hp, BASE_SPEED*self.rules.speed_multiplier

    def next_wave(self):
        upcoming = self.wave+1
        if self.finished or (not self.sandbox and upcoming > TOTAL_WAVES):
            return None
        hp, speed = self.enemy_stats(upcoming)
        return WavePreview(upcoming, wave_size(upcoming), hp, speed)

    def update(self, dt, enemies_alive):
        if self.finished:
            return []
        self.elapsed += dt
        spawns = []
        if self.to_spawn > 0:
            self.spawn_timer -= dt
            while self.to_spawn > 0 and self.spawn_timer <= 0:
                spawns.append(self.enemy_stats())
                self.to_spawn -= 1
                self.spawn_timer += SPAWN_GAP
        elif enemies_alive == 0:
            if self.wave > self.waves_cleared:
                self.waves_cleared = self.wave
                self.break_timer = WAVE_BREAK
                if not self.sandbox and self.waves_cleared == TOTAL_WAVES:
                    self.status = 'won'
                    return []
            self.break_timer -= dt
            if self.break_timer <= 0:
                self.wave += 1
                self.to_spawn = wave_size(self.wave)
                self.spawn_timer = 0.0
        return spawns

    def enemy_killed(self):
        if not self.finished:
            self.kills += 1

    def skip_break(self):
        if self.between_waves:
            self.break_timer = 0.0

    def enemy_leaked(self):
        if self.finished:
            return
        self.leaked += 1
        if self.sandbox:
            return
        self.lives = max(0, self.lives-1)
        if self.lives == 0:
            self.status = 'lost'

    @property
    def score(self):
        points = self.kills*POINTS_PER_KILL
        if self.status == 'won':
            points += self.lives*POINTS_PER_LIFE_LEFT
        return round(points*self.rules.score_multiplier)

    def result(self):
        return RunResult(self.difficulty, self.status == 'won', self.score, round(self.elapsed, 1),
                         self.leaked, self.waves_cleared, self.kills)


class GameClock:
    def __init__(self):
        self.paused = False
        self.speed = SPEEDS[0]

    def toggle_pause(self):
        self.paused = not self.paused

    def cycle_speed(self):
        self.speed = SPEEDS[(SPEEDS.index(self.speed)+1) % len(SPEEDS)]

    def steps(self, dt):
        if self.paused:
            return []
        return [dt]*self.speed
