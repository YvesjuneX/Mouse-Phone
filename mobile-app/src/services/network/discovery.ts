export type Computer = { name: string; ip: string };
const DESKTOP_PORT = 8765;

export function discoveryAddresses(ownIp: string, saved: string[]): string[] {
  const parts = ownIp.split('.');
  const ownHost = Number(parts[3]);
  const prefix = parts.slice(0, 3).join('.') + '.';
  // DHCP often assigns neighbouring addresses. Probe those before empty low IPs.
  const nearby = Array.from({ length: 254 }, (_, index) => index + 1)
    .filter(host => host !== ownHost)
    .sort((a, b) => Math.abs(a - ownHost) - Math.abs(b - ownHost))
    .map(host => prefix + host);
  return [...new Set([...saved.filter(ip => ip.startsWith(prefix) && ip !== ownIp), ...nearby])];
}

// Each probe owns its timer and settles exactly once, including timeout/error races.
export function probeComputer(ip: string, timeoutMs = 2500): Promise<Computer | null> {
  return new Promise((resolve) => {
    let done = false;
    let ws: WebSocket | undefined;
    const finish = (result: Computer | null) => {
      if (done) return;
      done = true;
      clearTimeout(timer);
      if (ws) {
        ws.onopen = ws.onmessage = ws.onerror = ws.onclose = null;
        try { ws.close(); } catch { /* Already closed. */ }
      }
      resolve(result);
    };
    const timer = setTimeout(() => finish(null), timeoutMs);
    try {
      ws = new WebSocket(`ws://${ip}:${DESKTOP_PORT}`);
      ws.onmessage = (event) => {
        try {
          const hello = JSON.parse(String(event.data));
          if (hello.type === 'remote_mouse') {
            finish({ ip, name: typeof hello.name === 'string' && hello.name ? hello.name : 'Ordenador encontrado' });
          }
        } catch { /* Ignore messages from unrelated WebSocket services. */ }
      };
      ws.onerror = () => finish(null);
      ws.onclose = () => finish(null);
    } catch { finish(null); }
  });
}

export async function discoverComputers(addresses: string[], onFound: (computer: Computer) => void,
  probe = probeComputer, concurrency = 8): Promise<number> {
  const queue = [...new Set(addresses)];
  let next = 0;
  let found = 0;
  await Promise.all(Array.from({ length: Math.min(concurrency, queue.length) }, async () => {
    while (next < queue.length) {
      const ip = queue[next++];
      const computer = await probe(ip);
      if (computer) { found++; onFound(computer); }
    }
  }));
  return found;
}
