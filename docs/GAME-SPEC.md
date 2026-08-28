# Bomb Jack (arcade, Tehkan 1984) — Gameplay Spec

**Target game** (user-confirmed): the 1984 Tehkan ARCADE platformer "Bomb Jack" (JP: ボンジャック).
- Dev/publish: Tehkan (later Tecmo); lead design Michitaka Tsuruta, programming Kazutoshi Ueda; NA arcade: Kitkorp. JP Mar 1984, NA Oct 1984.
- NOT the Taito side-scrolling bomber "B-52 / Bomb Jack" (1982/84). NOT the NES "Mighty Bomb Jack" (1986, same layouts but scrolling passages).
- Sources: Wikipedia "Bomb Jack" (fetched: research/bombjack-wiki.*), Grokipedia "Bomb Jack" (research/grokipedia.*), StrategyWiki snippets via DuckDuckGo (direct fetch 403), screenshot research/refs/wiki-3.png.

## Core loop
- Fixed single screen per round, no scrolling. **Collect all 24 red bombs** to clear the round.
- Jack is a superhero who can high-jump and **float/hover in the air**. No weapons — pure evasion.
- Controls (original): **8-way joystick + 1 jump button**.
  - Hold jump longer → higher jump. In mid-air, **tap** jump → slow controlled descent (hover/glide).
  - Stick up/down modulates jump height / fall speed.

## Bombs & scoring
- 24 bombs per round, static placement per screen layout.
- First bomb collected → bombs **light up in sequence**; collecting a lit one lights the next.
- Unlit bomb = 100, lit bomb = 200, each × bonus multiplier (starts 1×, max 5× via B power-up).
- Jump = 10 pts (minor).
- **Round-end bonus** for collecting 20/21/22/23 lit bombs in sequence: 10,000 / 20,000 / 30,000 / 50,000.
- Bonus meter at top of screen: fills as bombs are collected (lit fill more); when full → **P** power-up appears.
- Extra life at 50,000 pts (operator-set in arcades; default ON in our port).

## Power-ups (glowing letter in hexagon, drifts across screen)
- **P** — freezes all enemies ~5 s; they become collectible coins (100–2,000 by color, × multiplier); Jack briefly invulnerable.
- **B** — score multiplier +1 (max 5×); +1,000 × multiplier; spawns coins.
- **E** — extra life; +1,000 × multiplier; appears periodically (every ~5,000 pts).
- **S** (rare) — +1,000 × multiplier, advances level, free credit (port: extra life).

## Enemies (spawn falling from top of screen; ~6 max on screen)
- **Bird** — patrols, then flies to chase Jack; dive-bombs.
- **Mummy** — walks along platforms, tracks Jack.
- **UFO/saucer** — accelerates when approaching Jack.
- **Orb** — aligns to Jack's row, bobs.
- Wiki: birds/mummies drop in and can **morph** into the floating saucer/orb types. Speed + spawn rate escalate over time within and across rounds.
- Touching any enemy = lose a life.

## Rounds / screens
- **5 distinct screen layouts/backgrounds** (Wikipedia; Grokipedia says 18 unique layouts over 5 themes: Egypt, Greece, Bavarian castle, city/harbor, night streets).
  → Plan: implement the 5 documented screens first; add more layouts in fidelity phase if warranted.
- **5th screen has no platforms at all** (aerial navigation).
- 3 lives. Arcade supported alternating 2P — out of scope (single player).

## Presentation
- Table-arcade pixel art: red bombs (lit = flashing), superhero Jack, platform silhouettes, themed backgrounds, top HUD (score, bonus meter, lives).
- Exact palette + geometry: extract programmatically from research/refs screenshots (Phase 2, pure-Python PNG decoder — this model has no image input; user is the visual judge).

## Open questions (verify in fidelity phase, w/ user + full-res screenshot)
1. Ladders? (Grokipedia claims mummies "climb ladders" — Wikipedia says nothing; screenshot check pending.)
2. Full enemy roster + exact behavior parameters (speeds, chase radii).
3. 18 layouts vs 5 — how many distinct platform maps existed.
4. Hover limits on the platform-free screen.
5. Sound: arcade had music chip; port = short WebAudio bleeps (no samples).
6. Exact screen resolution / sprite pixel sizes (Tehkan Z80 board).

## Corrections from user longplay review (2026-08-28, authoritative)
- Bomb states: RED bombs are FIXED (unlit). LIT bombs turn BLACK and MOVE (patrol). Sequence lighting starts after first pickup.
- Random power-up: makes enemies DESTRUCTIBLE BY CONTACT with Jack (touch kills).
- Screen cycle order (from longplay ROUND numbers): 1=pyramid, 2=Greek acropolis, 3=castle, 4=skyscraper/harbor, 5=night street (no platforms).
- Per-screen palettes: bezel + platform + sky colors change per screen (green/green/purple, orange/yellow/purple, gold/yellow/deep-blue, yellow/yellow/blue, cyan/none/near-black).
