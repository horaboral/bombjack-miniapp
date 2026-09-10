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
runBlock(findBlock(b => b.includes('function enemyStep')), 'enemy');
const S = sandbox;
let ok = 1;
function check(cond, msg, failmsg) { console.log((cond ? 'PASS' : 'FAIL') + ': ' + (cond ? msg : failmsg || msg)); if (!cond) ok = 0; }

// Set up screen 0 (pyramid, has platforms)
S.setScreen(0);
S.G.st = S.ST.PLAY;
S.G.freeze = 0;
S.P.dead = true; // prevent player interactions/death noise

// Test 1: enemy on a platform walks; at the tip it either turns or falls
const e = S.spawnEnemy('cat');
e.surf = 'plat';
const pl0 = S.G.plat[0];
e.minX = pl0.x + 6; e.maxX = pl0.x + pl0.w - 6; e.baseY = pl0.y - 17; e.y = e.baseY; e.x = pl0.x + pl0.w - 10; e.dir = 1; e.jumpCd = 99999;
const startE = e.x;
let fell = false, turned = false;
for (let f = 0; f < 120; f++) {
  S.stepEnemyWalk(e);
  if (e.y > pl0.y - 5) { fell = true; break; }
  if (e.dir === -1 && e.x <= pl0.x + pl0.w - 10) { turned = true; break; }
}
check(fell || turned, 'at platform tip: enemy either turns back or falls (fell=' + fell + ', turned=' + turned + ', dx=' + (e.x - startE).toFixed(1) + ')', 'enemy neither turned nor fell at the tip');

// Test 2: enemy can jump to a higher platform when one exists
const e2 = S.spawnEnemy('cat');
// put it on the LOWEST platform
let lowest = null; for (const p of S.G.plat) if (!lowest || p.y > lowest.y) lowest = p;
e2.surf = 'plat'; e2.minX = lowest.x + 6; e2.maxX = lowest.x + lowest.w - 6; e2.baseY = lowest.y - 17; e2.y = e2.baseY; e2.x = lowest.x + lowest.w / 2; e2.dir = 1;
e2.jumpCd = 1; // trigger jump check immediately
const beforeY = e2.baseY;
S.stepEnemyWalk(e2);
check(e2.baseY < beforeY - 5, 'enemy jumped to a higher platform (baseY ' + beforeY + ' -> ' + e2.baseY + ')', 'no jump to higher platform (baseY ' + e2.baseY + ')');

// Test 3: freeze end un-coins minis (body back)
S.setScreen(0); S.G.st = S.ST.PLAY;
S.G.boss = { kind: 'roach', x: 70, y: 40, bw: 23, bh: 48, frames: [] };
S.G.enemies = [];
S.spawnMiniBoss(S.G.boss);
const mini = S.G.enemies[0];
for (let f = 0; f < 300 && mini.dropping; f++) S.enemyStep();
// freeze it
S.G.freeze = 5;
for (const ee of S.G.enemies) if (!ee.frozen) { ee.frozen = true; ee.coin = true; }
check(mini.coin === true, 'mini frozen -> coin (head in goo)', 'mini not frozen');
// let freeze run out
for (let f = 0; f < 20 && S.G.freeze > 0; f++) S.enemyStep();
check(S.G.freeze === 0 && mini.coin === false, 'freeze end: mini body restored (coin=false)', 'mini still coin after freeze ended: coin=' + mini.coin);

console.log(ok ? '=== ALL WALK TESTS PASSED ===' : '=== SOME WALK TESTS FAILED ===');
process.exit(ok ? 0 : 1);
