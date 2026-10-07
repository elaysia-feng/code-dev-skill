/**
 * Shared semver comparison.
 *
 * Both bin/install.js (--check) and bin/check-update.js need this. Keeping one
 * implementation avoids the drift that let install.js call an undefined
 * compareVersions() and crash on every invocation.
 */

const VERSION_RE = /^(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?(?:\+[0-9A-Za-z.-]+)?$/;

/**
 * Parse a version string into comparable parts.
 *
 * @param {string} v version string
 * @returns {{major:number, minor:number, patch:number, pre:string[]}|null} parts, or null if unparsable
 */
function parseVersion(v) {
  const m = VERSION_RE.exec(String(v).trim());
  if (!m) return null;
  return {
    major: Number(m[1]),
    minor: Number(m[2]),
    patch: Number(m[3]),
    pre: m[4] ? m[4].split('.') : [],
  };
}

/**
 * Compare a prerelease identifier list against a release version.
 * A prerelease sorts BEFORE the corresponding release (1.2.0-beta < 1.2.0),
 * and identifiers compare numerically when numeric, lexically otherwise.
 */
function comparePre(a, b) {
  if (a.length === 0 && b.length === 0) return 0;
  if (a.length === 0) return 1;   // release > prerelease
  if (b.length === 0) return -1;  // prerelease < release
  const len = Math.max(a.length, b.length);
  for (let i = 0; i < len; i++) {
    const x = a[i];
    const y = b[i];
    if (x === undefined) return -1;
    if (y === undefined) return 1;
    const xn = /^\d+$/.test(x);
    const yn = /^\d+$/.test(y);
    if (xn && yn) {
      const d = Number(x) - Number(y);
      if (d !== 0) return d;
    } else if (xn !== yn) {
      return xn ? -1 : 1; // numeric identifiers sort below alphanumeric ones
    } else if (x !== y) {
      return x < y ? -1 : 1;
    }
  }
  return 0;
}

/**
 * Compare two semver strings.
 *
 * @param {string} a
 * @param {string} b
 * @returns {number} negative if a < b, 0 if equal, positive if a > b
 */
function compareVersions(a, b) {
  const pa = parseVersion(a);
  const pb = parseVersion(b);
  if (!pa && !pb) return 0;
  if (!pa) return -1;
  if (!pb) return 1;
  for (const key of ['major', 'minor', 'patch']) {
    if (pa[key] !== pb[key]) return pa[key] - pb[key];
  }
  return comparePre(pa.pre, pb.pre);
}

module.exports = { parseVersion, compareVersions };