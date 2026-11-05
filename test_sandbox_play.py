import os
import unittest

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

import pygame

from game_session import FIRST_WAVE_DELAY, GameSession


def clear_waves(screen, count):
    s = screen.session
    s.update(FIRST_WAVE_DELAY, 0)
    while s.waves_cleared < count:
        for _ in s.update(1.0, 0):
            s.enemy_killed()
        s.update(0.01, 0)
        s.skip_break()
        s.update(0.01, 0)


class SandboxResultTests(unittest.TestCase):
    def test_result_is_marked_sandbox(self):
        self.assertTrue(GameSession('Easy', sandbox=True).result().sandbox)
        self.assertFalse(GameSession('Easy').result().sandbox)
        self.assertEqual(GameSession('Easy', sandbox=True).result().mode, 'sandbox')


class SandboxLeaveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((1, 1))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def make(self, sandbox=True, fail=None):
        from game_screen import DIFFICULTIES, GameScreen
        self.saved, self.exited = [], []

        def record(result):
            if fail:
                raise fail
            self.saved.append(result)
        return GameScreen(DIFFICULTIES[0], on_exit=lambda: self.exited.append(True), on_finish=record, sandbox=sandbox)

    def press(self, screen, key):
        screen.handle(pygame.event.Event(pygame.KEYDOWN, key=key, mod=0, unicode=''))

    def test_leaving_sandbox_saves_waves_reached(self):
        g = self.make()
        clear_waves(g, 3)
        self.press(g, pygame.K_ESCAPE)
        self.assertEqual(self.exited, [True])
        self.assertEqual([(r.sandbox, r.waves_cleared) for r in self.saved], [(True, 3)])

    def test_menu_button_also_saves(self):
        g = self.make()
        clear_waves(g, 2)
        g.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=g.menu_button.center))
        self.assertEqual(len(self.saved), 1)

    def test_nothing_saved_before_the_first_wave_is_cleared(self):
        g = self.make()
        self.press(g, pygame.K_ESCAPE)
        self.assertEqual((self.saved, self.exited), ([], [True]))

    def test_regular_games_are_not_saved_on_leave(self):
        g = self.make(sandbox=False)
        clear_waves(g, 2)
        self.press(g, pygame.K_ESCAPE)
        self.assertEqual(self.saved, [])

    def test_save_failure_still_leaves_the_game(self):
        g = self.make(fail=ConnectionError('server down'))
        clear_waves(g, 2)
        self.press(g, pygame.K_ESCAPE)
        self.assertEqual(self.exited, [True])


if __name__ == '__main__':
    unittest.main()
