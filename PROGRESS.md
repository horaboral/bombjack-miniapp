# Bomb Jack Mini-App — PROGRESS (read this FIRST in any new session)

Last updated: VISION FIXED — model can now read images (added `input: [text, image]` to qwen38 entries in C:\Users\gru\.dsh\settings.yaml). Phase 0 DONE; Phase 2 palette extraction in progress. Next gate: credentials from user.

## State
- **Phase 0 Research & plan: DONE** → docs/GAME-SPEC.md, PLAN.md, research/ artifacts.
- **Phase 1 Scaffold: BLOCKED** on GitHub PAT (user `horaboral`) + full bot token.
- **Phase 2 Palette: mostly DONE** (pre-repo) → research/visual-notes.md (layout + working palette), palette-full.json/palette-wiki3.json (quantitative). Final hex tuning happens when CONFIG is written.

## Next actions (in order)
1. Get from user: (a) fine-grained GitHub PAT (repo scope), (b) full bot token for Tetris bot (bot id 8699678610).
2. Create repo `horaboral/bombjack-miniapp` via GitHub API (one elevated python call), git init, commit docs (gitignore research/refs — copyright).
3. Write `bombjack.html` skeleton: viewport meta, touch-action none, landscape-lock overlay, full-bleed canvas, Telegram SDK + fallback shim (copy pattern from research/tetris-ref/tetris.html lines 5-36), title screen "BOMB JACK — TAP TO START", fixed-60Hz loop.
4. Phases 2-9 per PLAN.md. Push after EVERY phase.

## Facts already learned (do NOT re-research)
- Target = Tehkan 1984 ARCADE Bomb Jack (platformer). NOT Taito B-52. NOT NES Mighty Bomb Jack.
- Mechanics: 24 bombs/round, lit-sequence, 100/200 × 1-5 multiplier, 20-23 lit-bomb round-end bonus (10k-50k), bonus meter → P, P/B/E/S hexagon power-ups, 3 lives, extra life @50k, 5 screens (5th has NO platforms), enemies spawn from top (~6 max): bird/mummy/UFO/orb, escalation over time. Controls: 8-way stick + jump (hold=height, mid-air tap=hover).
- Tetris reference (horaboral/tetris-mini-app): ONLY 2 files — PLAN.md + single self-contained tetris.html (38KB, canvas, pointer events on canvas, Telegram SDK CDN + fallback shim, viewport meta user-scalable=no, touch-action:none). No CI/deploy config in repo → we'll enable GitHub Pages via API.
- Sandbox quirks: python.exe/git/node.exe are KILLED silently + SChannel TLS broken in file sandbox mode → every external op (fetch, git) needs one-shot elevated pwsh; BATCH all external work into one script per approval. curl.exe also denied.
- VISION WORKS NOW: read_image is unblocked via `input: [text, image]` on qwen38 model entries in C:\Users\gru\.dsh\settings.yaml (gate was dsh-tool-fs inputModalities check, sourced from dsh-llm-pi-ai model config). I can view research/refs/wiki-3.png directly; still cross-check with research/palette.py numbers (pure-stdlib PNG decode) for exact hex values, and the user remains final visual judge.
- Long writes on this model can truncate mid-payload (observed in-session) → keep writes ≤ ~4KB, verify byte length after each, rebuild in chunked edits if cut.
- Grokipedia/StrategyWiki/MobyGames bot-block; all needed content already saved in research/ — do NOT re-fetch (grokipedia now 404s).

## Key files
- PLAN.md — master plan (phases, touch design, risks). docs/GAME-SPEC.md — verified mechanics.
- research/fetch.py, research/fetch_imgs2.py — re-fetchers (need elevated run).
- research/refs/wiki-3.png — 250px reference; research/refs/full.png — 400x250 full-res (downloaded).
- research/visual-notes.md — I viewed the screenshot directly (vision works); layout + working palette for CONFIG.
- research/palette-full.json, palette-wiki3.json — quantitative top-20 palettes (16-step quantized). research/palette.py — re-runnable extractor.

## Credentials (status)
- [PENDING] GitHub PAT — asked user.
- [PENDING] Bot token (Tetris bot, id 8699678610) — asked user.
