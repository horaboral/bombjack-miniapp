// Renders the REAL drawSupermanS from bombjack.html in headless Chrome and
// saves a PNG strip of spin phases.
const fs = require('fs');
const path = require('path');
const puppeteer = require('puppeteer-core');

const CHROME = 'C:\\Users\\gru\\.cache\\puppeteer\\chrome\\win64-149.0.7827.22\\chrome-win64\\chrome.exe';

(async () => {
  const html = fs.readFileSync(path.join(__dirname, '..', 'bombjack.html'), 'utf8');
  const i = html.indexOf('function drawSupermanS');
  if (i < 0) throw new Error('drawSupermanS not found');
  let j = html.indexOf('{', i), depth = 0, k = j;
  for (; k < html.length; k++) {
    if (html[k] === '{') depth++;
    else if (html[k] === '}') { depth--; if (depth === 0) break; }
  }
  const fnSrc = html.slice(i, k + 1);
  const outPath = path.join(__dirname, 'preview_superman_real.png');

  const browser = await puppeteer.launch({
    executablePath: CHROME,
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--force-color-profile=srgb'],
  });
  const page = await browser.newPage();
  await page.setViewport({ width: 1500, height: 150, deviceScaleFactor: 1 });
  // Build a self-contained page with the real function embedded.
  const pageHtml = `<!DOCTYPE html><html><head><meta charset="utf-8"></head>
<body style="margin:0;background:#0a0e18;">
<canvas id="c" width="1500" height="150"></canvas>
<script>
window.__drawSupermanS = ${fnSrc.replace('function drawSupermanS', 'function')} ;
const SIZE = 9, cell = 150, phases = [0,10,20,30,40,50,60,70,80,90];
const g = document.getElementById('c').getContext('2d');
g.fillStyle = '#0a0e18'; g.fillRect(0,0,1500,150);
for (let i = 0; i < phases.length; i++) {
  g.save();
  g.translate(i*cell + 10, 10);
  g.scale(6, 6);
  window.__drawSupermanS(g, 10, 12, SIZE, phases[i]);
  g.restore();
  g.fillStyle = '#c8c8c8'; g.font = '13px monospace';
  g.fillText('rot ' + phases[i], i*cell + 10, 138);
}
document.title = 'done';
<\/script></body></html>`;
  await page.setContent(pageHtml, { waitUntil: 'load' });
  await page.waitForFunction("document.title === 'done'", { timeout: 5000 });
  await page.screenshot({ path: outPath });
  await browser.close();
  console.log('wrote ' + outPath);
})().catch(e => { console.error(e && e.message || e); process.exit(1); });
