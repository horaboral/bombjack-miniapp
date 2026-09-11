import { readFileSync, writeFileSync } from 'node:fs';
const full = JSON.parse(readFileSync('_sess_dump.json', 'utf8'));

function toolName(l) { return l.data?.name || null; }
function toolArgs(l) {
  const a = l.data?.arguments;
  if (a == null) return null;
  if (typeof a === 'string') { try { return JSON.parse(a); } catch { return a; } }
  return a;
}
function resultText(l) {
  const c = l.data?.message?.content;
  if (!Array.isArray(c)) return '';
  let out = '';
  for (const part of c) {
    const inner = part.content;
    if (Array.isArray(inner)) for (const t of inner) if (t.type === 'text') out += t.text + '\n';
    else if (typeof inner === 'string') out += inner + '\n';
  }
  return out;
}
function isToolError(l) {
  const c = l.data?.message?.content;
  if (Array.isArray(c)) for (const part of c) if (part.isError) return true;
  return false;
}
function argSig(l) {
  const a = toolArgs(l);
  if (a == null) return '';
  // normalize: for pwsh take command tail; for read take file_path+offset+limit
  if (a.command) return a.command.slice(0, 200);
  const keys = ['file_path','path','pattern','offset','limit','query','queries'];
  return keys.filter(k => a[k] != null).map(k => `${k}=${typeof a[k] === 'string' ? a[k].slice(0, 150) : JSON.stringify(a[k])}`).join(' ');
}

// For each session: find runs of >=3 consecutive identical (tool, sig) calls,
// and collect error->same-tool-immediately-retried patterns.
const out = {};
for (const [sid, lines] of Object.entries(full)) {
  const calls = [];
  let lastErrTool = null;
  for (const l of lines) {
    if (l.type === 'tool/call') calls.push({ name: toolName(l), sig: argSig(l), t: l.time, args: toolArgs(l) });
    if (l.type === 'tool/result' && lastErrTool !== null) {
      // check if the NEXT call (already in calls after push ordering) — handle below
    }
  }
  // runs of identical consecutive
  const runs = [];
  let run = [];
  for (const c of calls) {
    const key = c.name + '||' + c.sig;
    const lastKey = run.length ? run[run.length-1].name + '||' + run[run.length-1].sig : null;
    if (key === lastKey) run.push(c); else { if (run.length >= 3) runs.push(run); run = [c]; }
  }
  if (run.length >= 3) runs.push(run);
  // error-then-retry: tool/result isError followed by tool/call same name
  const errRetry = [];
  for (let i = 1; i < lines.length; i++) {
    if (lines[i].type === 'tool/result' && isToolError(lines[i])) {
      const next = lines[i+1];
      if (next?.type === 'tool/call') {
        errRetry.push({ tool: toolName(next), err: resultText(lines[i]).replace(/\s+/g,' ').slice(0, 160) });
      }
    }
  }
  out[sid] = { runs: runs.map(r => ({ tool: r[0].name, sig: r[0].sig, n: r.length })), errRetryCount: errRetry.length, errRetry: errRetry.slice(0, 15) };
}
writeFileSync('_sess_loops.json', JSON.stringify(out, null, 2));
let totalRuns = 0;
for (const [sid, o] of Object.entries(out)) {
  if (!o.runs.length && !o.errRetryCount) continue;
  console.log(`\n=== ${sid} ===  (err->same-tool retries: ${o.errRetryCount})`);
  for (const r of o.runs) { totalRuns++; console.log(`  RUN x${r.n}  ${r.tool}: ${r.sig.slice(0, 120)}`); }
  for (const e of o.errRetry.slice(0, 6)) console.log(`  ERR-RETRY ${e.tool}: ${e.err.slice(0, 120)}`);
}
console.log(`\nTOTAL runs(>=3 identical consecutive): ${totalRuns}`);
