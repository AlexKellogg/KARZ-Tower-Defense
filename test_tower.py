import unittest

from enemy import PlaceholderEnemy
from tower import Tower, TowerLevel, BASE_TOWER_LEVELS

ROUTE = [(0, 0), (100, 0), (100, 100)]


def enemy_at(progress, hp=100):
    e = PlaceholderEnemy(ROUTE, hp=hp)
    e.progress = progress
    return e


class EnemyTests(unittest.TestCase):
    def test_moves_along_route_and_finishes(self):
        e = PlaceholderEnemy(ROUTE, speed=50)
        e.update(1)
        self.assertEqual(e.pos, (50, 0))
        e.update(2)
        self.assertEqual(e.pos, (100, 50))
        e.update(10)
        self.assertTrue(e.reached_end)
        self.assertFalse(e.alive)

    def test_take_damage_reports_kill(self):
        e = PlaceholderEnemy(ROUTE, hp=10)
        self.assertFalse(e.take_damage(4))
        self.assertTrue(e.take_damage(10))
        self.assertEqual(e.hp, 0)
        self.assertFalse(e.take_damage(1))


class TowerTests(unittest.TestCase):
    def test_targets_furthest_enemy_in_range(self):
        t = Tower(50, 20, levels=(TowerLevel(range=60, damage=5, fire_rate=1),))
        near_start = enemy_at(40)
        further = enemy_at(80)
        out_of_range = enemy_at(195)
        self.assertIs(t.pick_target([near_start, further, out_of_range]), further)

    def test_ignores_enemies_out_of_range_or_dead(self):
        t = Tower(500, 500)
        self.assertIsNone(t.pick_target([enemy_at(50)]))
        t = Tower(50, 20)
        dead = enemy_at(50, hp=1)
        dead.take_damage(1)
        self.assertIsNone(t.pick_target([dead]))

    def test_cooldown_limits_fire_rate(self):
        t = Tower(50, 20)
        e = enemy_at(50, hp=1000)
        rate, dmg = t.stats.fire_rate, t.stats.damage
        self.assertIs(t.update(0.01, [e]), e)
        self.assertIsNone(t.update(0.01, [e]))
        t.update(1/rate, [e])
        self.assertEqual(e.hp, 1000-2*dmg)

    def test_upgrades_improve_stats_and_stop_at_max(self):
        t = Tower(0, 0)
        for before, after in zip(BASE_TOWER_LEVELS, BASE_TOWER_LEVELS[1:]):
            self.assertTrue(t.can_upgrade)
            self.assertTrue(t.upgrade())
            self.assertGreater(after.damage, before.damage)
            self.assertGreaterEqual(after.range, before.range)
        self.assertFalse(t.can_upgrade)
        self.assertFalse(t.upgrade())
        self.assertEqual(t.level, len(BASE_TOWER_LEVELS)-1)

    def test_footprint_works_with_map_placement(self):
        t = Tower(10, 20, radius=16)
        self.assertEqual(t.footprint, (10, 20, 16))
        self.assertTrue(t.contains(20, 20))
        self.assertFalse(t.contains(40, 20))


if __name__ == '__main__':
    unittest.main()