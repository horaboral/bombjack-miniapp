# Telegram Mini-App Game — Lessons Learned

Distilled from the Bomb Jack build (2026-08-28 → 2026-09-02). Read this BEFORE starting the next Telegram game; every item below cost real playtest rounds.

## 1. Input model (the #1 pain source)

- **Left thumb stays on screen forever → steering must be a relative stick, not absolute position.** Left zone = steering stick: record origin on touchstart, drag delta = direction, 60px radius cap, 12px dead zone. Never "jump to finger position" — the left thumb never leaves the screen.
- **Right thumb = jump, press to jump + glide, hold to rise.** Tap-to-jump with a move threshold (<18px, <40 ticks) is the accepted model.
- **Per-pointer ownership is mandatory.** Map `pointerId → {mode:'steer'|'jump'}`. A new finger must NEVER invalidate or steal an existing pointer's function. Second finger landing in an occupied zone = ignored, not reassigned. Without this, a stray second tap kills the steering stick mid-jump.
- **Use pointer events, not touch events.** Pointer events give stable `pointerId` across multi-touch; raw touch events force you to re-derive identity from `changedTouches`, which breaks on simultaneous lifts.
- **Block the Telegram host from stealing gestures**: `WebApp.disableVerticalSwipes()`, plus `touchmove` preventDefault (passive:false) and `gesturestart` preventDefault. Otherwise the page slides/minimizes when the user steers.
- **Steering up must have a real effect** (here: hold-up = keep rising, terminal velocity capped, ceiling clamp). A stick axis that does nothing reads as "controls are broken".

## 2. Telegram WebApp specifics

- `Telegram.WebApp.ready() + expand()` in a try/catch at load; the game must also work in a plain browser (guard every `Telegram.WebApp.*` access).
- `setHeaderColor`/`setBackgroundColor` to match the game's top band — otherwise a white/foreign header band shows above the canvas and offsets the visual frame.
- Haptics: `HapticFeedback.impactOccurred('light'|'medium'|'heavy')` on pickups/hits, `notificationOccurred('success')` on round clear. Free juice; wrap in try/catch.
- No MainButton for the start screen — the game is started by tapping the canvas; MainButton adds a native button that conflicts with tap-to-start.
- **Audio must start after a user gesture.** `new AudioContext()` on load is suspended; only create/resume it inside the first tap handler.
- Telegram webviews are iOS WKWebView / Android Chrome — WebAudio API is fine, but test `exponentialRampToValueAtTime` with non-zero start values (0 is illegal and throws).

## 3. Game rules & level data (silent-failure traps)

- **Never hardcode a level-clear threshold that can drift from the level data.** We shipped `bombsGot >= 24` while screen 1 had 18 bombs → eating every bomb did nothing, and the user saw no way to progress. Derive the threshold from the data: `bombsGot >= G.bombs.length`, and give the player a visible counter (bombs remaining) so "what do I do?" never happens.
- **After every level-data edit, verify counts** (bombs per screen, platform reachability) — a 2-line script or a headless screenshot beats a playtest round.
- Reachability: with fixed jump height, every bomb must be reachable from some platform/ground; with hold-to-rise, the ceiling clamp defines the top boundary. Keep the two consistent.

## 4. Audio

- **Short loops feel broken.** A 4-second loop is "a noise machine"; the reference game has distinct A-B-A'-C phrases. Use 128 steps (4× 32) with a lookahead scheduler: `setInterval(30ms)` schedules notes ~0.12s ahead at exact 1/16-note timing from `AC.currentTime`. No per-frame stepping (that drifts and stutters on frame drops).
- Per-screen themes with different BPM/key (96–168 bpm) make screen changes audible and satisfying.
- Funny death sound: stepped pitch drops (880→660→520→400) then `exponentialRampToValueAtTime` down to ~55Hz over ~1.5s, plus a ~7Hz LFO on pitch for "wah-wah". Cheap, instantly readable as "I died".
- One shared noise buffer for drums; kick = sine with exponential pitch drop 120→42Hz.

## 5. Fidelity loop (comparing to the reference video)

- **Extract reference frames at 2s intervals and number them** (015=pyramid, 025=title, …) so claims like "bombs sit ON platforms" are checkable.
- Enemy behavior to copy: each enemy owns ONE surface (ground or a platform), patrols its bounds, turns at edges; hoverers float a few px above their surface with a sine bob. Do not let enemies float freely.
- One-way platforms: pass through from below, land on top (prevBottom ≤ top+1 && newBottom ≥ top, only when vy ≥ 0).
- Title screen: 3D stacked logo (two lines are safer than one line for fit), sunburst, themed backdrop, hi-res hero, "1 CREDIT / TAP TO START / HI-SCORE" — all of it sells the arcade feel.

## 6. Headless verification on this Windows/Edge host (verified 2026-09-02)

- `msedge --headless=new --dump-dom` returns EMPTY output in this Edge build — do not rely on it to read page text/DOM.
- `--virtual-time-budget` makes `--screenshot` write nothing — drop it; screenshot + `Start-Sleep 2s` instead.
- `--window-size` does NOT control the rendered viewport (innerWidth came out ~564px) → screenshots look oversized/clipped. Workaround: temp copy of the HTML with injected CSS `html{width:400px!important;height:711px!important;overflow:hidden;}` and screenshot that.
- "Logo clipped" was a viewport-crop artifact, not a layout bug — probe pages with coordinate logging beat pixel eyeballing.
- To test a non-title state, generate a temp copy with a JS hook (force state, spawn entities, then `window.__stop` guard in `frame()`).
- `node --check` on extracted `<script>` blocks is the cheap syntax gate before every push.

## 7. Deployment

- GitHub Pages serves the pushed HTML; verify with `Invoke-WebRequest` on the live URL **and a cache-busting query** — the first fetch after push can be the stale cached copy (~15–45s).
- PowerShell reports git success on stderr as exit code 1 — check the actual `old..new ref -> ref` line, not `$LASTEXITCODE`.
- Keep the whole game in ONE self-contained HTML file (base64 backgrounds, no build step) — trivial to serve, trivial to test, no asset 404s.
- Clean temp artifacts (`refs/`, harness copies, screenshots) before pushing; keep them gitignored.

## 8. Process

- Persist plan + progress to disk after each phase (BSOD-safety requirement).
- When the user asserts something works in the reference, verify against the frames, not the screenshot of our build.
- Ask "what does the player see when this state is reached?" for every state transition — the missing round-clear was invisible because nothing told the player the goal or the progress.
