# Touch Control Design — v2 (finalized 2026-08, user proposal merged)

## Original arcade mapping (what we must reproduce)
- 8-way joystick: L/R = run. Vertical input shapes jump (up = higher/slower fall, down = fast fall).
- Jump button: **hold duration = jump height**. **Mid-air tap = halt ascent / slow controlled descent (glide)** — the pseudo-flight that defines the game.
- Skills the game demands: sub-frame jump latency, variable jump height, mid-air glide, smooth continuous steering — ALL simultaneously.

## Layout (landscape, full-bleed canvas)
- **LEFT 45% = STEER zone (relative drag — user's "sliding fingers", ADOPTED)**
  - Place thumb anywhere in the zone; slide left/right = run speed. No fixed joystick anchor: thumb never leaves its comfort spot, no re-centering.
  - Dead-zone ~12px, full speed at ~40px displacement; speed = linear ramp.
  - Slide up = slow descent (glide assist), slide down = fast fall. Maps 1:1 to the original's vertical stick.
  - Relative (not absolute): each pointer tracks its own start point.
- **RIGHT 55% = JUMP zone**
  - Big canvas-drawn button (bottom-right, ~96px) — but the WHOLE zone is active, so the finger can land anywhere.
  - **Tap = jump, immediately.** **Hold finger down = higher jump** (release cuts it, like the original). **Tap again mid-air = glide / 1/3 fall speed** until landing or re-tap.
  - This is a 1:1 semantic clone of the arcade button with zero added latency.

## Why NOT double-tap to jump (user proposal — rejected, here's why)
- Double-tap costs 150–300ms (two taps + disambiguation) on the single most timing-critical action in the game. Jump timing IS the skill.
- Single tap gets identical ergonomics (one finger, anywhere in the zone) with 0 extra latency, and the hold gesture gives us variable height for free.
- The slide-steer half of the proposal is better than my original fixed virtual joystick — merged in.

## Multi-touch & plumbing
- Pointer Events on canvas, `touch-action:none`, separate `pointerId` per zone → steer + jump truly simultaneous; releasing one finger never disturbs the other.
- Fixed 60Hz logic (rAF + accumulator); input sampled each frame; jump processed within 1 frame.
- Telegram: HapticFeedback — light on jump, medium on hit, success on bomb pickup; themeParams for HUD colors.
- Landscape-lock overlay (rotate hint) when aspect < 1.

## Modes & tuning (fidelity loop)
- `CONFIG.controls = { mode: "zones", deadZone: 12, fullPx: 40, glideFall: 1/3 }` — mode switchable later to "fixed-stick" A/B test.
- Desktop debug: arrows + space (hold).
- Feel targets vs longplay: run speed, jump arc, glide duration tuned frame-by-frame against research/refs/ video tiles.
- User is the judge each session: "play 2 minutes — what feels off?"
