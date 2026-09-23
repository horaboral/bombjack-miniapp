// Renders the REAL drawSupermanS + drawMitsubishi from bombjack.html in
// headless Chrome and saves a PNG: Superman row (spin phases) + Mitsubishi row.
const fs = require('fs');
const path = require('path');
const puppeteer = require('puppeteer-core');

const CHROME = 'C:\\Users\\gru\\.cache\\puppeteer\\chrome\\win64-149.0.7827.22\\chrome-win64\\chrome.exe';

function extractFn(html, name) {
  const i = html.indexOf('function ' + name);
  if (i < 0) throw new Error(name + ' not found');
  let j = html.indexOf('{', i), depth = 0, k = j;
  for (; k < html.length; k++) {
    if (html[k] === '{') depth++;
    else if (html[k] === '}') { depth--; if (depth === 0) break; }
  }
  return html.slice(i, k + 1);
}

(async () => {
  const html = fs.readFileSync(path.join(__dirname, '..', 'bombjack.html'), 'utf8');
  const fnS = extractFn(html, 'drawSupermanS');
  const fnM = extractFn(html, 'drawMitsubishi');
  const fnP = extractFn(html, 'drawPillBase');
  const outPath = path.join(__dirname, 'preview_superman_real.png');

  const W = 1500, H = 320;
  const browser = await puppeteer.launch({
    executablePath: CHROME,
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--force-color-profile=srgb'],
  });
  const page = await browser.newPage();
  await page.setViewport({ width: W, height: H, deviceScaleFactor: 1 });
  const pageHtml = `<!DOCTYPE html><html><head><meta charset="utf-8"></head>
<body style="margin:0;background:#0a0e18;">
<canvas id="c" width="${W}" height="${H}"></canvas>
<script>
function drawPillBase(g, x, y, w, h, borderCol, rotT) { ${fnP.replace('function drawPillBase(g, x, y, w, h, borderCol, rotT) {', '')}
function drawSupermanS(g, x, y, size, rotT) { ${fnS.replace('function drawSupermanS(g, x, y, size, rotT) {', '')}
function drawMitsubishi(g, x, y, size, rotT) { ${fnM.replace('function drawMitsubishi(g, x, y, size, rotT) {', '')}
const SIZE = 9, cell = 150, phases = [0,10,20,30,40,50,60,70,80,90];
const g = document.getElementById('c').getContext('2d');
g.fillStyle = '#0a0e18'; g.fillRect(0,0,${W},${H});
// row 1: Superman, spin phases
for (let i = 0; i < phases.length; i++) {
  g.save(); g.translate(i*cell + 10, 10); g.scale(6, 6);
  drawSupermanS(g, 10, 12, SIZE, phases[i]); g.restore();
  g.fillStyle = '#c8c8c8'; g.font = '12px monospace';
  g.fillText('rot ' + phases[i], i*cell + 10, 132);
}
// row 2: Mitsubishi, same phases (size reference)
for (let i = 0; i < phases.length; i++) {
  g.save(); g.translate(i*cell + 10, 170); g.scale(6, 6);
  drawMitsubishi(g, 10, 12, SIZE, phases[i]); g.restore();
  g.fillStyle = '#888'; g.font = '12px monospace';
  g.fillText('MITSU rot ' + phases[i], i*cell + 10, 292);
}
document.title = 'done';
<\/script></body></html>`;
  page.on('pageerror', (e) => console.error('PAGE ERROR:', e.message));
  page.on('console', (m) => { if (m.type() === 'error') console.error('CONSOLE:', m.text()); });
  await page.setContent(pageHtml, { waitUntil: 'load' });
  await page.waitForFunction("document.title === 'done'", { timeout: 15000 });
  await page.screenshot({ path: outPath });
  await browser.close();
  console.log('wrote ' + outPath);
})().catch(e => { console.error(e && e.message || e); process.exit(1); });
