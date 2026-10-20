import argparse
import os
import tempfile
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--smoke', action='store_true', help='Open every screen for a few frames without a window')
    args = parser.parse_args()
    if args.smoke:
        os.environ['SDL_VIDEODRIVER'] = 'dummy'
        os.environ['SDL_AUDIODRIVER'] = 'dummy'
    import pygame
    from accounts import AccountStore
    from screens import App, HomeScreen, MapSelectScreen, SettingsScreen, SignUpScreen
    from game_screen import DIFFICULTIES
    pygame.init()
    try:
        if args.smoke:
            with tempfile.TemporaryDirectory() as tmp:
                store = AccountStore(Path(tmp)/'smoke.db')
                app = App(store)
                app.run(frames=3)
                app.go(SignUpScreen(app))
                app.run(frames=3)
                app.account = store.sign_up('Smoke Test', 'smoke', 'smoke@example.com', 'password123')
                for screen in (HomeScreen, SettingsScreen, MapSelectScreen):
                    app.go(screen(app))
                    app.run(frames=3)
                app.play(DIFFICULTIES[0])
                app.run(frames=30)
                store.close()
            print('Smoke test complete: every screen rendered.')
        else:
            App(AccountStore()).run()
    finally:
        pygame.quit()


if __name__ == '__main__':
    main()