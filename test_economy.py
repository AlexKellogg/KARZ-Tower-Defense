import unittest

from economy import Economy, STARTING_MONEY, TOWER_COST


class Tower:
    def __init__(self, x, y):
        self.level = 0

    @property
    def can_upgrade(self):
        return self.level < 2

    def upgrade(self):
        self.level += 1


class EconomyTests(unittest.TestCase):
    def test_purchase_and_insufficient_funds(self):
        economy = Economy()
        self.assertEqual(economy.money, STARTING_MONEY)
        self.assertTrue(economy.spend(TOWER_COST))
        self.assertEqual(economy.money, STARTING_MONEY - TOWER_COST)
        self.assertFalse(economy.spend(999))
        self.assertEqual(economy.money, STARTING_MONEY - TOWER_COST)

    def test_kill_reward(self):
        economy = Economy()
        economy.earn(5)
        self.assertEqual(economy.money, STARTING_MONEY + 5)

    def test_upgrades_and_refund(self):
        economy = Economy()
        tower = Tower(100, 100)
        self.assertEqual(economy.upgrade_cost(tower), 40)
        tower.upgrade()
        self.assertEqual(economy.upgrade_cost(tower), 70)
        self.assertEqual(economy.tower_refund(tower), 90)
        tower.upgrade()
        self.assertIsNone(economy.upgrade_cost(tower))
        self.assertEqual(economy.tower_refund(tower), 160)

    def test_sandbox_does_not_change_balance(self):
        economy = Economy(sandbox=True)
        self.assertTrue(economy.spend(10000))
        economy.earn(100)
        self.assertEqual(economy.money, STARTING_MONEY)

    def test_negative_amount_rejected(self):
        economy = Economy()
        with self.assertRaises(ValueError):
            economy.spend(-1)
        with self.assertRaises(ValueError):
            economy.earn(-1)


if __name__ == '__main__':
    unittest.main()
