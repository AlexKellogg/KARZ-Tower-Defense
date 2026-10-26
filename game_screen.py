from pathlib import Path

import pygame

import ui
from backend import DIFFICULTY_NAMES
from enemy import PlaceholderEnemy
from game_session import TOTAL_WAVES, GameClock, GameSession, format_time
from map_runtime import load_map
from tower import BASE_TOWER_LEVELS, Tower

MAP_PATH = Path(__file__).parent/'maps'/'desert_highway.tmx'
MAP_IMAGE = Path(__file__).parent/'maps'/'desert_highway.png'

# Placeholder: every difficulty uses the same map for now, change later.
DIFFICULTY_STYLE = {
    'Easy': ((56, 160, 110), 'Relaxed waves to learn the basics.'),
    'Medium': ((220, 160, 50), 'Tougher enemies, tighter economy.'),
    'Hard': ((226, 108, 64), 'Fast waves that punish weak setups.'),
    'Impossible': ((150, 70, 170), 'Only for perfect strategies.'),
}
DIFFICULTIES = tuple({'name': name, 'color': DIFFICULTY_STYLE[name][0], 'blurb': DIFFICULTY_STYLE[name][1]}
                     for name in DIFFICULTY_NAMES)

SHOT_FLASH = 0.08
TOWER_RADIUS = 16
LEVEL_COLORS = ((133, 185, 209), (120, 200, 140), (235, 190, 80))
MAP_SIZE = (960, 576)
WIN_COLOR = (56, 160, 110)
LOSS_COLOR = (196, 64, 82)
PLACE_OK = (60, 210, 120)
PLACE_BLOCKED = (235, 70, 70)
SANDBOX_COLOR = (62, 132, 196)


def draw_tower(surface, tower, selected):
    P = ui.px
    x, y, r = P(tower.x), P(tower.y), P(tower.radius)
    ax, ay = tower.aim
    pygame.draw.circle(surface, (44, 64, 80), (x, y), r)
    pygame.draw.circle(surface, LEVEL_COLORS[tower.level % len(LEVEL_COLORS)], (x, y), r-P(4))
    pygame.draw.line(surface, (44, 64, 80), (x, y), (x+ax*(r+P(6)), y+ay*(r+P(6))), P(6))
    for i in range(tower.level+1):
        pygame.draw.circle(surface, (250, 245, 230), (x+P(i*8-tower.level*4), y+r+P(5)), P(3))
    if selected:
        pygame.draw.circle(surface, (255, 255, 255), (x, y), r+P(3), P(2))


def draw_range(surface, x, y, rng, color):
    P = ui.px
    overlay = pygame.Surface((P(MAP_SIZE[0]), P(MAP_SIZE[1])), pygame.SRCALPHA)
    pygame.draw.circle(overlay, (*color, 40), (P(x), P(y)), P(rng))
    pygame.draw.circle(overlay, (*color, 140), (P(x), P(y)), P(rng), P(2))
    surface.blit(overlay, (0, 0))


def draw_placement(surface, x, y, ok):
    P = ui.px
    color = PLACE_OK if ok else PLACE_BLOCKED
    if ok:
        draw_range(surface, x, y, BASE_TOWER_LEVELS[0].range, color)
    overlay = pygame.Surface((P(TOWER_RADIUS*2+8), P(TOWER_RADIUS*2+8)), pygame.SRCALPHA)
    c = overlay.get_width()//2
    pygame.draw.circle(overlay, (*color, 110), (c, c), P(TOWER_RADIUS))
    pygame.draw.circle(overlay, (*color, 255), (c, c), P(TOWER_RADIUS), P(2))
    if not ok:
        d = P(6)
        pygame.draw.line(overlay, (255, 255, 255, 235), (c-d, c-d), (c+d, c+d), P(3))
        pygame.draw.line(overlay, (255, 255, 255, 235), (c-d, c+d), (c+d, c-d), P(3))
    surface.blit(overlay, (P(x)-c, P(y)-c))


class GameScreen:
    def __init__(self, difficulty, on_exit, on_finish=None, sandbox=False):
        self.difficulty = difficulty
        self.sandbox = sandbox
        self.on_exit = on_exit
        self.on_finish = on_finish
        self.map = load_map(MAP_PATH)
        self.art = pygame.transform.smoothscale(self.map.artwork, (ui.px(MAP_SIZE[0]), ui.px(MAP_SIZE[1])))
        self.upgrade_button = pygame.Rect(790, 586, 155, 44)
        self.menu_button = pygame.Rect(676, 586, 104, 44)
        self.pause_button = pygame.Rect(564, 586, 50, 44)
        self.speed_button = pygame.Rect(620, 586, 50, 44)
        self.levels_button = ui.Button((330, 418, 142, 44), 'Levels', 'secondary')
        self.again_button = ui.Button((488, 418, 142, 44), 'Play again')
        self.restart()

    def restart(self):
        self.session = GameSession(self.difficulty['name'], sandbox=self.sandbox)
        self.clock = GameClock()
        self.towers, self.enemies, self.shots = [], [], []
        self.selected = None
        self.show_zones = False
        self.result = None
        self.unlocked = ()
        self.save_error = ''

    def footprints(self):
        return [t.footprint for t in self.towers]

    def try_upgrade(self):
        if self.selected is not None:
            self.selected.upgrade()

    def finish(self):
        self.result = self.session.result()
        self.selected = None
        if self.on_finish is None or self.sandbox:
            return
        try:
            self.unlocked = tuple(self.on_finish(self.result) or ())
        except Exception as e:
            self.save_error = f'Score not saved: {e}'

    def handle(self, event):
        if self.result is not None:
            if self.levels_button.clicked(event) or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                self.on_exit()
            elif self.again_button.clicked(event) or (event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN):
                self.restart()
            return
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.on_exit()
            elif event.key in (pygame.K_SPACE, pygame.K_p):
                self.clock.toggle_pause()
            elif event.key == pygame.K_f:
                self.clock.cycle_speed()
            elif event.key == pygame.K_b:
                self.show_zones = not self.show_zones
            elif event.key == pygame.K_u:
                self.try_upgrade()
            elif event.key == pygame.K_n and self.sandbox:
                self.session.skip_break()
            elif event.key == pygame.K_z and self.towers:
                if self.towers.pop() is self.selected:
                    self.selected = None
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            self.selected = None
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            x, y = event.pos
            if self.menu_button.collidepoint(x, y):
                self.on_exit()
            elif self.pause_button.collidepoint(x, y):
                self.clock.toggle_pause()
            elif self.speed_button.collidepoint(x, y):
                self.clock.cycle_speed()
            elif self.upgrade_button.collidepoint(x, y):
                self.try_upgrade()
            else:
                clicked = next((t for t in self.towers if t.contains(x, y)), None)
                if clicked is not None:
                    self.selected = clicked
                elif self.map.can_place(x, y, TOWER_RADIUS, self.footprints()):
                    self.towers.append(Tower(x, y, TOWER_RADIUS))
                    self.selected = None
                else:
                    self.selected = None

    def update(self, dt):
        for step in self.clock.steps(dt):
            if self.result is not None:
                return
            self.step(step)

    def step(self, dt):
        for hp, speed in self.session.update(dt, len(self.enemies)):
            self.enemies.append(PlaceholderEnemy(self.map.waypoints, hp=hp, speed=speed))
        for enemy in self.enemies:
            enemy.update(dt)
        for tower in self.towers:
            hit = tower.update(dt, self.enemies)
            if hit is not None:
                muzzle = (tower.x+tower.aim[0]*(TOWER_RADIUS+6), tower.y+tower.aim[1]*(TOWER_RADIUS+6))
                self.shots.append([muzzle, hit.pos, SHOT_FLASH])
                if hit.hp == 0:
                    self.session.enemy_killed()
        for enemy in self.enemies:
            if enemy.reached_end:
                self.session.enemy_leaked()
        self.enemies = [e for e in self.enemies if e.alive]
        for shot in self.shots:
            shot[2] -= dt
        self.shots = [s for s in self.shots if s[2] > 0]
        if self.session.finished:
            self.finish()

    def draw_map(self, screen):
        P = ui.px
        screen.fill((26, 29, 34))
        screen.blit(self.art, (0, 0))
        if self.show_zones:
            overlay = pygame.Surface((P(MAP_SIZE[0]), P(MAP_SIZE[1])), pygame.SRCALPHA)
            for i, role in enumerate(self.map.roles):
                if role == 2:
                    pygame.draw.rect(overlay, (30, 170, 100, 75), ui.scaled((i % 20*48, i//20*48, 48, 48)))
            screen.blit(overlay, (0, 0))
        if self.selected is not None:
            draw_range(screen, self.selected.x, self.selected.y, self.selected.stats.range, (255, 255, 255))
        for enemy in self.enemies:
            ex, ey = enemy.pos
            pygame.draw.circle(screen, (35, 30, 25), (P(ex+2), P(ey+3)), P(9))
            pygame.draw.circle(screen, (232, 78, 53), (P(ex), P(ey)), P(8))
            pygame.draw.rect(screen, (60, 20, 20), ui.scaled((ex-9, ey-15, 18, 4)))
            pygame.draw.rect(screen, (90, 220, 110), (P(ex-9), P(ey-15), P(18*enemy.hp/enemy.max_hp), P(4)))
        for tower in self.towers:
            draw_tower(screen, tower, tower is self.selected)
        for (sx, sy), (tx, ty), _ in self.shots:
            pygame.draw.line(screen, (255, 235, 140), (P(sx), P(sy)), (P(tx), P(ty)), P(3))

    def draw_hud(self, screen, mx, my):
        s = self.session
        if self.sandbox:
            stats = f'Wave {max(1, s.wave)}   Leaked {s.leaked}   Kills {s.kills}   Money ∞'
        else:
            stats = f'Wave {max(1, s.wave)}/{TOTAL_WAVES}   Lives {s.lives}   Time {format_time(s.elapsed)}   Kills {s.kills}'
        ui.text(screen, stats, 15, (236, 233, 223), (18, 588), bold=True)
        chip = ui.chip(screen, self.difficulty['name'].upper(), self.difficulty['color'], (30+ui.text_width(stats, 15, True), 587))
        if self.sandbox:
            ui.chip(screen, 'SANDBOX', SANDBOX_COLOR, (chip.right+8, 587))
        if self.selected is not None:
            t = self.selected.stats
            info = f'Selected: level {self.selected.level+1}/{len(self.selected.levels)}   range {t.range:g}   dmg {t.damage:g}   rate {t.fire_rate:g}/s'
        else:
            info = 'Click: place / select   U: upgrade   Z: undo   Space: pause   F: speed   Esc: menu'
            if self.sandbox:
                info = 'Click: place / select   U: upgrade   Z: undo   N: next wave   Space: pause   F: speed   Esc: menu'
        ui.text(screen, info, 13, (189, 185, 175), (18, 614))
        self.draw_controls(screen, mx, my)
        hover = self.menu_button.collidepoint(mx, my)
        ui.rounded(screen, self.menu_button, (78, 82, 92) if hover else (60, 63, 70), 8)
        ui.text(screen, 'Menu', 15, (245, 245, 240), self.menu_button.center, bold=True, anchor='center')
        enabled = self.selected is not None and self.selected.can_upgrade
        hover = self.upgrade_button.collidepoint(mx, my)
        fill = ((70, 150, 95) if hover else (55, 125, 80)) if enabled else (60, 63, 70)
        ui.rounded(screen, self.upgrade_button, fill, 8)
        label = 'Max level' if self.selected is not None and not self.selected.can_upgrade else 'Upgrade (free)'
        ui.text(screen, label, 15, (245, 245, 240) if enabled else (140, 140, 145), self.upgrade_button.center, bold=True, anchor='center')
        if self.result is not None:
            return
        preview = s.next_wave()
        if s.between_waves:
            banner = f'Wave {s.wave+1} starting in {max(1, round(s.break_timer+0.49))}'
            if preview is not None:
                banner += f'   ·   {preview.count} enemies, {preview.hp} HP each'
            if self.sandbox:
                banner += '   ·   N to start now'
            width = ui.text_width(banner, 15, True)+40
            ui.rounded(screen, (480-width/2, 14, width, 34), (30, 50, 104, 225), 17)
            ui.text(screen, banner, 15, ui.WHITE, (480, 31), bold=True, anchor='center')
        elif preview is not None:
            label = f'Next: wave {preview.wave}  ·  {preview.count} × {preview.hp} HP'
            width = ui.text_width(label, 13, True)+28
            ui.rounded(screen, (MAP_SIZE[0]-width-12, 12, width, 28), (30, 50, 104, 200), 14)
            ui.text(screen, label, 13, ui.WHITE, (MAP_SIZE[0]-12-width/2, 26), bold=True, anchor='center')

    def draw_controls(self, screen, mx, my):
        P = ui.px
        paused = self.clock.paused
        for rect, active in ((self.pause_button, paused), (self.speed_button, self.clock.speed > 1)):
            hover = rect.collidepoint(mx, my)
            fill = (215, 160, 50) if active else ((78, 82, 92) if hover else (60, 63, 70))
            ui.rounded(screen, rect, fill, 8)
        cx, cy = self.pause_button.center
        if paused:
            pygame.draw.polygon(screen, (245, 245, 240), [(P(cx-6), P(cy-9)), (P(cx-6), P(cy+9)), (P(cx+9), P(cy))])
        else:
            for dx in (-6, 2):
                pygame.draw.rect(screen, (245, 245, 240), ui.scaled((cx+dx, cy-9, 5, 18)))
        ui.text(screen, f'{self.clock.speed}x', 15, (245, 245, 240), self.speed_button.center, bold=True, anchor='center')

    def draw_result(self, screen):
        r = self.result
        ui.dim(screen, (20, 14, 6, 140))
        ui.card(screen, (300, 120, 360, 364))
        won_color = WIN_COLOR if r.won else LOSS_COLOR
        ui.text(screen, 'Victory!' if r.won else 'Defeat', 32, won_color, (480, 168), bold=True, anchor='center')
        ui.chip(screen, self.difficulty['name'].upper(), self.difficulty['color'], (480, 196), anchor='midtop')
        rows = (('Score', f'{r.score:,}'), ('Time', format_time(r.time_seconds)), ('Lives lost', str(r.lives_lost)),
                ('Waves survived', f'{r.waves_cleared}/{TOTAL_WAVES}'), ('Kills', str(r.kills)))
        for i, (label, value) in enumerate(rows):
            y = 238+i*28
            ui.text(screen, label, 15, ui.MUTED, (340, y))
            ui.text(screen, value, 15, ui.NAVY, (620, y), bold=True, anchor='topright')
        if self.save_error:
            ui.text(screen, self.save_error, 13, ui.ERROR, (480, 390), anchor='center')
        elif self.unlocked:
            ui.rounded(screen, (340, 378, 280, 28), (232, 244, 236), 14)
            ui.text(screen, f'New level unlocked: {", ".join(self.unlocked)}', 13, WIN_COLOR, (480, 392), bold=True, anchor='center')
        self.levels_button.draw(screen)
        self.again_button.draw(screen)

    def draw(self, screen):
        self.draw_map(screen)
        mx, my = ui.mouse_pos()
        if self.result is None:
            over_tower = any(t.contains(mx, my) for t in self.towers)
            if 0 <= mx < MAP_SIZE[0] and 0 <= my < MAP_SIZE[1] and not over_tower:
                draw_placement(screen, mx, my, self.map.can_place(mx, my, TOWER_RADIUS, self.footprints()))
        if self.clock.paused and self.result is None:
            ui.dim(screen, (20, 14, 6, 90))
            ui.rounded(screen, (380, 250, 200, 76), (30, 50, 104, 235), 16)
            ui.text(screen, 'Paused', 26, ui.WHITE, (480, 278), bold=True, anchor='center')
            ui.text(screen, 'Space to resume', 13, (214, 226, 248), (480, 306), anchor='center')
        self.draw_hud(screen, mx, my)
        if self.result is not None:
            self.draw_result(screen)
