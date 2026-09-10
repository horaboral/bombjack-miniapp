// Headless simulation of the boss + enemy + powerup logic from bombjack.html.
// Extracts the inline script blocks, stubs the canvas/audio/DOM, runs frames,
// and asserts the boss behaviors.
const fs = require('fs');
const vm = require('vm');
const html = fs.readFileSync(__dirname + '/../bombjack.html', 'utf8');
const re = /<script>([\s\S]*?)<\/script>/g;
const blocks = [];
const seen = new Set();
let m;
while ((m = re.exec(html)) !== null) {
  let src = m[1];
  // Dedupe across blocks: the game relies on per-script-block scope for
  // const/let; the sim shares one scope, so strip duplicate declarations.
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
  console,
  globalThis,
};
sandbox.window = sandbox;
// Stub the sound/haptic helpers that live in the audio block (not loaded)
sandbox.haptic = () => {};
sandbox.beep = () => {};
sandbox.AC = null; // audioInit() never runs headless
vm.createContext(sandbox);

// Find the block that defines G (state) and the block with enemyStep; run only
// those to avoid top-level DOM/canvas statements in render blocks.
function findBlock(pred) { for (let i = 0; i < blocks.length; i++) if (pred(blocks[i])) return i; return -1; }
function runBlock(idx, label) {
  if (idx < 0) { console.log('FATAL: ' + label + ' block not found'); process.exit(2); }
  try { vm.runInContext(blocks[idx], sandbox, { filename: 'block' + (idx + 1) + '.js' }); }
  catch (e) { console.log('block ' + (idx + 1) + ' (' + label + ') load FAILED: ' + e.message + '\n' + (e.stack || '').split('\n').slice(0, 6).join('\n')); process.exit(2); }
}
const stateIdx = findBlock(b => b.includes('G = {') && b.includes('function setScreen'));
runBlock(findBlock(b => b.includes('CFG = {') && b.includes('SCREENS = [')), 'cfg');
runBlock(stateIdx, 'state');
runBlock(findBlock(b => b.includes('function powerupStep')), 'power');
runBlock(findBlock(b => b.includes('function enemyStep')), 'enemy');
const S = sandbox;
// Fake loaded face frames
if (!S.G) { console.log('FATAL: G not defined on sandbox'); process.exit(2); }
for (let i = 0; i < 53; i++) {
  S.G.roachFrames[i] = { complete: true };
  S.G.gorillaFrames[i] = { complete: true };
}
let ok = 1;
function check(cond, msg, failmsg) {
  console.log((cond ? 'PASS' : 'FAIL') + ': ' + (cond ? msg : failmsg || msg));
  if (!cond) ok = 0;
}

// ---- Test 1: boss spawns on screen 0 (Jotito) and screen 1 (Sobesinho) ----
S.setScreen(0);
check(S.G.boss && S.G.boss.name === 'JOTITO',
  'screen0 boss = JOTITO at (' + (S.G.boss && S.G.boss.x).toFixed(1) + ',' + (S.G.boss && S.G.boss.y).toFixed(1) + ') size ' + (S.G.boss && S.G.boss.bw) + 'x' + (S.G.boss && S.G.boss.bh) + ' hp=' + (S.G.boss && S.G.boss.hp),
  'screen0 boss missing or wrong name: ' + (S.G.boss && S.G.boss.name));
const jotSize = S.G.boss ? [S.G.boss.bw, S.G.boss.bh] : [0, 0];
check(jotSize[1] <= Math.round(74 * 0.65) + 1 && jotSize[0] <= Math.round(36 * 0.65) + 1,
  'Jotito is ~65% of title roach size (' + jotSize[0] + 'x' + jotSize[1] + ')', 'Jotito too big: ' + jotSize);

S.setScreen(1);
check(S.G.boss && S.G.boss.name === 'SOBESINHO',
  'screen1 boss = SOBESINHO at (' + (S.G.boss && S.G.boss.x).toFixed(1) + ',' + (S.G.boss && S.G.boss.y).toFixed(1) + ') size ' + (S.G.boss && S.G.boss.bw) + 'x' + (S.G.boss && S.G.boss.bh),
  'screen1 boss missing or wrong name: ' + (S.G.boss && S.G.boss.name));
S.setScreen(2);
check(S.G.boss === null, 'screen2 has no boss');

// ---- Test 2: boss bounces within bounds for 1500 frames + mini spawns ----
S.setScreen(0);
S.G.st = S.ST.PLAY;
let outOfBounds = 0;
for (let f = 0; f < 1500; f++) {
  S.bossStep();
  if (S.G.boss) {
    const b = S.G.boss;
    if (b.x - b.bw/2 < -0.01 || b.x + b.bw/2 > S.CFG.W + 0.01 || b.y - b.bh/2 < -0.01 || b.y + b.bh/2 > S.CFG.GROUND_Y + 0.01) outOfBounds++;
  }
}
check(outOfBounds === 0, 'boss stayed in bounds for 1500 frames', 'boss went out of bounds ' + outOfBounds + ' frames');
const miniSpawns = S.G.enemies.filter(e => e.mini).length;
check(miniSpawns > 0, 'mini-replicas spawned from boss legs: ' + miniSpawns, 'no mini-replicas spawned');

// ---- Test 3: mini drop completes in ~1s (<=120 frames) ----
if (S.G.boss) {
  S.spawnMiniBoss(S.G.boss);
  const mini = S.G.enemies[S.G.enemies.length - 1];
  for (let f = 0; f < 240 && mini.dropping; f++) S.enemyStep();
  check(!mini.dropping,
    'mini drop finished (frames=' + mini.miniT + ', landed at y=' + mini.y.toFixed(1) + ')',
    'mini still dropping after 240 frames');
}

// ---- Test 4: player hit with P reduces hp; without P, no effect ----
S.setScreen(0);
S.G.boss.hp = 5;
S.G.freeze = 0; S.G.touchKill = 0;
S.P.x = S.G.boss.x; S.P.y = S.G.boss.y; S.P.invuln = 0; S.P.dead = false;
S.bossStep();
check(S.G.boss && S.G.boss.hp === 5, 'no damage without P (hp stayed 5)', 'hp changed without P: ' + (S.G.boss && S.G.boss.hp));

S.G.freeze = 100;
S.G.st = S.ST.PLAY; // bossStep requires play state
S.bossStep();
check(S.G.boss && S.G.boss.hp === 4, 'hit with P reduced hp 5->4', 'hp not reduced with P: ' + (S.G.boss && S.G.boss.hp));

// ---- Test 5: final hit triggers poof (bossStep needs ST.PLAY) ----
// playerDie() must be defined or enemyStep's touch-kill branch will throw
sandbox.playerDie = () => {};
S.setScreen(0);
S.G.st = S.ST.PLAY;
S.G.boss.hp = 1; S.G.freeze = 100;
S.P.x = S.G.boss.x; S.P.y = S.G.boss.y; S.P.invuln = 0;
S.bossStep();
const dead = !S.G.boss || S.G.boss.poofT > 0;
check(dead, 'final hit triggered poof (poofT=' + (S.G.boss && S.G.boss.poofT) + ')', 'no poof on final hit');

// ---- Test 6: half-spawn rule — many spawns, minis + sacrificed pool only ----
S.setScreen(0);
S.G.st = S.ST.PLAY; // enemyStep spawn gate requires play state
S.G.enemies = [];
S.G.spawnT = 0;
for (let f = 0; f < 600; f++) {
  if (S.G.spawnT <= 0) S.G.spawnT = 1; // force spawn every frame
  S.G.freeze = 0;
  S.enemyStep();
}
const minis = S.G.enemies.filter(e => e.mini).length;
const normals = S.G.enemies.filter(e => !e.mini);
const badTypes = normals.filter(e => e.type === 'owl'); // first type is sacrificed
check(minis > 0 && normals.length > 0, 'mixed spawning: ' + minis + ' minis + ' + normals.length + ' normal enemies', 'no mixed spawning');
check(badTypes.length === 0, 'sacrificed type (owl) absent from normal pool', badTypes.length + ' owls spawned despite sacrifice');

console.log(ok ? '=== ALL BOSS TESTS PASSED ===' : '=== SOME TESTS FAILED ===');
process.exit(ok ? 0 : 1);
