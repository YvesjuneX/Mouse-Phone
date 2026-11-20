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
from mouse_phone.security.session_crypto import SecureSession, new_keypair, unb64


async def animate(motion: Motion) -> None:
    previous = time.perf_counter()
    while True:
        await asyncio.sleep(ANIMATION_INTERVAL_SECONDS)
        now = time.perf_counter()
        motion.tick(now - previous)
        previous = now


async def handle_client(websocket, pairing=None) -> None:
    motion = Motion(read_cursor, write_cursor, screen_bounds())
    controller = RemoteController(motion)
    animation = asyncio.create_task(animate(motion))
    print(f"Móvil conectado: {websocket.remote_address}")
    try:
        await websocket.send(json.dumps({"type": "remote_mouse", "version": 6, "name": socket.gethostname(), "pairing_required": pairing is not None, "encrypted": True}))
        authenticated, session = pairing is None, None
        async for raw_message in websocket:
            try:
                message = json.loads(raw_message)
                if not authenticated:
                    if message.get("type") == "session_init":
                        private, public = new_keypair()
                        mode = message.get("mode")
                        extra = pairing.current().qr_secret if mode == "qr" else b""
                        session = SecureSession(private, unb64(message["public"]), extra)
                        if mode == "code": pairing.show_code(session.sas)
                        await websocket.send(json.dumps({"type": "session_offer", "public": public, "mode": mode}))
                        continue
                    if message.get("type") != "secure" or session is None:
                        await websocket.send(json.dumps({"type": "pair_result", "ok": False, "reason": "authentication_required"}))
                        continue
                    confirmation = session.decrypt(message)
                    if confirmation.get("type") != "confirm" or (confirmation.get("mode") == "code" and confirmation.get("code") != session.sas): raise ValueError("invalid confirmation")
                    authenticated = True
                    await websocket.send(json.dumps(session.encrypt({"type": "session_ready"})))
                    continue
                if session is not None:
                    if message.get("type") != "secure": raise ValueError("unencrypted command")
                    message = session.decrypt(message)
                await controller.execute(message)
            except windows.pyautogui.FailSafeException:
                motion.reset(); print("Protección de esquina activa: aparta el cursor con el ratón físico.")
            except (ValueError, KeyError, TypeError, json.JSONDecodeError) as error: print(f"Mensaje ignorado: {error}")
    except websockets.ConnectionClosed: pass
    finally:
        animation.cancel()
        await asyncio.gather(animation, return_exceptions=True)
        print("Móvil desconectado")
