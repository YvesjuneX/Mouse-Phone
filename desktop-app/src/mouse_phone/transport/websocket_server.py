"""Capa de transporte WebSocket; no contiene reglas de entrada de Windows."""
import asyncio
import json
import socket
import time

import websockets

from mouse_phone.application.controller import RemoteController
from mouse_phone.config.settings import ANIMATION_INTERVAL_SECONDS
from mouse_phone.input.motion import Motion
from mouse_phone.input.windows import read_cursor, screen_bounds, write_cursor
from mouse_phone.input import windows


async def animate(motion: Motion) -> None:
    previous = time.perf_counter()
    while True:
        await asyncio.sleep(ANIMATION_INTERVAL_SECONDS)
        now = time.perf_counter()
        motion.tick(now - previous)
        previous = now


async def handle_client(websocket) -> None:
    motion = Motion(read_cursor, write_cursor, screen_bounds())
    controller = RemoteController(motion)
    animation = asyncio.create_task(animate(motion))
    print(f"Móvil conectado: {websocket.remote_address}")
    try:
        await websocket.send(json.dumps({"type": "remote_mouse", "version": 3, "name": socket.gethostname()}))
        async for raw_message in websocket:
            try: await controller.execute(json.loads(raw_message))
            except windows.pyautogui.FailSafeException:
                motion.reset(); print("Protección de esquina activa: aparta el cursor con el ratón físico.")
            except (ValueError, KeyError, TypeError, json.JSONDecodeError) as error: print(f"Mensaje ignorado: {error}")
    except websockets.ConnectionClosed: pass
    finally:
        animation.cancel()
        await asyncio.gather(animation, return_exceptions=True)
        print("Móvil desconectado")
