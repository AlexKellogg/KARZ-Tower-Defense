import json
import os
import unittest

os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import pygame
from backend import checkpoint_json,AccountError
from economy import Economy
from enemy import PlaceholderEnemy
from game_session import GameSession,WAVE_CLEAR_BONUS
from tower import Tower,TOWER_TYPES


class PolishLogicTests(unittest.TestCase):
    def test_manual_start_waits_without_counting_time(self):
        s=GameSession('Hard',manual_start=True)
        self.assertEqual(s.update(50,0),[])
        self.assertEqual((s.wave,s.elapsed),(0,0))
        s.start_first_wave();s.update(.01,0)
        self.assertEqual(s.wave,1)

    def test_bonus_paid_once_and_not_kill_income(self):
        s=GameSession('Hard');s.wave=1;s.to_spawn=0
        s.update(.01,0)
        self.assertEqual(s.economy.money,180+WAVE_CLEAR_BONUS)
        self.assertEqual(s.economy.earned,0)
        s.update(.01,0)
        self.assertEqual(s.economy.money,200)
        snap=s.snapshot();r=GameSession.resume('Hard',snap);r.update(.01,0)
        self.assertEqual(r.economy.money,200)

    def test_bonus_on_final_wave_not_loss_or_sandbox(self):
        for sandbox in (False,True):
            s=GameSession('Easy',sandbox=sandbox);s.wave=5;s.waves_cleared=4
            s.update(.01,0)
            self.assertEqual(s.economy.money,150 if sandbox else 170)
        s=GameSession('Hard');s.status='lost';s.wave=1;s.update(.1,0)
        self.assertEqual(s.economy.money,180)

    def test_trial_balance(self):
        for name,cash in [('Hard',180),('Impossible',200)]:
            s=GameSession(name)
            self.assertEqual(s.economy.money,cash)
            self.assertEqual(s.enemy_stats(1),(38,88))
            self.assertEqual(s.enemy_stats(10),(96,88))
        self.assertEqual(GameSession('Easy').enemy_stats(1),(24,80))
        self.assertEqual(GameSession('Medium').enemy_stats(1),(34,88))

    def test_slow_refresh_no_stacking_and_partial_expiry(self):
        e=PlaceholderEnemy([(0,0),(1000,0)],speed=100)
        e.apply_slow(.5,1);e.apply_slow(.5,1);e.apply_slow(.7,5)
        e.update(1.5)
        self.assertAlmostEqual(e.progress,100)
        self.assertEqual(e.slow_factor,1)
        e.apply_slow(.65,2);e.update(.5);e.apply_slow(.65,2)
        self.assertEqual(e.slow_remaining,2)

    def test_cryo_actually_slows(self):
        e=PlaceholderEnemy([(0,0),(300,0)],hp=50,speed=100);e.progress=30
        t=Tower(30,20,tower_type='cryo');t.update(.01,[e])
        self.assertEqual(e.hp,48)
        e.update(1)
        self.assertAlmostEqual(e.progress,95)

    def test_mortar_filters_splash_and_counts_each_victim(self):
        enemies=[PlaceholderEnemy([(0,0),(400,0)],hp=10) for _ in range(3)]
        for e,p in zip(enemies,(30,40,50)):e.progress=p
        t=Tower(30,20,tower_type='mortar')
        t.update(.01,enemies,lambda e:e is not enemies[1])
        self.assertEqual([e.hp for e in enemies],[0,10,0])
        self.assertEqual(len(t.last_hits),2)
        t.update(.01,enemies,lambda e:False)
        self.assertEqual(t.last_hits,[])

    def test_type_costs_upgrades_and_full_refunds(self):
        for kind,spec in TOWER_TYPES.items():
            e=Economy(starting_money=1000);t=Tower(0,0,tower_type=kind)
            e.spend(spec.cost)
            for cost in spec.upgrade_costs:
                self.assertEqual(e.upgrade_cost(t),cost)
                e.spend(cost);t.upgrade()
            self.assertIsNone(e.upgrade_cost(t))
            e.refund(e.tower_refund(t));self.assertEqual(e.money,1000)


class PolishScreenTests(unittest.TestCase):
    def setUp(self):
        pygame.init();pygame.display.set_mode((960,780))
        from game_screen import GameScreen,DIFFICULTIES
        self.game=GameScreen(DIFFICULTIES[2],on_exit=lambda:None,manual_start=True)

    def tearDown(self):pygame.quit()

    def click(self,pos):self.game.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=pos))

    def test_shop_purchase_cancel_and_start(self):
        g=self.game
        self.click(g.shop_buttons['cryo'].center)
        self.click((72,72))
        self.assertEqual(g.towers[0].tower_type,'cryo')
        self.assertEqual(g.session.economy.money,120)
        g.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=3,pos=(0,0)))
        self.click((120,72));self.assertEqual(len(g.towers),1)
        self.click(g.start_button.center);g.update(.01)
        self.assertEqual(g.session.wave,1)

    def test_insufficient_money_is_visible_and_no_purchase(self):
        g=self.game;g.session.economy.money=10
        self.click(g.shop_buttons['mortar'].center);self.click((72,72))
        self.assertEqual(g.towers,[])
        self.assertIn('Need $80',g.feedback)
        self.assertEqual(g.session.economy.money,10)

    def test_mixed_save_roundtrip_and_legacy(self):
        g=self.game;saved=[];g.on_checkpoint=saved.append
        g.session.wave=g.session.waves_cleared=1
        g.towers=[Tower(72+i*48,72,tower_type=kind) for i,kind in enumerate(TOWER_TYPES)]
        g.checkpoint();state=json.loads(checkpoint_json('Hard','regular',saved[0]))
        g.restart(state)
        self.assertEqual([t.tower_type for t in g.towers],list(TOWER_TYPES))
        legacy={**state,'towers':[{'x':72,'y':72,'level':1}]}
        g.restart(legacy);self.assertEqual(g.towers[0].tower_type,'cannon')
        with self.assertRaises(AccountError):
            checkpoint_json('Hard','regular',{**state,'towers':[{'x':72,'y':72,'level':1,'type':'bad'}]})

    def test_splash_kills_reward_once_and_respects_real_tunnel(self):
        g=self.game;g.session.start_first_wave()
        # Two exposed enemies along the middle horizontal road; one under the roof.
        g.session.wave=1;g.session.to_spawn=1;g.session.spawn_timer=100
        visible=[PlaceholderEnemy([(408,264),(500,264)],hp=10,speed=0) for _ in range(2)]
        hidden=PlaceholderEnemy([(552,360),(552,400)],hp=10,speed=0)
        g.enemies=visible+[hidden];g.towers=[Tower(456,312,tower_type='mortar')]
        g.step(.01)
        self.assertEqual(g.session.kills,2)
        self.assertEqual(g.session.economy.money,190)
        self.assertEqual(hidden.hp,10)
        g.step(.01);self.assertEqual(g.session.kills,2)


if __name__=='__main__':unittest.main()
