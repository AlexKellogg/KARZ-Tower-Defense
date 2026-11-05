"""Simple per-run tower defense economy."""

STARTING_MONEY = 150
TOWER_COST = 50
UPGRADE_COSTS = (40, 70)


class Economy:
    def __init__(self, sandbox=False, starting_money=STARTING_MONEY):
        self.sandbox = sandbox
        self.money = starting_money

    def can_afford(self, amount):
        return self.sandbox or self.money >= amount

    def spend(self, amount):
        if amount < 0:
            raise ValueError('Cost cannot be negative')
        if not self.can_afford(amount):
            return False
        if not self.sandbox:
            self.money -= amount
        return True

    def earn(self, amount):
        if amount < 0:
            raise ValueError('Reward cannot be negative')
        if not self.sandbox:
            self.money += amount

    @staticmethod
    def upgrade_cost(tower):
        return UPGRADE_COSTS[tower.level] if tower.can_upgrade else None

    @staticmethod
    def tower_refund(tower):
        return TOWER_COST + sum(UPGRADE_COSTS[:tower.level])
