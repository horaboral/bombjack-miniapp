// Trace what happens when an enemy falls off a platform tip
const fs = require('fs');
const vm = require('vm');
const html = fs.readFileSync(__dirname + '/../bombjack.html', 'utf8');
const re = /<script>([\s\S]*?)<\/script>/g;
const blocks = [];
const seen = new Set();
let m;
while ((m = re.exec(html)) !== null) {
  let src = m[1];
  src = src.replace(/^(?:const|let) (\w+)/gm, (mm, name) => seen.has(name) ? '' : (seen.add(name), 'var ' + name));
  blocks.push(src);
}
const ctxStub = () => new Proxy({}, { get: (t, p) => (typeof p === 'string' ? () => {} : undefined) });
const elStub = () => ({ width: 0, height: 0, getContext: ctxStub, addEventListener: () => {}, getBoundingClientRect: () => ({ left: 0, top: 0, width: 0, height: 0 }), setPointerCapture: () => {} });
const sandbox = {
  window: null, localStorage: { getItem: () => '0', setItem: () => {} },
  document: { createElement: () => ({ width: 0, height: 0, getContext: ctxStub }), getElementById: elStub, addEventListener: () => {}, body: { appendChild: () => {}, style: {} } },
  performance: { now: () => 0 }, navigator: { vibrate: () => {} },
  Telegram: { WebApp: { ready(){}, expand(){}, setHeaderColor(){}, setBackgroundColor(){}, onEvent(){}, offEvent(){}, sendData(){}, initData:'', initDataUnsafe:{}, version:'', platform:'', colorScheme:'dark', themeParams:{}, HapticFeedback:{ impactOccurred(){}, notificationOccurred(){}, selectionChanged(){} }, MainButton:{ setText(){return this;}, setColor(){}, show(){}, hide(){}, onClick(){}, offClick(){} }, BackButton:{ show(){}, hide(){}, onClick(){}, offClick(){} } } },
  Image: class { constructor() { this.complete = false; } },
  AudioContext: null, webkitAudioContext: null,
  requestAnimationFrame: () => 0, addEventListener: () => {},
  setTimeout: () => 0, setInterval: () => 0,
  console, globalThis,
};
sandbox.window = sandbox;
sandbox.haptic = () => {}; sandbox.beep = () => {}; sandbox.AC = null;
vm.createContext(sandbox);
function findBlock(pred) { for (let i = 0; i < blocks.length; i++) if (pred(blocks[i])) return i; return -1; }
function runBlock(idx, label) {
  if (idx < 0) { console.log('FATAL: ' + label + ' block not found'); process.exit(2); }
  vm.runInContext(blocks[idx], sandbox, { filename: 'block' + (idx + 1) + '.js' });
}
runBlock(findBlock(b => b.includes('CFG = {') && b.includes('SCREENS = [')), 'cfg');
runBlock(findBlock(b => b.includes('G = {') && b.includes('function setScreen')), 'state');
runBlock(findBlock(b => b.includes('function enemyStep')), 'enemy');
const S = sandbox;

S.setScreen(0);
S.G.st = S.ST.PLAY;
S.G.freeze = 0;
S.P.dead = true; // prevent death noise

// Show all platforms
console.log('Platforms (screen 0):');
for (const p of S.G.plat) console.log('  y=' + p.y + ' x=[' + p.x + ',' + (p.x + p.w) + '] w=' + p.w);

// Place a cat on the 2nd-lowest platform (y=168), near its right edge
// so it walks right and falls off
S.G.enemies = [];
const e = S.spawnEnemy('cat');
// pyramid: [[10,200,34],[86,200,34],[40,168,46],[10,140,34],[86,140,34],[52,112,40]]
// 2nd lowest = y=168 (x=40,w=46), above the bottom two
const pl = S.G.plat.find(p => p.y === 168);
e.surf = 'plat'; e.minX = pl.x + 6; e.maxX = pl.x + pl.w - 6;
e.baseY = pl.y - 17; e.y = e.baseY;
e.x = pl.x + pl.w - 8; e.dir = 1; // near right edge, walking right
e.speed = 0.4; e.type = 'cat'; e.jumpCd = 99999;
e._jumpStop = 0; e._jumpTarget = null; e._fallFrom = null; e.vy = 0; e.t = 0;

console.log('\nStarting: cat on plat y=168 at x=' + e.x + ', walking right (maxX=' + e.maxX + ')');
console.log('Plats below: y=200 at x=[10,44] and x=[86,120]');
console.log('Cat x range: ' + e.x + ' -> ' + (e.x + 30) + ' (will walk right past maxX=' + e.maxX + ')');

// Trace 80 frames
for (let f = 0; f < 80; f++) {
  S.stepEnemyWalk(e);
  if (f < 20 || f % 10 === 0) {
    const overEdge = (e.surf !== 'ground') && ((e.x < e.minX) || (e.x > e.maxX));
    console.log('f=' + f + ' x=' + e.x.toFixed(1) + ' y=' + e.y.toFixed(1) + ' vy=' + e.vy.toFixed(2) + ' surf=' + e.surf + ' fallFrom=' + (e._fallFrom || '-') + ' overEdge=' + overEdge);
  }
  if (e.surf === 'ground') {
    console.log('  -> Landed on GROUND at f=' + f + ' (missed all platforms below!)');
    break;
  }
}
console.log('\nFinal: surf=' + e.surf + ' x=' + e.x.toFixed(1) + ' y=' + e.y.toFixed(1));

// Now trace what the landing search finds
console.log('\n--- Landing search trace ---');
const srcTop = e._fallFrom || (168);
console.log('srcTop=' + srcTop);
for (const p2 of S.G.plat) {
  if (p2.y >= srcTop - 1) { console.log('  plat y=' + p2.y + ' x=[' + p2.x + ',' + (p2.x + p2.w) + '] — SKIPPED (not below srcTop)'); continue; }
  const inX = e.x > p2.x - 4 && e.x < p2.x + p2.w + 4;
  console.log('  plat y=' + p2.y + ' x=[' + p2.x + ',' + (p2.x + p2.w) + '] — x=' + e.x.toFixed(1) + ' ' + (inX ? 'IN RANGE' : 'MISS'));
}
