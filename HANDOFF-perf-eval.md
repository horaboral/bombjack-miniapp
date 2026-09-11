# HANDOFF — Agent Performance Evaluation (resume here)

**Task (user, verbatim):** "evaluate your performance. What could be bettered with an enhanced system prompt, your performance with tools, how many times you call them, the times you interpret their result wrongly. For this I want you to run an analysis on all our sessions, where you failed, what you could do better, where you started looping. Any other parameter you think would help in terms of the model, like reasoning budget, penalties etc. Search the web if needed"

User logging off; this is a resume point.

## STATE: analysis data is COMPLETE. Only the final report remains.

### 1. Decoded artifacts (all on disk in workdir)
- `_sess_dump.json` — every event line of all 8 sessions, decoded from `C:\Users\gru\.dsh\sessions\--D-dsh~0020workspace-dsh~0020test~0020project--\<dir>\session.jsonl.zstd`
- `_sess_report.json` — per-session + grand metrics
- `_sess_loops.json` — 30 consecutive-duplicate-call runs (≥3 identical in a row) + error→same-tool retries
- `_sess_analyze.mjs` — decoder (faithful port of `scanZstdFrames` from `@deepseek-ai/dsh-session-persistence-jsonl`, plus Node `zstdDecompressSync` per frame). Re-runnable anytime.
- Scratch: `_sess_dbg*.mjs`, `_sess_deep.mjs`, `_sess_probe.json` (deletable)

**Decoder recipe (worked):** session files are multi-frame zstd; Node's `zstdDecompressSync` on the WHOLE buffer only returns frame 1. Must walk frames by block headers (see `_sess_analyze.mjs`) and decompress each `[start,end)` slice. All 8 files decoded clean, 0 corrupt.

### 2. KEY METRICS (from `_sess_report.json`)
Grand across 8 sessions: **2,474 tool calls, 54 tool errors (2.2%), 2,24 user messages, 95 back-to-back identical tool-call pairs, 30 runs of ≥3 identical consecutive calls, 50 LLM retries, 55 compactions, 19 approvals.**

Tool distribution (grand): pwsh 1024, read 404, edit 289, write 289, grep 201, web_search 49, read_image 50, todo_write 58, job_output 58, glob 24, ask_user_question 17, subagent 3, misc <5.

Per-session (sid → turns/steps/calls/errors/retries/compactions):
- `session-4419aa77` (biggest, bombjack+mempalace): 30t/1534s/1528 calls/11 err/35 retry/28 compact
- `session-030c0467` (session-read repair + bombjack): 26t/626s/629 calls/24 err/10 retry/11 compact
- `session-c816bc81`: 20t/157s/186 calls/16 err/5 retry/13 compact/19 approvals
- `session-c32f5103`: 3t/86s/89 calls/2 err/0 retry/3 compact
- `1956f448`: 1t/36s/35 calls/1 err · `83d9e62`: 1t/8s/7 calls/0 err · `e4a40a89`, `session-59142530`: near-empty

**All 50 LLM retries = `503 "Loading model"` from local `qwen38-docker-q4-k-xl` provider** (policyKey normal/5 retries). Infrastructure, NOT model behavior — don't count against the model.

### 3. FAILURE CATEGORIES (from error-text aggregation)
Ranked by count:
1. **`edit` "old_string was not found"** ×10 (9× bombjack.html + 1× settings/profiles) — THE dominant model-caused failure. Pattern: edited a file from memory / after a compaction without re-reading exact current text; multi-line old_string mismatch.
2. **`edit` "requires reading … first"** ×7 — fs-observation-policy: tried to edit without a prior read in-session.
3. **`web_search` "Insufficient Balance" / "no API key"** ×7 — infra/billing, not model.
4. **`read_image` "model does not decode …"** ×10 — model (qwen38) can't take image input for certain refs; retried anyway.
5. `grep` timeout 30s ×3, `write` smoke/refs sandbox-denied ×3, `exit_plan_mode` outside plan mode ×1, `update_goal` no current goal ×1, missing-required-prop arg validation ×2, sandbox file-denied ×1.

**Interpreting-results-wrongly evidence:** the 30 duplicate-call runs ARE the "looping / misread" signal. Worst: `session-4419aa77` had an **edit ×11 consecutive identical** run on bombjack.html (same old_string failing repeatedly = kept re-sending a non-matching edit instead of re-reading), plus edit ×9 and ×7 runs on `memory-palace/consolidate.py`. `session-030c0467` had edit ×8 and ×5 on bombjack.html, pwsh ×7 (same creds-read script), job_output ×3 (polling). Root cause each time: **act on assumed file state instead of re-observing after a failed op or a compaction.**

### 4. WEB RESEARCH (done — cite these)
- [Increasing the Thinking Budget is Not All You Need](https://arxiv.org/html/2512.19585v1) — bigger reasoning budget ≠ better; strategy matters (Qwen3/DeepSeek-R1 distill).
- [Token-Budget-Aware LLM Reasoning (arXiv 2412.18547)](https://arxiv.org/pdf/2412.18547) — budget-aware reasoning.
- [BudgetThinker (arXiv 2508.17196)](https://arxiv.org/html/2508.17196) — control tokens for budget-aware reasoning.
- [Repetition Penalties: Preventing Loops in LLM Generation](https://mbrenndoerfer.com/writing/repetition-penalties-language-model-generation) — frequency vs presence penalty mechanics.
- [Stop the LLM From Rambling: Using Penalties to Control Repetition](https://dev.to/superorange0707/stop-the-llm-from-rambling-using-penalties-to-control-repetition-5h8) — frequency_penalty reduces already-seen tokens.
- [r/LocalLLaMA: Repetition penalties are terribly implemented](https://www.reddit.com/r/LocalLLaMA/comments/1g383mq/repetition_penalties_are_terribly_implemented_a/) — frequency penalty distorts grammar ("a/the/and"); penalties are a blunt instrument, better to fix at the loop/harness level.
- [SWE-Bench Pro (Scale)](https://static.scale.com/uploads/654197dc94d34f66c0f5184e/SWEAP_Eval_Scale%20(9).pdf) — small models (Qwen3-32B class) fail more on **tool use, syntax, context management**; large models on semantic correctness.

### 5. WHAT THE FINAL REPORT SHOULD CONTAIN (write this — the only remaining step)
Structure it as a direct answer to the user's sub-questions:
1. **Overall** — 2.2% tool-error rate is healthy; 2,474 calls / 2,24 msgs ≈ 11 calls/msg; the real cost is *loops*, not one-off errors.
2. **System-prompt improvements** (grounded in the data):
   - Add a hard rule: **after any `edit`/`write` failure or after a compaction, MUST `read` the exact region again before re-attempting** (would have eliminated the ×11/×9/×8 edit loops).
   - Add: **never retry an identical tool call more than once** — on a 2nd identical attempt, change strategy (re-read, widen/narrow, different tool). The 95 duplicate pairs are pure waste.
   - Add: **image tooling gate** — check the model accepts images before `read_image` (10 wasted calls); otherwise fall back to describe-by-code.
   - Add: **polling cap** for `job_output` (×3 runs) — use `wait:true` instead of repeated reads.
3. **Tool-call behavior** — pwsh is 41% of all calls (1024). Much of that is one-off `node -e` / `Set-Location` scripts that could be batched or written to a temp file once. Recommend: reuse a scratch script file instead of re-emitting identical pwsh blocks (the pwsh ×7 duplicate run).
4. **Wrong interpretation of results** — the concrete evidence is the 30 duplicate runs; the fix is observe→act discipline, not more tokens.
5. **Model params** (from research, cite links above):
   - **Reasoning budget:** don't just raise it (arXiv 2512.19585) — allocate *per task type*: low for mechanical edit/read, higher for multi-file refactor & debugging. A flat big budget wastes latency on the 1,500+ trivial steps.
   - **Penalties:** a small **frequency_penalty (0.1–0.3)** could suppress the token-level rambling, BUT it's a blunt instrument that distorts normal grammar (LocalLLaMA) and does NOT stop *tool-call* loops (those are structural, not token-repetition). Prefer harness-side loop detection (which DSH already has — `dsh-repeat-tool-reminder`) over sampling penalties for tool loops.
   - **Qwen3-class caveat** (SWE-Bench Pro): at this model size, tool-use and context management are the weak points — exactly where our data shows the failures, so the levers are prompt + harness, not more raw reasoning.
6. **Bottom line** — the highest-leverage single change: an "observe-before-retry, max-one-identical-retry" rule in the system prompt. It directly targets the 30 loops and 23 edit errors, which are the bulk of real waste.

### 6. Cleanup before/after
- Optional: delete scratch `_sess_dbg*.mjs`, `_sess_deep.mjs`, `_sess_probe.json`. KEEP `_sess_analyze.mjs`, `_sess_loops.mjs`, `_sess_report.json`, `_sess_dump.json`, `_sess_loops.json` as evidence.
- bombjack.html is currently committed & pushed (last: `817465c` hi-score table). The perf-eval work is analysis-only; no game changes expected.
- This workdir is NOT a git repo for these scratch files (gitignored except bombjack.html/docs/.gitignore) — so the handoff file + JSONs are the durable record.
