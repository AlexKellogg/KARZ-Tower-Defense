import os
import unittest

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

import pygame

from game_session import FIRST_WAVE_DELAY, SPEEDS, TOTAL_WAVES, GameClock, GameSession, wave_size


class ClockTests(unittest.TestCase):
    def test_starts_unpaused_at_normal_speed(self):
        clock = GameClock()
        self.assertFalse(clock.paused)
        self.assertEqual(clock.steps(0.016), [0.016])

    def test_pause_stops_time_and_resume_brings_it_back(self):
        clock = GameClock()
        clock.toggle_pause()
        self.assertEqual(clock.steps(0.016), [])
        clock.toggle_pause()
        self.assertEqual(clock.steps(0.016), [0.016])

    def test_speed_cycles_and_runs_extra_steps(self):
        clock = GameClock()
        seen = []
        for _ in SPEEDS:
            seen.append(clock.speed)
            self.assertEqual(clock.steps(0.02), [0.02]*clock.speed)
            clock.cycle_speed()
        self.assertEqual(seen, list(SPEEDS))
        self.assertEqual(clock.speed, SPEEDS[0])

    def test_paused_at_high_speed_still_does_nothing(self):
        clock = GameClock()
        clock.cycle_speed()
        clock.toggle_pause()
        self.assertEqual(clock.steps(0.02), [])


class PreviewTests(unittest.TestCase):
    def test_preview_before_the_first_wave_matches_what_spawns(self):
        s = GameSession('Hard')
        preview = s.next_wave()
        self.assertEqual((preview.wave, preview.count), (1, wave_size(1)))
        spawned = []
        s.update(FIRST_WAVE_DELAY, 0)
        while s.to_spawn:
            spawned += s.update(1.0, len(spawned))
        self.assertEqual(len(spawned), preview.count)
        self.assertTrue(all(hp == preview.hp and speed == preview.speed for hp, speed in spawned))

    def test_preview_gets_harder_each_wave_and_with_difficulty(self):
        easy, hard = GameSession('Easy'), GameSession('Hard')
        self.assertGreater(hard.next_wave().hp, easy.next_wave().hp)
        easy.wave = 2
        self.assertGreater(easy.next_wave().hp, GameSession('Easy').next_wave().hp)

    def test_no_preview_after_the_last_wave_or_when_finished(self):
        s = GameSession('Easy')
        s.wave = TOTAL_WAVES
        self.assertIsNone(s.next_wave())
        s = GameSession('Easy')
        s.status = 'lost'
        self.assertIsNone(s.next_wave())

    def test_sandbox_always_has_a_next_wave(self):
        s = GameSession('Easy', sandbox=True)
        s.wave = TOTAL_WAVES+3
        self.assertEqual(s.next_wave().wave, TOTAL_WAVES+4)


class GameScreenControlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((1, 1))
        from game_screen import DIFFICULTIES, GameScreen
        cls.make = staticmethod(lambda: GameScreen(DIFFICULTIES[0], on_exit=lambda: None))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def key(self, screen, key):
        screen.handle(pygame.event.Event(pygame.KEYDOWN, key=key, mod=0, unicode=''))

    def click(self, screen, rect):
        screen.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center))

    def start_wave(self, screen):
        screen.update(FIRST_WAVE_DELAY)
        screen.update(0.05)
        self.assertTrue(screen.enemies)

    def test_space_pauses_everything(self):
        g = self.make()
        self.start_wave(g)
        before = ([e.progress for e in g.enemies], g.session.elapsed)
        self.key(g, pygame.K_SPACE)
        for _ in range(20):
            g.update(0.05)
        self.assertEqual(([e.progress for e in g.enemies], g.session.elapsed), before)
        self.key(g, pygame.K_p)
        g.update(0.05)
        self.assertGreater(g.session.elapsed, before[1])

    def test_pause_and_speed_buttons_work_by_mouse(self):
        g = self.make()
        self.click(g, g.pause_button)
        self.assertTrue(g.clock.paused)
        self.click(g, g.speed_button)
        self.assertEqual(g.clock.speed, SPEEDS[1])
        self.assertEqual(g.towers, [])

    def test_double_speed_moves_enemies_twice_as_far(self):
        normal, fast = self.make(), self.make()
        self.start_wave(normal)
        self.start_wave(fast)
        self.key(fast, pygame.K_f)
        lead = lambda g: g.enemies[0].progress
        n0, f0 = lead(normal), lead(fast)
        normal.update(0.05)
        fast.update(0.05)
        self.assertAlmostEqual(lead(fast)-f0, 2*(lead(normal)-n0))

    def test_can_still_place_towers_while_paused(self):
        g = self.make()
        self.key(g, pygame.K_SPACE)
        spot = next((x, y) for y in range(24, 576, 12) for x in range(24, 960, 12)
                    if g.map.can_place(x, y, 16, []))
        g.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=spot))
        self.assertEqual(len(g.towers), 1)

    def test_restart_resets_pause_and_speed(self):
        g = self.make()
        self.key(g, pygame.K_SPACE)
        self.key(g, pygame.K_f)
        g.restart()
        self.assertFalse(g.clock.paused)
        self.assertEqual(g.clock.speed, SPEEDS[0])


if __name__ == '__main__':
    unittest.main()
