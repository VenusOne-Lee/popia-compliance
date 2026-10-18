#!/usr/bin/env node
// popia-kit for JavaScript-first builders. Runs the Python tools (stdlib only)
// with the python3 already on your machine. Nothing is sent anywhere.
//
//   npx -y github:VenusOne-Lee/popia-compliance scan .
//
// Engineering guidance, not legal advice. See DISCLAIMER.md.
'use strict';
const {spawnSync} = require('child_process');
const path = require('path');

const cli = path.join(__dirname, '..', 'scripts', 'cli.py');
const candidates = process.platform === 'win32' ? ['py', 'python', 'python3'] : ['python3', 'python'];

for (const py of candidates) {
  const args = py === 'py' ? ['-3', cli, ...process.argv.slice(2)] : [cli, ...process.argv.slice(2)];
  const r = spawnSync(py, args, {stdio: 'inherit'});
  if (r.error && r.error.code === 'ENOENT') continue;
  if (r.error) {
    console.error('popia-kit: could not start ' + py + ' (' + r.error.code + ')');
    process.exit(1);
  }
  process.exit(r.status === null ? 1 : r.status);
}
console.error('popia-kit needs Python 3.8 or newer. Install it from https://www.python.org/downloads/ and try again.');
process.exit(1);
