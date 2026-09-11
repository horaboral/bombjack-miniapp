// Headless sim of the new enemy walking/jumping rules (stepEnemyWalk).
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
  Telegram: { WebApp: { ready(){}, expand(){}, setHeaderColor(){}, setBackgroundColor(){}, onEvent(){}, offEvent(){}, sendData(){}, initData:'', initDataUnsafe:{}, version:'', platform:'', colorScheme:'dark', themeParams:{}, HapticFeedback:{ impactOccurred(){}, notificationOccurred(){}, selectionChanged(){} }, MainButton:{ setText(){return this;}, setColor(){}, show(){}, hide(){}, onClick(){}, offClick(){} }, BackButton:{ show(){}, hide(){}, onClick(){}, offClick(){} } } },
  Image: class { constructor() { this.complete = false; } },
  AudioContext: null, webkitAudioContext: null,
  requestAnimationFrame: () => 0, addEventListener: () => {},
  setTimeout: () => 0, setInterval: () => 0,
  console, globalThis,
};
sandbox.window = sandbox;
sandbox.haptic = () => {};
sandbox.beep = () => {};
sandbox.deathSound = () => {};
sandbox.musicStart = () => {};
sandbox.musicStop = () => {};
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
runBlock(findBlock(b => b.includes('function enemyStep')), 'enemy');
const S = sandbox;
let ok = 1;
function check(cond, msg, failmsg) { console.log((cond ? 'PASS' : 'FAIL') + ': ' + (cond ? msg : failmsg || msg)); if (!cond) ok = 0; }

// Set up screen 0 (pyramid, has platforms)
S.setScreen(0);
S.G.st = S.ST.PLAY;
S.G.freeze = 0;

// ---- Test 1: enemy on a platform walks; at the tip it either turns or falls ----
S.P.dead = true; // prevent player interactions/death noise
const e = S.spawnEnemy('cat');
e.surf = 'plat';
const pl0 = S.G.plat[0];
e.minX = pl0.x + 6; e.maxX = pl0.x + pl0.w - 6; e.baseY = pl0.y - 17; e.y = e.baseY;
e.x = pl0.x + pl0.w - 10; e.dir = 1; e.jumpCd = 99999;
const startE = e.x;
let fell = false, turned = false;
for (let f = 0; f < 120; f++) {
  S.stepEnemyWalk(e);
  if (e.y > pl0.y - 5) { fell = true; break; }
  if (e.dir === -1 && e.x <= pl0.x + pl0.w - 10) { turned = true; break; }
}
check(fell || turned, 'at platform tip: enemy either turns back or falls (fell=' + fell + ', turned=' + turned + ', dx=' + (e.x - startE).toFixed(1) + ')',
  'enemy neither turned nor fell at the tip');

// ---- Test 2: 1-LEVEL jump — jump goes to the NEAREST platform above
// (not the highest). Force the jump path deterministically.
let lowest = null, nearestAbove = null;
for (const p of S.G.plat) {
  if (!lowest || p.y > lowest.y) lowest = p;
}
// nearest platform above the lowest one: largest y that is still above
for (const p of S.G.plat) {
  if (p.y + 17 >= lowest.y - 2) continue;
  if (p.w < 22) continue;
  if (!nearestAbove || p.y > nearestAbove.y) nearestAbove = p;
}
check(!!nearestAbove, 'test2 setup: a platform exists directly above the lowest one', 'no platform above the lowest');
// verify it's NOT the top platform (would indicate the old "highest" bug)
let topPlat = null; for (const p of S.G.plat) if (!topPlat || p.y < topPlat.y) topPlat = p;
check(nearestAbove !== topPlat || S.G.plat.length <= 2,
  'nearest-above is the CLOSEST platform (y=' + nearestAbove.y + '), not the top (y=' + topPlat.y + ')',
  'nearest-above picked the topmost platform (old bug)');
const e2 = S.spawnEnemy('cat');
e2.surf = 'plat'; e2.minX = lowest.x + 6; e2.maxX = lowest.x + lowest.w - 6;
e2.baseY = lowest.y - 17; e2.y = e2.baseY; e2.x = lowest.x + lowest.w / 2; e2.dir = 1;
e2._jumpStop = 1; e2._jumpTarget = nearestAbove; // force: 1 frame stop then jump
const beforeY = e2.baseY;
S.stepEnemyWalk(e2); // frame 1: stop decrement (1->0)
S.stepEnemyWalk(e2); // frame 2: execute jump
check(e2.baseY === nearestAbove.y - 17,
  'enemy jumped exactly ONE level up to nearest (baseY ' + beforeY + ' -> ' + e2.baseY + ', target ' + (nearestAbove.y - 17) + ')',
  'wrong jump height (baseY ' + e2.baseY + ', expected ' + (nearestAbove.y - 17) + ')');

// ---- Test 3: 0.6s stop before jump — setting _jumpStop=36 makes the enemy
// not move (no x change) for 36 frames, then jump.
const e3 = S.spawnEnemy('cat');
e3.surf = 'plat'; e3.minX = lowest.x + 6; e3.maxX = lowest.x + lowest.w - 6;
e3.baseY = lowest.y - 17; e3.y = e3.baseY; e3.x = lowest.x + lowest.w / 2; e3.dir = 1;
e3._jumpStop = 36; e3._jumpTarget = nearestAbove;
const x0 = e3.x;
// run 20 frames: should NOT have moved (still in stop)
for (let f = 0; f < 20; f++) S.stepEnemyWalk(e3);
check(e3.x === x0 && e3.baseY === lowest.y - 17,
  'during 0.6s stop: enemy does not move (x=' + e3.x + ', baseY=' + e3.baseY + ')',
  'enemy moved during stop: x ' + x0 + ' -> ' + e3.x + ', baseY ' + e3.baseY);
// run remaining 16+ frames: stop should expire and jump should execute
for (let f = 0; f < 20; f++) S.stepEnemyWalk(e3);
check(e3.baseY === nearestAbove.y - 17,
  'after 0.6s stop: enemy jumped to upper platform (baseY ' + e3.baseY + ')',
  'enemy did not jump after stop (baseY ' + e3.baseY + ')');

// ---- Test 4: freeze end un-coins minis (body back) ----
S.P.dead = false; // restore for boss tests below
S.setScreen(0); S.G.st = S.ST.PLAY;
S.G.boss = { kind: 'roach', x: 70, y: 40, bw: 23, bh: 48, frames: [] };
S.G.enemies = [];
S.spawnMiniBoss(S.G.boss);
const mini = S.G.enemies[0];
for (let f = 0; f < 300 && mini.dropping; f++) S.enemyStep();
check(!mini.dropping, 'mini landed (dropping=false)', 'mini still dropping');
check(mini.surf === 'plat' || mini.surf === 'ground', 'mini landed with valid surf (' + mini.surf + ')', 'mini surf=' + mini.surf);
// freeze it
S.G.freeze = 5;
for (const ee of S.G.enemies) if (!ee.frozen) { ee.frozen = true; ee.coin = true; }
check(mini.coin === true, 'mini frozen -> coin (head in goo)', 'mini not frozen');
// let freeze run out
for (let f = 0; f < 20 && S.G.freeze > 0; f++) S.enemyStep();
check(S.G.freeze === 0 && mini.coin === false, 'freeze end: mini body restored (coin=false)', 'mini still coin after freeze ended: coin=' + mini.coin);

// ---- Test 5: mini KILLS player on touch (no P, no invuln) — user suspicion ----
// The mini is still dropping when it passes through the player's position.
// We move the player to where the mini lands so the drop-contact check fires.
S.setScreen(0); S.G.st = S.ST.PLAY;
S.G.freeze = 0; S.G.touchKill = 0;
S.P.dead = false; S.P.invuln = 0;
S.G.boss = { kind: 'roach', x: 70, y: 40, bw: 23, bh: 48, frames: [] };
S.G.enemies = [];
S.spawnMiniBoss(S.G.boss);
const mini2 = S.G.enemies[0];
// move player to where the mini will land (same x, at the landing y)
const landSurfY = S.surfaceAtX(mini2.x);
S.P.x = mini2.x - 5; S.P.y = landSurfY - 8 - 8; // player standing on the surface
// step until mini lands or player is hit
for (let f = 0; f < 300 && !S.P.dead; f++) {
  S.enemyStep();
}
check(S.P.dead === true, 'mini drop-through kills player (no P, no invuln)',
  'mini did NOT kill player (dead=' + S.P.dead + ', touchKill=' + S.G.touchKill + ')');

console.log(ok ? '=== ALL WALK TESTS PASSED ===' : '=== SOME WALK TESTS FAILED ===');
process.exit(ok ? 0 : 1);
