"""Standalone map/placement preview; no waves, economy, or combat yet."""
import argparse
import os
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--smoke', action='store_true', help='Run three frames without opening a window')
    args = parser.parse_args()
    if args.smoke:
        os.environ['SDL_VIDEODRIVER'] = 'dummy'
        os.environ['SDL_AUDIODRIVER'] = 'dummy'
    import pygame
    from map_runtime import load_map
    pygame.init()
    pygame.display.set_caption('KARZ TD · Desert highway placement preview')
    screen = pygame.display.set_mode((960, 640))
    game_map = load_map(Path(__file__).parent / 'maps/desert_highway.tmx')
    font = pygame.font.Font(None, 23)
    clock = pygame.time.Clock()
    towers = []
    show_zones = False
    radius = 16
    distance = 0.0
    frames = 0
    running = True
    points = [pygame.Vector2(p) for p in game_map.waypoints]
    lengths = [a.distance_to(b) for a, b in zip(points, points[1:])]
    total = sum(lengths)
    try:
        while running:
            dt = min(clock.tick(60)/1000, 0.05)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_b:
                        show_zones = not show_zones
                    elif event.key == pygame.K_z and towers:
                        towers.pop()
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    x, y = event.pos
                    if game_map.can_place(x, y, radius, towers):
                        towers.append((x, y, radius))
            screen.fill((26, 29, 34))
            screen.blit(game_map.artwork, (0, 0))
            if show_zones:
                overlay = pygame.Surface((960, 576), pygame.SRCALPHA)
                for i, role in enumerate(game_map.roles):
                    if role == 2:
                        pygame.draw.rect(overlay, (30, 170, 100, 75), (i%20*48, i//20*48, 48, 48))
                screen.blit(overlay, (0, 0))
            distance = (distance+90*dt) % total
            remaining = distance
            for k, length in enumerate(lengths):
                if remaining <= length:
                    enemy = points[k].lerp(points[k+1], remaining/length)
                    pygame.draw.circle(screen, (35, 30, 25), (round(enemy.x+2), round(enemy.y+3)), 8)
                    pygame.draw.circle(screen, (232, 78, 53), (round(enemy.x), round(enemy.y)), 7)
                    break
                remaining -= length
            for x, y, r in towers:
                pygame.draw.circle(screen, (44, 64, 80), (x, y), r)
                pygame.draw.circle(screen, (133, 185, 209), (x, y), r-4)
                pygame.draw.line(screen, (44, 64, 80), (x, y), (x+18, y-7), 6)
            x, y = pygame.mouse.get_pos()
            if 0 <= x < 960 and 0 <= y < 576:
                color = (60, 210, 120) if game_map.can_place(x, y, radius, towers) else (245, 78, 78)
                pygame.draw.circle(screen, color, (x, y), radius, 2)
            screen.blit(font.render('Click: place tower   B: buildable overlay   Z: undo tower   Esc: exit', True, (236, 233, 223)), (18, 590))
            screen.blit(font.render('Green = entire tower fits. Red = blocked. Red marker follows the enemy route.', True, (189, 185, 175)), (18, 614))
            pygame.display.flip()
            frames += 1
            if args.smoke and frames >= 3:
                running = False
    finally:
        pygame.quit()
    print(f'Preview complete: {frames} frames; {len(game_map.waypoints)} waypoints.')


if __name__ == '__main__':
    main()
