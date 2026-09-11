import { readFileSync } from 'node:fs';
import { zstdDecompressSync } from 'node:zlib';

const file = process.argv[2];
const buf = readFileSync(file);
const MAGIC = Buffer.from([0x28, 0xb5, 0x2f, 0xfd]);

// Walk frames by finding magic offsets and using content-size when present.
let i = 0;
let frameIdx = 0;
let totalText = '';
while (i + 4 <= buf.length) {
  const b0 = buf[i];
  if (b0 >= 0x20 && b0 <= 0x2f) { const sz = buf.readUInt32LE(i+1); i += 4 + sz; continue; }
  if (!MAGIC.every((m,k) => buf[i+k] === m)) { i += 1; continue; }
  const fhd = buf[i+4];
  const hasCS = (fhd & 0x01) !== 0;
  const hasSum = (fhd & 0x04) !== 0;
  let p = i + 5;
  let cs = -1;
  if (hasCS) { const n = [1,2,4,8][(fhd>>3)&0x03]; cs = buf.readUIntLE(p, n); p += n; }
  if (fhd & 0x02) p += 1;
  const end = cs >= 0 ? p + cs + (hasSum ? 4 : 0) : -1;
  let ok = false;
  if (end > 0) {
    try {
      const dec = zstdDecompressSync(buf.subarray(i, end));
      totalText += dec.toString('utf8') + '\n';
      ok = true; i = end;
    } catch(e) { /* fallthrough to trial */ }
  }
  if (!ok) {
    // trial: expand end until success (cap a few MB per step)
    let lo = i + 8, hi = Math.min(buf.length, i + 4_000_000);
    let found = -1;
    // binary-ish search not valid for zstd; do linear from next magic
    // find next magic after i+4
    let nm = buf.indexOf(MAGIC, i + 4);
    if (nm === -1 || nm > hi) nm = buf.length;
    try { const dec = zstdDecompressSync(buf.subarray(i, nm)); totalText += dec.toString('utf8') + '\n'; i = nm; found = nm; }
    catch(e) { console.log('frame', frameIdx, 'at', i, 'could not decompress (end trial', nm, '):', e.message.slice(0,80)); i += 4; }
  }
  frameIdx++;
  if (frameIdx > 5000) break;
}
console.log('frames:', frameIdx, 'total text bytes:', totalText.length);
const lines = totalText.split('\n').filter(l=>l.trim());
console.log('lines:', lines.length);
const types = {};
for (const l of lines) { try { const o = JSON.parse(l); types[o.type||'?'] = (types[o.type||'?']||0)+1; } catch {} }
console.log(JSON.stringify(types, null, 1));
console.log('sample line types ok. first line:', lines[0]?.slice(0,120));
console.log('a tool line:', lines.find(l=>l.includes('"tool'))?.slice(0,200));
