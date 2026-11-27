"""Simple per-run tower defense economy."""

STARTING_MONEY = 150
TOWER_COST = 50
UPGRADE_COSTS = (40, 70)


class Economy:
    def __init__(self, sandbox=False, starting_money=STARTING_MONEY):
        self.sandbox = sandbox
        self.money = starting_money
        self.spent = 0
        self.earned = 0

    def can_afford(self, amount):
        return self.sandbox or self.money >= amount

    def spend(self, amount):
        if amount < 0:
            raise ValueError('Cost cannot be negative')
        if not self.can_afford(amount):
            return False
        if not self.sandbox:
            self.money -= amount
            self.spent += amount
        return True

    def earn(self, amount):
        if amount < 0:
            raise ValueError('Reward cannot be negative')
        if not self.sandbox:
            self.money += amount
            self.earned += amount

    def refund(self, amount):
        """Gives money back for a removed tower. Refunds are not earnings and cancel out what was spent."""
        if amount < 0:
            raise ValueError('Refund cannot be negative')
        if not self.sandbox:
            self.money += amount
            self.spent = max(0, self.spent-amount)

    @staticmethod
    def upgrade_cost(tower):
        costs = tower.spec.upgrade_costs if hasattr(tower,'spec') else UPGRADE_COSTS
        return costs[tower.level] if tower.can_upgrade else None

    @staticmethod
    def tower_refund(tower):
        if hasattr(tower,'spec'):
            return tower.spec.cost + sum(tower.spec.upgrade_costs[:tower.level])
        return TOWER_COST + sum(UPGRADE_COSTS[:tower.level])
