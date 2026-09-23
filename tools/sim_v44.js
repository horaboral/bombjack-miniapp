// v44: verify the user's specific complaints are fixed:
// 1. Enemies fall from platforms when reaching the tip
// 2. No enemies on the top platform exclusively (they spread across levels)
// 3. No teleporting (jump only if x overlaps target platform)
// 4. Jump is strictly vertical
// 5. Fall is strictly vertical (no x drift)
const fs = require('fs');
const vm = require('vm');
const html = fs.readFileSync(__dirname + '/../bombjack.html', 'utf8');
const re = /<script>([\s\S]*?)<\/script>/g;
const blocks = []; const seen = new Set(); let m;
while ((m = re.exec(html)) !== null) {
  let src = m[1];
  src = src.replace(/^(?:const|let) (\w+)/gm, (mm, name) => seen.has(name) ? '' : (seen.add(name), 'var ' + name));
  blocks.push(src);
}
const ctxStub = () => new Proxy({}, { get: (t, p) => (typeof p === 'string' ? () => {} : undefined) });
const elStub = () => ({ width: 0, height: 0, getContext: ctxStub, addEventListener: () => {} });
const sandbox = {
  window: null, localStorage: { getItem: () => '0', setItem: () => {} },
  document: { createElement: () => ({ width: 0, height: 0, getContext: ctxStub }), getElementById: elStub, addEventListener: () => {}, body: { appendChild: () => {}, style: {} } },
  performance: { now: () => 0 }, navigator: { vibrate: () => {} },
  Telegram: { WebApp: { ready(){}, expand(){}, setHeaderColor(){}, setBackgroundColor(){}, onEvent(){}, offEvent(){}, sendData(){}, initData:'', initDataUnsafe:{}, version:'', platform:'', colorScheme:'dark', themeParams:{}, HapticFeedback:{ impactOccurred(){}, notificationOccurred(){}, selectionChanged(){} }, MainButton:{ setText(){return this}, setColor(){return this}, show(){}, hide(){}, onClick(){}, offClick(){} }, BackButton:{ show(){}, hide(){}, onClick(){}, offClick(){} } } },
  Image: class { constructor() { this.complete = false; } },
  AudioContext: null, webkitAudioContext: null,
  requestAnimationFrame: () => 0, addEventListener: () => {},
  setTimeout: (fn) => 0, setInterval: () => 0, console, globalThis,
};
sandbox.window = sandbox;
sandbox.haptic = () => {}; sandbox.beep = () => {}; sandbox.AC = null;
sandbox.deathSound = () => {}; sandbox.musicStart = () => {}; sandbox.musicStop = () => {};
vm.createContext(sandbox);
function findBlock(pred) { for (let i = 0; i < blocks.length; i++) if (pred(blocks[i])) return i; return -1; }
function runBlock(idx, label) {
  if (idx < 0) { console.log('FATAL: ' + label); process.exit(2); }
  vm.runInContext(blocks[idx], sandbox, { filename: 'b' + idx });
}
runBlock(findBlock(b => b.includes('CFG = {') && b.includes('SCREENS = [')), 'cfg');
runBlock(findBlock(b => b.includes('G = {') && b.includes('function setScreen')), 'state');
runBlock(findBlock(b => b.includes('function powerupStep')), 'power');
runBlock(findBlock(b => b.includes('function enemyStep')), 'enemy');
const S = sandbox;
for (let i = 0; i < 53; i++) { S.G.roachFrames[i] = { complete: true }; S.G.gorillaFrames[i] = { complete: true }; }

let passed = 0, failed = 0;
function check(name, cond) {
  if (cond) { console.log('  PASS: ' + name); passed++; }
  else { console.log('  FAIL: ' + name); failed++; }
}

// ============================================================
// TEST 1: Enemy falls off platform tip and lands below
// ============================================================
console.log('\n[Test 1: Enemy falls off platform tip]');
{
  S.G.st = S.ST.PLAY;
  S.setScreen(0);
  S.G.st = S.ST.PLAY;
  S.G.enemies = [];
  S.G.boss = null;
  S.G.freeze = 0;

  // Spawn 10 cats on the y=168 platform, all with different x positions.
  // Over 1000 frames, at least some should fall off.
  let anyFell = false, anyLanded = false, maxDrift = 0;
  let fallCount = 0;
  for (let i = 0; i < 6; i++) {
    const e = S.spawnEnemy('cat');
    if (!e) break;
    e.x = 46 + i * 5; e.baseY = 168 - 8; e.surf = 'plat'; e.minX = 46; e.maxX = 80;
    e.y = e.baseY; e.vy = 0; e.dir = i % 2 === 0 ? 1 : -1; e.jumpCd = 99999;
    e._fallStartX = null; // set when fall begins
  }
  for (let f = 0; f < 1200; f++) {
    for (const e of S.G.enemies) {
      if (e.dead) continue;
      S.stepEnemyWalk(e);
      if (e._fallFrom != null) {
        if (e._fallStartX == null) e._fallStartX = e.x;
        anyFell = true;
        fallCount++;
        maxDrift = Math.max(maxDrift, Math.abs(e.x - e._fallStartX));
      } else {
        e._fallStartX = null;
      }
      if (e.surf === 'ground') anyLanded = true;
    }
  }
  check('at least one enemy fell off a platform tip (fallFrames=' + fallCount + ')', anyFell);
  check('at least one enemy landed below', anyLanded);
  check('x stayed fixed during falls (maxDrift=' + maxDrift.toFixed(2) + ')', maxDrift < 1.0);
}

// ============================================================
// TEST 2: Enemies spread across platforms (not all on top)
// ============================================================
console.log('\n[Test 2: Enemies spread across platform levels]');
{
  S.G.st = S.ST.PLAY;
  S.setScreen(0);
  S.G.st = S.ST.PLAY;
  S.G.enemies = [];
  S.G.boss = null;
  S.G.freeze = 0;
  S.G.spawnT = 1; // spawn immediately

  // Run 600 frames, tracking which levels enemies visit
  const levelsVisited = new Set();
  let topCount = 0, totalFrames = 0;
  for (let f = 0; f < 600; f++) {
    S.enemyStep();
    for (const e of S.G.enemies) {
      if (e.dead) continue;
      totalFrames++;
      if (e.surf === 'ground') levelsVisited.add('ground');
      else if (e._jumpT != null) levelsVisited.add('air');
      else {
        const platY = e.baseY + (e.type === 'owl' || e.type === 'ghost' || e.type === 'roach' || e.type === 'gorilla' ? 17 : 8);
        for (const p of S.G.plat) {
          if (Math.abs(platY - p.y) < 5) {
            levelsVisited.add('y=' + p.y);
            if (p.y === 112) topCount++;
            break;
          }
        }
      }
    }
  }
  console.log('  Levels visited: ' + [...levelsVisited].join(', '));
  check('enemies visited >= 2 different levels over time', levelsVisited.size >= 2);
  check('not all frames on top platform (top=' + topCount + '/' + totalFrames + ')', topCount < totalFrames);
}

// ============================================================
// TEST 3: No teleport — jump only if x overlaps target
// ============================================================
console.log('\n[Test 3: No teleport (x must overlap target platform)]');
{
  S.G.st = S.ST.PLAY;
  S.setScreen(0);
  S.G.st = S.ST.PLAY;
  S.G.enemies = [];
  S.G.boss = null;
  S.G.freeze = 0;

  // Enemy on the y=200 LEFT platform (x=[10,44], walkable [16,38])
  // At x=12: y=140 LEFT is [10,44] — x=12 IS in range. y=168 is [40,86] — NOT.
  // y=112 is [52,92] — NOT. So nextPlatformAbove returns y=140.
  // At x=100: y=140 RIGHT is [86,120] — x=100 IS in range. y=168 [40,86] — NOT.
  // y=112 [52,92] — NOT. So nextPlatformAbove returns y=140 RIGHT.
  // We need an x that's NOT in ANY platform above. The gaps between platforms:
  // y=168 [40,86] and y=200 LEFT [10,44]: gap is x=[44,40] — no gap (overlap).
  // y=168 [40,86] and y=200 RIGHT [86,120]: overlap at x=86.
  // The only way to have no platform above is to be on the TOP platform.
  // So test: enemy on y=112 (top) — no platform above.
  const e = S.spawnEnemy('cat');
  e.x = 70; e.baseY = 112 - 8; e.surf = 'plat'; e.minX = 58; e.maxX = 86; e.y = e.baseY; e.vy = 0;
  e.dir = 1;
  S.G.enemies = [e];
  const hp = S.nextPlatformAbove(e);
  check('no platform above top platform (nextPlatformAbove=' + (hp ? 'y=' + hp.y : 'null') + ')', hp === null);
  e.jumpCd = 1;
  for (let f = 0; f < 50; f++) S.stepEnemyWalk(e);
  check('no jump initiated from top (jumpT=' + e._jumpT + ')', e._jumpT == null);
}

// ============================================================
// TEST 4: Jump IS allowed when x overlaps
// ============================================================
console.log('\n[Test 4: Jump allowed when x overlaps target]');
{
  S.G.st = S.ST.PLAY;
  S.setScreen(0);
  S.G.st = S.ST.PLAY;
  S.G.enemies = [];
  S.G.boss = null;
  S.G.freeze = 0;

  // Enemy on the y=168 platform (x=[40,86], walkable [46,80])
  // The y=140 LEFT platform is at x=[10,44]. Enemy at x=46 is NOT in [10,44].
  // But the y=140 RIGHT platform is at x=[86,120]. Enemy at x=80 is NOT in [86,120].
  // So no jump should happen from x=46-80 to y=140.
  // Instead, let's put the enemy at x=50 on y=168. The y=112 platform is at x=[52,92].
  // x=50 is NOT in [52,92]. So no jump to y=112 either.
  // Let's try x=60 on y=168. y=112 is at x=[52,92]. x=60 IS in [52,92]. Jump allowed!
  const e = S.spawnEnemy('cat');
  e.x = 60; e.baseY = 168 - 8; e.surf = 'plat'; e.minX = 46; e.maxX = 80; e.y = e.baseY; e.vy = 0;
  e.dir = 1;
  // Force the jump: set _jumpStop and _jumpTarget directly
  const targetPlat = S.G.plat.find(p => p.y === 112);
  e._jumpStop = 36;
  e._jumpTarget = targetPlat;
  S.G.enemies = [e];

  let jumped = false;
  for (let f = 0; f < 200; f++) {
    S.stepEnemyWalk(e);
    if (e._jumpT != null) { jumped = true; break; }
  }
  check('enemy jump initiated when x overlapped target (jumped=' + jumped + ')', jumped);
  // run the jump arc to completion
  for (let f = 0; f < 50 && e._jumpT != null; f++) S.stepEnemyWalk(e);
  check('enemy landed on upper platform (baseY=' + e.baseY.toFixed(0) + ', expected ' + (112 - 8) + ')', Math.abs(e.baseY - (112 - 8)) < 3);
  // also verify it's not at the fly offset
  check('non-fly enemy at correct offset (baseY=' + e.baseY.toFixed(0) + ' != ' + (112 - 17) + ')', Math.abs(e.baseY - (112 - 17)) > 3);

  // Sub-test: enemy at x=46 on y=168 — y=112 platform is at x=[52,92], x=46 is NOT in range
  // Should NOT jump
  const e2 = S.spawnEnemy('cat');
  e2.x = 46; e2.baseY = 168 - 8; e2.surf = 'plat'; e2.minX = 46; e2.maxX = 80;
  e2.y = e2.baseY; e2.vy = 0; e2.dir = 1;
  const e2Target = S.G.plat.find(p => p.y === 112);
  e2._jumpStop = 36; e2._jumpTarget = e2Target;
  S.G.enemies = [e2];
  // Simulate the jumpCd trigger: the code checks nextPlatformAbove which filters by x
  // But we set _jumpTarget directly, so we need to test the nextPlatformAbove logic
  const hp = S.nextPlatformAbove(e2);
  check('nextPlatformAbove returns null when x does not overlap (x=46, target y=112 x=[52,92])', hp === null);
}

// ============================================================
// TEST 5: Mini drop — no teleport, lands below spawn
// ============================================================
console.log('\n[Test 5: Mini drop lands below spawn]');
{
  S.G.st = S.ST.PLAY;
  S.setScreen(0);
  S.G.st = S.ST.PLAY;
  S.G.enemies = [];
  S.G.freeze = 0;
  S.G.boss = { x: 72, y: 100, bw: 23, bh: 48, kind: 'roach', name: 'JOTITO', hp: 10, spawnCd: 100 };
  S.spawnMiniBoss(S.G.boss);
  const mini = S.G.enemies[0];
  const spawnY = mini._dropFrom;
  const startX = mini.x;

  let maxVy = 0, xDrift = 0;
  for (let f = 0; f < 300; f++) {
    S.enemyStep();
    maxVy = Math.max(maxVy, Math.abs(mini.vy));
    xDrift = Math.max(xDrift, Math.abs(mini.x - startX));
    if (!mini.dropping) break;
  }
  check('mini landed', !mini.dropping);
  check('mini vy capped (max=' + maxVy.toFixed(2) + ')', maxVy <= 1.21);
  check('mini x fixed during drop (drift=' + xDrift.toFixed(2) + ')', xDrift < 0.5);
  check('mini landed below spawn (y=' + mini.y.toFixed(0) + ' >= spawnY=' + spawnY.toFixed(0) + ')', mini.y >= spawnY - 2);
}

console.log('\n' + passed + ' passed, ' + failed + ' failed');
process.exit(failed ? 1 : 0);
