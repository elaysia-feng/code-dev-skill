const https = require('node:https');

const PACKAGE_NAME = 'readability-first-coding';
const PACKAGE_URL = 'https://raw.githubusercontent.com/elaysia-feng/code-dev-skill/main/package.json';
const MAX_RESPONSE_BYTES = 65536;

module.exports = function getRemoteVersion() {
  return new Promise(resolve => {
    let settled = false;
    const finish = version => {
      if (!settled) {
        settled = true;
        resolve(version);
      }
    };

    const request = https.get(PACKAGE_URL, { timeout: 15000 }, response => {
      if (response.statusCode !== 200) {
        response.resume();
        finish(null);
        return;
      }

      response.setEncoding('utf8');
      let body = '';
      response.on('data', chunk => {
        body += chunk;
        if (Buffer.byteLength(body, 'utf8') > MAX_RESPONSE_BYTES) {
          finish(null);
          response.destroy();
        }
      });
      response.on('end', () => {
        try {
          const pkg = JSON.parse(body);
          if (pkg.name !== PACKAGE_NAME || typeof pkg.version !== 'string'
              || !/^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$/.test(pkg.version)) {
            finish(null);
            return;
          }
          finish(pkg.version);
        } catch {
          finish(null);
        }
      });
    });

    request.on('timeout', () => request.destroy(new Error('GitHub version request timed out')));
    request.on('error', () => finish(null));
  });
};
