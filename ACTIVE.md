# Drift2D — Active State

Last updated: 2026-04-14

## Goal
Prove Drift2D works across multiple game genres, not just platformers.

## Status
- Jungle Kong (DKC-style platformer) — 5 levels, improved bot, score system — done, on master
- Sokoban example — done, at examples/sokoban/

## What was just done
Jungle Kong iteration 4:
- **Bot AI (autoplay.py)**: added `_last_y` vertical-stuck tracker (jump if stuck 2s), barrel
  approach logic (move toward barrel and jump into it when close), random jump timing variation
  (changes every 0.8-2s so bot isn't robotic), falling-platform steering (scans tilemap while
  falling at vy > 200 and steers toward nearest platform below).
- **Level 4**: vertical-heavy level, 5 enemies, 6 barrels required for progression, 21 rows x 54 cols.
- **Level 5**: boss gauntlet, 24 rows, 18 enemies, 5 bananas, narrow platforms, door far right.
- **Score system (game.py)**: +10 per banana, +100 per enemy kill, score carries across levels.
  Aerial combo multiplier (x2, x3... capped x8) for consecutive kills without landing. Score
  displayed in HUD. Banana HUD count flashes yellow->white for 0.4s after collection. Combo
  text displayed near bottom of screen when combo >= 2.

## Next steps
- Consider top-down shooter or match-3 example for further genre breadth
- Level 5 has no barrels — could add a barrel section for variety
- Combo counter could decay more gracefully (fade out rather than instant reset)
