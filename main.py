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
    from backend import RunResult
    from game_screen import DIFFICULTIES
    from local_backend import LocalBackend
    from screens import (AdminScreen, App, HomeScreen, LeaderboardScreen, MapSelectScreen, SettingsScreen,
                         SignUpScreen)
    pygame.init()
    try:
        if args.smoke:
            with tempfile.TemporaryDirectory() as tmp:
                backend = LocalBackend(Path(tmp)/'smoke.db')
                app = App(backend)
                app.run(frames=3)
                app.go(SignUpScreen(app))
                app.run(frames=3)
                app.account = backend.sign_up('Smoke Test', 'smoke', 'smoke@example.com', 'password123')
                backend.record_run(app.account, RunResult('Easy', True, 900, 140.0, 2, 5, 60))
                for screen in (HomeScreen, SettingsScreen, MapSelectScreen, LeaderboardScreen):
                    app.go(screen(app))
                    app.run(frames=3)
                app.play(DIFFICULTIES[0])
                app.run(frames=30)
                app.play(DIFFICULTIES[0], sandbox=True)
                app.run(frames=30)
                app.account = backend.promote_by_email('smoke@example.com')
                for screen in (HomeScreen, AdminScreen, MapSelectScreen):
                    app.go(screen(app))
                    app.run(frames=3)
                for difficulty in DIFFICULTIES[1:]:
                    app.play(difficulty)
                    app.run(frames=3)
                    app.play(difficulty, sandbox=True)
                    app.run(frames=3)
                backend.close()
            print('Smoke test complete: every screen rendered.')
        else:
            App(LocalBackend()).run()
    finally:
        pygame.quit()


if __name__ == '__main__':
    main()
