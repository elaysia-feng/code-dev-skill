#!/usr/bin/env node

/**
 * Check if a newer version of readability-first-coding is available.
 *
 * Usage:
 *   npx readability-first-check              # check for updates
 *   npx readability-first-check --json       # machine-readable output
 *
 * Exit codes:
 *   0 — up to date or check succeeded
 *   1 — newer version available
 *   2 — error (network, missing tooling)
 *   3 — package not installed locally
 */

const fs = require('node:fs');
const path = require('node:path');
const getRemoteVersion = require(path.join(__dirname, 'remote-version.js'));
const { compareVersions } = require(path.join(__dirname, 'version.js'));

const PKG_NAME = 'readability-first-coding';

function getLocalVersion() {
  // Try to find the installed package in node_modules
  const candidates = [
    path.join(process.cwd(), 'node_modules', PKG_NAME, 'package.json'),
    path.join(__dirname, '..', 'package.json'), // running from source repo
  ];
  for (const p of candidates) {
    if (fs.existsSync(p)) {
      return JSON.parse(fs.readFileSync(p, 'utf8')).version;
    }
  }
  return null;
}

async function main() {
  const args = process.argv.slice(2);
  const json = args.includes('--json');

  const local = getLocalVersion();
  const remote = await getRemoteVersion();

  if (!remote) {
    const msg = 'Could not fetch remote version. Check your network connection.';
    if (json) {
      process.stderr.write(JSON.stringify({ status: 'error', error: msg }) + '\n');
    } else {
      console.error(`ERROR: ${msg}`);
    }
    process.exit(2);
  }

  if (!local) {
    if (json) {
      console.log(JSON.stringify({ status: 'not_installed', installed: false, latest: remote }));
    } else {
      console.log(`Package "${PKG_NAME}" is not installed locally.`);
      console.log(`Latest version: ${remote}`);
      console.log('\nInstall with: npm install github:elaysia-feng/code-dev-skill');
    }
    process.exit(3);
  }

  const cmp = compareVersions(local, remote);

  if (json) {
    console.log(JSON.stringify({
      status: cmp >= 0 ? 'up_to_date' : 'update_available',
      installed: true,
      local,
      remote,
      upToDate: cmp >= 0,
    }));
  } else {
    if (cmp >= 0) {
      console.log(`You are up to date! (v${local})`);
    } else {
      console.log(`Update available: v${local} → v${remote}`);
      console.log(`\nRun: npx readability-first-install --update`);
    }
  }

  process.exit(cmp >= 0 ? 0 : 1);
}

main().catch(error => {
  const msg = 'Could not fetch remote version. Check your network connection: ' + error.message;
  if (process.argv.includes('--json')) {
    process.stderr.write(JSON.stringify({ status: 'error', error: msg }) + '\n');
  } else {
    console.error('ERROR: ' + msg);
  }
  process.exitCode = 2;
});
