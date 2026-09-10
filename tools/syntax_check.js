// Extract all inline <script> blocks from bombjack.html and syntax-check
// each one with node --check via vm compilation (no execution).
const fs = require('fs');
const vm = require('vm');
const html = fs.readFileSync(__dirname + '/../bombjack.html', 'utf8');
const re = /<script>([\s\S]*?)<\/script>/g;
let m, i = 0, fail = 0;
while ((m = re.exec(html)) !== null) {
  i++;
  try {
    new vm.Script(m[1], { filename: 'block' + i + '.js' });
    console.log('block ' + i + ': OK (' + m[1].length + ' chars)');
  } catch (e) {
    fail++;
    console.log('block ' + i + ': SYNTAX ERROR: ' + e.message);
  }
}
console.log(fail === 0 ? 'ALL OK' : fail + ' FAILURES');
process.exit(fail === 0 ? 0 : 1);
