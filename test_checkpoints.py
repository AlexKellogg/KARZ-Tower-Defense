import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

import pygame

from backend import checkpoint_json
from game_session import GameSession, wave_size
from tower import Tower

STRONG_SPOTS = ((150, 250), (230, 180), (300, 250), (120, 330), (60, 150))


def play_until(screen, waves, limit=900):
    t = 0.0
    while screen.session.waves_cleared < waves and screen.result is None and t < limit:
        screen.update(0.05)
        t += 0.05


def add_strong_towers(screen, count=5):
    for x, y in STRONG_SPOTS[:count]:
        tower = Tower(x, y, 16)
        tower.upgrade()
        tower.upgrade()
        screen.towers.append(tower)


class SessionSnapshotTests(unittest.TestCase):
    def cleared(self, waves, sandbox=False):
        s = GameSession('Easy', sandbox=sandbox)
        s.update(10, 0)
        while s.waves_cleared < waves:
            for _ in s.update(1.0, 0):
                s.enemy_killed()
            s.update(0.01, 0)
            s.skip_break()
            s.update(0.01, 0)
        return s

    def test_resume_restores_everything_and_continues_with_the_next_wave(self):
        s = self.cleared(2)
        s.enemy_leaked()
        snap = s.snapshot()
        r = GameSession.resume('Easy', snap)
        self.assertEqual((r.wave, r.waves_cleared, r.lives, r.kills, r.leaked, r.economy.money, round(r.elapsed, 2)),
                         (2, 2, s.lives, s.kills, s.leaked, s.economy.money, round(s.elapsed, 2)))
        self.assertTrue(r.between_waves)
        r.update(10, 0)
        self.assertEqual((r.wave, r.to_spawn), (3, wave_size(3)))

    def test_bad_saves_are_refused(self):
        good = self.cleared(2).snapshot()
        for bad in ({**good, 'version': 7}, {**good, 'wave': 0}, {**good, 'wave': 5}, {'wave': 2}):
            with self.subTest(bad=bad), self.assertRaises((ValueError, KeyError)):
                GameSession.resume('Easy', bad)

    def test_sandbox_can_resume_past_the_normal_wave_count(self):
        s = GameSession.resume('Easy', {**self.cleared(2).snapshot(), 'wave': 9}, sandbox=True)
        self.assertEqual(s.waves_cleared, 9)


class GameScreenCheckpointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((1, 1))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def make(self, resume=None, sandbox=False):
        from game_screen import DIFFICULTIES, GameScreen
        self.saves, self.events, self.exited = [], [], []

        def checkpoint(state):
            self.saves.append(state)
            self.events.append('clear' if state is None else f"save {state['wave']}")

        def finish(result):
            self.events.append('record')
            return ()

        return GameScreen(DIFFICULTIES[0], on_exit=lambda: self.exited.append(True), on_finish=finish,
                          sandbox=sandbox, on_checkpoint=checkpoint, resume=resume)

    def test_a_checkpoint_is_saved_after_each_cleared_wave(self):
        g = self.make()
        add_strong_towers(g)
        play_until(g, 3)
        self.assertEqual([s['wave'] for s in self.saves], [1, 2, 3])
        last = self.saves[-1]
        self.assertEqual(len(last['towers']), 5)
        self.assertEqual({t['level'] for t in last['towers']}, {2})
        self.assertEqual(last['money'], g.session.economy.money)
        checkpoint_json('Easy', 'regular', last)

    def test_winning_records_the_score_then_clears_the_checkpoint(self):
        g = self.make()
        add_strong_towers(g)
        play_until(g, 99)
        self.assertTrue(g.result.won)
        self.assertEqual(self.events[-2:], ['record', 'clear'])
        self.assertEqual([e for e in self.events if e.startswith('save')], ['save 1', 'save 2', 'save 3', 'save 4'])

    def test_leaving_between_waves_keeps_towers_bought_during_the_break(self):
        g = self.make()
        add_strong_towers(g, 3)
        play_until(g, 2)
        self.assertTrue(g.session.between_waves)
        g.towers.append(Tower(60, 150, 16))
        g.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0, unicode=''))
        self.assertEqual((self.saves[-1]['wave'], len(self.saves[-1]['towers'])), (2, 4))
        self.assertEqual(self.exited, [True])

    def test_leaving_mid_wave_keeps_the_last_checkpoint(self):
        g = self.make()
        add_strong_towers(g, 3)
        play_until(g, 2)
        while g.session.between_waves:
            g.update(0.05)
        saves_before = len(self.saves)
        g.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0, unicode=''))
        self.assertEqual(len(self.saves), saves_before)
        self.assertEqual(self.saves[-1]['wave'], 2)

    def test_resuming_rebuilds_the_game_and_it_can_be_finished(self):
        first = self.make()
        add_strong_towers(first)
        play_until(first, 2)
        saved = self.saves[-1]
        g = self.make(resume=saved)
        self.assertTrue(g.resumed)
        self.assertEqual((g.session.waves_cleared, g.session.lives, g.session.economy.money),
                         (2, saved['lives'], saved['money']))
        self.assertEqual([(t.x, t.y, t.level) for t in g.towers], [(t['x'], t['y'], t['level']) for t in saved['towers']])
        play_until(g, 99)
        self.assertTrue(g.result.won)
        self.assertEqual(g.result.kills, sum(wave_size(w) for w in range(1, 6)))

    def test_a_broken_save_starts_a_fresh_game(self):
        g = self.make(resume={'version': 1, 'wave': 'oops'})
        self.assertFalse(g.resumed)
        self.assertEqual((g.session.waves_cleared, g.towers), (0, []))

    def test_play_again_starts_fresh(self):
        first = self.make()
        add_strong_towers(first)
        play_until(first, 2)
        g = self.make(resume=self.saves[-1])
        add_strong_towers(g)
        play_until(g, 99)
        g.restart()
        self.assertEqual((g.session.waves_cleared, g.towers, g.resumed), (0, [], False))


class MapSelectPromptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((1, 1))

    def setUp(self):
        from local_backend import LocalBackend
        from screens import App
        self.tmp = tempfile.TemporaryDirectory()
        self.backend = LocalBackend(Path(self.tmp.name)/'karz.db')
        self.app = App(self.backend)
        self.app.account = self.backend.sign_up('Kaden', 'kaden', 'kaden@example.com', 'password123')

    def tearDown(self):
        self.backend.close()
        self.tmp.cleanup()

    def click(self, pos):
        self.app.current.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos))

    def open_select(self):
        from screens import MapSelectScreen
        self.app.go(MapSelectScreen(self.app))
        return self.app.current

    def save_and_quit_after(self, waves):
        from game_screen import GameScreen
        select = self.open_select()
        self.click(select.buttons(select.cards[0].move(0, -6))[0].center)
        game = self.app.current
        self.assertIsInstance(game, GameScreen)
        add_strong_towers(game)
        play_until(game, waves)
        game.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0, unicode=''))

    def test_no_prompt_without_a_saved_game(self):
        from game_screen import GameScreen
        select = self.open_select()
        self.click(select.buttons(select.cards[0].move(0, -6))[0].center)
        self.assertIsInstance(self.app.current, GameScreen)

    def test_continue_resumes_from_the_saved_wave(self):
        from game_screen import GameScreen
        self.save_and_quit_after(3)
        select = self.open_select()
        self.click(select.buttons(select.cards[0].move(0, -6))[0].center)
        self.assertIsNotNone(select.prompt)
        self.assertEqual(select.prompt[2]['wave'], 3)
        select.draw(self.app.screen)
        self.click(select.continue_button.rect.center)
        game = self.app.current
        self.assertIsInstance(game, GameScreen)
        self.assertEqual((game.resumed, game.session.waves_cleared, len(game.towers)), (True, 3, 5))

    def test_new_game_throws_the_save_away(self):
        self.save_and_quit_after(2)
        select = self.open_select()
        self.click(select.buttons(select.cards[0].move(0, -6))[0].center)
        self.click(select.new_button.rect.center)
        self.assertEqual((self.app.current.resumed, self.app.current.session.waves_cleared), (False, 0))
        self.assertIsNone(self.backend.load_checkpoint(self.app.account, 'Easy', 'regular'))

    def test_escape_closes_the_prompt(self):
        self.save_and_quit_after(1)
        select = self.open_select()
        self.click(select.buttons(select.cards[0].move(0, -6))[0].center)
        select.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0, unicode=''))
        self.assertIsNone(select.prompt)
        self.assertIs(self.app.current, select)

    def test_sandbox_has_its_own_save(self):
        from game_screen import GameScreen
        select = self.open_select()
        self.click(select.buttons(select.cards[0].move(0, -6))[1].center)
        game = self.app.current
        add_strong_towers(game)
        play_until(game, 6)
        game.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0, unicode=''))
        self.assertIsNone(self.backend.load_checkpoint(self.app.account, 'Easy', 'regular'))
        select = self.open_select()
        self.click(select.buttons(select.cards[0].move(0, -6))[1].center)
        self.click(select.continue_button.rect.center)
        self.assertIsInstance(self.app.current, GameScreen)
        self.assertEqual((self.app.current.sandbox, self.app.current.session.waves_cleared), (True, 6))


if __name__ == '__main__':
    unittest.main()
