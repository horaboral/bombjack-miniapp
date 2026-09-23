const http = require('http');
const fs = require('fs');
const path = require('path');
const root = process.argv[2] || __dirname;
const port = parseInt(process.argv[3] || '8899');
const mime = { '.html':'text/html', '.png':'image/png', '.jpg':'image/jpeg', '.js':'text/javascript', '.json':'application/json', '.mp3':'audio/mpeg', '.svg':'image/svg+xml' };
http.createServer((req, res) => {
  let p = decodeURIComponent(req.url.split('?')[0]);
  if (p === '/') p = '/bombjack.html';
  const full = path.join(root, p);
  if (fs.existsSync(full) && fs.statSync(full).isFile()) {
    const ext = path.extname(full).toLowerCase();
    res.writeHead(200, { 'Content-Type': mime[ext] || 'application/octet-stream' });
    fs.createReadStream(full).pipe(res);
  } else {
    res.writeHead(404); res.end('not found');
  }
}).listen(port, '127.0.0.1', () => console.log('serving ' + root + ' on ' + port));
