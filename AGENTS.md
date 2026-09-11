# Workspace notes (dsh test project)

Project-specific guidance for this workspace. The global `~/.dsh/AGENTS.md`
rules (delegate, shell discipline, failure handling, file hygiene) also apply.

## This workspace
- Used for DSH test sessions and performance-analysis exercises. Analysis
  artifacts live under `C:\Users\gru\.dsh\tmp-sessions\` (session zstd
  extraction, cross-session analyzer, failure breakdowns).
- The DSH implementation checkout for inspecting/extending DSH itself is at
  `C:\Users\gru\AppData\Local\npm-cache\_npx\1e7f6d9597241db0\`.

## Session log analysis
- Session logs are zstd concatenated checksummed frames (magic `28 b5 2f fd`
  LE). Node `zstdDecompressSync` decodes one frame per call — scan frames,
  subarray, decompress each.
- Key event shapes (see `C:\Users\gru\.dsh\tmp-sessions\` for working
  extractors):
  - `tool/call`: `data = { turn, step, callId, name, arguments }` —
    `arguments` is a JSON **string**; `callId` is directly on data.
  - `tool/result`: link back via `data.message.source.callId`.
  - `assistant/message`: tool calls exist as separate `tool/call` events, not
    as blocks inside assistant content.
  - `user/message`: `data.content` is directly on data (no nested `message`).
- Interpretability gate: `assertEventsSupported` in
  `dsh-session-persistence` — `KNOWN_SESSION_EVENT_TYPES.has(type) ||
  event.ignorable === true`.
