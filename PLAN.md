# Bomb Jack — Telegram Mini-App: Master Plan

Game: Tehkan 1984 arcade **Bomb Jack** (see docs/GAME-SPEC.md). Platform: Telegram Mini App in the existing Tetris bot, mobile landscape, GitHub Pages (HTTPS required by Telegram).

## 0. Resilience protocol (BSOD-proof)
- **PROGRESS.md is the single source of truth.** Any new session: read PROGRESS.md + PLAN.md, resume. Never trust chat history.
- Commit + push after EVERY phase (batch git ops into one elevated call).
- Research artifacts saved under research/ (re-fetchable via research/fetch.py — needs one elevated run).
- Small writes only (≤ ~4KB per tool call); verify byte length after each write (this model truncates long payloads — observed).
- Public repo contains NO copyrighted screenshots: `research/` gitignored; sprites are procedurally redrawn pixel art (no ROM data).

## 1. Architecture (mirrors the Tetris reference)
- Repo `horaboral/bombjack-miniapp` (new; user-confirmed). Reference repo has exactly: `PLAN.md` + one self-contained `tetris.html` (38KB). We mirror that:
  - **`bombjack.html`** — the entire game in ONE file: HTML shell, CSS, all JS. Canvas + pointer events (no DOM buttons, like Tetris). No build step, no dependencies.
  - Telegram WebApp SDK from CDN (`https://telegram.org/js/telegram-web-app.js`) + inline fallback shim (pattern: research/tetris-ref/tetris.html lines 5–36).
  - `meta viewport` = `width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no`; `touch-action:none`; `-webkit-user-select:none`.
  - WebAudio for sound (start on first user gesture — mobile policy).
- Deploy: GitHub Pages on `main` root → `https://horaboral.github.io/bombjack-miniapp/` (enable via API in Phase 8).
- Local dev: open bombjack.html directly (file:// works — no fetches); desktop keyboard for fast iteration.

## 2. Touch controls (hero on touchscreen — the critical design)
Original: 8-way joystick + 1 jump button (hold = jump height; mid-air tap = hover).
- **Left ~45% of screen: floating virtual joystick.** Touch down anywhere in left zone → stick base appears under finger; 8-way analog; dead-zone 0.2; max travel ~55px. X = horizontal run; Y = vertical intent (up = boost jump, down = fast-fall). Finger may slide; stick clamps to zone. On release → stick vanishes, inputs zeroed.
- **Right side: one big JUMP button** (drawn on canvas, bottom-right, ~30% screen height, thumb-reachable).
  - Hold duration = jump height: sample hold time; ≥ ~140ms = full jump, shorter = proportional (min tap height).
  - Mid-air fresh tap = **hover**: slow controlled descent (≈1/3 fall speed) until tap again or landing. This is the original's signature move.
- **Multi-touch**: track pointer ids separately (stick pointer ≠ jump pointer); `pointerdown/move/up/cancel` + `e.preventDefault()`; both hands always usable simultaneously.
- **Landscape lock**: portrait → full overlay "ROTATE YOUR PHONE"; re-check on `resize`/`orientationchange`; respect safe-area insets (`env(safe-area-inset-*)`).
- **Haptics** (Telegram HapticFeedback): light = bomb pickup (pitched), medium = power-up, heavy = death.
- Desktop debug keys (dev only): arrows + space.
- Why not tap-to-jump anywhere: original is stick+button; a dedicated hold-sensitive button preserves the hold-to-jump-height and hover semantics that make the game playable.

## 3. Game code structure (inside bombjack.html)
- `CONFIG` — ALL tunable constants (palette, speeds, sizes, scoring) in one object → fidelity tuning is constant edits.
- `SCREENS[]` — 5 screen defs: platform AABBs, bomb positions (24), background theme.
- `Input` — pointer state → `{stickX, stickY, jumpHeld, jumpPressed}` (unified keyboard/pointer).
- `Player` — physics: run accel/friction, hold-based jump impulse, gravity, fast-fall, hover timer, platform collisions, lives, invuln flash after respawn.
- `Bombs` — 24 instances, lit-sequence state, pickup scoring, bonus-meter fill.
- `Enemies` — spawner (from top, ≤6, escalating), types: bird / mummy / ufo / orb, morph ground↔air phases.
- `Powerups` — hexagon P/B/E/S, drift, effects (freeze→coins, multiplier, extra life, free credit).
- `Coins` — 100–2,000 colored, × multiplier.
- `Sprites` — procedural pixel art: draw pixel grids to offscreen canvases at load (Jack 4 poses, bomb lit/unlit, 4 enemies, hexagon, coins, background silhouettes).
- `HUD` — score, multiplier, bonus meter bar, lives, level; round-clear & game-over panels; high score + 3-letter initials (localStorage).
- `Telegram` — SDK init, MainButton (PLAY/RESTART), themeParams bg, HapticFeedback, sendData for score.
- Loop: `requestAnimationFrame` + fixed 1/60 accumulator (deterministic physics).

## 4. Phases
- **Phase 0 — Research & plan (DONE):** sources in research/, GAME-SPEC.md, this plan, PROGRESS.md.
- **Phase 1 — Scaffold (needs PAT):** create repo via GitHub API; git init; commit docs; bombjack.html skeleton (shell, landscape overlay, title screen, loop, SDK+shim). *Accept: title screen renders on phone via file:// and in dev browser; push.*
- **Phase 2 — Fidelity anchors:** fetch full-res screenshot (https://upload.wikimedia.org/wikipedia/en/e/e6/Bombjack_Screenshot.png, elevated one-shot); write research/palette.py (pure-stdlib PNG decode: dominant palette, dimensions, sprite bounding boxes) → research/palette.json; hardcode palette + screen metrics into CONFIG; start docs/FIDELITY.md. *Accept: palette.json exists, CONFIG uses it; push.*
- **Phase 3 — Player Jack:** procedural sprites (run/jump/hover/fall), physics per §2, 5 SCREENS with platforms, death/respawn/lives. *Accept: full movement across all 5 screens incl. platform-free #5; push.*
- **Phase 4 — Bombs & scoring:** 24 bombs/layout, lit-sequence, 100/200 × multiplier, bonus meter UI, round-end 20–23 bonus, extra life @50k, round flow (5-cycle loop, escalation). *Accept: complete round plays with correct scores; push.*
- **Phase 5 — Enemies:** top-of-screen spawns (≤6), bird/mummy/ufo/orb AI, ground↔air morph, within-round + cross-round escalation. *Accept: behaviors match GAME-SPEC; push.*
- **Phase 6 — Power-ups & coins:** P/B/E/S hexagons + spawn triggers, freeze→coins (100–2,000 × mult), multiplier, extra life, free credit. *Accept: all four + coins work; push.*
- **Phase 7 — Sound, HUD polish, high score:** WebAudio bleeps (gesture-gated), round transitions, game-over + initials (localStorage), Telegram MainButton/theme/haptics/sendData score. *Accept: full loop with juice; push.*
- **Phase 8 — Telegram deploy (needs bot token):** enable GitHub Pages via API; set bot menu — BotFather main-button → Bomb Jack (user confirms menu layout: replace Tetris vs. add /tetris + /bombjack commands); test end-to-end on real phone. *Accept: full round playable from bot on phone; push.*
- **Phase 9 — Fidelity iteration loop:** user plays 2 min → deltas into docs/FIDELITY.md (palette, sprite shapes, bomb placement, movement feel, enemy speeds, HUD) → fix CONFIG/sprites → repeat until user says it feels right (gate: 3 consecutive clean rounds).

## 5. Fidelity methodology (no emulator, no image input on this model)
1. Reference screenshots on disk (research/refs/) — user views them; I extract palette/geometry programmatically (research/palette.py).
2. docs/FIDELITY.md — living delta table (original → implemented → fix).
3. Every session ends with one user check: "play 2 minutes, what's off?"
4. All tunables in CONFIG → iteration = constant edits, not rewrites.

## 6. Risks & mitigations
- qwen38 truncates long tool payloads (observed): small writes, verify lengths, chunked rebuilds.
- Sandbox kills external binaries + SChannel TLS: one elevated one-shot per batch of external work; batch aggressively (one script per approval).
- git push needs elevation each time → push once per phase, not per commit.
- Bot-blocked sources: content already saved; don't re-fetch.
- Copyright: research/refs gitignored; procedural redraw only.
- Context limits: PROGRESS.md = resume point; keep chat lean.

## 7. Credentials (gates)
- [PENDING] GitHub PAT for `horaboral` → gates Phases 1 & 8.
- [PENDING] Bot token for Tetris bot (id 8699678610) → gates Phase 8.

