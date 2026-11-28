# Final polish local test

Double-click **Play Final Test.cmd**. This uses the Python environment in your normal KARZ checkout, but runs this separate copy. No server or login is required. All four maps are unlocked. Choose Normal to test balance; Sandbox has free towers.

Your normal checkout, accounts, saves, and leaderboard are untouched. Test saves and run/checkpoint logs are stored in `.playtest-data/`. Nothing has been pushed.

## Trial changes

| Tower | Purchase | Two upgrades | Role |
| --- | ---: | --- | --- |
| Cannon | $50 | $40 / $70 | Existing single-target damage |
| Cryo | $60 | $45 / $70 | Low damage with a temporary slow; slows do not stack |
| Mortar | $80 | $55 / $85 | Splash damage against visible groups |

All towers have three levels and respect sight blockers and protected tunnels. Normal games award $20 after each cleared wave, in addition to existing kill rewards. Selling retains the full refund.

Hard starts with $180; Extreme (called Impossible in the UI) starts with $200. Both use 88 enemy speed and a 1.6 HP multiplier (38 HP in wave 1). Easy/Medium starting cash and enemies are unchanged. Clear-wave targets remain 5/7/10/10. These settings need human playtesting.

## Controls

- Choose a tower card or press 1 / 2 / 3, then click a build zone.
- Press Enter or click Start wave 1 when your defenses are ready.
- Click a placed tower to inspect it. U upgrades; Z sells for a full refund.
- Right-click cancels placement; B shows build zones.
- Space pauses; F changes speed.

Please note the map, wave, tower mix, cash, and whether a loss felt caused by insufficient damage, reach, or income. Try an ordinary stationary defense first; repeated pause/sell/rebuild should not be required for the intended normal-game experience.

The launcher records completed results and wave checkpoints in `.playtest-data/runs.jsonl`. Closing mid-wave resumes from the last saved wave checkpoint, not the exact closing instant.
