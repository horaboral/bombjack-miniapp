# Design: Model Matrix + Subagent Roster (two-GPU local stack)

Status: draft for review — no containers touched yet.
Scope: how the orchestrator (me, 27B on the 3090), the 780M iGPU, and the
content lanes (ComfyUI, TTS, voice) coexist; which subagents exist and what
they are for; and where the conscious load/unload decisions live.

---

## 1. Hardware ground truth (verified)

| Device | Class | Memory | Notes |
|---|---|---|---|
| RTX 3090 | dGPU, CUDA | 24 GB VRAM | Resident: `qwen38-server` (Qwen 3.6 27B Q4_K_M, ctx 132,096). nvidia-smi: 24,090/24,576 MiB used. |
| AMD Radeon 780M | **iGPU** (Zen 4, RDNA3), Vulkan | 16 GB **shared DDR5** (carved from system RAM) | Not in nvidia-smi (correct — it's AMD). `llama-server.exe` Vulkan build staged at `D:\dsh\repos\780m-helper\llama-b10726-win-vulkan\`. Display also uses it. |

Key consequences:

1. **The 3090 is a single-tenant card.** 27B (17.5 GB weights + KV at 131k)
   and any ComfyUI lane (7–18.5 GB) cannot coexist. The 3090 is a
   **swap domain**: 27B is default; content lanes swap it out.
2. **The 780M is a shared-memory iGPU.** 16 GB sounds like VRAM-class
   headroom, but it is DDR5 shared with the CPU and the display:
   - bandwidth ≈ 60–90 GB/s vs the 3090's 936 GB/s → decode speed is
     roughly 1–3 t/s for a 7B–14B GGUF (community reports for the same
     silicon range 2–8 t/s with ROCm; expect less via Vulkan on Windows);
   - FP8 dequantizes to FP16 in software paths → **prefer Q4/Q5 GGUF**
     over fp8 safetensors;
   - it can freeze the display if the carve-out is over-committed
     (known 780M failure mode; the reference stacks reserve 20–24 GB
     and tune kernel params).
   So the 780M is a **slow workbench**: fine for background,
   latency-tolerant, throwaway-context work. Not for anything
   interactive.
3. **ComfyUI does not fit the 780M** (for your model class, correctly).
   One community data point: z-image-turbo BF16 + GGUF VAE fit in the
   16 GB and rendered a 720×1280 image in ~40 s on the 780M under
   **Linux/ROCm** — so it is *possible* with the lightest models, but on
   Windows/Vulkan with your model roster it's not a lane to plan around.

## 2. The three domains (the core of the design)

```
┌─────────────────────────────────────────────────────────────────────────┐
│ DOMAIN A — BRAIN (3090, default tenant)                                 │
│   qwen38 27B, -np 2 slots, ctx 131k                                     │
│   slot 0: orchestrator (me, resident, 131k)                             │
│   slot 1: 27B subagents (Coder / Auditor) — same model, fresh ctx       │
│   This domain is alive whenever the 3090 is not in Domain B.            │
└─────────────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────────────┐
│ DOMAIN B — CONTENT (3090, swap tenant)                                  │
│   ComfyUI lanes (image 7–18.5 GB, music ~8 GB, video needs dual card)   │
│   + premium voice (~14 GB, on-demand, exclusive with video)            │
│   Enter via model-manager: unload 27B → free GPU → start lane →         │
│   render → harvest → unload lane → reload 27B.                          │
│   The orchestrator is UNINTERRUPTIBLE here: while Domain B is active,   │
│   I (27B) am down. See §5 for how that is handled.                      │
└─────────────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────────────┐
│ DOMAIN C — WORKBENCH (780M, always-on, concurrent with A or B)         │
│   llama-server Vulkan, resident workhorse 7B/14B Q4                     │
│   Tinkerer / Scribe / Researcher subagents. Slow (1–5 t/s),             │
│   latency-tolerant only. Also the only place a small-VL fits.           │
│   (Optional, later, Linux/ROCm: light z-image-turbo lane, ~40 s/img.)   │
└─────────────────────────────────────────────────────────────────────────┘
```

The load/unload **authority** is Domain A (me) consulting the matrix; the
**hands** are the model-manager service (a deterministic, zero-intelligence
`load/unload/status/warm` API — the trimmed `:8022` orchestrator).
Domain C is warm-resident and never swapped (except when its carve-out
must shrink for a Domain B render that hogs system RAM — see §6).

## 3. Model matrix (the "don't lose track" artifact)

Single source of truth: `shared/models-registry.json` (upgraded). I read it
before every delegation or swap and update `state` after every load/unload.
This replaces the "which model is where" memory with a file I own.

| key | model | domain | quant | VRAM | ctx | capabilities | state | load cost |
|---|---|---|---|---|---|---|---|---|
| `qwen38` | Qwen 3.6 27B | A (slot 0+1) | Q4_K_M | ~17.5 GB + KV | 131k (slot 0) / 32k (slot 1) | code, reasoning, orchestration | **resident** | boot ~30–60 s (already warm) |
| `workbench-14b` | Qwen3 14B | C | Q4_K_M | ~9–10 GB | 32k | code-lite, ops, summarize, research | warm (lazy first use) | ~1–2 min (GGUF load over DDR5) |
| `workbench-7b` | Qwen3 8B | C | Q5_K_M | ~5–6 GB | 32k | summarize, scribe, fast triage | warm | ~30–60 s |
| `workbench-vl` (later) | Qwen3-VL 8B + mmproj | C | Q4 | ~7–8 GB | 16k | image analysis | cold | ~1 min |
| `comfy-image` | Z-Image 7 / Chroma 9 / HiDream 15 / Ideogram 18.5 | B | fp8/GGUF | 7–18.5 GB | — | image | **cold** | ~1–3 min (weights + ComfyUI boot) |
| `comfy-music` | ACE-Step | B | — | ~8 GB | — | music/SFX | cold | ~1 min |
| `comfy-video` | LTX/Sulphur 22B / Wan 14B | B (dual card) | GGUF | 22+ GB | — | video | cold | ~2–4 min |
| `voice-step` | Step-Audio-EditX | B | bf16/AWQ | 14 GB (3–4 GB AWQ) | — | premium voice | cold, on-demand | ~1 min |
| `voice-kokoro` | Kokoro TTS | C or CPU | — | ~0.3 GB | — | fast voice, zero GPU | CPU | ~2 s |
| `dolphin` (retained) | Dolphin Mistral 24B Venice | B (swap) | Q4_K_M | ~13–19 GB | 32k | uncensored chat, creative | cold | ~1 min |

Rules the matrix encodes (the "conscious decision" logic):

- **Default tenant of the 3090 is always `qwen38`.** Every Domain B load is
  a *temporary eviction with a guaranteed return* (your openclaw
  temp-swap idea, kept — it was the right idea for this use case).
- **Delegation target choice:** if the task is coding/reasoning/audit →
  Domain A slot 1 (best model). If the task is ops/log-triage/summarize/
  research and is latency-tolerant → Domain C (frees the 3090 entirely).
- **Content requests never interrupt active coding** without explicit user
  approval — a render is minutes of 27B-downtime, which is a user decision,
  not mine.
- **`state` is written after every transition** and the full log goes to
  `swap-history.json` (already exists) — this is the audit trail.

## 4. Subagent roster (fixed roles, not ad-hoc)

| subagent | target | domain | ctx | job | returns |
|---|---|---|---|---|---|
| **Coder** | qwen38 slot 1 | A | 32k | full-stack implementation, multi-file refactors, compose/container authoring | diff/summary + files on disk |
| **Auditor** | qwen38 slot 1 | A | 32k | code/security/config review, "is this right?" | verdict + findings |
| **Tinkerer** | workbench-14b | C | 16k | docker ops, config edits, log triage, "run X, report" | report + changed files |
| **Scribe** | workbench-7b | C | 16k | transcript compaction, memory-palace entries, Work-Unit result extraction | text |
| **Researcher** | workbench-14b (or qwen38 slot 1 for hard questions) | C/A | 16k | web search + synthesis, docs reading | sourced summary |
| **Vision** (later) | workbench-vl | C | 8k | image analysis | description |

Contract: every subagent call is a **Work Unit** (your existing
`INTER-MODEL-PROTOCOL.md` schema — brief, constraints, output_format,
result). The subagent writes its result to the Work Unit file and returns
only the result to me. My slot-0 context grows by the result size, never by
the subagent's working context.

Roster notes:
- **qwen38 as a subagent is the primary path** — same model as me, isolated
  context, zero extra hardware (just `-np 2`). This is the single highest
  ROI change in the whole design and it is a flag on the container you run.
- Domain C subagents buy **concurrency** (they work while I work, and while
  Coder works) and **context isolation**; they do not buy speed.
- Dolphin stays a *swap* model in Domain B, not a resident — it fits the
  3090, and uncensored chat is interactive, so it gets the fast card.

## 5. The Domain B problem: I am down while content renders

Honest edge case: while ComfyUI holds the 3090, **the 27B orchestrator does
not exist** — I am the thing that was unloaded. The openclaw design had the
same hole and never solved it. Three layers of mitigation, in order of
cheapness:

1. **Job-ization (default).** A content request becomes a *job*: I write the
   Work Unit (prompt, lane, params), call `model-manager load comfy-image`,
   fire the render, and **the job runs unattended**. Because I'm down during
   it, the *completion* path is not "I get called" — it is a **watcher**:
   the model-manager (or the existing watchdog pattern you already run at
   `:8023`) detects render done → unloads the lane → reloads qwen38 →
   drops the result into my session's inbox (a file I read on my next turn,
   or a Telegram notification that pings me). I wake up, harvest, continue.
   This is exactly your "instruct the work, obtain it, incorporate it into
   a larger workflow" loop — with the watcher closing the loop that a
   single-model brain can't close for itself.
2. **Domain C as the degraded brain.** While the 3090 renders, the
   workbench-14b keeps answering trivial Telegram messages ("is it done?")
   and can even take *new* low-stakes tasks. It knows one rule: "the 27B is
   down for a render; do nothing that matters; report progress." This keeps
   the Telegram channel alive without pretending the 14B is me.
3. **No mid-render interruptions of the render itself.** Cancellation is
   user-initiated and goes through model-manager (stop lane, restart 27B).

## 6. Memory budget (the thing that can actually bite you)

- System RAM: 16 GB is carved to the 780M. A Domain B render with a 22 GB
  GGUF video model mmaps that from RAM too. **Video + warm workbench can
  over-commit.** Rule: `model-manager` unloads the 780M workbench
  (cheap: it's just a process) before starting any video lane; image/music
  lanes coexist fine.
- Display stability: the 780M also drives the screen. Keep the carve-out at
  16 GB and never run the workbench at 100% for hours unattended; a
  `warm` cap of "unload after N minutes idle" protects the desktop.
- 3090 slot 1 KV: two 131k slots won't both fit; slot 1 gets 32k. That is
  the working set of a coding task, not a whole project — bigger jobs get
  split into multiple Work Units (the batch field already exists).

## 7. Build order (each step independently valuable)

1. **`-np 2` on `qwen38-server` + register slot-1 usage in DSH.** Same
   model, isolated subagent contexts. No new hardware. *Do this first — it
   fixes the measured 5.3M-token / 58-compaction problem by itself.*
2. **Trim `:8022` to the dumb manager.** Keep: preflight, stop,
   verify-gpu-free, start, verify-healthy, recovery, swap-history,
   temp-swap-with-auto-return. Delete: everything that assumes "the master
   is a model on 8020". Add: `watch` (job completion → reload 27B → inbox).
3. **Stand up the 780M workbench.** llama-server Vulkan, workbench-14b Q4
   resident with idle-unload; register as second DSH provider.
4. **Bench the 780M** (`llama-bench` with the staged binary): confirm t/s
   for 14b/7b Q4 and that the 16 GB carve is stable under load. Adjust the
   matrix's "state" defaults from the numbers.
5. **Wire the Telegram watcher loop** (render → done → reload → notify →
   harvest). This is what makes Domain B usable by a brain that's asleep
   during it.
6. **Later:** workbench-vl; Linux/ROCm z-image-turbo experiment on the
   780M (the 40 s/img data point is worth one afternoon if image work grows).

## 8. What this design deliberately is not

- Not a small-model router. The 27B decides; the manager obeys; the 780M
  grinds. Load/unload authority stays with the strong brain + a
  deterministic hands-service (the openclaw fatal coupling — master =
  swappable blob — stays removed).
- Not a speed system. The 780M buys concurrency and context isolation, not
  throughput. Video on the 3090 is as slow as it was; nothing here makes
  rendering faster, it just stops rendering from eating the brain.
- Not a dual-card video rig. Video still needs the second 3090 you had in
  club-3090; on this box, video is the one lane that waits for a spare card
  or a RAM-heavy single-card compromise (1280×720 OOMs per your own docs).
