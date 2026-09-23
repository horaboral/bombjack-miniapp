// Detailed trace of ONE enemy: does it ever fall off a platform tip?
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
S.G.st = S.ST.PLAY;
S.setScreen(0);
S.G.st = S.ST.PLAY;
S.G.enemies = [];
S.G.boss = null;
S.G.freeze = 0;

console.log('PYRAMID platforms:');
for (const p of S.G.plat) console.log('  y=' + p.y + ' x=[' + p.x + ',' + (p.x + p.w) + '] w=' + p.w);
console.log('GROUND_Y=' + S.CFG.GROUND_Y);

// Spawn ONE enemy on the bottom-left platform (y=200, x=[10,44])
// Force it to be a non-fly type (cat) so it doesn't bob
const e = S.spawnEnemy('cat');
e.x = 20; e.baseY = 200 - 8; e.surf = 'plat'; e.minX = 16; e.maxX = 38; e.y = e.baseY; e.vy = 0;
e.dir = 1; // walking right
e.jumpCd = 9999; // disable jumping for this trace
S.G.enemies = [e];

console.log('\nTracing one cat on bottom-left platform (y=200, x=[10,44], walkable=[16,38])');
console.log('Starting at x=' + e.x + ', dir=' + e.dir + ' (right)');
console.log('');

let frames = 0;
let fell = false;
let events = [];
for (frames = 0; frames < 600; frames++) {
  const prevX = e.x;
  const prevBaseY = e.baseY;
  const prevSurf = e.surf;
  const prevMinX = e.minX;
  const prevMaxX = e.maxX;

  S.stepEnemyWalk(e);

  // detect events
  if (e.baseY !== prevBaseY) {
    events.push('frame ' + frames + ': BASEY CHANGE ' + prevBaseY.toFixed(1) + ' -> ' + e.baseY.toFixed(1) + ' (x=' + e.x.toFixed(1) + ', surf=' + e.surf + ', jumpT=' + e._jumpT + ', jumpStop=' + e._jumpStop + ', jumpTarget=' + (e._jumpTarget ? 'y=' + e._jumpTarget.y : 'null') + ', fallFrom=' + e._fallFrom + ')');
  }
  if (e.surf !== prevSurf) {
    events.push('frame ' + frames + ': SURF CHANGE ' + prevSurf + ' -> ' + e.surf + ' (x=' + e.x.toFixed(1) + ', baseY=' + e.baseY.toFixed(1) + ', minX=' + e.minX + ', maxX=' + e.maxX + ')');
  }
  if (e.minX !== prevMinX || e.maxX !== prevMaxX) {
    events.push('frame ' + frames + ': RANGE CHANGE [' + prevMinX + ',' + prevMaxX + '] -> [' + e.minX + ',' + e.maxX + '] (x=' + e.x.toFixed(1) + ', surf=' + e.surf + ')');
  }
  if (e._fallFrom != null) {
    events.push('frame ' + frames + ': FALLING (x=' + e.x.toFixed(1) + ', y=' + e.y.toFixed(1) + ', vy=' + e.vy.toFixed(2) + ', fallFrom=' + e._fallFrom + ')');
    fell = true;
  }
  if (e.x <= e.minX + 0.5 || e.x >= e.maxX - 0.5) {
    // near edge
    if (frames % 20 === 0) {
      events.push('frame ' + frames + ': NEAR EDGE (x=' + e.x.toFixed(2) + ', minX=' + e.minX + ', maxX=' + e.maxX + ', dir=' + e.dir + ')');
    }
  }
  if (events.length > 0) {
    for (const ev of events) console.log(ev);
    events = [];
  }
  if (e.surf === 'ground' && prevSurf !== 'ground') {
    console.log('*** ENEMY REACHED GROUND at frame ' + frames + ', x=' + e.x.toFixed(1) + ' ***');
    break;
  }
}

if (!fell) {
  console.log('\n*** NO FALL DETECTED in ' + frames + ' frames ***');
  console.log('Final state: x=' + e.x.toFixed(1) + ', baseY=' + e.baseY.toFixed(1) + ', surf=' + e.surf + ', minX=' + e.minX + ', maxX=' + e.maxX + ', dir=' + e.dir);
}
