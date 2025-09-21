#!/usr/bin/env node
const { spawnSync } = require('node:child_process');
const { existsSync, mkdirSync } = require('node:fs');
const path = require('node:path');

const pkgDir = path.join(__dirname, '..');
const installRoot = path.join(pkgDir, 'dist');
const binDir = path.join(installRoot, 'bin');
const binName = process.platform === 'win32' ? 'ai-dlc-cli.exe' : 'ai-dlc-cli';
const installedBinary = path.join(binDir, binName);

if (!existsSync(binDir)) {
  mkdirSync(binDir, { recursive: true });
}

if (existsSync(installedBinary)) {
  // Already installed; skip unless user forces reinstall.
  return;
}

const versionTag = require('../package.json').aiDlc?.cargoVersion || require('../package.json').version;
const args = ['install', 'ai-dlc-cli', '--root', installRoot, '--locked'];
if (versionTag) {
  args.push('--version', versionTag);
}

const check = spawnSync('cargo', ['--version'], { stdio: 'ignore' });
if (check.status !== 0) {
  console.error('Rust toolchain not found. Install it from https://rustup.rs/ before using the ai-dlc npm package.');
  process.exit(1);
}

const result = spawnSync('cargo', args, { stdio: 'inherit' });
if (result.status !== 0) {
  console.error('\nFailed to install ai-dlc-cli via cargo. Ensure Rust is installed and accessible on PATH.');
  process.exit(result.status ?? 1);
}
