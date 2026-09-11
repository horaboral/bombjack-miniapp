import { readFileSync } from 'node:fs';
import { zstdDecompressSync } from 'node:zlib';

const file = process.argv[2];
const buf = readFileSync(file);
const MAGIC = [0x28, 0xb5, 0x2f, 0xfd];
const isMagic = (b, i) => MAGIC.every((m,k) => b[i+k] === m);

// find all magic offsets (cap)
let offs = [], i = 0;
while (i + 4 <= buf.length && offs.length < 50) {
  if (isMagic(buf, i)) offs.push(i);
  i++;
}
console.log('magic offsets (first 50):', offs);
for (const o of offs.slice(0, 8)) {
  const fhd = buf[o+4];
  const hasCS = (fhd & 0x01) !== 0;
  let cs = -1, p = o + 5;
  if (hasCS) { const n = [1,2,4,8][(fhd>>3)&0x03]; cs = buf.readUIntLE(p, n); p += n; }
  if (fhd & 0x02) p += 1;
  console.log('frame at', o, 'fhd=0x'+fhd.toString(16), 'hasCS=', hasCS, 'cs=', cs, 'headerEnd=', p);
  // try decompress [o, o+p+cs]
  if (hasCS) {
    const end = p + cs;
    try {
      const dec = zstdDecompressSync(buf.subarray(o, end));
      console.log('  -> decompressed OK, bytes=', dec.length, 'head=', dec.toString('utf8').slice(0, 80).replace(/\n/g,' '));
    } catch (e) {
      console.log('  -> FAILED to [o,end):', e.message.slice(0, 80));
      // try whole rest
      try {
        const dec = zstdDecompressSync(buf.subarray(o));
        console.log('  -> whole-rest OK bytes=', dec.length);
      } catch (e2) { console.log('  -> whole-rest FAILED:', e2.message.slice(0,80)); }
    }
  }
}
