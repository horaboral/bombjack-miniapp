# Spec: 780M workbench provider + `-np 2` two-slot 3090

Status: ready-to-apply. No container has been touched yet.
Apply order is at the bottom. Step 1 (780M provider) is safe to apply now —
it adds a second provider and does not restart anything. Step 2 (`-np 2`)
restarts `qwen38-server`, which drops the model serving the current session.

---

## Bench results (measured this session)

Hardware: AMD Radeon 780M iGPU (RDNA3), 16 GB shared DDR5 carve-out, Vulkan
1.4.350. Engine: staged `llama-server.exe` b10726 win-vulkan at
`D:\dsh\repos\780m-helper\llama-b10726-win-vulkan\`.

| Test | Model | Engine | Result |
|---|---|---|---|
| 780M decode | Qwen3.5-4B Q4_K_M | Vulkan | **2.5 t/s** (256 tok in 102.9 s) |
| 780M prompt | Qwen3.5-4B Q4_K_M | Vulkan | **78 t/s** (1,836 tok in 23.5 s) |
| 3090 decode | Qwen3.8-27B UD-Q4_K_XL | **Vulkan** (contended) | 0.33 t/s — **INVALID, discard** |
| 3090 decode | Qwen3.8-27B Q4_K_M | **CUDA** (live container) | **~60 t/s** (club-3090 SINGLE_CARD.md: "llamacpp/mtp … ~60 code TPS", 2026-05-24) |

Notes on the numbers:

- The 3090 Vulkan run was invalid: the live CUDA `qwen38-server` already held
  ~17.5 GB of the 24 GB, so the Vulkan 27B ran memory-starved. It is a
  warning, not a number: **the 3090 is served by CUDA (the container), never
  Vulkan.** Do not plan any Vulkan path for the 3090.
- 780M decode (2.5 t/s) is ~24× slower than the 3090 CUDA (~60 t/s). This is
  the shared-DDR5 bandwidth wall. It confirms the design premise: the 780M is
  a **context-isolation + concurrency** workbench, not a speed path.
- 780M prompt (78 t/s) is the more useful number for agent work: a subagent
  that reads a 2K-token Work Unit brief spends ~25 s on prefill and ~1 min on
  a 256-token result. Acceptable for background Tinkerer/Scribe/Researcher
  tasks; not for anything interactive.
- **Model choice for the 780M resident:** a 4B Q4 (~2.5 GB) leaves ~13 GB of
  the 16 GB carve for KV + the display. A 14B Q4 (~9 GB) fits but would cut
  decode to ~1–1.5 t/s and leave little KV headroom. **Recommend 4B as the
  resident workhorse**; the 14B is a "later, if 4B quality isn't enough"
  swap, not the default.
- **The 780M also drives the display.** A 16 GB carve-out shared with the
  desktop can freeze under sustained load (known 780M failure mode; the
  reference stacks reserve 20–24 GB and tune kernel params). Mitigation in
  the spec: idle-unload the workbench after N minutes, and never run it
  while a ComfyUI render is hogging system RAM.

---

## Step 1 — Register the 780M as a DSH provider (safe, no restart)

### 1a. Run the 780M server

The staged binary is a normal `llama-server.exe`. Run it as a persistent
process (Task Scheduler at logon, or a `run_in_background` job for now):

```
D:\dsh\repos\780m-helper\llama-b10726-win-vulkan\llama-server.exe `
  -m D:\.lmstudio\models\lmstudio-community\Qwen3.5-4B-GGUF\Qwen3.5-4B-Q4_K_M.gguf `
  -ngl 99 -c 8192 -b 512 -ub 128 --host 127.0.0.1 --port 8099
```

- `-ngl 99` offloads all layers to the iGPU.
- `-c 8192` is a workbench-sized ctx (a Work Unit + its result fits easily);
  it keeps KV small on shared memory.
- Port **8099** (chosen free; the 8098 Vulkan test server was killed).
- Model name defaults to the file basename; if DSH needs a stable alias, add
  `-a workbench` (then use `id: workbench` below).

### 1b. Add the provider to `C:\Users\gru\.dsh\settings.yaml`

The existing `qwen38-docker-q4-k-xl` provider (port 8020) stays untouched.
Add a sibling:

```yaml
    qwen38-780m-vulkan:
      displayName: 780m workbench
      api: openai
      baseURL: http://127.0.0.1:8099/v1
      models:
        - id: workbench-4b
          name: Qwen3.5-4B (780M)
```

This is additive — the active provider/model (`qwen38-docker-q4-k-xl` /
`qwen38`) is unchanged. The 780M becomes *available to subagents*, not the
default. Subagents target it explicitly by model id.

### 1c. Verify

`curl.exe http://127.0.0.1:8099/v1/models` should list the workbench model.
A DSH subagent call with `model: workbench-4b` should route to 8099 and
return (slowly) a result.

---

## Step 2 — Two-role mode: Thinker (132K) ↔ Orchestrator (64K/32K)

Compaction is **not lossless**. A deep-dive plan is dozens of turns of
reading, weighing, and building a coherent argument; my context accumulates
that reasoning, and every compaction degrades it. **132K is not "more than a
turn needs" — it is "more room before the lossy compaction hits," and for a
thinker that is the whole point.** So the thinker stays at 132K, and the
implementation work (read spec, dispatch, harvest) moves to a *separate*
role that doesn't need 132K.

### Roles

| Role | Ctx | Job | Container / port |
|---|---|---|---|
| **Thinker** | **132K**, single slot | plan, spec, deep-dive — the *me* you talk to now | `qwen38-server` / **8020**, **unchanged** |
| **Orchestrator** | 64K (slot 0) | read the spec, dispatch Work Units, harvest results | `concurrent` / **8021** |
| **Coder / Auditor** | 32K (slot 1, driver-hard-capped) | do the implementation Work Unit | `concurrent` / **8021** |

**The spec file is the lossless bridge.** The thinker writes it at 132K; the
orchestrator reads it at 64K and implements. The 132K reasoning survives the
role switch because it's on disk, re-readable, lossless — not because it fits
in the orchestrator's context.

### The hard constraint, stated once

Only **one 27B container fits on the 3090 at a time** (24 GB holds one
resident 27B: ~20.4 GB resting + KV). The thinker and the orchestrator+coder
**time-share the card; they do not coexist.** The mode switch is **your**
decision (planning vs. implementing), not a mid-task eviction — so there is
no "I'm down while the coder runs" pain. (A second 27B *process* alongside
the thinker is ≈ 35 GB — impossible; the split is two *containers*, one up at
a time.)

### The memory model (per-token KV, not a fixed reservation)

- **Weights + overhead: fixed** ≈ 20.4 GB (16.4 GB Q4_K_XL + MTP/mmproj/CUDA).
- **KV: per slot, per token, grows with actual use.** 27B @ Q8_0 ≈ 25 MB per
  1K tokens (CLIFFS.md): 132K → ~3.3 GB, 64K → ~1.6 GB, 32K → ~0.8 GB.
- **Concurrent slots = concurrent KV pools, both resident.** VRAM =
  20.4 GB + slot0-KV + slot1-KV.
- **`-np 2 -c 132000` is an OOM vector** (two 132K ceilings → 20.4 + 3.3 +
  3.3 = ~27 GB if both fill). That is why the `concurrent` container uses
  **`-c 64000`**: both slots get a 64K ceiling (worst case 20.4 + 1.6 + 1.6 =
  **~23.6 GB, fits with margin**). KV is **linear** in token count (25 MB/1K),
  so 2×64K is safe on its own — **no driver cap is required for memory
  safety.**
- The coder's **32K driver cap is a *quality* guardrail, not a memory
  requirement.** It enforces "a Work Unit that needs >32K of context was too
  big and should be split" — preventing the coder from producing degraded
  output by re-reading its own tool outputs. You may drop it (the coder can
  then use up to 64K, still no OOM); keeping it just enforces bounded Work
  Units. **The memory safety of `concurrent` rests entirely on the 64K engine
  ceiling, not on the driver cap.**
- **Do not raise the `concurrent` ceiling above ~96K** (2×96K → 20.4 + 2.4 +
  2.4 = ~25.2 GB, OOM). 64K is the safe default; 96K is the hard ceiling for
  this container.

### Container definitions (already written, nothing started)

- `C:\Users\gru\test-qwen-project\docker-compose.yml`:
  - `qwen38` (8020): **single slot, `-c ${CTX_SIZE}` = 132000, no `--parallel`**
    — the thinker, untouched.
  - `concurrent` (8021): same image, `-a qwen38c`, **`-c 64000 --parallel 2`**
    — orchestrator (slot 0) + coder (slot 1).
- `C:\Users\gru\test-qwen-project\.env`: `CTX_SIZE=132000` (thinker only;
  `concurrent` hardcodes its own 64000).
- DSH (`C:\Users\gru\.dsh\settings.yaml`): add provider `qwen38-concurrent`
  → `http://127.0.0.1:8021/v1`, model id `qwen38c`. **Do not make it the
  active provider** until you switch modes.

### The mode switch (explicit user action, not automatic)

"Done planning, switch to implement":
1. `docker stop qwen38-server` (free the 3090; the thinker's DSH session file
   stays on disk — nothing is lost).
2. `docker compose up -d concurrent` (from `C:\Users\gru\test-qwen-project\`).
3. Flip DSH active provider → `qwen38-concurrent` / `qwen38c` (or point the
   orchestrator's DSH session at it).
4. The orchestrator reads the spec file(s) and starts dispatching.

Switch back the same way (stop `concurrent`, start `qwen38-server`, flip the
provider). The 780M workbench (8099) is on the iGPU and is **never** part of
this swap — it stays up through both modes.

### Fallback (if 64K proves too small for the *thinker*)

If deep dives keep compacting painfully at 132K, the next lever is **IQ4_XS**
(weights 16.4 → ~13.4 GB), which frees ~3 GB so the thinker can run a bigger
KV or the coder can have a bigger ceiling — a comfort lever, applied to the
`concurrent` container, not the thinker. Serial swap (thinker evicted while a
standalone coder runs) remains the no-concurrency last resort.

### 2d. Where the DSH driver cap lives (investigated)

The "driver cap" for a DSH subagent session is **not a separate knob** — it
is the **`contextWindow` on the model entry in `settings.yaml`**, which feeds
the compaction plugin. The chain:

1. `settings.yaml` model entry declares `contextWindow` (e.g. `90000` on the
   thinker's `qwen38` — that's already a cap *below* the 132K engine ceiling).
2. The `dsh-compaction-basic` plugin resolves a per-target policy
   (`resolveTargetPolicy(config, {provider, model})`) and scales it into
   concrete token budgets via `resolveCompactSpec(policy, contextWindow)`:
   **compact at `thresholdRatio` × `contextWindow`** (default 0.8 → 72,000
   tokens for a 90K window), **retain `retainRatio` × window** (default 0.16).
3. When the session's context pressure crosses the threshold, compaction fires
   (lossy summary + retained recent tail). So `contextWindow` is the
   **effective session ceiling** — the point at which DSH starts compressing.

**Per-subagent override** exists via the subagent's `agentOptions` (declared
in the Work Unit / delegation call): `provider`, `model`, `reasoningEffort`,
`maxTokens`. A subagent can target a *different provider/model entry* (e.g.
`qwen38-concurrent`/`qwen38c`) whose `contextWindow` is smaller — that is the
mechanism for a 32K coder cap while the orchestrator runs at 64K. The cap is
per **provider/model route**, not per slot, so slot 0 and slot 1 on the same
route share the same compaction ceiling.

**Concrete shape for a 32K coder cap** (if you want it): add a second model
entry to the `qwen38-concurrent` provider:

```yaml
    qwen38-concurrent:
      displayName: qwen38 concurrent (orchestrator + coder)
      api: openai
      baseURL: http://127.0.0.1:8021/v1
      models:
        - id: qwen38c
          name: Qwen3.8-27B (orchestrator, 64K)
          contextWindow: 64000
        - id: qwen38c-coder
          name: Qwen3.8-27B (coder, 32K cap)
          contextWindow: 32000
```

Both entries point at the same server; llama.cpp's `-c 64000` is the hard
engine ceiling (both slots), and the DSH `contextWindow: 32000` makes the
coder's session compact at 25.6K — the *quality* guardrail. The coder
subagent is then delegated with `agentOptions: { provider: "qwen38-concurrent",
model: "qwen38c-coder" }`. Drop the second entry if you want the coder to use
the full 64K (no OOM either way).

**Reasoning effort** is a separate per-session/per-subagent knob
(`agentOptions.reasoningEffort`), resolved by the provider adapter. It is NOT
the same as `contextWindow`. See the matrix below.

### 2e. Reasoning-effort matrix per role

The `qwen38` provider uses `compat.thinkingFormat: chat-template` with
`chatTemplateKwargs: { enable_thinking: false }`. On the live 27B, **thinking
is ON by default** (llama.cpp's Qwen3 chat template defaults `enable_thinking`
to true when not supplied); the DSH `chatTemplateKwargs` block *overrides* it
to false for sessions that don't set `reasoningEffort`. When a session sets
`reasoningEffort` (any level), DSH sends `enable_thinking: true` and the
thinking budget follows the effort level (minimal 1K / low 2K / medium 8K /
high 16K tokens; xhigh clamps to high).

| Role | Effort | Rationale |
|---|---|---|
| **Thinker** (132K, 8020) | **xhigh** (→ high, 16K thinking budget) | Deep planning/spec work; the 132K window absorbs the thinking tokens. |
| **Orchestrator** (64K slot 0, 8021) | **medium** (8K budget) | Read spec, dispatch, harvest — bounded, fast. Doesn't need deep deliberation. |
| **Coder** (32K slot 1, 8021) | **medium** (or low for mechanical units) | Correctness over depth; 32K cap means the thinking budget eats a bigger fraction of the window. Low (2K) for pure "apply this diff" units. |
| **Tinkerer / Scribe** (4B, 8099) | **off** (no `reasoningEffort`) | 4B has no meaningful reasoning budget; `enable_thinking: false` keeps it fast. |

The `reasoningEfforts` map in the provider entry (`low/medium/high`) declares
which levels are selectable in the UI; **xhigh is in pi-ai's enum** and
clamps to high — so the planner can be on xhigh even though the map only lists
`low/medium/high`. If you want xhigh to appear as a choice, add it to the map
(it's accepted by the adapter either way).

### 2c. Verify (Option A)

- `docker inspect qwen38-server --format '{{json .Config.Cmd}}'` shows
  `--parallel 2` and `-c 64000`.
- `curl.exe http://127.0.0.1:8020/health` → healthy.
- Two concurrent `POST /v1/chat/completions` (one short, one long) both
  progress without one fully blocking the other (llama.cpp schedules slots;
  with one GPU the compute is time-sliced, but contexts are independent).
- `nvidia-smi` shows total VRAM under 24 GB with both slots' KV allocated.
- A DSH subagent call targeting `qwen38` on 8020 runs in a *different
  session* (its own context array) and returns only its result — the
  in-process driver contract, unchanged by `-np 2`.

### 2g. Verify (concurrent container, two-role mode)

- `docker inspect qwen38-concurrent --format '{{json .Config.Cmd}}'` shows
  `-c 64000 --parallel 2`.
- `curl.exe http://127.0.0.1:8021/health` → healthy (start_period 180 s).
- Two concurrent requests to 8021 (slot 0 + slot 1) both progress.
- `nvidia-smi` shows total VRAM under 24 GB with both slots' KV allocated
  (worst case ~23.6 GB at 2×64K).
- A DSH subagent targeting `qwen38c-coder` compacts at ~25.6K (32K × 0.8)
  while the orchestrator session on `qwen38c` compacts at ~51.2K (64K × 0.8).
- `qwen38-server` (8020) is **stopped** during concurrent mode; the thinker
  session file is on disk and resumes losslessly after the swap back.

### BSOD note (0x113 VIDEO_TDR_FAILURE — recurring)

The 3090 has crashed **30+ times with bugcheck 0x113** (VIDEO_TDR_FAILURE,
GPU 0x10de, params 0x19/0x2/0x10de/0x2204) from 7/26 through 9/7/2026,
identical signature every time. The machine freezes for ~18 minutes before
the Windows watchdog forces a reboot. `TdrDelay` is already raised to 96 s
(default 2 s) — that has not prevented the crashes. Driver 32.0.16.1062
(dated 6/11/2026) predates the first crash, so this is not a new-driver
regression.

**What the minidump actually shows** (strings scan of
`C:\WINDOWS\Minidump\090726-15375-01.dmp`, no WinDbg needed):

```
nvlddmkm  \Device\Video3  UCodeReset TDR occurred on GPUID:100
PCI\VEN_10DE&DEV_2204&SUBSYS_403B1458&REV_A1
```

- `DEV_2204` = the 3090's GPU id (= bugcheck param 4, the violating GPU).
- `SUBSYS_403B1458` = **1458 = ASUS** (ASUS 3090).
- **`UCodeReset`** = the NVIDIA driver's *microcode reset* path — on an engine
  hang, nvlddmkm first tries a soft GPU microcode reset. **The TDR fired inside
  that reset path and the reset failed.** That is why `TdrDelay=96` does not
  help: 96 s buys time for a hung engine to finish, but the failure mode is the
  *reset itself failing*, after which dxgkrnl bugchecks. Same sequence, all 30+
  crashes.

**Driver version check (done 9/7, post-reboot):** the container does NOT
embed its own kernel driver — the NVIDIA Container Toolkit mounts the host's
`nvidia.ko` + UMD into the container, so host and container always run the
same KMD. The UMD (user-mode driver, `libcuda.so`) is what can drift:

| Layer | Version | Date |
|---|---|---|
| Host KMD (`nvlddmkm.sys`) | **610.62** (32.0.16.1062) | 6/11/2026 |
| Container UMD (`libcuda.so.1`, injected) | **610.43.02** | 5/20 (image build) |
| Container `compat/libcuda.so.560.35.05` | 560.19 (CUDA 12.6 compat) | 10/2024 (image) |
| Container CUDA toolkit | 12.6.77 | image |

The UMD is **19 minor versions behind** the host KMD (610.43 vs 610.62).
NVIDIA supports UMD ≤ KMD (forward compat), so this is not a hard mismatch —
but it *is* a real version skew: the container's `libcuda.so` was baked into
the image on 5/20 and has not been refreshed since the host driver updated.
If the 610.62 KMD changed the reset/TDR path, the older UMD may not handle the
new behavior correctly. **Fix:** rebuild the container image with
`nvidia/cuda:12.6.3` (or pull a fresh `nvidia/cuda` base) so the UMD matches
the host KMD. Alternatively, the `compat/` 560.35 UMD is even older and would
be a worse mismatch — verify the container is NOT accidentally loading it
(`LD_LIBRARY_PATH` does not include `/usr/local/cuda/compat/`, so it should
not be, but confirm after repaste).

So the failure is **GPU-side** (engine hang → reset failure), not a compute
pattern. MTP speculative decoding was ruled out as a cause.

**Working hypothesis (user): the 3090 overheats — new thermal paste being
installed.** Sustained LLM load pushes
the GPU junction to its throttle limit; a dried-out factory thermal paste
(2–3+ years old) lets the junction run hot enough that the engine hangs and the
reset path fails.

**Action: repaste the 3090** (and clean the fins with compressed air — 3090
coolers clog fast). Acceptance test after repaste: a 30-min sustained decode
(or OCCT GPU stress) with `nvidia-smi -q -d TEMPERATURE,POWER,CLOCK` logged
every 10 s. If the junction stays well under the 90 °C throttle limit and no
UCodeReset TDR fires, the card is healthy and the two-27B-swap design is safe.
If it still TDRs after a clean repaste, stop treating it as thermal and move to
card/VRM/PSU diagnosis (VRM sag under the 3090's power spikes, or a failing
GPU/VRAM).

**Mode-switch risk note:** each swap (stop 8020 → start 8021) loads the 27B
into 24 GB — a VRAM/thermal spike and a TDR risk event. Until the card is
confirmed healthy post-repaste, add a `nvidia-smi` responsiveness check after
each swap before DSH points at it.

---

## 2f. vLLM alternative — evaluated, llama.cpp stays primary

The `qwen38-3090` vLLM container (vLLM 0.27.1, Qwen3.8-27B W4A16 `-fast`,
DFlash2 drafter, port 18020, `C:\Users\gru\qwen38-3090\`) was evaluated as a
one-container replacement for the thinker/concurrent swap. Measured facts from
its startup log:

- **KV pool = 5.2 GB total** (`kv_cache_memory_bytes: 5583457484`) →
  **57,669 tokens** at **96.8 KB/token** (bf16 KV). The hybrid
  GDN/linear-attention architecture makes per-token KV ~4× cheaper than a
  full-attention 27B, which is why 64K looks affordable.
- Config: `max_model_len 57344`, `max_num_seqs 4`,
  `max_num_batched_tokens 2048`, `gpu_memory_utilization 0.93`,
  `enable_prefix_caching True`, `tool_call_parser qwen3_xml`,
  `reasoning_parser qwen3`, `num_speculative_tokens 15` (DFlash2 drafts 7 +
  8 context fill).
- Weight load: **~109 s** from the D: mount (17.1 GB, 8 safetensors).
- Decode: ~114–124 t/s (DFlash2) vs ~60 t/s (llama.cpp MTP).
- `CTX=fast/long/huge` are **launch params** (`.env`), not patches — the
  qwen harness handles them; but switching CTX restarts the container
  (900 s start period), so it is not a hot swap.

**Why it does not replace the llama.cpp design:**

1. **KV is a shared pool, not per-agent.** 57,669 tokens total means 2 agents
   at 64K *cannot both be active* (need 128K tokens; pool holds 57.7K).
   llama.cpp's `-np 2 -c 64000` guarantees 2×64K (23.6 GB). "Any number of
   132K subagents" is not feasible on 24 GB under *any* engine — 132K ×
   96.8 KB ≈ 12.8 GB per agent; two = 25.6 GB.
2. **One model per container.** vLLM serves one model. The 64K-orchestrator +
   32K-coder split (per-agent `contextWindow`) needs two model entries —
   llama.cpp does it via one route + DSH `agentOptions` (coder →
   `qwen38c-coder` @ 32000). vLLM would need a second container or
   `--served-model-name` trickery that does not change the shared KV pool.
3. **Tool-calling trap (the "silently failed past a threshold"):** both the
   `qwen3` reasoning parser and `qwen3_xml` tool parser are active. With
   thinking ON, a long `<thinking>` block eats `max_tokens`, the tool XML is
   truncated mid-emit, and the parser returns **zero tool_calls + empty
   content**. Fix if vLLM is used: raise DSH `max_tokens` to 4096+ for tool
   sessions, or send `enable_thinking: false` for tool calls.
4. **Model load is slow from the D: mount (~109 s).** vLLM reads the
   safetensors over the Windows→WSL2 mount path; a native-WSL2 (Linux) path
   loads faster. But C: is filling (70 GB free) and D: has 882 GB free, so the
   mount stays — load time is the price.

**Verdict (revised 2026-09-09 after the CTX=long test — see 2g):** the
role-split rethink made vLLM the primary path for the single-container
setup. llama.cpp `concurrent` (8021) remains the deterministic 2×64K
fallback, but the "two concurrent 27B agents" it provided was a redundant
second *me* — the real concurrency (main session + coder subagent) is
what vLLM delivers natively.

---

## 2g. CTX=long test results (measured 2026-09-09, port 18021)

New container `qwen38-3090-long` (`C:\Users\gru\qwen38-3090-long\`, same
image, `CTX=long SPEC=dflash2 DFLASH_TOKENS=7 PREFIX_CACHE=1`), thinker
8020 stopped. Model `qwen3.8-27b` from the `-fast` variant,
`max_model_len 131072`, int8 KV, prefix caching on. DSH provider
`vllm-3090-long` wired in settings.yaml (`qwen3.8-27b` 131072 +
`qwen3.8-27b-coder` 32000, both `enable_thinking: false`).

**Throughput** (harness: `C:\Users\gru\qwen38-3090-long\run_tests.py`):

| Test | Result |
|---|---|
| decode, thinking ON (512 tok) | avg **70.2 t/s** (40.9–85.6; run 1 = CUDA-graph warmup) |
| decode, thinking OFF (512 tok) | avg **61.2 t/s** (57.8–64.6) |
| 4-way concurrent (512 each) | **111.2 t/s aggregate** (1288 tok / 11.6 s, avg TTFT 0.29 s) |
| prefill (~4019 tok) | **597 t/s** |

**Tool-call A/B at the exact 64K-failure setting (max_tokens=1500, 4 iters
× 5 cases):** thinking ON **20/20**, thinking OFF **20/20**. The silent
failure did **not** reproduce. It is load/context-dependent, not a hard
parser bug: at 1500 tokens on short prompts the model's thinking stays short
enough that the tool XML always completes. The mechanical risk is real — a
12-token probe returned `content: null` with reasoning present (reasoning
swallows the budget before content) — so the standing rule stands:
**tool sessions run `enable_thinking: false`** (already in the provider) and
**`max_tokens ≥ 4096`** if thinking is ever needed on.

**Thermals** (~4 min mixed load, `gpu_log.csv`, nvidia-smi every 10 s):
86–87 °C flat (idle-start 85 °C @ 0% util), 92–100% util, 206–249 W
(under the 280 W cap, no throttle), **no TDR**. Verdict: the card is
**hot but stable**; the vLLM path is thermally acceptable. The warm-at-idle
(85 °C at 0% util) is consistent with degraded paste, so the PTM975
repaste remains worth doing for margin — but it is **not blocking**.

**Net:** one vLLM container now carries the whole 27B role set — main
session at 131K + coder subagents (32K cap via `agentOptions`) concurrent,
~60–111 t/s, no mode switch. llama.cpp 8021 stays as the deterministic
2×64K fallback.

---

## Step 3 — Subagent roster wiring (after 1 + 2)

With the providers registered, the roster from `design-model-matrix.md` maps
to concrete targets:

| subagent | provider / model id | port | notes |
|---|---|---|---|
| Coder | `vllm-3090-long` / `qwen3.8-27b-coder` | 18021 | 27B, **32K** cap, concurrent w/ main session (vLLM batching) |
| Auditor | `vllm-3090-long` / `qwen3.8-27b-coder` | 18021 | 27B, 32K, isolated ctx (same route as Coder) |
| Tinkerer | `workbench-780m-vulkan` | 8099 | 4B on 780M, slow, background |
| Scribe | `workbench-780m-vulkan` | 8099 | 4B on 780M |
| Researcher | `workbench-780m-vulkan` (or Coder for hard ones) | 8099 / 18021 | 14B = on-demand swap on the 780M |

**Revised 2026-09-09:** the 27B subagent route moved from llama.cpp
`qwen38-concurrent` (8021) to vLLM `vllm-3090-long` (18021) — see 2g. The
**main session** runs on `qwen3.8-27b` (131K, the "orchestrator"/"me" — the
same session that plans, now also dispatching), and Coder/Auditor are the
subagents it dispatches, targeting `qwen3.8-27b-coder` (32K) via
`agentOptions: {provider: "vllm-3090-long", model: "qwen3.8-27b-coder"}`.
No mode switch: vLLM serves main + subagents concurrently on one container.
The llama.cpp `qwen38-concurrent` provider (8021) stays registered as the
deterministic 2×64K fallback if vLLM ever misbehaves.

Every subagent call is a Work Unit (your `INTER-MODEL-PROTOCOL.md` schema);
the subagent writes the result to the Work Unit file and returns only the
result. My slot-0 ctx grows by the result size, never by the subagent's
working context.

---

## Step 4 — ComfyUI as the 3090 swap tenant (the actual content solution)

ComfyUI **never fits the 780M** for your model class (7–18.5 GB per image
lane, shared DDR5 makes even a 7 GB lane ~10× slower than the 3090), and
it **cannot coexist with the 27B on the 3090** (16.4 GB + 7 GB KV = 24 GB,
already full). The solution is not a third GPU — it's **time-sharing the
3090**: ComfyUI is the *swap tenant*, the 27B is the *default tenant*, and
the model-manager (8022) does the swap.

### The loop (concrete)

1. You ask for an image (Telegram or in-session).
2. I write the Work Unit (prompt, lane, params) to `/shared/work/<id>.json`.
3. I call the model-manager: `load comfy-image` → it runs
   preflight → stop `qwen38-server` → verify GPU freed → start ComfyUI →
   verify healthy. **I am now down** (I'm the thing that got unloaded).
4. The render runs unattended (the 780M 4B stays up as a degraded brain for
   "is it done?").
5. The **watcher** (your existing `:8023` watchdog pattern) detects
   render-done → calls model-manager `unload comfy-image` → restarts
   `qwen38-server` → verifies healthy → drops the result into my inbox /
   pings Telegram.
6. I wake up, harvest the Work Unit result, continue.

### What this means

- **ComfyUI and the 27B never coexist.** They serialize on the 3090, with
  the manager doing the swap and the watcher closing the loop. There is no
  configuration where both are resident on 24 GB; the design stops
  pretending there is.
- **Each render costs minutes of me-down** (swap out ~60–90 s + render +
  swap back ~60–90 s). That's the honest price, and it's a *user decision*
  (you ask for the image), not something I do silently.
- **The model-manager is the trimmed 8022 orchestrator**: keep
  preflight/stop/verify-gpu/start/verify-healthy/recovery/swap-history,
  delete everything that assumes "the master is a model on 8020". The
  watcher is the new addition (or the existing watchdog extended to watch
  render completion, not just gateway health).
- **Dolphin and the voice models are swap tenants too** (same loop, same
  cost). The 780M is *never* a swap tenant — it's always-on and cheap.

## Apply order

1. **Step 1 (now, safe):** start the 780M server on 8099, add the
   `qwen38-780m-vulkan` provider to `settings.yaml`, verify with a subagent
   call. No restart, no disruption.
2. **Step 2 (last thing, before logging off):** apply Option A (`-np 2`,
   `CTX_SIZE=64000`) — this **restarts `qwen38-server`**, dropping the model
   serving the current session. This is the blip you asked to have at the
   very end.
3. **Step 3:** wire the roster, do a real Coder (slot 1) + Tinkerer (780M)
   delegation as a smoke test — confirms true concurrency (both progress at
   once) and that my ctx is 64K not 132K.
4. **Step 4 (separate milestone):** trim the 8022 orchestrator to the dumb
   manager + add the watcher loop. Do a real image render end-to-end
   (ask → Work Unit → swap → render → harvest → reload → notify). This is
   the ComfyUI solution made real.

## What I did NOT change

- No container restarted. `qwen38-server` is still the live single-slot
  132K orchestrator. `model-orchestrator` (8022) untouched.
- The 780M test server I started on 8099 during the bench is still running
  (it's the workbench). The 3090 Vulkan test server on 8098 was killed.
- No `.env` or compose file edited.
