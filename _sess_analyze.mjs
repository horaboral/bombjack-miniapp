import { readFileSync, readdirSync, statSync, writeFileSync } from 'node:fs';
import { zstdDecompressSync } from 'node:zlib';

const SES = "C:\\Users\\gru\\.dsh\\sessions\\--D-dsh~0020workspace-dsh~0020test~0020project--";
const ZSTD_MAGIC = 0xfd2fb528;

// Faithful port of the package's scanZstdFrames (block-walking frame scanner).
function scanZstdFrames(buffer) {
  const frames = [];
  let offset = 0;
  while (offset < buffer.length) {
    const start = offset;
    if (buffer.length - offset < 4) return { frames, tornStart: start };
    if (buffer.readUInt32LE(offset) !== ZSTD_MAGIC) return { frames, tornStart: start, corrupt: true };
    offset += 4;
    if (offset === buffer.length) return { frames, tornStart: start };
    const descriptor = buffer.readUInt8(offset);
    offset += 1;
    if ((descriptor & 24) !== 0) return { frames, tornStart: start, corrupt: true };
    const contentSizeFlag = descriptor >>> 6;
    const singleSegment = (descriptor & 32) !== 0;
    const checksum = (descriptor & 4) !== 0;
    const dictionaryFlag = descriptor & 3;
    const dictionaryBytes = dictionaryFlag === 3 ? 4 : dictionaryFlag;
    const contentSizeBytes = contentSizeFlag === 0 ? (singleSegment ? 1 : 0) : (1 << contentSizeFlag);
    const remainingHeaderBytes = (singleSegment ? 0 : 1) + dictionaryBytes + contentSizeBytes;
    if (buffer.length - offset < remainingHeaderBytes) return { frames, tornStart: start };
    offset += remainingHeaderBytes;
    for (;;) {
      if (buffer.length - offset < 3) return { frames, tornStart: start };
      const blockHeader = buffer.readUIntLE(offset, 3);
      offset += 3;
      const lastBlock = (blockHeader & 1) !== 0;
      const blockType = (blockHeader >>> 1) & 3;
      const blockSize = blockHeader >>> 3;
      if (blockType === 3) return { frames, tornStart: start, corrupt: true };
      const payloadBytes = blockType === 1 ? 1 : blockSize;
      if (buffer.length - offset < payloadBytes) return { frames, tornStart: start };
      offset += payloadBytes;
      if (lastBlock) break;
    }
    if (checksum) {
      if (buffer.length - offset < 4) return { frames, tornStart: start };
      offset += 4;
    }
    frames.push({ start, end: offset });
  }
  return { frames };
}

function loadSession(file) {
  const buf = readFileSync(file);
  const { frames, corrupt } = scanZstdFrames(buf);
  const lines = [];
  for (const f of frames) {
    try {
      const dec = zstdDecompressSync(buf.subarray(f.start, f.end));
      for (const l of dec.toString('utf8').split('\n')) {
        if (!l.trim()) continue;
        try { lines.push(JSON.parse(l)); } catch {}
      }
    } catch (e) { lines.push({ _decompressError: String(e).slice(0, 80) }); }
  }
  return { lines, corrupt: !!corrupt };
}

const dirs = readdirSync(SES, { withFileTypes: true }).filter(d => d.isDirectory()).map(d => d.name);
const summary = [];
const full = {};
for (const d of dirs) {
  const file = SES + '\\' + d + '\\session.jsonl.zstd';
  const { lines, corrupt } = loadSession(file);
  const types = {};
  for (const l of lines) types[l.type || 'unknown'] = (types[l.type || 'unknown'] || 0) + 1;
  summary.push({ dir: d, bytes: statSync(file).size, lines: lines.length, corrupt, types });
  full[d] = lines;
}
writeFileSync('_sess_dump.json', JSON.stringify(full));
console.log(JSON.stringify(summary, null, 2));
