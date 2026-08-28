# Bomb Jack Mini-App — PROGRESS (read this FIRST in any new session)

Last updated: PLAYTEST ROUND 1 FIXES APPLIED (in progress — smoke/push pending). GitHub Pages still 404 (manual Settings→Pages step likely needed). Reasoning OFF applied to qwen38 (settings.yaml).

## State
- **Playtest Round 1 (2026-08-29): FIXES APPLIED, VERIFYING** — user feedback: "aspect ratio is off, pyramids badly drawn, jump too low, death sequence off (jack disappears), lit bombs all over the place + deadly, powerups spill out of play area, music absent".
  - Aspect: uniform letterbox (SC=fit + OX/OY centering), render translate fixed, pointer zones remapped through toLogical() so L/R zones track the playfield.
  - Pyramid bg: two-face shaded pyramids + sun + sphinx silhouette (replaced flat triangles).
  - Jump: JUMP_V 3.15→3.6, GRAV 0.16→0.15, JUMP_HOLD 0.045→0.055 (reaches upper platforms).
  - Death: spin+hop+fade animation over deadT (was instant disappear).
  - Lit bombs: max 2 move (most-recently-lit) with slow drift 0.035px/f; others light in place.
  - Powerups: spawn in-bounds (x 6..248, y 30..100), bounce off walls, 900-tick TTL.
  - Music: 32-step square-lead + triangle-bass chiptune; starts on newGame (gesture-gated), stops on game over.
  - VERIFIED: 6/6 script blocks node --check clean; headless smoke PASS (letterbox SC=2.163 exact, L/R zones correct, no NaN over 6000 ticks, powerups in-bounds, max 1-2 lit bombs actively moving, all 5 states render). Committed `f8cb6ed` + pushed to main.
- **Phase 0 Research & plan: DONE** → docs/GAME-SPEC.md, PLAN.md, research/ artifacts.
- **Phase 1: REPO LIVE** → `horaboral/bombjack-miniapp` created + pushed. Latest commit `acbe6e8`.
- **Phase 2 Palette: DONE** — 5 screens with palettes in bombjack.html SCREENS array. VIDEO is canonical visual reference.
- **Phases 3–7 (game core): DONE** → single `bombjack.html` (34KB, 6 `<script>` blocks, all node --check clean + headless smoke PASS):
  - Title / PLAY / ROUNDCLEAR / GAMEOVER / INITIALS state machine; fixed 60Hz loop.
  - 5 screens (pyramid, Greek, castle, skyscraper, night) cycling by round%5; per-screen sky/bezel/plat/ground colors + platforms + 24 bombs each.
  - 24-bomb lit sequence: all red/fixed until first pickup, then 1 lights per 40 ticks (black, slow patrol); 100/200 × mult; round bonus 20/21/22/23 lit = 10k/20k/30k/50k; round-clear check AFTER pickup loop (bug fixed in acbe6e8).
  - Enemies spawn from top (≤6): bird/mummy/UFO/orb + ground↔air morph, escalating speed.
  - Power-ups P(freeze)/B(+mult +coins)/E(+life)/S(touch-kill) in hexagons; bonus meter → powerup; coins.
  - Touch controls per CONTROLS.md v2: left-45% relative-drag steer (dead-zone/full-px), right-55% tap/hold jump + mid-air glide + fast-fall; pointerId multi-touch; HapticFeedback; landscape "ROTATE" overlay; desktop arrows+space.
  - WebAudio bleeps (user-gesture gated), Telegram SDK CDN + shim + MainButton + expand, hi-score + initials in localStorage, lives/extra-life@50k, screen-space JUMP button + steer-stick visuals.
- **GitHub Pages: PENDING** — repo public, `has_pages=false`. PUT /pages → 404 (fine-grained PAT has Pages WRITE, verified via tetris PUT→204). 404 = GitHub hasn't provisioned the new repo's Pages backend yet; background pwsh job polls PUT every 30s. Once 2xx: verify https://horaboral.github.io/bombjack-miniapp/.
- **Reasoning OFF: DONE** — settings.yaml qwen38 entry now has `reasoningEfforts` + `compat.thinkingFormat: chat-template` + `chatTemplateKwargs.enable_thinking: false`. Verified: test prompt completion_tokens 33→2, no reasoning_content. Hot-reloaded, applies from next model call. vLLM entries intentionally unchanged.
- **BSOD (5 crashes 8/25–8/28, all identical)**: bugcheck 0x113 = NVIDIA RTX 3090 TDR. Mitigations: 280W limit, lean context, small writes, subagents. Minidumps: C:\WINDOWS\Minidump\082826-*.dmp.

## Next actions (in order)
1. Finish round-1 verification: node --check all blocks + headless smoke + git commit/push.
2. **USER PLAYTEST ROUND 2** (fidelity loop, PLAN.md §5): user plays 2 min → what feels off? Iterate.
3. GitHub Pages: repo has never returned 2xx from API (404s for 40+ min) — user must do the manual step: GitHub → horaboral/bombjack-miniapp → Settings → Pages → Deploy from a branch → main / (root) → Save. Then verify https://horaboral.github.io/bombjack-miniapp/.
4. Phase 8: wire to Telegram bot 8699678610 (menuButton / webhook or long-poll) so the mini-app is reachable in Telegram.
5. Phase 9: polish + final push.
6. Repo hygiene: `refs/watch.html` (1.1MB YouTube HTML), `throughput.py`, `trunc-test/` are untracked leftovers — `refs/` must NOT be in the public repo; confirm .gitignore covers them or delete.

## Facts already learned (do NOT re-research)
- Target = Tehkan 1984 ARCADE Bomb Jack (platformer). NOT Taito B-52. NOT NES Mighty Bomb Jack.
- CANONICAL VISUAL REFERENCE = user's YouTube video "Bomb Jack [Arcade Longplay] (1984) Tehkan" (1116s, id TKzYmjnNbcA). Shows: 5 themed backgrounds (pyramid/sphinx, Greek acropolis, Bavarian castle, skyscrapers/harbor, night street) cycling; 18 platform layouts; HUD = "SIDE-ONE" top-left + score + ×N box top-center, bottom bar ROUND -N- + HI-SCORE + life icons bottom-left; ladders on most stages; bombs sit on platforms AND along screen edges; enemies ~same size as Jack. NOTE: the wiki screenshot (green bezel, right-side HUD) does NOT match the longplay's HUD/bezel — treat the VIDEO as ground truth, wiki screenshot as secondary.
- Mechanics: 24 bombs/round, lit-sequence, 100/200 × 1-5 multiplier, 20-23 lit-bomb round-end bonus (10k-50k), bonus meter → P, P/B/E/S hexagon power-ups, 3 lives, extra life @50k, 5 screens (5th has NO platforms), enemies spawn from top (~6 max): bird/mummy/UFO/orb, escalation over time. Controls: 8-way stick + jump (hold=height, mid-air tap=hover).
- Tetris reference (horaboral/tetris-mini-app): ONLY 2 files — PLAN.md + single self-contained tetris.html (38KB, canvas, pointer events on canvas, Telegram SDK CDN + fallback shim, viewport meta user-scalable=no, touch-action:none). No CI/deploy config in repo → we'll enable GitHub Pages via API.
- Sandbox quirks: python.exe/git/node.exe are KILLED silently + SChannel TLS broken in file sandbox mode → every external op (fetch, git) needs one-shot elevated pwsh; BATCH all external work into one script per approval. curl.exe also denied.
- VISION WORKS NOW: read_image is unblocked via `input: [text, image]` on qwen38 model entries in C:\Users\gru\.dsh\settings.yaml (gate was dsh-tool-fs inputModalities check, sourced from dsh-llm-pi-ai model config). I can view research/refs/wiki-3.png directly; still cross-check with research/palette.py numbers (pure-stdlib PNG decode) for exact hex values, and the user remains final visual judge.
- Long writes on this model can truncate mid-payload (observed in-session) → keep writes ≤ ~4KB, verify byte length after each, rebuild in chunked edits if cut.
- Grokipedia/StrategyWiki/MobyGames bot-block; all needed content already saved in research/ — do NOT re-fetch (grokipedia now 404s).

## Key files
- PLAN.md — master plan (phases, touch design, risks). docs/GAME-SPEC.md — verified mechanics. docs/CONTROLS.md — touch controls v2 (FINAL).
- research/fetch.py, research/fetch_imgs2.py — re-fetchers (need elevated run).
- research/refs/wiki-3.png — 250px reference; research/refs/full.png — 400x250 full-res (downloaded).
- research/visual-notes.md — I viewed the screenshot directly (vision works); layout + working palette for CONFIG.
- research/palette-full.json, palette-wiki3.json — quantitative top-20 palettes (16-step quantized). research/palette.py — re-runnable extractor.

## Credentials (status)
- [DONE] GitHub PAT (horaboral) — stored in .creds.json (gitignored).
- [DONE] Bot token (Tetris bot, id 8699678610) — stored in .creds.json (gitignored). Used in Phase 8.
