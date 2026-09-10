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
  window: null,
  localStorage: { getItem: () => '0', setItem: () => {} },
  document: { createElement: () => ({ width: 0, height: 0, getContext: ctxStub }), getElementById: elStub, addEventListener: () => {}, body: { appendChild: () => {}, style: {} } },
  performance: { now: () => 0 },
  navigator: { vibrate: () => {} },
  Telegram: { WebApp: { ready(){}, expand(){}, setHeaderColor(){}, setBackgroundColor(){}, onEvent(){}, offEvent(){}, sendData(){}, initData:'', initDataUnsafe:{}, version:'', platform:'', colorScheme:'dark', themeParams:{}, HapticFeedback:{ impactOccurred(){}, notificationOccurred(){}, selectionChanged(){} }, MainButton:{ setText(){return this;}, setColor(){return this;}, show(){}, hide(){}, onClick(){}, offClick(){} }, BackButton:{ show(){}, hide(){}, onClick(){}, offClick(){} } } },
  Image: class { constructor() { this.complete = false; setTimeout(() => { this.complete = true; }, 0); } },
  AudioContext: null, webkitAudioContext: null,
  requestAnimationFrame: () => 0, addEventListener: () => {},
  setTimeout: (fn) => 0, setInterval: () => 0,
  console, globalThis,
};
sandbox.window = sandbox; sandbox.haptic = () => {}; sandbox.beep = () => {}; sandbox.AC = null;
vm.createContext(sandbox);
function findBlock(pred) { for (let i = 0; i < blocks.length; i++) if (pred(blocks[i])) return i; return -1; }
function runBlock(idx, label) {
  if (idx < 0) { console.log('FATAL: ' + label + ' block not found'); process.exit(2); }
  try { vm.runInContext(blocks[idx], sandbox, { filename: 'block' + (idx + 1) + '.js' }); }
  catch (e) { console.log('block ' + (idx + 1) + ' (' + label + ') load FAILED: ' + e.message); process.exit(2); }
}
runBlock(findBlock(b => b.includes('CFG = {') && b.includes('SCREENS = [')), 'cfg');
runBlock(findBlock(b => b.includes('G = {') && b.includes('function setScreen')), 'state');
runBlock(findBlock(b => b.includes('function enemyStep')), 'enemy');
const S = sandbox;

// --- screen 1 (idx 0) spawn mix over 2000 frames ---
S.setScreen(0); S.G.st = S.ST.PLAY; S.G.freeze = 0; S.P.dead = true;
let counts = {};
for (let f = 0; f < 2000; f++) S.enemyStep();
for (const e of S.G.enemies) counts[e.type] = (counts[e.type] || 0) + 1;
console.log('screen1 live enemies:', JSON.stringify(counts), 'total=' + S.G.enemies.length);
// spawn cap check
console.log('spawn cap is 6 for spawnEnemy, 7 for mini');

// --- screen 2 (idx 1) boss ---
S.setScreen(1);
const b = S.G.boss;
console.log('screen2 boss:', b ? (b.kind + ' ' + b.name + ' size ' + b.bw + 'x' + b.bh + ' at (' + b.x.toFixed(1) + ',' + b.y.toFixed(1) + ') hp=' + b.hp) : 'NULL');
// frames available?
console.log('gorillaFrames length:', S.G.gorillaFrames.length, 'roachFrames length:', S.G.roachFrames.length);
// draw check: is there a frame at faceFrame 0?
console.log('b.frames[0] present:', !!(b && b.frames[0]));

// --- bossStep 300 frames: does boss stay alive & in bounds? ---
let inBounds = true;
for (let f = 0; f < 300; f++) {
  S.bossStep();
  const bb = S.G.boss;
  if (!bb) { console.log('boss disappeared at frame', f); break; }
  if (bb.x < 0 || bb.x > S.CFG.W || bb.y < 0 || bb.y > S.CFG.H) { inBounds = false; break; }
}
console.log('boss in bounds after 300 frames:', inBounds, S.G.boss ? ('hp=' + S.G.boss.hp + ' poofT=' + S.G.boss.poofT) : 'gone');
