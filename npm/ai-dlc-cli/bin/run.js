#!/usr/bin/env node
const { spawn } = require('node:child_process');
const { existsSync } = require('node:fs');
const path = require('node:path');

const binName = process.platform === 'win32' ? 'ai-dlc-cli.exe' : 'ai-dlc-cli';
const binPath = path.join(__dirname, '..', 'dist', 'bin', binName);

if (!existsSync(binPath)) {
  console.error('ai-dlc-cli binary not found. Run `npm install ai-dlc-cli` again or build via cargo.');
  process.exit(1);
}

const child = spawn(binPath, process.argv.slice(2), { stdio: 'inherit' });
child.on('exit', code => process.exit(code));
child.on('error', err => {
  console.error(err);
  process.exit(1);
});
