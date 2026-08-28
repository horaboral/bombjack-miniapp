# Bomb Jack Mini-App — PROGRESS (read this FIRST in any new session)

Last updated: 3rd BSOD recovered. Remote backup LIVE (repo pushed, commit 8db87bf). Credentials stored. Touch controls v2 finalized (docs/CONTROLS.md). BSOD cause identified: NVIDIA 0x113 TDR.

## State
- **Phase 0 Research & plan: DONE** → docs/GAME-SPEC.md, PLAN.md, research/ artifacts.
- **Phase 1: REPO LIVE** → `horaboral/bombjack-miniapp` created + pushed (commit 8db87bf: .gitignore, PLAN, PROGRESS, GAME-SPEC). Pages: API PUT → 404, retry = research/pages.py. `bombjack.html`: NOT started.
- **Phase 2 Palette: mostly DONE** (pre-repo) → research/visual-notes.md (layout + working palette), palette-full.json/palette-wiki3.json (quantitative). Final hex tuning happens when CONFIG is written. VIDEO is the canonical visual reference (see Facts).
- **BSOD (5 crashes 8/25–8/28, all identical)**: bugcheck 0x113 VIDEO_TIMEOUT_DETECTED (0x19,0x2,0x10de,0x2204) = NVIDIA RTX 3090 TDR crash under sustained load. Correlation: retake/compact = biggest single inference = GPU peak. Mitigations: user's 280W limit; we keep context lean (small images, small writes, delegate to subagents). Minidumps: C:\WINDOWS\Minidump\082826-*.dmp.

## Next actions (in order)
1. Retry GitHub Pages (research/pages.py — needs elevated run) + verify https://horaboral.github.io/bombjack-miniapp/ after first html push.
2. Write `bombjack.html` skeleton: viewport meta, touch-action none, landscape-lock overlay, full-bleed canvas, Telegram SDK + fallback shim (copy pattern from research/tetris-ref/tetris.html lines 5-36), title screen "BOMB JACK — TAP TO START", fixed-60Hz loop.
3. Implement controls per docs/CONTROLS.md v2: left 45% relative-drag steer, right 55% tap/hold jump + mid-air tap glide, multi-touch pointerId, HapticFeedback, landscape overlay.
4. Phases 2-9 per PLAN.md. Push after EVERY phase.

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
