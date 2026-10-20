from pathlib import Path

import pygame

import ui
from enemy import PlaceholderEnemy
from map_runtime import load_map
from tower import BASE_TOWER_LEVELS, Tower

MAP_PATH = Path(__file__).parent/'maps'/'desert_highway.tmx'
MAP_IMAGE = Path(__file__).parent/'maps'/'desert_highway.png'

# Placeholder: every difficulty uses the same map and enemy stats for now, change later.
DIFFICULTIES = (
    {'name': 'Easy', 'color': (56, 160, 110), 'blurb': 'Relaxed waves to learn the basics.'},
    {'name': 'Medium', 'color': (220, 160, 50), 'blurb': 'Tougher enemies, tighter economy.'},
    {'name': 'Hard', 'color': (226, 108, 64), 'blurb': 'Fast waves that punish weak setups.'},
    {'name': 'Impossible', 'color': (150, 70, 170), 'blurb': 'Only for perfect strategies.'},
)

# Placeholder spawn rate, change later.
SPAWN_INTERVAL = 1.0
SHOT_FLASH = 0.08
TOWER_RADIUS = 16
LEVEL_COLORS = ((133, 185, 209), (120, 200, 140), (235, 190, 80))
MAP_SIZE = (960, 576)


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


class GameScreen:
    def __init__(self, difficulty, on_exit):
        self.difficulty = difficulty
        self.on_exit = on_exit
        self.map = load_map(MAP_PATH)
        self.art = pygame.transform.smoothscale(self.map.artwork, (ui.px(MAP_SIZE[0]), ui.px(MAP_SIZE[1])))
        self.upgrade_button = pygame.Rect(790, 586, 155, 44)
        self.menu_button = pygame.Rect(676, 586, 104, 44)
        self.towers, self.enemies, self.shots = [], [], []
        self.selected = None
        self.show_zones = False
        self.spawn_timer = 0.0
        self.spawned = self.kills = self.leaked = 0

    def footprints(self):
        return [t.footprint for t in self.towers]

    def try_upgrade(self):
        if self.selected is not None:
            self.selected.upgrade()

    def handle(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.on_exit()
            elif event.key == pygame.K_b:
                self.show_zones = not self.show_zones
            elif event.key == pygame.K_u:
                self.try_upgrade()
            elif event.key == pygame.K_z and self.towers:
                if self.towers.pop() is self.selected:
                    self.selected = None
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            self.selected = None
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            x, y = event.pos
            if self.menu_button.collidepoint(x, y):
                self.on_exit()
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
        self.spawn_timer -= dt
        if self.spawn_timer <= 0:
            self.spawn_timer = SPAWN_INTERVAL
            self.spawned += 1
            # Placeholder enemy health and speed, change later.
            self.enemies.append(PlaceholderEnemy(self.map.waypoints, hp=20+self.spawned*2, speed=80))
        for enemy in self.enemies:
            enemy.update(dt)
        for tower in self.towers:
            hit = tower.update(dt, self.enemies)
            if hit is not None:
                muzzle = (tower.x+tower.aim[0]*(TOWER_RADIUS+6), tower.y+tower.aim[1]*(TOWER_RADIUS+6))
                self.shots.append([muzzle, hit.pos, SHOT_FLASH])
                if hit.hp == 0:
                    self.kills += 1
        self.leaked += sum(1 for e in self.enemies if e.reached_end)
        self.enemies = [e for e in self.enemies if e.alive]
        for shot in self.shots:
            shot[2] -= dt
        self.shots = [s for s in self.shots if s[2] > 0]

    def draw(self, screen):
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

        mx, my = pygame.mouse.get_pos()
        over_tower = any(t.contains(mx, my) for t in self.towers)
        if 0 <= mx < MAP_SIZE[0] and 0 <= my < MAP_SIZE[1] and not over_tower:
            ok = self.map.can_place(mx, my, TOWER_RADIUS, self.footprints())
            color = (60, 210, 120) if ok else (245, 78, 78)
            if ok:
                draw_range(screen, mx, my, BASE_TOWER_LEVELS[0].range, color)
            pygame.draw.circle(screen, color, (P(mx), P(my)), P(TOWER_RADIUS), P(2))

        stats = f'Towers: {len(self.towers)}   Kills: {self.kills}   Leaked: {self.leaked}'
        ui.text(screen, stats, 15, (236, 233, 223), (18, 588), bold=True)
        ui.chip(screen, self.difficulty['name'].upper(), self.difficulty['color'], (30+ui.text_width(stats, 15, True), 587))
        if self.selected is not None:
            s = self.selected.stats
            info = f'Selected: level {self.selected.level+1}/{len(self.selected.levels)}   range {s.range:g}   dmg {s.damage:g}   rate {s.fire_rate:g}/s'
        else:
            info = 'Click: place / select   U: upgrade   Right-click: deselect   Z: undo   Esc: menu'
        ui.text(screen, info, 13, (189, 185, 175), (18, 614))
        hover = self.menu_button.collidepoint(mx, my)
        ui.rounded(screen, self.menu_button, (78, 82, 92) if hover else (60, 63, 70), 8)
        ui.text(screen, 'Menu', 15, (245, 245, 240), self.menu_button.center, bold=True, anchor='center')
        enabled = self.selected is not None and self.selected.can_upgrade
        hover = self.upgrade_button.collidepoint(mx, my)
        fill = ((70, 150, 95) if hover else (55, 125, 80)) if enabled else (60, 63, 70)
        ui.rounded(screen, self.upgrade_button, fill, 8)
        label = 'Max level' if self.selected is not None and not self.selected.can_upgrade else 'Upgrade (free)'
        ui.text(screen, label, 15, (245, 245, 240) if enabled else (140, 140, 145), self.upgrade_button.center, bold=True, anchor='center')