import { DESKTOP_PORT } from '../../config/constants';

export function connectRemoteSocket(ip: string): WebSocket {
  return new WebSocket(`wss://${ip}:${DESKTOP_PORT}`);
}

export function sendRemoteMessage(socket: WebSocket | null, message: object): void {
  if (socket?.readyState === WebSocket.OPEN) socket.send(JSON.stringify(message));
}
