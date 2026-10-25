import argparse
import os


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--smoke', action='store_true', help='Run a few frames without opening a window')
    args = parser.parse_args()
    if args.smoke:
        os.environ['SDL_VIDEODRIVER'] = 'dummy'
        os.environ['SDL_AUDIODRIVER'] = 'dummy'
    import pygame
    pygame.init()
    import ui
    from game_screen import DIFFICULTIES, GameScreen
    screen, present = ui.setup_display('KARZ TD · Desert highway tower preview')
    state = {'running': True}
    game = GameScreen(DIFFICULTIES[0], on_exit=lambda: state.update(running=False))
    clock = pygame.time.Clock()
    frames = 0
    try:
        while state['running']:
            dt = 0.05 if args.smoke else min(clock.tick(60)/1000, 0.05)
            for event in pygame.event.get():
                ui.track_mouse(event)
                if event.type in (pygame.QUIT, pygame.WINDOWCLOSE):
                    state['running'] = False
                else:
                    game.handle(event)
            game.update(dt)
            game.draw(screen)
            present()
            frames += 1
            if args.smoke and frames >= 3:
                state['running'] = False
    finally:
        pygame.quit()
    print(f'Preview complete: {frames} frames; {len(game.map.waypoints)} waypoints.')


if __name__ == '__main__':
    main()