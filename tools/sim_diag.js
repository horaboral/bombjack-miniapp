// Quick diagnostic: verify boss + enemy spawning works after v41 changes
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
sandbox.haptic = () => {}; sandbox.beep = () => {};
sandbox.deathSound = () => {}; sandbox.musicStart = () => {}; sandbox.musicStop = () => {};
sandbox.AC = null;
vm.createContext(sandbox);
function findBlock(pred) { for (let i = 0; i < blocks.length; i++) if (pred(blocks[i])) return i; return -1; }
function runBlock(idx, label) {
  if (idx < 0) { console.log('FATAL: ' + label + ' block not found'); process.exit(2); }
  vm.runInContext(blocks[idx], sandbox, { filename: 'block' + (idx + 1) + '.js' });
}
runBlock(findBlock(b => b.includes('CFG = {') && b.includes('SCREENS = [')), 'cfg');
runBlock(findBlock(b => b.includes('G = {') && b.includes('function setScreen')), 'state');
runBlock(findBlock(b => b.includes('function enemyStep')), 'enemy');
const S = sandbox;

// Fake boss frames (simulates loaded sprites)
for (let i = 0; i < 53; i++) {
  S.G.roachFrames[i] = { complete: true };
  S.G.gorillaFrames[i] = { complete: true };
}

// Set up screen 0 (Jotito)
S.setScreen(0);
S.G.st = S.ST.PLAY;
S.G.freeze = 0;
S.G.enemies = [];
S.G.spawnT = 50; // force a spawn soon

console.log('Boss:', S.G.boss ? S.G.boss.name + ' spawnCd=' + S.G.boss.spawnCd : 'NULL');
console.log('spawnT:', S.G.spawnT);
console.log('enemies:', S.G.enemies.length);

// Run 600 frames (10s at 60fps) and count spawns
let totalSpawned = 0;
for (let f = 0; f < 600; f++) {
  const before = S.G.enemies.length;
  S.enemyStep();
  S.bossStep();
  const after = S.G.enemies.length;
  if (after > before) totalSpawned += (after - before);
}
const minis = S.G.enemies.filter(e => e.mini).length;
const normals = S.G.enemies.filter(e => !e.mini).length;
console.log('After 600 frames: ' + S.G.enemies.length + ' alive (' + minis + ' minis, ' + normals + ' normal), ' + totalSpawned + ' total spawned');
console.log('Boss still alive?', S.G.boss ? 'YES (hp=' + S.G.boss.hp + ', spawnCd=' + S.G.boss.spawnCd + ')' : 'NO');
console.log('spawnT:', S.G.spawnT);

if (totalSpawned > 0) {
  console.log('OK: spawning works');
} else {
  console.log('BROKEN: no spawns in 600 frames');
  // check why
  console.log('  G.st:', S.G.st, 'G.freeze:', S.G.freeze);
  console.log('  G.boss:', S.G.boss ? 'yes' : 'no');
  console.log('  enemy cap: ' + S.G.enemies.length + ' (max 6/7)');
}
