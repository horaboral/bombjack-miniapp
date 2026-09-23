const vm = require('vm');
const fs = require('fs');
const html = fs.readFileSync('bombjack.html', 'utf8');
const blocks = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);
let ok = true;
for (let i = 0; i < blocks.length; i++) {
  try {
    // just check it parses
    const src = blocks[i].replace(/\bconst\b/g, 'var').replace(/\blet\b/g, 'var');
    vm.compileFunction(src, [], { filename: 'block' + i });
    console.log('block ' + i + ': OK (' + src.length + ' chars)');
  } catch (e) {
    console.log('block ' + i + ': FAIL ' + e.message);
    ok = false;
  }
}
process.exit(ok ? 0 : 1);
