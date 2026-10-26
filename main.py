import argparse
import os
import tempfile
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--smoke', action='store_true', help='Open every screen for a few frames without a window')
    parser.add_argument('--server', default=os.environ.get('KARZ_SERVER_URL', ''),
                        help='KARZ server URL, e.g. http://127.0.0.1:8000. Leave empty to save on this computer only.')
    parser.add_argument('--offline', action='store_true', help='Ignore KARZ_SERVER_URL and save on this computer only')
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
                backend.close()
            print('Smoke test complete: every screen rendered.')
        elif args.server and not args.offline:
            from remote_backend import RemoteBackend
            backend = RemoteBackend(args.server)
            try:
                App(backend).run()
            finally:
                backend.close()
        else:
            App(LocalBackend()).run()
    finally:
        pygame.quit()


if __name__ == '__main__':
    main()
