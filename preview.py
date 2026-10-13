import argparse
import os
from pathlib import Path

# Placeholder spawn rate, change later.
SPAWN_INTERVAL = 1.0
SHOT_FLASH = 0.08
LEVEL_COLORS = ((133, 185, 209), (120, 200, 140), (235, 190, 80))


def draw_tower(pygame, screen, tower, selected):
    x, y, r = round(tower.x), round(tower.y), tower.radius
    ax, ay = tower.aim
    pygame.draw.circle(screen, (44, 64, 80), (x, y), r)
    pygame.draw.circle(screen, LEVEL_COLORS[tower.level % len(LEVEL_COLORS)], (x, y), r-4)
    pygame.draw.line(screen, (44, 64, 80), (x, y), (x+ax*(r+6), y+ay*(r+6)), 6)
    for i in range(tower.level+1):
        pygame.draw.circle(screen, (250, 245, 230), (x-(tower.level*4)+i*8, y+r+5), 3)
    if selected:
        pygame.draw.circle(screen, (255, 255, 255), (x, y), r+3, 2)


def draw_range(pygame, screen, x, y, rng, color):
    overlay = pygame.Surface((960, 576), pygame.SRCALPHA)
    pygame.draw.circle(overlay, (*color, 40), (round(x), round(y)), rng)
    pygame.draw.circle(overlay, (*color, 140), (round(x), round(y)), rng, 2)
    screen.blit(overlay, (0, 0))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--smoke', action='store_true', help='Run a few frames without opening a window')
    args = parser.parse_args()
    if args.smoke:
        os.environ['SDL_VIDEODRIVER'] = 'dummy'
        os.environ['SDL_AUDIODRIVER'] = 'dummy'
    import pygame
    from map_runtime import load_map
    from tower import Tower, BASE_TOWER_LEVELS
    from enemy import PlaceholderEnemy
    pygame.init()
    pygame.display.set_caption('KARZ TD · Desert highway tower preview')
    screen = pygame.display.set_mode((960, 640))
    game_map = load_map(Path(__file__).parent / 'maps/desert_highway.tmx')
    font = pygame.font.Font(None, 23)
    clock = pygame.time.Clock()
    upgrade_button = pygame.Rect(790, 586, 155, 44)
    towers, enemies, shots = [], [], []
    selected = None
    show_zones = False
    radius = 16
    spawn_timer = 0.0
    spawned = kills = leaked = 0
    frames = 0
    running = True

    def try_upgrade():
        if selected is not None:
            selected.upgrade()

    try:
        while running:
            dt = min(clock.tick(60)/1000, 0.05)
            if args.smoke:
                dt = 0.05
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_b:
                        show_zones = not show_zones
                    elif event.key == pygame.K_u:
                        try_upgrade()
                    elif event.key == pygame.K_z and towers:
                        removed = towers.pop()
                        if removed is selected:
                            selected = None
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
                    selected = None
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    x, y = event.pos
                    if upgrade_button.collidepoint(x, y):
                        try_upgrade()
                        continue
                    clicked = next((t for t in towers if t.contains(x, y)), None)
                    if clicked is not None:
                        selected = clicked
                    elif game_map.can_place(x, y, radius, [t.footprint for t in towers]):
                        towers.append(Tower(x, y, radius))
                        selected = None
                    else:
                        selected = None

            spawn_timer -= dt
            if spawn_timer <= 0:
                spawn_timer = SPAWN_INTERVAL
                spawned += 1
                # Placeholder enemy health and speed, change later.
                enemies.append(PlaceholderEnemy(game_map.waypoints, hp=20+spawned*2, speed=80))

            for enemy in enemies:
                enemy.update(dt)
            for tower in towers:
                hit = tower.update(dt, enemies)
                if hit is not None:
                    shots.append([(tower.x+tower.aim[0]*(radius+6), tower.y+tower.aim[1]*(radius+6)), hit.pos, SHOT_FLASH])
                    if hit.hp == 0:
                        kills += 1
            leaked += sum(1 for e in enemies if e.reached_end)
            enemies = [e for e in enemies if e.alive]
            for shot in shots:
                shot[2] -= dt
            shots = [s for s in shots if s[2] > 0]

            screen.fill((26, 29, 34))
            screen.blit(game_map.artwork, (0, 0))
            if show_zones:
                overlay = pygame.Surface((960, 576), pygame.SRCALPHA)
                for i, role in enumerate(game_map.roles):
                    if role == 2:
                        pygame.draw.rect(overlay, (30, 170, 100, 75), (i%20*48, i//20*48, 48, 48))
                screen.blit(overlay, (0, 0))
            if selected is not None:
                draw_range(pygame, screen, selected.x, selected.y, selected.stats.range, (255, 255, 255))
            for enemy in enemies:
                ex, ey = round(enemy.pos[0]), round(enemy.pos[1])
                pygame.draw.circle(screen, (35, 30, 25), (ex+2, ey+3), 9)
                pygame.draw.circle(screen, (232, 78, 53), (ex, ey), 8)
                bar = 18*enemy.hp/enemy.max_hp
                pygame.draw.rect(screen, (60, 20, 20), (ex-9, ey-15, 18, 4))
                pygame.draw.rect(screen, (90, 220, 110), (ex-9, ey-15, bar, 4))
            for tower in towers:
                draw_tower(pygame, screen, tower, tower is selected)
            for start, end, _ in shots:
                pygame.draw.line(screen, (255, 235, 140), start, end, 3)

            mx, my = pygame.mouse.get_pos()
            hovering_tower = any(t.contains(mx, my) for t in towers)
            if 0 <= mx < 960 and 0 <= my < 576 and not hovering_tower:
                ok = game_map.can_place(mx, my, radius, [t.footprint for t in towers])
                color = (60, 210, 120) if ok else (245, 78, 78)
                if ok:
                    draw_range(pygame, screen, mx, my, BASE_TOWER_LEVELS[0].range, color)
                pygame.draw.circle(screen, color, (mx, my), radius, 2)

            screen.blit(font.render(f'Towers: {len(towers)}   Kills: {kills}   Leaked: {leaked}', True, (236, 233, 223)), (18, 590))
            if selected is not None:
                s = selected.stats
                info = f'Selected: level {selected.level+1}/{len(selected.levels)}  range {s.range:g}  dmg {s.damage:g}  rate {s.fire_rate:g}/s'
            else:
                info = 'Click: place / select tower   U or button: upgrade   Right-click: deselect   Z: undo   B: zones'
            screen.blit(font.render(info, True, (189, 185, 175)), (18, 614))
            enabled = selected is not None and selected.can_upgrade
            hover = upgrade_button.collidepoint(mx, my)
            fill = ((70, 150, 95) if hover else (55, 125, 80)) if enabled else (60, 63, 70)
            pygame.draw.rect(screen, fill, upgrade_button, border_radius=8)
            label = 'Max level' if selected is not None and not selected.can_upgrade else 'Upgrade (free)'
            text = font.render(label, True, (245, 245, 240) if enabled else (140, 140, 145))
            screen.blit(text, text.get_rect(center=upgrade_button.center))
            pygame.display.flip()
            frames += 1
            if args.smoke and frames >= 3:
                running = False
    finally:
        pygame.quit()
    print(f'Preview complete: {frames} frames; {len(game_map.waypoints)} waypoints.')


if __name__ == '__main__':
    main()