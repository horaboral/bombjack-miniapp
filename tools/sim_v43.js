// v43 verification: strictly vertical jumps/falls, slow speed, shared bob phase, mini landing offset.
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
  Telegram: { WebApp: { ready(){}, expand(){}, setHeaderColor(){}, setBackgroundColor(){}, onEvent(){}, offEvent(){}, sendData(){}, initData:'', initDataUnsafe:{}, version:'', platform:'', colorScheme:'dark', themeParams:{}, HapticFeedback:{ impactOccurred(){}, notificationOccurred(){}, selectionChanged(){} }, MainButton:{ setText(){return this}, setColor(){return this}, show(){}, hide(){}, onClick(){}, offClick(){} }, BackButton:{ show(){}, hide(){}, onClick(){}, offClick(){} } } },
  Image: class { constructor() { this.complete = false; setTimeout(() => { this.complete = true; }, 0); } },
  AudioContext: null, webkitAudioContext: null,
  requestAnimationFrame: () => 0, addEventListener: () => {},
  setTimeout: (fn) => 0, setInterval: () => 0,
  console, globalThis,
};
sandbox.window = sandbox;
sandbox.haptic = () => {}; sandbox.beep = () => {}; sandbox.AC = null;
sandbox.deathSound = () => {}; sandbox.musicStart = () => {}; sandbox.musicStop = () => {};
vm.createContext(sandbox);
function findBlock(pred) { for (let i = 0; i < blocks.length; i++) if (pred(blocks[i])) return i; return -1; }
function runBlock(idx, label) {
  if (idx < 0) { console.log('FATAL: ' + label + ' block not found'); process.exit(2); }
  try { vm.runInContext(blocks[idx], sandbox, { filename: 'block' + (idx + 1) + '.js' }); }
  catch (e) { console.log('block ' + (idx + 1) + ' (' + label + ') load FAILED: ' + e.message); process.exit(2); }
}
runBlock(findBlock(b => b.includes('CFG = {') && b.includes('SCREENS = [')), 'cfg');
runBlock(findBlock(b => b.includes('G = {') && b.includes('function setScreen')), 'state');
runBlock(findBlock(b => b.includes('function powerupStep')), 'power');
runBlock(findBlock(b => b.includes('function enemyStep')), 'enemy');
const S = sandbox;
if (!S.G) { console.log('FATAL: G not defined'); process.exit(2); }
for (let i = 0; i < 53; i++) { S.G.roachFrames[i] = { complete: true }; S.G.gorillaFrames[i] = { complete: true }; }

let passed = 0, failed = 0;
function check(name, cond) {
  if (cond) { console.log('  PASS: ' + name); passed++; }
  else { console.log('  FAIL: ' + name); failed++; }
}

// setup: PLAY state on screen 0 (PYRAMID), no boss
S.G.st = S.ST.PLAY;
S.setScreen(0);
S.G.st = S.ST.PLAY;
S.G.enemies = [];
S.G.boss = null;
S.G.freeze = 0;

// --- Test 1: jump is strictly vertical (x unchanged) ---
console.log('\n[Test 1: Jump is strictly vertical]');
{
  S.G.enemies = [];
  const e = S.spawnEnemy('owl'); // fly type, offset 17
  // force onto middle platform (y=168, w=46 at x=40)
  e.x = 60; e.baseY = 168 - 17; e.surf = 'plat'; e.minX = 41; e.maxX = 85; e.y = e.baseY; e.vy = 0;
  S.G.enemies.push(e);
  const startX = e.x;
  // trigger jump to upper platform (y=112)
  e._jumpStop = 36; e._jumpTarget = S.G.plat.find(p => p.y === 112);
  let maxDrift = 0;
  for (let i = 0; i < 80; i++) {
    S.enemyStep();
    if (e._jumpT != null) { // only measure during the jump arc
      maxDrift = Math.max(maxDrift, Math.abs(e.x - startX));
    }
  }
  check('x drift < 1px during jump arc (got ' + maxDrift.toFixed(2) + ')', maxDrift < 1);
  check('landed on upper platform (baseY=' + e.baseY.toFixed(1) + ' expected ' + (112-17) + ')', Math.abs(e.baseY - (112 - 17)) < 3);
}

// --- Test 2: fall is slow (vy capped at 1.2) ---
console.log('\n[Test 2: Fall speed is slow]');
{
  S.G.enemies = [];
  const e = S.spawnEnemy(null);
  e.x = 45; e.baseY = 168 - 17; e.surf = 'plat'; e.minX = 41; e.maxX = 85; e.y = e.baseY; e.vy = 0; e.dir = 1;
  S.G.enemies.push(e);
  let maxVy = 0;
  for (let i = 0; i < 200; i++) {
    S.enemyStep();
    maxVy = Math.max(maxVy, Math.abs(e.vy));
    if (e.surf === 'ground') break;
  }
  check('vy capped at 1.2 (got ' + maxVy.toFixed(2) + ')', maxVy <= 1.21);
}

// --- Test 3: mini drop is slow ---
console.log('\n[Test 3: Mini drop is slow]');
{
  S.G.enemies = [];
  S.G.boss = { x: 72, y: 100, bw: 23, bh: 48, kind: 'roach', name: 'JOTITO', hp: 10, spawnCd: 100 };
  S.spawnMiniBoss(S.G.boss);
  const mini = S.G.enemies[0];
  let maxVy = 0;
  for (let i = 0; i < 200; i++) {
    S.enemyStep();
    maxVy = Math.max(maxVy, Math.abs(mini.vy));
    if (!mini.dropping) break;
  }
  check('mini vy capped at 1.2 (got ' + maxVy.toFixed(2) + ')', maxVy <= 1.21);
  check('mini landed', !mini.dropping);
}

// --- Test 4: shared bob phase ---
console.log('\n[Test 4: Shared bob phase]');
{
  S.G.enemies = [];
  const e1 = S.spawnEnemy(null);
  const e2 = S.spawnEnemy(null);
  e1.type = 'owl'; e2.type = 'owl';
  e1.x = 50; e1.baseY = 168 - 17; e1.surf = 'plat'; e1.minX = 41; e1.maxX = 85; e1.y = e1.baseY; e1.t = 5;
  e2.x = 70; e2.baseY = 168 - 17; e2.surf = 'plat'; e2.minX = 41; e2.maxX = 85; e2.y = e2.baseY; e2.t = 5;
  S.G.enemies.push(e1, e2);
  S.enemyStep();
  const diff = Math.abs(e1.y - e2.y);
  check('same-type same-platform y diff < 0.1 (got ' + diff.toFixed(3) + ')', diff < 0.1);
}

// --- Test 5: mini landing offset (fly = 17) ---
console.log('\n[Test 5: Mini landing offset (fly=17, non-fly=8)]');
{
  S.G.enemies = [];
  S.G.boss = { x: 72, y: 100, bw: 23, bh: 48, kind: 'roach', name: 'JOTITO', hp: 10, spawnCd: 100 };
  S.spawnMiniBoss(S.G.boss);
  const mini = S.G.enemies[0];
  for (let i = 0; i < 300; i++) { S.enemyStep(); if (!mini.dropping) break; }
  if (!mini.dropping) {
    // mini should land on the first platform BELOW its spawn position
    // (not the highest platform under x, which might be above the spawn)
    const spawnY = mini._dropFrom;
    let expectedSurf = S.CFG.GROUND_Y;
    for (const pl of S.G.plat) {
      if (pl.y <= spawnY) continue;
      if (mini.x > pl.x && mini.x < pl.x + pl.w && pl.y < expectedSurf) expectedSurf = pl.y;
    }
    const expectedY = expectedSurf - 17; // roach is fly type
    check('roach mini lands below spawn (y=' + mini.y.toFixed(1) + ' expected ' + expectedY.toFixed(1) + ', spawn=' + spawnY.toFixed(1) + ')', Math.abs(mini.y - expectedY) < 2);
  } else {
    check('mini landed (still dropping after 300 frames, y=' + mini.y + ')', false);
  }
}

console.log('\n' + passed + ' passed, ' + failed + ' failed');
process.exit(failed ? 1 : 0);
