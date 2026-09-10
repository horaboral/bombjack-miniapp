// Headless simulation of hero gravity / rise-zone physics from bombjack.html.
// Verifies: rise only while steer angle is in 50..130deg (majorly up);
// outside the band the hero falls (up steer only glides = slower fall).
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
sandbox.window = sandbox;
sandbox.haptic = () => {};
sandbox.beep = () => {};
sandbox.AC = null;
vm.createContext(sandbox);
function findBlock(pred) { for (let i = 0; i < blocks.length; i++) if (pred(blocks[i])) return i; return -1; }
function runBlock(idx, label) {
  if (idx < 0) { console.log('FATAL: ' + label + ' block not found'); process.exit(2); }
  try { vm.runInContext(blocks[idx], sandbox, { filename: 'block' + (idx + 1) + '.js' }); }
  catch (e) { console.log('block ' + (idx + 1) + ' (' + label + ') load FAILED: ' + e.message); process.exit(2); }
}
runBlock(findBlock(b => b.includes('CFG = {') && b.includes('SCREENS = [')), 'cfg');
runBlock(findBlock(b => b.includes('G = {') && b.includes('function setScreen')), 'state');
const S = sandbox;
let ok = 1;
function check(cond, msg, failmsg) {
  console.log((cond ? 'PASS' : 'FAIL') + ': ' + (cond ? msg : failmsg || msg));
  if (!cond) ok = 0;
}

// Set up player mid-air, no stick (we drive IN.sx/sy directly)
function airPlayer(y) {
  S.P.x = 70; S.P.y = y; S.P.vy = 0; S.P.vx = 0;
  S.P.grounded = false; S.P.glide = false; S.P.dead = false; S.P.invuln = 0;
  S.G.jumpQueued = 0; S.G.jumpHeld = false;
  S.G.stick = null; S.G.stickT = 0;
  S.IN.sx = 0; S.IN.sy = 0;
  S.G.st = S.ST.PLAY;
  S.G.enemies = []; // no touch deaths
  S.G.plat = [];
}

// ---- Test 1: hold straight up (90deg) => hero keeps rising ----
airPlayer(150);
S.IN.sx = 0; S.IN.sy = -1;
const y0 = S.P.y;
for (let f = 0; f < 30; f++) S.playerStep();
check(S.P.y < y0 - 5, 'straight-up steer (90deg) keeps rising (y ' + y0 + ' -> ' + S.P.y.toFixed(1) + ')',
  'did not rise: y ' + S.P.y.toFixed(1));

// ---- Test 2: hold 45deg up-right (outside band, <50) => hero does NOT rise ----
airPlayer(150);
S.IN.sx = 0.707; S.IN.sy = -0.707; // 45deg from horizontal
const y1 = S.P.y;
for (let f = 0; f < 30; f++) S.playerStep();
check(S.P.y > y1, '45deg steer (outside 50..130) does not lift; hero falls (y ' + y1 + ' -> ' + S.P.y.toFixed(1) + ')',
  'hero rose on 45deg steer: y ' + S.P.y.toFixed(1));

// ---- Test 3: hold 135deg up-left (outside band, >130) => no rise ----
airPlayer(150);
S.IN.sx = -0.707; S.IN.sy = -0.707; // 135deg
const y2 = S.P.y;
for (let f = 0; f < 30; f++) S.playerStep();
check(S.P.y > y2, '135deg steer (outside 50..130) does not lift; hero falls (y ' + y2 + ' -> ' + S.P.y.toFixed(1) + ')',
  'hero rose on 135deg steer: y ' + S.P.y.toFixed(1));

// ---- Test 4: hold 60deg (inside band) => rises ----
airPlayer(150);
S.IN.sx = Math.cos(60 * Math.PI / 180); S.IN.sy = -Math.sin(60 * Math.PI / 180);
const y3 = S.P.y;
for (let f = 0; f < 30; f++) S.playerStep();
check(S.P.y < y3 - 3, '60deg steer (inside band) keeps rising (y ' + y3 + ' -> ' + S.P.y.toFixed(1) + ')',
  'did not rise at 60deg: y ' + S.P.y.toFixed(1));

// ---- Test 5: hold 120deg (inside band) => rises ----
airPlayer(150);
S.IN.sx = Math.cos(120 * Math.PI / 180); S.IN.sy = -Math.sin(120 * Math.PI / 180);
const y4 = S.P.y;
for (let f = 0; f < 30; f++) S.playerStep();
check(S.P.y < y4 - 3, '120deg steer (inside band) keeps rising (y ' + y4 + ' -> ' + S.P.y.toFixed(1) + ')',
  'did not rise at 120deg: y ' + S.P.y.toFixed(1));

// ---- Test 6: release thumb (no steer) => hero falls (no lift) ----
airPlayer(150);
S.IN.sx = 0; S.IN.sy = 0;
const y5 = S.P.y;
for (let f = 0; f < 30; f++) S.playerStep();
check(S.P.y > y5, 'no steer (thumb released) => hero falls (y ' + y5 + ' -> ' + S.P.y.toFixed(1) + ')',
  'did not fall with no steer: y ' + S.P.y.toFixed(1));

// ---- Test 7: rising, then steer drops outside band => rise stops, falls ----
airPlayer(150);
S.IN.sx = 0; S.IN.sy = -1;
for (let f = 0; f < 15; f++) S.playerStep(); // establish rise
S.G.stickT = 0; // clear grace
S.IN.sx = 1; S.IN.sy = 0; // steer flat right (0deg, outside band)
const y6 = S.P.y;
for (let f = 0; f < 30; f++) S.playerStep();
check(S.P.y > y6, 'after leaving rise band, hero starts falling (y ' + y6 + ' -> ' + S.P.y.toFixed(1) + ')',
  'kept rising after leaving band: y ' + S.P.y.toFixed(1));

// ---- Test 8: grace — brief wobble (10 frames) outside band does not kill rise ----
airPlayer(150);
S.IN.sx = 0; S.IN.sy = -1;
for (let f = 0; f < 15; f++) S.playerStep(); // rising, stickT=10
S.IN.sx = 0; S.IN.sy = 0; // wobble: no steer for a moment
const y7 = S.P.y;
for (let f = 0; f < 8; f++) S.playerStep(); // within 10-tick grace
check(S.P.y <= y7 + 1, 'brief 8-frame wobble stays within grace, still rising/level (y ' + y7 + ' -> ' + S.P.y.toFixed(1) + ')',
  'wobble killed the rise immediately: y ' + S.P.y.toFixed(1));

console.log(ok ? '=== ALL PHYSICS TESTS PASSED ===' : '=== SOME PHYSICS TESTS FAILED ===');
process.exit(ok ? 0 : 1);
