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

const { execSync } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');

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

function getRemoteVersion() {
  // Try npm registry first (works for published packages)
  try {
    const out = execSync(`npm view ${PKG_NAME} version`, {
      encoding: 'utf8',
      timeout: 15000,
      stdio: ['pipe', 'pipe', 'pipe'],
    }).trim();
    if (out) return out;
  } catch {
    // not on npm registry — fall through to git
  }

  // Fallback: query git remote for latest tag
  try {
    const repoUrl = getRepoUrl();
    const out = execSync(`git ls-remote --tags --refs ${repoUrl}`, {
      encoding: 'utf8',
      timeout: 15000,
      stdio: ['pipe', 'pipe', 'pipe'],
    }).trim();
    if (out) {
      // Parse tags like "refs/tags/v1.2.3" or "refs/tags/1.2.3"
      const tags = out.split('\n').map(line => {
        const match = line.match(/refs\/tags\/v?(\d+\.\d+\.\d+)$/);
        return match ? match[1] : null;
      }).filter(Boolean);
      if (tags.length) {
        tags.sort(compareVersions);
        return tags[tags.length - 1];
      }
    }
  } catch {
    // git not available or network error
  }

  return null;
}

function parseVersionParts(v) {
  // Strip pre-release suffixes like "1.2.3-beta" → [1, 2, 3]
  return v.split('.').map(s => {
    const n = parseInt(s, 10);
    return isNaN(n) ? 0 : n;
  });
}

function compareVersions(a, b) {
  const pa = parseVersionParts(a);
  const pb = parseVersionParts(b);
  const len = Math.max(pa.length, pb.length);
  for (let i = 0; i < len; i++) {
    const av = pa[i] || 0;
    const bv = pb[i] || 0;
    if (av !== bv) return av - bv;
  }
  return 0;
}

function getRepoUrl() {
  // Derive from package.json repository field
  try {
    const pkgPath = path.join(__dirname, '..', 'package.json');
    if (fs.existsSync(pkgPath)) {
      const pkg = JSON.parse(fs.readFileSync(pkgPath, 'utf8'));
      if (pkg.repository && pkg.repository.url) {
        // Convert "git+https://github.com/..." to "https://github.com/..."
        return pkg.repository.url.replace(/^git\+/, '');
      }
    }
  } catch {
    // fall through to default
  }
  return 'https://github.com/elaysia-feng/code-dev-skill.git';
}

function main() {
  const args = process.argv.slice(2);
  const json = args.includes('--json');

  const local = getLocalVersion();
  const remote = getRemoteVersion();

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
      console.log(`\nInstall with: npm install ${PKG_NAME}`);
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

main();
