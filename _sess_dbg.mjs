import { readFileSync } from 'node:fs';
import { zstdDecompressSync } from 'node:zlib';

const file = process.argv[2];
const buf = readFileSync(file);
console.log('file size', buf.length);
console.log('first 16 bytes:', buf.subarray(0, 16).toString('hex'));
const MAGIC = Buffer.from([0x28, 0xb5, 0x2f, 0xfd]);
// find all magic offsets
let off = buf.indexOf(MAGIC);
let count = 0;
while (off !== -1 && count < 20) {
  console.log('magic at', off, 'fhd=', buf[off + 4].toString(16), 'fhd byte5=', buf[off + 5] ? buf[off+5].toString(16) : '');
  count++;
  off = buf.indexOf(MAGIC, off + 1);
}
console.log('magic count (first 20):', count);
// try whole-file decompress
try {
  const dec = zstdDecompressSync(buf);
  console.log('whole-file decompress OK, bytes:', dec.length);
  const s = dec.toString('utf8');
  console.log('first 300:', s.slice(0, 300));
} catch (e) {
  console.log('whole-file decompress FAILED:', e.message.slice(0, 150));
}
