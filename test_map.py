import json
import os
from pathlib import Path
import unittest

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

from map_runtime import GameMap, load_map


class PlacementTests(unittest.TestCase):
    def test_free_centers_and_joined_zones(self):
        m = GameMap(3, 2, 48, [2, 2, 0, 2, 0, 0], [], None)
        self.assertTrue(m.can_place(31.5, 21.2, 10))
        self.assertTrue(m.can_place(48, 24, 16))  # footprint spans two buildable tiles
        self.assertFalse(m.can_place(88, 24, 16))  # center valid, footprint leaves zone
        self.assertFalse(m.can_place(44, 44, 16))  # touches the nonbuildable inner corner
        self.assertFalse(m.can_place(5, 24, 16))
        self.assertFalse(m.can_place(48, 24, 16, [(50, 24, 16)]))

    def test_blockers_and_tunnels_control_targeting(self):
        # Top row: buildable, blocker, open. Bottom row: tunnel, path, open.
        m = GameMap(3, 2, 48, [2, 3, 0, 4, 1, 0], [], None)
        self.assertFalse(m.has_line_of_sight(24, 24, 120, 24))
        self.assertTrue(m.has_line_of_sight(24, 72, 120, 72))
        self.assertFalse(m.can_target(120, 72, (24, 72)))
        self.assertTrue(m.can_target(120, 72, (72, 72)))
        self.assertFalse(m.enemy_visible((24, 72)))
        self.assertTrue(m.enemy_visible((72, 72)))

    def test_tmx_matches_approved_layout(self):
        import pygame
        pygame.init()
        pygame.display.set_mode((1, 1))
        try:
            path = Path(__file__).parent / 'maps/desert_highway.tmx'
            m = load_map(path)
            layout = json.loads(path.with_suffix('.json').read_text())
            self.assertEqual(m.roles, layout['tiles'])
            self.assertEqual(m.waypoints, [(p['x'], p['y']) for p in layout['waypoints']])
            self.assertEqual((m.width, m.height, m.tile_size), (20, 12, 48))
            self.assertEqual(m.artwork.get_size(), (960, 576))
            self.assertEqual(m.roles.count(1), 59)
            self.assertEqual(m.roles.count(2), 60)
            for i, role in enumerate(m.roles):
                self.assertEqual(m.can_place(i%20*48+24, i//20*48+24), role == 2)
        finally:
            pygame.quit()

    def test_canyon_crossing_matches_approved_layout(self):
        import pygame
        pygame.init()
        pygame.display.set_mode((1, 1))
        try:
            path = Path(__file__).parent / 'maps/canyon_crossing.tmx'
            m = load_map(path)
            layout = json.loads(path.with_suffix('.json').read_text())
            self.assertEqual(m.roles, layout['tiles'])
            self.assertEqual(m.waypoints, [(p['x'], p['y']) for p in layout['waypoints']])
            self.assertEqual((m.width, m.height, m.tile_size), (20, 12, 48))
            self.assertEqual(m.artwork.get_size(), (960, 576))
            self.assertEqual(m.roles.count(1), 49)
            self.assertEqual(m.roles.count(2), 38)
            self.assertEqual((layout['name'], layout['difficulty'], layout['clearWave']),
                             ('Canyon Crossing', 'Medium', 7))
            self.assertEqual(layout['rows'], [
                '....................', 'SPPPPPPP............', '...BBBBP.BBB........',
                '...BBBBP.BBB.PPPPPP.', '.......P.....P....P.', '.BPPPPPP.....PBBBBP.',
                'BBP..........PBBBBP.', '..P.BBB......PBBBBP.', '..PPPPPPPPPPPPBBB.P.',
                '..............BBB.P.', '..................PE', '....................',
            ])
        finally:
            pygame.quit()

    def test_razorback_pass_matches_approved_layout(self):
        import pygame
        pygame.init()
        pygame.display.set_mode((1, 1))
        try:
            path = Path(__file__).parent / 'maps/razorback_pass.tmx'
            m = load_map(path)
            layout = json.loads(path.with_suffix('.json').read_text())
            self.assertEqual(m.roles, layout['tiles'])
            self.assertEqual(m.waypoints, [(p['x'], p['y']) for p in layout['waypoints']])
            self.assertEqual((m.width, m.height, m.tile_size), (20, 12, 48))
            self.assertEqual(m.artwork.get_size(), (960, 576))
            self.assertEqual((m.roles.count(1), m.roles.count(2), m.roles.count(3), m.roles.count(4)),
                             (31, 31, 21, 2))
            self.assertEqual((layout['name'], layout['difficulty'], layout['clearWave']),
                             ('Razorback Pass', 'Hard', 10))
            self.assertEqual(layout['rows'], [
                '........X...........', '.BBB..BBX...........', 'SPPPPPPBX.......XX..',
                '...XXXPXX.........PE', '...XBBP....BB...BBP.', '...XBBPPPPPPB...BBP.',
                '...XBB..BBBP.XXXX.P.', '.........BBT.XBBX.P.', '...........T..BBXXP.',
                '...........PPPPPPPP.', '...........BBB......', '....................',
            ])
        finally:
            pygame.quit()


if __name__ == '__main__':
    unittest.main()
