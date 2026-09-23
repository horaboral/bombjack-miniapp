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
S.G.boss = { x: 72, y: 100, w: 23, h: 48, kind: 'roach', name: 'JOTITO', hp: 10, spawnCd: 100 };
S.spawnMiniBoss(S.G.boss);
const mini = S.G.enemies[0];
console.log('mini start: x=' + mini.x + ' y=' + mini.y + ' baseY=' + mini.baseY + ' dropping=' + mini.dropping + ' type=' + mini.type);
console.log('surfaceAtX(' + mini.x + ') = ' + S.surfaceAtX(mini.x));
for (let i = 0; i < 50; i++) {
  S.enemyStep();
  if (i < 10 || i % 10 === 0 || !mini.dropping) {
    console.log('frame ' + i + ': y=' + mini.y.toFixed(2) + ' vy=' + (mini.vy||0).toFixed(3) + ' dropping=' + mini.dropping);
  }
  if (!mini.dropping) { console.log('landed at frame ' + i + ', y=' + mini.y.toFixed(2)); break; }
}
if (mini.dropping) console.log('still dropping after 50 frames, y=' + mini.y.toFixed(2));
