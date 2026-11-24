"""Capa de transporte WebSocket; no contiene reglas de entrada de Windows."""
import asyncio
import json
import socket
import time

import websockets
from cryptography.exceptions import InvalidTag

from mouse_phone.application.controller import RemoteController
from mouse_phone.config.settings import ANIMATION_INTERVAL_SECONDS
from mouse_phone.input.motion import Motion
from mouse_phone.input.windows import read_cursor, screen_bounds, write_cursor
from mouse_phone.input import windows
from mouse_phone.security.session_crypto import SecureSession, new_keypair, unb64, b64
from mouse_phone.security.message_validation import MAX_MESSAGE_BYTES, MessageValidationError, validate_message


async def animate(motion: Motion) -> None:
    previous = time.perf_counter()
    while True:
        await asyncio.sleep(ANIMATION_INTERVAL_SECONDS)
        now = time.perf_counter()
        motion.tick(now - previous)
        previous = now


async def handle_client(websocket, pairing=None, registry=None, sessions=None) -> None:
    motion = Motion(read_cursor, write_cursor, screen_bounds())
    controller = RemoteController(motion)
    animation = asyncio.create_task(animate(motion))
    print(f"Móvil conectado: {websocket.remote_address}")
    try:
        await websocket.send(json.dumps({"type": "remote_mouse", "version": 6, "name": socket.gethostname(), "pairing_required": pairing is not None, "encrypted": True}))
        authenticated, session, device_id, device_name, session_mode, active_session = pairing is None, None, None, None, None, None
        async for raw_message in websocket:
            try:
                if not isinstance(raw_message, str) or len(raw_message.encode("utf-8")) > MAX_MESSAGE_BYTES: raise MessageValidationError("message too large")
                message = validate_message(json.loads(raw_message))
                if not authenticated:
                    if message.get("type") == "session_init":
                        private, public = new_keypair()
                        mode, device_id, device_name = message.get("mode"), message.get("device_id"), message.get("device_name")
                        known = registry.authorize(device_id) if registry and mode == "known" else None
                        details = pairing.current()
                        extra = known or (details.qr_secret if mode == "qr" else details.code.encode() if mode == "code" else b"")
                        if mode == "known" and not known:
                            await websocket.send(json.dumps({"type": "pair_result", "ok": False, "reason": "authorization_required"})); continue
                        session = SecureSession(private, unb64(message["public"]), extra)
                        session_mode = mode
                        await websocket.send(json.dumps({"type": "session_offer", "public": public, "mode": mode}))
                        continue
                    if message.get("type") != "secure" or session is None:
                        await websocket.send(json.dumps({"type": "pair_result", "ok": False, "reason": "authentication_required"}))
                        continue
                    try:
                        confirmation = validate_message(session.decrypt(message))
                    except (ValueError, InvalidTag):
                        if session_mode == "code":
                            await websocket.send(json.dumps({"type": "pair_result", "ok": False, "reason": "invalid_code"}))
                            continue
                        raise
                    if confirmation.get("type") != "confirm" or (confirmation.get("mode") == "code" and not pairing.verify(confirmation.get("code"))):
                        if session_mode == "code":
                            await websocket.send(json.dumps({"type": "pair_result", "ok": False, "reason": "invalid_code"}))
                            continue
                        raise ValueError("invalid confirmation")
                    authenticated = True
                    token = registry.register_temporary(device_id, device_name) if registry and session_mode in {"qr", "code"} else None
                    if sessions: active_session = sessions.register(device_id, device_name, websocket, asyncio.get_running_loop())
                    await websocket.send(json.dumps(session.encrypt({"type": "session_ready", "credential": b64(token) if token else None})))
                    continue
                if session is not None:
                    if message.get("type") != "secure": raise ValueError("unencrypted command")
                    try:
                        message = validate_message(session.decrypt(message))
                    except (ValueError, InvalidTag):
                        await websocket.close(code=4002, reason="invalid secure message")
                        break
                if registry and device_id and registry.authorize(device_id) is None:
                    await websocket.close(code=4003, reason="authorization revoked")
                    break
                await controller.execute(message)
            except windows.pyautogui.FailSafeException:
                motion.reset(); print("Protección de esquina activa: aparta el cursor con el ratón físico.")
            except (MessageValidationError, ValueError, KeyError, TypeError, json.JSONDecodeError) as error: print(f"Mensaje ignorado: {error}")
    except websockets.ConnectionClosed: pass
    finally:
        if sessions: sessions.unregister(active_session)
        animation.cancel()
        await asyncio.gather(animation, return_exceptions=True)
        print("Móvil desconectado")
