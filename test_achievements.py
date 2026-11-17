import os
import unittest

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

import pygame

from achievements import ACHIEVEMENT_IDS, ACHIEVEMENTS, AchievementTracker
from economy import TOWER_COST, Economy
from test_checkpoints import add_strong_towers, play_until
from tower import Tower


def ids(found):
    return [a.id for a in found]


class DefinitionTests(unittest.TestCase):
    def test_ids_are_unique_and_short_enough_for_the_database(self):
        self.assertEqual(len(ACHIEVEMENT_IDS), len(set(ACHIEVEMENT_IDS)))
        self.assertTrue(all(len(i) <= 40 for i in ACHIEVEMENT_IDS))

    def test_the_first_set_from_the_backlog_is_there(self):
        for wanted in ('first_win', 'flawless', 'builder', 'hard_win'):
            self.assertIn(wanted, ACHIEVEMENT_IDS)

    def test_every_achievement_tracks_a_real_stat(self):
        tracker = AchievementTracker()
        for achievement in ACHIEVEMENTS:
            self.assertTrue(hasattr(tracker.progress, achievement.stat), achievement.id)


class TrackerTests(unittest.TestCase):
    def test_ten_towers_on_the_map_unlocks_builder_once(self):
        tracker = AchievementTracker()
        found = []
        for count in range(1, 13):
            found += tracker.tower_built(count)
        self.assertEqual(ids(found), ['builder'])

    def test_placing_and_refunding_one_tower_does_not_count_as_ten(self):
        tracker = AchievementTracker()
        for _ in range(12):
            self.assertEqual(tracker.tower_built(1), [])

    def test_wave_clears(self):
        tracker = AchievementTracker()
        self.assertEqual(tracker.wave_cleared(4), [])
        self.assertEqual(ids(tracker.wave_cleared(5)), ['survivor'])

    def test_max_level_tower(self):
        tracker = AchievementTracker()
        tower = Tower(0, 0)
        tower.upgrade()
        self.assertEqual(tracker.tower_upgraded(tower), [])
        tower.upgrade()
        self.assertEqual(ids(tracker.tower_upgraded(tower)), ['fully_loaded'])

    def test_wins(self):
        self.assertEqual(ids(AchievementTracker().game_won('Easy', lives_lost=3)), ['first_win'])
        self.assertEqual(ids(AchievementTracker().game_won('Medium', lives_lost=0)), ['first_win', 'flawless'])
        self.assertEqual(ids(AchievementTracker().game_won('Hard', lives_lost=2)), ['first_win', 'hard_win'])

    def test_gold_milestones_come_from_the_economy(self):
        tracker, economy = AchievementTracker(), Economy(starting_money=1000)
        for _ in range(79):
            economy.earn(5)
        self.assertEqual(tracker.economy_changed(economy), [])
        economy.earn(5)
        self.assertEqual(ids(tracker.economy_changed(economy)), ['gold_rush'])
        economy.spend(499)
        self.assertEqual(tracker.economy_changed(economy), [])
        economy.spend(1)
        self.assertEqual(ids(tracker.economy_changed(economy)), ['big_spender'])

    def test_already_unlocked_ones_are_not_repeated(self):
        tracker = AchievementTracker(already={'first_win'})
        self.assertEqual(ids(tracker.game_won('Hard', lives_lost=1)), ['hard_win'])
        self.assertEqual(tracker.unlocked, {'first_win', 'hard_win'})

    def test_disabled_tracker_never_unlocks(self):
        tracker = AchievementTracker(enabled=False)
        for _ in range(20):
            self.assertEqual(tracker.tower_built(20), [])
        self.assertEqual(tracker.game_won('Hard', 0), [])


class EconomyTotalTests(unittest.TestCase):
    def test_spent_and_earned_totals(self):
        economy = Economy()
        economy.spend(TOWER_COST)
        economy.earn(5)
        self.assertEqual((economy.spent, economy.earned), (TOWER_COST, 5))

    def test_refunds_cancel_spending_and_are_not_earnings(self):
        economy = Economy()
        economy.spend(TOWER_COST)
        economy.refund(TOWER_COST)
        self.assertEqual((economy.money, economy.spent, economy.earned), (150, 0, 0))
        with self.assertRaises(ValueError):
            economy.refund(-1)

    def test_sandbox_counts_nothing(self):
        economy = Economy(sandbox=True)
        economy.spend(500)
        economy.earn(500)
        economy.refund(50)
        self.assertEqual((economy.spent, economy.earned), (0, 0))


class GameScreenAchievementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((1, 1))

    @classmethod
    def tearDownClass(cls):
        import ui
        ui._font.cache_clear()

    def make(self, sandbox=False, known=(), fail=False):
        from game_screen import DIFFICULTIES, GameScreen
        self.saved = []

        def unlock(new_ids):
            if fail:
                raise ConnectionError('server down')
            self.saved.append(list(new_ids))

        return GameScreen(DIFFICULTIES[0], on_exit=lambda: None, on_finish=lambda result: (), sandbox=sandbox,
                          on_achievements=unlock, achievements=known)

    def click(self, screen, x, y):
        screen.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(x, y)))

    def build_spots(self, screen, count):
        spots = [(x, y) for y in range(24, 576, 24) for x in range(24, 960, 24)
                 if screen.map.can_place(x, y, 16, [])]
        built = 0
        for x, y in spots:
            if built == count:
                break
            before = len(screen.towers)
            self.click(screen, x, y)
            built += len(screen.towers) > before
        return built

    def test_winning_saves_first_win_and_shows_a_popup(self):
        g = self.make()
        add_strong_towers(g)
        play_until(g, 5)
        self.assertTrue(g.result.won)
        self.assertIn(['first_win'], [s[:1] for s in self.saved])
        self.assertIn('first_win', g.known_achievements)
        self.assertTrue(g.toasts)
        g.draw(pygame.display.get_surface())

    def test_wave_clears_and_kill_money_feed_the_tracker(self):
        g = self.make()
        add_strong_towers(g)
        play_until(g, 5)
        unlocked = {i for batch in self.saved for i in batch}
        self.assertIn('survivor', unlocked)
        self.assertGreater(g.tracker.progress.gold_earned, 0)
        self.assertEqual(g.tracker.progress.gold_earned, g.session.economy.earned)

    def test_building_towers_unlocks_builder(self):
        g = self.make()
        g.session.economy.money = 10_000
        self.assertEqual(self.build_spots(g, 10), 10)
        self.assertIn('builder', [i for batch in self.saved for i in batch])
        self.assertIn('builder', [t[0].id for t in g.toasts])

    def test_known_achievements_do_not_pop_up_again(self):
        g = self.make(known={'builder', 'big_spender'})
        g.session.economy.money = 10_000
        self.build_spots(g, 10)
        self.assertEqual(self.saved, [])

    def test_sandbox_never_unlocks(self):
        g = self.make(sandbox=True)
        self.build_spots(g, 12)
        add_strong_towers(g)
        play_until(g, 6)
        self.assertEqual(self.saved, [])
        self.assertEqual(g.toasts, [])

    def test_save_failure_does_not_crash_the_game(self):
        g = self.make(fail=True)
        g.session.economy.money = 10_000
        self.build_spots(g, 10)
        self.assertIn('builder', g.known_achievements)
        self.assertEqual(self.saved, [])

    def test_popups_show_one_at_a_time_and_expire(self):
        from achievements import BY_ID
        from game_screen import TOAST_TIME
        g = self.make()
        g.award([BY_ID['first_win'], BY_ID['flawless']])
        g.clock.paused = True
        g.update(TOAST_TIME+0.1)
        self.assertEqual([t[0].id for t in g.toasts], ['flawless'])
        g.update(TOAST_TIME+0.1)
        self.assertEqual(g.toasts, [])

    def test_play_again_keeps_what_was_unlocked(self):
        g = self.make()
        g.session.economy.money = 10_000
        self.build_spots(g, 10)
        g.restart()
        g.session.economy.money = 10_000
        self.build_spots(g, 10)
        unlocked = [i for batch in self.saved for i in batch]
        self.assertEqual(sorted(unlocked), ['big_spender', 'builder'])


if __name__ == '__main__':
    unittest.main()
