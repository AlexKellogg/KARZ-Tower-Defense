"""Regression checks for the Hard map's frontend wiring and tunnel rendering."""
import os
import unittest
from types import SimpleNamespace

os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import pygame
import ui
from enemy import PlaceholderEnemy
from game_screen import DIFFICULTIES, GameScreen
from screens import MapSelectScreen


class HardMapTests(unittest.TestCase):
    def setUp(self):
        pygame.init()
        self.surface, _ = ui.setup_display('Hard map test')
        self.hard = next(d for d in DIFFICULTIES if d['name'] == 'Hard')
        self.game = GameScreen(self.hard, on_exit=lambda: None)

    def tearDown(self):
        pygame.quit()

    def test_card_preview_and_play_button_use_hard_map(self):
        played = []
        app = SimpleNamespace(
            account=SimpleNamespace(is_admin=True),
            backend=SimpleNamespace(unlocked_difficulties=lambda account: tuple(d['name'] for d in DIFFICULTIES)),
            play=lambda difficulty, **kwargs: played.append((difficulty, kwargs)),
        )
        selector = MapSelectScreen(app)
        self.assertEqual(self.hard['map_name'], 'Razorback Pass')
        self.assertEqual(self.hard['map_path'].stem, 'razorback_pass')
        self.assertEqual(self.hard['map_image'].stem, 'razorback_pass')
        expected = ui.load_image(self.hard['map_image'], (176, 106), radius=8)
        self.assertEqual(pygame.image.tobytes(selector.thumbs['Hard'], 'RGBA'),
                         pygame.image.tobytes(expected, 'RGBA'))
        play, sandbox = selector.buttons(selector.cards[2].move(0, -6))
        for button in (play, sandbox):
            selector.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=button.center))
        self.assertEqual(played, [(self.hard, {}), (self.hard, {'sandbox': True})])

    def test_tunnel_hides_entire_enemy_then_restores_it(self):
        # Tunnel occupies column 12, rows 8 and 9 (1-based), y=[336,432).
        m = self.game.map
        self.game.draw_map(self.surface)
        baseline = pygame.image.tobytes(self.surface, 'RGB')
        for y, visible in ((335.9, True), (336, False), (360, False),
                           (384, False), (431.9, False), (432, True)):
            enemy = SimpleNamespace(pos=(552, y), hp=30, max_hp=30)
            self.game.enemies = [enemy]
            self.assertEqual(m.enemy_visible(enemy.pos), visible)
            self.assertEqual(m.can_target(504, y, enemy.pos), visible)
            self.game.draw_map(self.surface)
            rendered = pygame.image.tobytes(self.surface, 'RGB')
            self.assertEqual(rendered == baseline, not visible)

    def test_enemy_continues_moving_through_tunnel(self):
        enemy = PlaceholderEnemy(self.game.map.waypoints, speed=48)
        states = []
        while not enemy.reached_end:
            states.append(self.game.map.enemy_visible(enemy.pos))
            enemy.update(0.25)
        self.assertIn(False, states)
        first_hidden = states.index(False)
        last_hidden = len(states)-1-states[::-1].index(False)
        self.assertTrue(all(not state for state in states[first_hidden:last_hidden+1]))
        self.assertTrue(states[first_hidden-1])
        self.assertTrue(states[last_hidden+1])


if __name__ == '__main__':
    unittest.main()
