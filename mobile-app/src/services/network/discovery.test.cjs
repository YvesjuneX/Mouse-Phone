const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const ts = require('typescript');
const Module = require('node:module');
const filename = require('node:path').join(__dirname, 'discovery.ts');
const compiled = new Module(filename, module);
compiled._compile(ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
}).outputText, filename);
const { probeComputer, discoverComputers, discoveryAddresses } = compiled.exports;

test('known computers and neighbours are in first batch without losing other addresses', () => {
  const addresses = discoveryAddresses('192.168.1.130', ['192.168.2.9', '192.168.1.200', '192.168.1.200']);
  assert.equal(addresses[0], '192.168.1.200');
  assert.ok(addresses.indexOf('192.168.1.129') < 8);
  assert.ok(addresses.indexOf('192.168.1.131') < 8);
  assert.equal(addresses.length, 253);
  assert.equal(new Set(addresses).size, 253);
  assert.ok(!addresses.includes('192.168.1.130'));
  assert.ok(addresses.includes('192.168.1.1'));
  assert.ok(addresses.includes('192.168.1.254'));
});

test('neighbour is reported before any offline probe times out', async () => {
  let timeouts = 0;
  let foundAt = -1;
  await discoverComputers(discoveryAddresses('192.168.1.130', []), () => { foundAt = timeouts; }, async ip => {
    if (ip === '192.168.1.129') return { ip, name: 'PC' };
    await new Promise(resolve => setTimeout(resolve, 1));
    timeouts++;
    return null;
  });
  assert.equal(foundAt, 0);
});

test('slow valid reply after 700ms is found and socket is closed', async () => {
  let closed = 0;
  global.WebSocket = class {
    constructor() { this.timer = setTimeout(() => this.onmessage?.({ data: JSON.stringify({ type: 'remote_mouse', name: 'PC' }) }), 800); }
    close() { clearTimeout(this.timer); closed++; this.onerror?.({}); this.onclose?.({}); }
  };
  assert.deepEqual(await probeComputer('192.168.1.129'), { ip: '192.168.1.129', name: 'PC' });
  assert.equal(closed, 1);
});

test('timeout followed by error/close settles once and queue finds every PC', async () => {
  let active = 0, peak = 0, closed = 0;
  global.WebSocket = class {
    constructor(url) {
      active++; peak = Math.max(peak, active);
      if (!url.includes('offline')) this.timer = setTimeout(() => this.onmessage?.({ data: '{"type":"remote_mouse","version":2}' }), 5);
    }
    close() { clearTimeout(this.timer); closed++; active--; this.onerror?.({}); this.onclose?.({}); }
  };
  const found = [];
  const count = await discoverComputers(['offline', 'pc1', 'pc2', 'pc1'], c => found.push(c.ip), ip => probeComputer(ip, 20), 2);
  assert.equal(count, 2);
  assert.deepEqual(found.sort(), ['pc1', 'pc2']);
  assert.equal(closed, 3);
  assert.equal(active, 0);
  assert.ok(peak <= 2);
});

test('unrelated service is not presented as a computer', async () => {
  global.WebSocket = class {
    constructor() { this.timer = setTimeout(() => this.onmessage?.({ data: '{"type":"other_service"}' }), 1); }
    close() { clearTimeout(this.timer); }
  };
  assert.equal(await probeComputer('other', 15), null);
});
