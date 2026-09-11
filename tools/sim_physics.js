// Headless simulation of the player rise-zone physics (v38: jump-gated rise).
// Key rule: the hero only rises while P.jumping is true AND the steer is in
// the 50..130 deg band. Mid-air jump taps have no effect. Pointing up from
// a free-fall does NOT lift the hero.
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
  Image: class { constructor() { this.complete = false; } },
  AudioContext: null, webkitAudioContext: null,
  requestAnimationFrame: () => 0, addEventListener: () => {},
  setTimeout: () => 0, setInterval: () => 0,
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
  vm.runInContext(blocks[idx], sandbox, { filename: 'block' + (idx + 1) + '.js' });
}
runBlock(findBlock(b => b.includes('CFG = {') && b.includes('SCREENS = [')), 'cfg');
runBlock(findBlock(b => b.includes('G = {') && b.includes('function setScreen')), 'state');
runBlock(findBlock(b => b.includes('function playerStep')), 'player');
const S = sandbox;
let pass = 0, fail = 0;
function check(cond, label, failMsg) {
  if (cond) { pass++; console.log('PASS: ' + label); }
  else { fail++; console.log('FAIL: ' + label + ' — ' + (failMsg || '')); }
}

// Set up player mid-air with an ACTIVE JUMP (P.jumping = true)
function jumpingPlayer(y) {
  S.P.x = 70; S.P.y = y; S.P.vy = -2; S.P.vx = 0;
  S.P.grounded = false; S.P.jumping = true; S.P.glide = false;
  S.P.dead = false; S.P.invuln = 0;
  S.G.jumpQueued = 0; S.G.jumpHeld = false;
  S.G.stick = null; S.G.stickT = 0;
  S.IN.sx = 0; S.IN.sy = 0;
  S.G.st = S.ST.PLAY;
  S.G.enemies = [];
  S.G.plat = [];
}

// Set up player mid-air with NO active jump (free-fall / post-jump)
function freefallPlayer(y) {
  S.P.x = 70; S.P.y = y; S.P.vy = 0; S.P.vx = 0;
  S.P.grounded = false; S.P.jumping = false; S.P.glide = false;
  S.P.dead = false; S.P.invuln = 0;
  S.G.jumpQueued = 0; S.G.jumpHeld = false;
  S.G.stick = null; S.G.stickT = 0;
  S.IN.sx = 0; S.IN.sy = 0;
  S.G.st = S.ST.PLAY;
  S.G.enemies = [];
  S.G.plat = [];
}

// ---- Test 1: jump in progress + hold straight up (90deg) => keeps rising ----
jumpingPlayer(150);
S.IN.sx = 0; S.IN.sy = -1;
const y0 = S.P.y;
for (let f = 0; f < 30; f++) S.playerStep();
check(S.P.y < y0 - 5, 'jump active + straight-up steer keeps rising (y ' + y0 + ' -> ' + S.P.y.toFixed(1) + ')',
  'did not rise: y ' + S.P.y.toFixed(1));

// ---- Test 2: jump in progress + 45deg (outside band) => no lift, falls ----
jumpingPlayer(150);
S.IN.sx = 0.707; S.IN.sy = -0.707;
const y1 = S.P.y;
for (let f = 0; f < 30; f++) S.playerStep();
check(S.P.y > y1, 'jump active + 45deg (outside band) does not lift (y ' + y1 + ' -> ' + S.P.y.toFixed(1) + ')',
  'rose on 45deg: y ' + S.P.y.toFixed(1));

// ---- Test 3: jump in progress + 135deg (outside band) => no lift ----
jumpingPlayer(150);
S.IN.sx = -0.707; S.IN.sy = -0.707;
const y2 = S.P.y;
for (let f = 0; f < 30; f++) S.playerStep();
check(S.P.y > y2, 'jump active + 135deg (outside band) does not lift (y ' + y2 + ' -> ' + S.P.y.toFixed(1) + ')',
  'rose on 135deg: y ' + S.P.y.toFixed(1));

// ---- Test 4: jump in progress + 60deg (inside band) => rises ----
jumpingPlayer(150);
S.IN.sx = Math.cos(60 * Math.PI / 180); S.IN.sy = -Math.sin(60 * Math.PI / 180);
const y3 = S.P.y;
for (let f = 0; f < 30; f++) S.playerStep();
check(S.P.y < y3 - 3, 'jump active + 60deg keeps rising (y ' + y3 + ' -> ' + S.P.y.toFixed(1) + ')',
  'did not rise at 60deg: y ' + S.P.y.toFixed(1));

// ---- Test 5: jump in progress + 120deg (inside band) => rises ----
jumpingPlayer(150);
S.IN.sx = Math.cos(120 * Math.PI / 180); S.IN.sy = -Math.sin(120 * Math.PI / 180);
const y4 = S.P.y;
for (let f = 0; f < 30; f++) S.playerStep();
check(S.P.y < y4 - 3, 'jump active + 120deg keeps rising (y ' + y4 + ' -> ' + S.P.y.toFixed(1) + ')',
  'did not rise at 120deg: y ' + S.P.y.toFixed(1));

// ---- Test 6: NO jump (free-fall) + point up => does NOT rise (THE KEY FIX) ----
freefallPlayer(150);
S.IN.sx = 0; S.IN.sy = -1;
const y5 = S.P.y;
for (let f = 0; f < 30; f++) S.playerStep();
check(S.P.y >= y5 - 2, 'free-fall + point up does NOT lift (y ' + y5 + ' -> ' + S.P.y.toFixed(1) + '), stays at or below start',
  'hero rose from free-fall on up-steer: y ' + S.P.y.toFixed(1));

// ---- Test 7: NO jump (free-fall) + no steer => falls ----
freefallPlayer(150);
S.IN.sx = 0; S.IN.sy = 0;
const y6 = S.P.y;
for (let f = 0; f < 30; f++) S.playerStep();
check(S.P.y > y6, 'free-fall + no steer => falls (y ' + y6 + ' -> ' + S.P.y.toFixed(1) + ')',
  'did not fall: y ' + S.P.y.toFixed(1));

// ---- Test 8: mid-air jump tap has NO effect ----
jumpingPlayer(150);
S.P.vy = -2;
S.G.jumpQueued = 1; // simulate a mid-air tap
S.playerStep();
check(S.P.vy > -3.5, 'mid-air tap does not re-jump (vy=' + S.P.vy.toFixed(2) + ', would be ~-4.25 if re-jumped)',
  'mid-air tap re-jumped: vy=' + S.P.vy.toFixed(2));

// ---- Test 9: jump rises, then player lands, then points up from ground => no lift (must jump first) ----
S.P.x = 70; S.P.y = S.CFG.GROUND_Y - S.CFG.PLAYER_H;
S.P.vy = 0; S.P.vx = 0; S.P.grounded = true; S.P.jumping = false;
S.G.st = S.ST.PLAY; S.G.enemies = []; S.G.plat = [];
S.G.stickT = 0;
S.IN.sx = 0; S.IN.sy = -1; // point up while grounded
const y7 = S.P.y;
for (let f = 0; f < 30; f++) S.playerStep();
check(S.P.y >= y7 - 1, 'pointing up from ground (no jump) does not lift (y ' + y7 + ' -> ' + S.P.y.toFixed(1) + ')',
  'hero lifted from ground without jump: y ' + S.P.y.toFixed(1));

console.log(fail === 0 ? '=== ALL PHYSICS TESTS PASSED ===' : '=== ' + fail + ' FAILED ===');
process.exit(fail === 0 ? 0 : 1);
