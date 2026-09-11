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
    if (part.type === 'tool-result' || part.type === 'tool_result' || part.content) {
      const inner = part.content;
      if (Array.isArray(inner)) for (const t of inner) if (t.type === 'text') out += t.text + '\n';
      else if (typeof inner === 'string') out += inner + '\n';
    } else if (part.type === 'text' && part.text) out += part.text + '\n';
  }
  return out;
}
function isToolError(l) {
  const c = l.data?.message?.content;
  if (Array.isArray(c)) for (const part of c) if (part.isError) return true;
  return false;
}

const perSession = {};
let grand = {
  toolCalls: 0, toolErrors: 0, steps: 0, userMsgs: 0, llmRetries: 0,
  compactions: 0, approvals: 0, byTool: {}, errByTool: {},
  repeatToolPairs: 0, repeatPairs: [],
};
for (const [sid, lines] of Object.entries(full)) {
  const s = { toolCalls: 0, toolErrors: 0, steps: 0, userMsgs: 0, llmRetries: 0,
    compactions: 0, approvals: 0, byTool: {}, errByTool: {},
    repeatPairs: [], turns: 0, firstTime: null, lastTime: null,
    errorSamples: [] };
  let prevTool = null;
  for (const l of lines) {
    const t = l.time || 0;
    if (!s.firstTime) s.firstTime = t;
    s.lastTime = t;
    switch (l.type) {
      case 'turn/start': s.turns++; break;
      case 'user/message': s.userMsgs++; break;
      case 'step/start': s.steps++; break;
      case 'llm/retry': s.llmRetries++; break;
      case 'compaction/start': s.compactions++; break;
      case 'approval/asked': s.approvals++; break;
      case 'tool/call': {
        const name = toolName(l) || '(unknown)';
        s.byTool[name] = (s.byTool[name] || 0) + 1;
        grand.byTool[name] = (grand.byTool[name] || 0) + 1;
        // repeated identical call (same tool, same args)
        if (prevTool && prevTool.name === name) {
          const key = name + '::' + JSON.stringify(toolArgs(l)).slice(0, 120);
          const pk = prevTool.key;
          if (key === pk) {
            s.repeatPairs.push({ name, args: String(toolArgs(l)).slice(0, 150) });
            grand.repeatToolPairs++;
          }
        }
        prevTool = { name, key: name + '::' + JSON.stringify(toolArgs(l)).slice(0, 120) };
        s.toolCalls++; grand.toolCalls++;
        break;
      }
      case 'tool/result': {
        if (isToolError(l)) {
          s.toolErrors++; grand.toolErrors++;
          // attribute to prev tool name
          const nm = prevTool?.name || '(unknown)';
          s.errByTool[nm] = (s.errByTool[nm] || 0) + 1;
          grand.errByTool[nm] = (grand.errByTool[nm] || 0) + 1;
          const txt = resultText(l).slice(0, 220);
          if (s.errorSamples.length < 12) s.errorSamples.push({ tool: nm, text: txt.replace(/\s+/g, ' ') });
        }
        break;
      }
    }
  }
  s.durationMin = s.firstTime ? Math.round((s.lastTime - s.firstTime) / 60000) : 0;
  grand.steps += s.steps; grand.userMsgs += s.userMsgs;
  grand.compactions += s.compactions; grand.approvals += s.approvals;
  perSession[sid] = s;
}
writeFileSync('_sess_report.json', JSON.stringify({ perSession, grand }, null, 2));

// console summary
for (const [sid, s] of Object.entries(perSession)) {
  console.log(`\n=== ${sid} ===`);
  console.log(`turns=${s.turns} steps=${s.steps} userMsgs=${s.userMsgs} toolCalls=${s.toolCalls} toolErrors=${s.toolErrors} llmRetries=${s.llmRetries} compactions=${s.compactions} approvals=${s.approvals} repeatPairs=${s.repeatPairs.length} durMin=${s.durationMin}`);
  const tools = Object.entries(s.byTool).sort((a,b)=>b[1]-a[1]);
  console.log('tools:', tools.map(([k,v])=>`${k}:${v}`).join(' '));
  if (Object.keys(s.errByTool).length) console.log('errors:', Object.entries(s.errByTool).sort((a,b)=>b[1]-a[1]).map(([k,v])=>`${k}:${v}`).join(' '));
  if (s.repeatPairs.length) console.log('repeated-call pairs:', JSON.stringify(s.repeatPairs.slice(0,8), null, 1));
}
console.log(`\n=== GRAND ===`);
console.log(JSON.stringify({ toolCalls: grand.toolCalls, toolErrors: grand.toolErrors, steps: grand.steps, userMsgs: grand.userMsgs, llmRetries: grand.llmRetries, compactions: grand.compactions, approvals: grand.approvals, repeatToolPairs: grand.repeatToolPairs, byTool: grand.byTool, errByTool: grand.errByTool }, null, 2));
