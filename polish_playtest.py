"""Offline, isolated playtest: every map unlocked, separate saves and run logs."""
import argparse
from dataclasses import asdict
from datetime import datetime
import json
import os
from pathlib import Path
import tempfile


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--smoke',action='store_true')
    args=parser.parse_args()
    if args.smoke:
        os.environ['SDL_VIDEODRIVER']='dummy'
        os.environ['SDL_AUDIODRIVER']='dummy'
    import pygame
    from backend import AccountError
    from local_backend import LocalBackend
    from game_screen import DIFFICULTIES
    from screens import App,MapSelectScreen
    from tower import TOWER_TYPES,Tower

    directory=Path(__file__).parent/'.playtest-data'
    directory.mkdir(exist_ok=True)
    class TestBackend(LocalBackend):
        def log(self,event,difficulty,payload):
            if args.smoke:return
            with (directory/'runs.jsonl').open('a',encoding='utf-8') as stream:
                stream.write(json.dumps({'time':datetime.now().isoformat(timespec='seconds'),
                                        'event':event,'difficulty':difficulty,'data':payload})+'\n')
        def save_checkpoint(self,account,difficulty,mode,state):
            result=super().save_checkpoint(account,difficulty,mode,state)
            self.log('checkpoint_'+mode,difficulty,state)
            return result
        def record_run(self,account,result):
            unlocked=super().record_run(account,result)
            self.log('result',result.difficulty,asdict(result))
            return unlocked
    temp=tempfile.TemporaryDirectory(dir=directory) if args.smoke else None
    backend=TestBackend(Path(temp.name)/'smoke.db' if temp else directory/'test-accounts.db')
    pygame.init()
    try:
        email='local-playtest@example.invalid'
        try:account=backend.sign_up('Local Playtester','local_playtester',email,'local-only-playtest')
        except AccountError:account=backend.log_in(email,'local-only-playtest')
        account=backend.promote_by_email(email)
        app=App(backend)
        app.account=account
        app.go(MapSelectScreen(app))
        if args.smoke:
            app.run(frames=2)
            for difficulty in DIFFICULTIES:
                for sandbox in (False,True):
                    app.play(difficulty,sandbox=sandbox)
                    g=app.current
                    assert g.session.awaiting_start
                    g.session.start_first_wave()
                    spots=[((i%20+.5)*48,(i//20+.5)*48) for i,r in enumerate(g.map.roles) if r==2]
                    for kind,(x,y) in zip(TOWER_TYPES,spots):
                        g.towers.append(Tower(x,y,tower_type=kind))
                    app.run(frames=3)
            print('Playtest smoke passed: isolated account, map selector, all 4 maps and both modes, all tower types.')
        else:app.run()
    finally:
        backend.close()
        pygame.quit()
        if temp:temp.cleanup()


if __name__=='__main__':
    main()
