"""Composición y arranque del servicio de escritorio."""
import asyncio
import websockets

from mouse_phone.config.settings import PORT
from mouse_phone.input import windows
from mouse_phone.system.network import local_ip
from mouse_phone.system.processes import stop_previous_server
from mouse_phone.transport.websocket_server import handle_client


async def main() -> None:
    stop_previous_server(PORT)
    print("Mouse Phone listo")
    print(f"Introduce esta IP en el móvil: {local_ip()}")
    print(f"Escuchando en ws://0.0.0.0:{PORT}")
    async with websockets.serve(handle_client, "0.0.0.0", PORT, compression=None): await asyncio.Future()


def run() -> None:
    windows.pyautogui.PAUSE = 0; windows.pyautogui.MINIMUM_DURATION = 0
    try: asyncio.run(main())
    except KeyboardInterrupt: print("\nServidor detenido")
