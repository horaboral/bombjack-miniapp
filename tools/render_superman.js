// Headless render of the REAL drawSupermanS from bombjack.html.
// Extracts the function source, runs it against a node-canvas context,
// and writes a PNG strip of spin phases.
const fs = require('fs');
const path = require('path');
const { createCanvas } = require('canvas');

const html = fs.readFileSync(path.join(__dirname, '..', 'bombjack.html'), 'utf8');
function extractFn(name) {
  const i = html.indexOf('function ' + name);
  if (i < 0) throw new Error(name + ' not found');
  let j = html.indexOf('{', i), depth = 0, k = j;
  for (; k < html.length; k++) {
    if (html[k] === '{') depth++;
    else if (html[k] === '}') { depth--; if (depth === 0) break; }
  }
  return html.slice(i, k + 1);
}
const src = extractFn('drawSupermanS');
const drawSupermanS = new Function('g', 'x', 'y', 'size', 'rotT', src);

const SIZE = 9;
const cell = 110, phases = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90];
const W = cell * phases.length, H = 150;
const canvas = createCanvas(W, H);
const g = canvas.getContext('2d');
g.fillStyle = '#0a0e18';
g.fillRect(0, 0, W, H);
phases.forEach((p, i) => {
  // each cell: draw at native size then it's tiny — scale context up 4x for visibility
  g.save();
  g.translate(i * cell + 8, 8);
  g.scale(4, 4);
  drawSupermanS(g, 11, 14, SIZE, p);
  g.restore();
  g.fillStyle = '#c8c8c8';
  g.font = '11px monospace';
  g.fillText('rot ' + p, i * cell + 8, H - 12);
});
fs.writeFileSync(path.join(__dirname, 'preview_superman_real.png'),
  canvas.toBuffer('image/png'));
console.log('wrote tools/preview_superman_real.png  (' + W + 'x' + H + ')');
