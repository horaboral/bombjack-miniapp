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
sandbox.window = sandbox; sandbox.haptic = () => {}; sandbox.beep = () => {}; sandbox.AC = null;
vm.createContext(sandbox);
function findBlock(pred) { for (let i = 0; i < blocks.length; i++) if (pred(blocks[i])) return i; return -1; }
function runBlock(idx, label) {
  if (idx < 0) { console.log('FATAL: ' + label + ' block not found'); process.exit(2); }
  vm.runInContext(blocks[idx], sandbox, { filename: 'block' + (idx + 1) + '.js' });
}
runBlock(findBlock(b => b.includes('CFG = {') && b.includes('SCREENS = [')), 'cfg');
runBlock(findBlock(b => b.includes('G = {') && b.includes('function setScreen')), 'state');
runBlock(findBlock(b => b.includes('function enemyStep')), 'enemy');
runBlock(findBlock(b => b.includes('function deathSound') || b.includes('function musicStart')), 'audio');
const S = sandbox;

// --- CHECK 1: screen progression order ---
// simulate round clears
let order = [];
S.setScreen(0);
for (let r = 0; r < 6; r++) {
  order.push(S.G.screenIdx + ':' + S.SCREENS[S.G.screenIdx].name);
  S.G.round++;
  S.setScreen((S.G.round - 1) % 5);
}
console.log('progression order:', order.join(' -> '));
const okOrder = S.SCREENS[0].name === 'PYRAMID' && order[1].includes('GREEK');
console.log(okOrder ? 'PASS: PYRAMID -> GREEK (Sobesinho not skipped)' : 'FAIL: GREEK still skipped!');
if (!okOrder) process.exit(1);

// --- CHECK 2: mini kills player on touch (no P, no invuln) ---
S.setScreen(0); S.G.st = S.ST.PLAY;
S.G.freeze = 0; S.G.touchKill = 0;
S.P.dead = false; S.P.invuln = 0;
S.G.enemies = [];
// spawn a mini at player position
S.spawnMiniBoss(S.G.boss);
const mini = S.G.enemies.find(e => e.mini);
if (!mini) { console.log('FAIL: no mini spawned'); process.exit(1); }
// place mini on player (force landed on GROUND so the touch check runs)
mini.dropping = false;
mini.surf = 'ground'; mini.baseY = S.CFG.GROUND_Y - 8;
mini.minX = 8; mini.maxX = S.CFG.W - 8;
mini.x = S.P.x + 5; mini.y = S.P.y + 8;
S.enemyStep();
console.log('mini touch -> player dead?', S.P.dead ? 'YES (PASS)' : 'NO (FAIL)');
if (!S.P.dead) process.exit(1);

// --- CHECK 3: boss kills player on touch without P ---
S.P.dead = false; S.P.invuln = 0;
S.G.freeze = 0;
S.setScreen(1); S.G.st = S.ST.PLAY;
const boss = S.G.boss;
console.log('screen 1 boss:', boss ? boss.kind + ' ' + boss.name : 'NULL');
if (!boss) { console.log('FAIL: no boss on screen 1'); process.exit(1); }
// place player on the boss (boss bounces within walls, so meet it mid-field)
boss.x = 70; boss.y = 120;
S.P.x = 66; S.P.y = 110; S.P.vx = 0; S.P.vy = 0;
S.P.invuln = 0; // setScreen grants 60 frames of invuln; clear it
S.bossStep();
console.log('boss touch (no P) -> player dead?', S.P.dead ? 'YES (PASS)' : 'NO (FAIL)');
if (!S.P.dead) process.exit(1);

// --- CHECK 4: boss does NOT kill player when P is active (freeze) ---
S.P.dead = false; S.P.invuln = 0;
S.P.dead = false; S.P.deadT = 0;
S.setScreen(1); S.G.st = S.ST.PLAY;
S.G.freeze = 300; // after setScreen (it resets freeze)
const boss2 = S.G.boss;
boss2.x = 70; boss2.y = 120;
S.P.x = 66; S.P.y = 110; S.P.vx = 0; S.P.vy = 0;
S.P.invuln = 0;
const hpBefore = boss2.hp;
S.bossStep();
console.log('boss touch (with P) -> player dead?', S.P.dead ? 'YES (FAIL)' : 'NO (PASS)');
console.log('boss hp dropped?', boss2.hp < hpBefore ? 'YES (PASS, hp=' + boss2.hp + ')' : 'NO (FAIL)');
if (S.P.dead) process.exit(1);
if (boss2.hp >= hpBefore) process.exit(1);

console.log('=== ALL KILL TESTS PASSED ===');
