// Measure where enemies sit at a given moment (snapshot distribution).
// Run several seeds to get a stable picture.
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

// Deterministic PRNG so results are reproducible
let seed = 42;
function rand() { seed = (seed * 1103515245 + 12345) & 0x7fffffff; return seed / 0x7fffffff; }

// Measure distribution at a snapshot: how many enemies sit at each level
function measure(framesToRun, seedVal) {
  seed = seedVal;
  // monkey-patch Math.random for reproducibility (Math is global in the vm)
  const vmGlobal = vm.runInContext('Math', sandbox);
  const origRandom = vmGlobal.random;
  vmGlobal.random = rand;

  S.G.st = S.ST.PLAY;
  S.setScreen(0);
  S.G.st = S.ST.PLAY;
  S.G.enemies = [];
  S.G.boss = null; // no boss = no minis, only the 4 normal types
  S.G.freeze = 0;
  S.G.spawnT = 1;

  for (let f = 0; f < framesToRun; f++) S.enemyStep();

  // snapshot: where is each living enemy?
  const dist = { 'y=112': 0, 'y=140': 0, 'y=168': 0, 'y=200': 0, 'ground': 0, 'air': 0 };
  let alive = 0;
  for (const e of S.G.enemies) {
    if (e.dead) continue;
    alive++;
    if (e._jumpT != null || (e._fallFrom != null) || (e.mini && e.dropping)) { dist['air']++; continue; }
    if (e.surf === 'ground') { dist['ground']++; continue; }
    const platY = e.baseY + (e.type === 'owl' || e.type === 'ghost' || e.type === 'roach' || e.type === 'gorilla' ? 17 : 8);
    let matched = false;
    for (const k of ['y=112', 'y=140', 'y=168', 'y=200']) {
      const py = parseInt(k.split('=')[1]);
      if (Math.abs(platY - py) < 5) { dist[k]++; matched = true; break; }
    }
    if (!matched) { dist['ground']++; } // fallback
  }
  vmGlobal.random = origRandom;
  return { dist, alive };
}

// Run several snapshots at different times, averaged over a few seeds
console.log('PYRAMID screen. No boss. Normal enemies only (owl/cat/ghost/slime).');
console.log('');
const times = [300, 600, 900]; // 5s, 10s, 15s
for (const t of times) {
  let totals = { 'y=112': 0, 'y=140': 0, 'y=168': 0, 'y=200': 0, 'ground': 0, 'air': 0 };
  let totalAlive = 0;
  const N = 5;
  for (let s = 0; s < N; s++) {
    const { dist, alive } = measure(t, 100 + s);
    totalAlive += alive;
    for (const k in totals) totals[k] += dist[k];
  }
  console.log('At t=' + t + ' frames (' + (t/60).toFixed(1) + 's), avg alive=' + (totalAlive/N).toFixed(1) + ':');
  for (const k of ['y=112', 'y=140', 'y=168', 'y=200', 'ground', 'air']) {
    const avg = totals[k] / N;
    const bar = '#'.repeat(Math.round(avg));
    console.log('  ' + k.padEnd(8) + ' ' + avg.toFixed(1).padStart(5) + '  ' + bar);
  }
  console.log('');
}
