import { readFileSync } from 'node:fs';
import { zstdDecompressSync } from 'node:zlib';

const file = process.argv[2];
const buf = readFileSync(file);
const text = zstdDecompressSync(buf).toString('utf8');
console.log('decompressed length:', text.length);
console.log('num newlines:', text.split('\n').length);
// Is it one big JSON or JSONL?
const first = text.slice(0, 200);
console.log('HEAD:', first);
console.log('TAIL:', text.slice(-200));
// Try to see if it's an array
const t2 = text.trim();
if (t2.startsWith('[') || t2.startsWith('{')) {
  try {
    const obj = JSON.parse(t2);
    console.log('PARSED as single JSON. type=', typeof obj, Array.isArray(obj) ? 'array len ' + obj.length : '');
    if (Array.isArray(obj)) {
      const types = {};
      for (const e of obj) { const k = e.type || e.kind || 'x'; types[k] = (types[k]||0)+1; }
      console.log('entry types:', JSON.stringify(types, null, 1));
      console.log('sample entry keys:', Object.keys(obj[0]||{}));
    }
  } catch (e) {
    console.log('single JSON parse failed:', e.message.slice(0,100));
    // maybe JSONL but with \r?
    const lines = t2.split(/\r?\n/).filter(l=>l.trim());
    console.log('non-empty lines:', lines.length);
    console.log('line0 head:', lines[0]?.slice(0,150));
  }
}
