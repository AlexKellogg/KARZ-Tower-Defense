import unittest

from game_session import (FIRST_WAVE_DELAY, POINTS_PER_KILL, POINTS_PER_LIFE_LEFT, SPAWN_GAP,
                          STARTING_LIVES, TOTAL_WAVES, WAVE_BREAK, GameSession, format_time, wave_size)


def play_wave(session, alive):
    spawned = []
    while session.to_spawn > 0 or not spawned:
        spawned += session.update(SPAWN_GAP, alive+len(spawned))
    return spawned


class SessionTests(unittest.TestCase):
    def test_first_wave_starts_after_delay_and_spawns_the_full_wave(self):
        s = GameSession('Easy')
        self.assertEqual(s.update(FIRST_WAVE_DELAY-0.1, 0), [])
        self.assertEqual(s.wave, 0)
        s.update(0.2, 0)
        self.assertEqual(s.wave, 1)
        self.assertEqual(len(play_wave(s, 0)), wave_size(1))

    def test_clearing_every_wave_wins(self):
        s = GameSession('Easy')
        s.update(FIRST_WAVE_DELAY, 0)
        for wave in range(1, s.clear_wave+1):
            for _ in play_wave(s, 0):
                s.enemy_killed()
            s.update(0.1, 0)
            self.assertEqual(s.waves_cleared, wave)
            if wave < s.clear_wave:
                self.assertTrue(s.between_waves)
                s.update(WAVE_BREAK, 0)
        self.assertEqual(s.status, 'won')
        result = s.result()
        self.assertTrue(result.won)
        self.assertEqual(result.lives_lost, 0)
        self.assertEqual(result.waves_cleared, s.clear_wave)
        kills = sum(wave_size(w) for w in range(1, s.clear_wave+1))
        self.assertEqual(result.kills, kills)
        self.assertEqual(result.score, kills*POINTS_PER_KILL+STARTING_LIVES*POINTS_PER_LIFE_LEFT)

    def test_wave_is_not_cleared_while_enemies_are_alive(self):
        s = GameSession('Easy')
        s.update(FIRST_WAVE_DELAY, 0)
        play_wave(s, 0)
        s.update(5, enemies_alive=3)
        self.assertEqual(s.waves_cleared, 0)
        self.assertFalse(s.finished)

    def test_losing_every_life_loses_and_stops_counting(self):
        s = GameSession('Easy')
        for _ in range(STARTING_LIVES-1):
            s.enemy_leaked()
        self.assertEqual((s.lives, s.status), (1, 'playing'))
        s.enemy_leaked()
        self.assertEqual((s.lives, s.status), (0, 'lost'))
        s.enemy_leaked()
        s.enemy_killed()
        self.assertEqual((s.leaked, s.kills), (STARTING_LIVES, 0))
        self.assertEqual(s.update(10, 0), [])
        self.assertFalse(s.result().won)

    def test_loss_score_only_counts_kills(self):
        s = GameSession('Easy')
        s.kills = 7
        s.waves_cleared = 2
        s.status = 'lost'
        self.assertEqual(s.score, 7*POINTS_PER_KILL)

    def test_harder_difficulties_have_tougher_enemies_and_bigger_scores(self):
        easy, impossible = GameSession('Easy'), GameSession('Impossible')
        for s in (easy, impossible):
            s.wave = 3
            s.kills = 10
        self.assertGreater(impossible.enemy_stats()[0], easy.enemy_stats()[0])
        self.assertGreater(impossible.enemy_stats()[1], easy.enemy_stats()[1])
        self.assertGreater(impossible.score, easy.score)

    def test_maps_set_their_own_clear_wave(self):
        self.assertEqual(GameSession('Easy').clear_wave, 5)
        self.assertEqual(GameSession('Medium').clear_wave, 7)
        self.assertEqual(GameSession('Hard').clear_wave, 10)
        self.assertEqual(GameSession('Impossible').clear_wave, 10)

    def test_timer_only_runs_while_playing(self):
        s = GameSession('Easy')
        s.update(1.5, 0)
        s.status = 'lost'
        s.update(10, 0)
        self.assertEqual(s.result().time_seconds, 1.5)
        self.assertEqual(format_time(83.9), '1:23')
        self.assertEqual(format_time(5), '0:05')


class SandboxTests(unittest.TestCase):
    def test_sandbox_keeps_going_past_the_last_wave(self):
        s = GameSession('Hard', sandbox=True)
        s.update(FIRST_WAVE_DELAY, 0)
        for _ in range(TOTAL_WAVES+3):
            play_wave(s, 0)
            s.update(0.1, 0)
            s.update(WAVE_BREAK, 0)
        self.assertFalse(s.finished)
        self.assertEqual(s.waves_cleared, TOTAL_WAVES+3)
        self.assertGreater(s.enemy_stats()[0], GameSession('Hard').enemy_stats()[0])

    def test_sandbox_leaks_never_cost_lives_or_end_the_game(self):
        s = GameSession('Easy', sandbox=True)
        for _ in range(STARTING_LIVES*3):
            s.enemy_leaked()
        self.assertEqual((s.lives, s.leaked, s.status), (STARTING_LIVES, STARTING_LIVES*3, 'playing'))

    def test_skip_break_starts_the_next_wave_right_away(self):
        s = GameSession('Easy', sandbox=True)
        self.assertTrue(s.between_waves)
        s.skip_break()
        s.update(0.01, 0)
        self.assertEqual(s.wave, 1)
        s.skip_break()
        self.assertEqual(s.wave, 1)


if __name__ == '__main__':
    unittest.main()
