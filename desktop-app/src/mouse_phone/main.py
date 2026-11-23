"""Composición y arranque del servicio de escritorio."""
import asyncio
import threading

import websockets

from mouse_phone.config.settings import PORT
from mouse_phone.input import windows
from mouse_phone.security.pairing import PairingManager
from mouse_phone.security.device_registry import DeviceRegistry
from mouse_phone.security.active_sessions import ActiveSessions
from mouse_phone.system.network import local_ip
from mouse_phone.system.processes import stop_previous_server
from mouse_phone.transport.websocket_server import handle_client
from mouse_phone.ui.desktop_window import DesktopWindow


class ServerRuntime:
    """Ejecuta asyncio en segundo plano mientras Tkinter controla la ventana."""
    def __init__(self, pairing: PairingManager, registry: DeviceRegistry, sessions: ActiveSessions):
        self.pairing = pairing
        self.registry = registry
        self.sessions = sessions
        self.stop_requested = threading.Event()
        self.ready = threading.Event()
        self.error: Exception | None = None

    async def serve(self) -> None:
        try:
            stop_previous_server(PORT)
            print("Mouse Phone listo")
            print(f"Escuchando en ws://0.0.0.0:{PORT}")
            async def client_handler(websocket):
                await handle_client(websocket, self.pairing, self.registry, self.sessions)
            async with websockets.serve(client_handler, "0.0.0.0", PORT, compression=None):
                self.ready.set()
                while not self.stop_requested.is_set(): await asyncio.sleep(.1)
        except Exception as error:
            self.error = error
            self.ready.set()
        finally:
            self.ready.set()

    def start(self) -> None:
        threading.Thread(target=lambda: asyncio.run(self.serve()), daemon=True).start()
        self.ready.wait()
        if self.error: raise self.error

    def stop(self) -> None:
        self.stop_requested.set()


async def main() -> None:
    """Compatibilidad para pruebas o arranque sin interfaz."""
    pairing, registry, sessions = PairingManager(), DeviceRegistry(), ActiveSessions()
    stop_previous_server(PORT)
    async with websockets.serve(lambda ws: handle_client(ws, pairing, registry, sessions), "0.0.0.0", PORT, compression=None):
        await asyncio.Future()


def run() -> None:
    windows.pyautogui.PAUSE = 0; windows.pyautogui.MINIMUM_DURATION = 0
    pairing, registry, sessions = PairingManager(), DeviceRegistry(), ActiveSessions()
    ip = local_ip()
    runtime = ServerRuntime(pairing, registry, sessions)
    try:
        runtime.start()
        DesktopWindow(ip, pairing, registry, sessions, runtime.stop).run()
    except KeyboardInterrupt:
        runtime.stop()
        print("\nServidor detenido")
