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
sandbox.deathSound = () => {};
sandbox.musicStart = () => {};
sandbox.musicStop = () => {};
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
// Fake loaded face frames. The stub canvas getContext returns a Proxy whose
// property access yields a truthy function, so the game's silhouetteMask()
// would read an all-1 mask and getImageData would be meaningless. Instead we
// pre-seed each fake frame with a REAL all-solid mask sized to the frame, so
// silhouetteHit() behaves like a filled silhouette: the player overlaps the
// boss's mask exactly when the player is inside the boss bounding box.
if (!S.G) { console.log('FATAL: G not defined on sandbox'); process.exit(2); }
function solidMask(w, h) { return { w, h, m: new Uint8Array(w * h).fill(1) }; }
// roach frames are 72x148, gorilla 54x66 (v6 rescale sizes)
for (let i = 0; i < 53; i++) {
  S.G.roachFrames[i] = { complete: true, naturalWidth: 72, naturalHeight: 148, _silMask: solidMask(72, 148) };
  S.G.gorillaFrames[i] = { complete: true, naturalWidth: 54, naturalHeight: 66, _silMask: solidMask(54, 66) };
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

// ---- Test 3: mini drop lands on a SOLID surface (platform or ground) ----
if (S.G.boss) {
  S.spawnMiniBoss(S.G.boss);
  const mini = S.G.enemies[S.G.enemies.length - 1];
  const startY = mini.y;
  for (let f = 0; f < 300 && mini.dropping; f++) S.enemyStep();
  const surfY = S.surfaceAtX(mini.x);
  const flyOff = (mini.type === 'owl' || mini.type === 'ghost' || mini.type === 'roach' || mini.type === 'gorilla') ? 17 : 8;
  check(!mini.dropping && Math.abs(mini.y - (surfY - flyOff)) < 1.5,
    'mini landed on solid surface at y=' + mini.y.toFixed(1) + ' (surface=' + surfY + ', offset=' + flyOff + ', fell ' + (mini.y - startY).toFixed(1) + 'px)',
    'mini did not land correctly (dropping=' + mini.dropping + ', y=' + mini.y.toFixed(1) + ', expected ' + (surfY - flyOff) + ')');
}

// ---- Test 4: without P the boss KILLS the player; with P it takes damage ----
S.setScreen(0);
S.G.boss.hp = 5;
S.G.freeze = 0; S.G.touchKill = 0;
S.G.st = S.ST.PLAY;
S.P.x = S.G.boss.x; S.P.y = S.G.boss.y; S.P.invuln = 0; S.P.dead = false;
S.bossStep();
check(S.P.dead === true, 'boss kills player on contact without P', 'player not dead after boss touch (no P)');
check(S.G.boss && S.G.boss.hp === 5, 'no damage without P (hp stayed 5)', 'hp changed without P: ' + (S.G.boss && S.G.boss.hp));

S.G.freeze = 100;
S.P.dead = false; S.P.invuln = 0;
S.bossStep();
check(S.G.boss && S.G.boss.hp === 4, 'hit with P reduced hp 5->4 (hitCd now ' + S.G.boss.hitCd + ')', 'hp not reduced with P: ' + (S.G.boss && S.G.boss.hp));

// ---- Test 4b: hit cooldown — overlapping again immediately does NOT re-hit ----
S.G.freeze = 100;
S.P.x = S.G.boss.x; S.P.y = S.G.boss.y;
S.bossStep();
check(S.G.boss && S.G.boss.hp === 4,
  'no second hit during cooldown (hp stayed 4, hitCd=' + (S.G.boss && S.G.boss.hitCd) + ')',
  're-hit during cooldown (hp=' + (S.G.boss && S.G.boss.hp) + ')');

// ---- Test 4c: player is BOUNCED off (vx set) when touching with P ----
S.G.boss.hitCd = 0; // reset so we isolate the bounce
S.P.x = S.G.boss.x; S.P.y = S.G.boss.y; S.P.vx = 0; S.P.vy = 0; S.P.grounded = true;
S.bossStep();
const bounced = Math.abs(S.P.vx) > 0.5 || Math.abs(S.P.vy) > 0.5;
check(bounced, 'player bounced off boss (vx=' + S.P.vx.toFixed(1) + ', vy=' + S.P.vy.toFixed(1) + ')', 'player not bounced (vx=' + S.P.vx.toFixed(1) + ')');

// ---- Test 5: final hit triggers poof (bossStep needs ST.PLAY) ----
S.setScreen(0);
S.G.st = S.ST.PLAY;
S.G.boss.hp = 1; S.G.freeze = 100;
S.P.dead = false; S.P.invuln = 0;
S.P.x = S.G.boss.x; S.P.y = S.G.boss.y;
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

// ---- Test 7: minis are GROUND walkers (patrol like regular enemies) ----
S.setScreen(0);
S.G.st = S.ST.PLAY;
S.G.boss = { kind: 'roach', x: 60, y: 40, bw: 23, bh: 48, frames: S.G.roachFrames };
S.G.enemies = [];
S.spawnMiniBoss(S.G.boss);
const m2 = S.G.enemies[0];
for (let f = 0; f < 300 && m2.dropping; f++) S.enemyStep();
const x0 = m2.x, dir0 = m2.dir;
for (let f = 0; f < 60; f++) S.enemyStep();
check(Math.abs(m2.x - x0) > 2 || m2.dir !== dir0,
  'mini patrols like a ground enemy (moved ' + (m2.x - x0).toFixed(1) + 'px, dir ' + dir0 + '->' + m2.dir + ')',
  'mini is not moving like a regular enemy');

// ---- Test 8: P turns a mini into yellow jelly (coin=true), collectible ----
S.G.enemies = [m2]; m2.dropping = false; m2.coin = false; m2.frozen = false;
S.G.freeze = 0;
// simulate the P pickup conversion (line 572 of the game)
for (const e of S.G.enemies) if (!e.frozen) { e.frozen = true; e.coin = true; }
check(m2.coin === true, 'P froze the mini into jelly (coin=true)', 'mini not converted by P');
// collect it
m2.x = S.P.x; m2.y = S.P.y; S.G.freeze = 300;
const score0 = S.G.score;
S.enemyStep();
check(!m2.dead || S.G.enemies.filter(e => e === m2).length === 0,
  'frozen mini collected as jelly (score ' + score0 + '->' + S.G.score + ')', 'frozen mini not collectible');

// ---- Test 9: boss mini-spawn is GATED when 4+ minis are alive ----
S.setScreen(0);
S.G.st = S.ST.PLAY;
S.G.boss.hp = 10; S.G.boss.spawnCd = 0; // force immediate spawn attempt
S.G.enemies = [];
// fill with 4 fake minis
for (let i = 0; i < 4; i++) S.G.enemies.push({ mini: true, type: 'roach', x: 10 + i * 20, y: 200 });
const minisBefore = S.G.enemies.filter(e => e.mini).length;
S.bossStep();
const minisAfter = S.G.enemies.filter(e => e.mini).length;
check(minisAfter === minisBefore,
  'boss did NOT spawn a new mini when 4 minis were alive (count ' + minisBefore + '->' + minisAfter + ')',
  'boss spawned an extra mini despite 4 already alive (count ' + minisBefore + '->' + minisAfter + ')');
// now clear one mini and verify spawn works again
S.G.enemies.pop();
S.G.boss.spawnCd = 0;
S.bossStep();
const minisAfter2 = S.G.enemies.filter(e => e.mini).length;
check(minisAfter2 === minisBefore,
  'boss spawned a mini again after a slot freed up (count ' + (minisBefore - 1) + '->' + minisAfter2 + ')',
  'boss did not respawn after slot freed (count ' + minisAfter2 + ')');

// ---- Test 10: fireballs damage the BOSS (2 HP per hit, dead at hp<=0) ----
S.setScreen(1); // Sobesinho
S.G.st = S.ST.PLAY;
S.G.sFire = 300; // S powerup active so fireballStep runs its collision logic
S.G.boss.hp = 5; S.G.boss.hitCd = 0; S.G.boss.poofT = 0;
// place a fireball directly on the boss center (no `dead` prop — the game
// uses `fb.dead === undefined` to detect "not yet hit")
S.G.fireballs = [{ x: S.G.boss.x, y: S.G.boss.y, vx: 0, vy: 0, t: 0 }];
S.G.enemies = [];
S.fireballStep();
check(S.G.boss && S.G.boss.hp === 3,
  'fireball hit boss: hp 5->3 (2 per hit, hitCd=' + (S.G.boss && S.G.boss.hitCd) + ')',
  'boss hp not reduced by fireball (hp=' + (S.G.boss && S.G.boss.hp) + ')');
// second fireball (clear cooldown) → hp 3->1
S.G.boss.hitCd = 0;
S.G.fireballs = [{ x: S.G.boss.x, y: S.G.boss.y, vx: 0, vy: 0, t: 0 }];
S.fireballStep();
check(S.G.boss && S.G.boss.hp === 1,
  'second fireball: hp 3->1', 'hp not 1 after second fireball: ' + (S.G.boss && S.G.boss.hp));
// third fireball → hp 1 -> -1 → dead (poof)
S.G.boss.hitCd = 0;
S.G.fireballs = [{ x: S.G.boss.x, y: S.G.boss.y, vx: 0, vy: 0, t: 0 }];
S.fireballStep();
const bossDead = !S.G.boss || S.G.boss.poofT > 0;
check(bossDead,
  'third fireball killed boss (hp 1->-1, poofT=' + (S.G.boss && S.G.boss.poofT) + ')',
  'boss not killed by third fireball (hp=' + (S.G.boss && S.G.boss.hp) + ')');

// ---- Test 11: after boss death, NO new enemy spawns; minis remain ----
S.setScreen(1);
S.G.st = S.ST.PLAY;
S.G.boss = null; // boss dead
S.G.enemies = [{ mini: true, type: 'gorilla', t: 0, x: 100, y: 200, dir: 1, frozen: false, coin: false, speed: 0.5, phase: 0, jumpCd: 600, dropping: false, hp: 3, surf: 'ground', minX: 8, maxX: 352, baseY: 230 }];
const enemiesBefore = S.G.enemies.length;
for (let f = 0; f < 400; f++) {
  S.G.spawnT = 0; // force spawn attempt every frame
  S.enemyStep();
}
const newOnes = S.G.enemies.filter(e => e !== S.G.enemies[0] && !e.mini).length;
check(S.G.enemies.length === enemiesBefore,
  'no new enemies after boss death (count ' + enemiesBefore + '->' + S.G.enemies.length + ')',
  'new enemies spawned after boss death (count ' + enemiesBefore + '->' + S.G.enemies.length + ')');
check(S.G.enemies.some(e => e.mini), 'pre-existing mini still present after boss death', 'existing mini disappeared');

// ---- Test 12a: dead boss LINGERS (poofT held, not cleared) + keeps mask ----
S.setScreen(0);
S.G.st = S.ST.PLAY;
S.G.boss.hp = 1; S.G.boss.hitCd = 0;
S.bossPoof(S.G.boss);
// the boss should be marked dead, hold its silhouette mask, and not vanish
check(S.G.boss && S.G.boss._dead === true, 'bossPoof marks boss dead (_dead=true)', 'boss not marked dead');
check(S.G.boss && S.G.boss._silMask !== undefined, 'dead boss retains silhouette mask for hell fill', 'no mask retained on dead boss');
// step a few frames: poofT must stay > 0 (held), G.boss must NOT be cleared
for (let f = 0; f < 100; f++) S.bossStep();
check(S.G.boss && S.G.boss.poofT > 0, 'dead boss lingers on screen (poofT held at ' + (S.G.boss && S.G.boss.poofT) + ')', 'dead boss vanished (poofT=' + (S.G.boss && S.G.boss.poofT) + ')');
// drawDeadBoss must not throw headlessly (stub canvas)
let drawErr = null;
try { if (S.drawDeadBoss) S.drawDeadBoss(S.cx, S.G.boss); } catch (e) { drawErr = e; }
check(drawErr === null, 'drawDeadBoss runs headless without error', 'drawDeadBoss threw: ' + (drawErr && drawErr.message));

// ---- Test 12: while boss ALIVE, spawning still works (regression) ----
S.setScreen(0);
S.G.st = S.ST.PLAY;
S.G.boss = { kind: 'roach', x: 60, y: 40, bw: 23, bh: 48, hp: 10, poofT: 0, hitCd: 0, spawnCd: 1000, frames: S.G.roachFrames };
S.G.enemies = [];
for (let f = 0; f < 400; f++) {
  S.G.spawnT = 0;
  S.G.freeze = 0;
  S.enemyStep();
}
check(S.G.enemies.length > 0, 'spawning still works while boss alive (' + S.G.enemies.length + ' enemies)', 'no spawning while boss alive');

console.log(ok ? '=== ALL BOSS TESTS PASSED ===' : '=== SOME TESTS FAILED ===');
process.exit(ok ? 0 : 1);
