import json
import os
from pathlib import Path
import unittest

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
import pygame
from export_caldera_map import ROWS, ROUTES
from game_screen import DIFFICULTIES, GameScreen
from game_session import wave_size
from map_runtime import load_map


class CalderaTests(unittest.TestCase):
    def setUp(self):
        pygame.init()
        pygame.display.set_mode((960,640))
        self.difficulty = next(d for d in DIFFICULTIES if d['name']=='Impossible')
        self.game = GameScreen(self.difficulty,on_exit=lambda:None)

    def tearDown(self):
        pygame.quit()

    def test_approved_layout_and_routes(self):
        m = self.game.map
        data = json.loads(Path(self.difficulty['map_path']).with_suffix('.json').read_text())
        self.assertEqual(data['rows'], ROWS)
        self.assertEqual(m.roles, data['tiles'])
        self.assertEqual([m.roles.count(i) for i in (1,2,3,4)], [48,30,16,4])
        self.assertEqual(m.artwork.get_size(),(960,576))
        self.assertEqual(m.routes, [[((c-.5)*48,(r-.5)*48) for c,r in route] for route in ROUTES])
        self.assertEqual([len(r) for r in m.routes],[26,26])
        self.assertEqual(self.difficulty['map_image'].stem,'calderas_edge')
        for i,role in enumerate(m.roles):
            self.assertEqual(m.can_place((i%20+.5)*48,(i//20+.5)*48),role==2)
        for route in m.routes:
            for a,b in zip(route,route[1:]):
                self.assertEqual(abs(a[0]-b[0])+abs(a[1]-b[1]),48)

    def test_both_tunnels_and_blockers(self):
        m = self.game.map
        for y,x0 in [(216,384),(360,480)]:
            for x,visible in [(x0-.01,True),(x0,False),(x0+48,False),(x0+96-.01,False),(x0+96,True)]:
                self.assertEqual(m.enemy_visible((x,y)),visible)
                if not visible:
                    self.assertFalse(m.can_target(x,y-48,(x,y)))
        self.assertFalse(m.has_line_of_sight(72,120,168,120))

    def test_alternation_preserves_wave_count_and_economy(self):
        g=self.game
        g.step(2)
        for _ in range(8):
            g.step(.8)
        self.assertEqual(len(g.enemies),wave_size(1))
        self.assertEqual([e.waypoints for e in g.enemies],[g.map.routes[i%2] for i in range(8)])
        self.assertEqual(g.session.economy.money,150)
        self.assertEqual((g.enemies[0].max_hp,g.enemies[0].speed),(62,108))

    def test_checkpoint_rejects_placeholder_and_accepts_current(self):
        state=dict(version=1,wave=1,lives=20,kills=8,leaked=0,money=190,elapsed=20,towers=[])
        old=GameScreen(self.difficulty,on_exit=lambda:None,resume=state)
        self.assertFalse(old.resumed)
        current=GameScreen(self.difficulty,on_exit=lambda:None,resume={**state,'map_id':'calderas_edge-v1'})
        self.assertTrue(current.resumed)
        saved=[]
        current.on_checkpoint=saved.append
        current.checkpoint()
        self.assertEqual(saved[0]['map_id'],'calderas_edge-v1')
        current.step(3)
        current.step(.01)
        self.assertEqual(current.enemies[0].waypoints,current.map.routes[0])

    def test_existing_map_still_uses_one_route(self):
        m=load_map(DIFFICULTIES[0]['map_path'])
        self.assertEqual(m.routes,[m.waypoints])


if __name__=='__main__':
    unittest.main()
