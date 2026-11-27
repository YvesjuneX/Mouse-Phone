"""Capa de transporte WebSocket; no contiene reglas de entrada de Windows."""
import asyncio
import json
import socket
import time

import websockets
import pyautogui
from cryptography.exceptions import InvalidTag

from mouse_phone.application.controller import RemoteController
from mouse_phone.config.settings import (
    ANIMATION_INTERVAL_SECONDS, MAX_ACTIVE_SESSIONS, MAX_MESSAGES_PER_SECOND,
    PAIRING_TIMEOUT_SECONDS,
)
from mouse_phone.input.motion import Motion
from mouse_phone.input.windows import read_cursor, screen_bounds, write_cursor
from mouse_phone.security.session_crypto import SecureSession, new_keypair, unb64, b64
from mouse_phone.security.message_validation import MAX_MESSAGE_BYTES, MessageValidationError, validate_message
from mouse_phone.security.network_limits import MessageRateLimiter


async def animate(motion: Motion) -> None:
    previous = time.perf_counter()
    while True:
        await asyncio.sleep(ANIMATION_INTERVAL_SECONDS)
        now = time.perf_counter()
        motion.tick(now - previous)
        previous = now


async def handle_client(websocket, pairing=None, registry=None, sessions=None, limiter=None, connection_guard=None) -> None:
    source = str(websocket.remote_address[0]) if isinstance(websocket.remote_address, tuple) else "unknown"
    admitted = connection_guard.admit(source) if connection_guard else True
    if not admitted:
        print("Conexión rechazada por límite de red.")
        await websocket.close(code=4008, reason="connection limit reached")
        return

    motion = Motion(read_cursor, write_cursor, screen_bounds())
    controller = RemoteController(motion)
    animation = asyncio.create_task(animate(motion))
    print(f"Móvil conectado: {websocket.remote_address}")
    message_limiter = MessageRateLimiter(MAX_MESSAGES_PER_SECOND)
    authenticated, session, device_id, device_name, session_mode, active_session = pairing is None, None, None, None, None, None

    async def close_incomplete_pairing() -> None:
        await asyncio.sleep(PAIRING_TIMEOUT_SECONDS)
        if not authenticated:
            print("Emparejamiento incompleto cerrado por tiempo de espera.")
            await websocket.close(code=4009, reason="pairing timeout")

    pairing_timeout = asyncio.create_task(close_incomplete_pairing()) if pairing is not None else None

    async def reject_code_attempt(device_id: str) -> bool:
        result = limiter.record_failure(source, device_id) if limiter else None
        if result and result.delay_seconds: await asyncio.sleep(result.delay_seconds)
        locked = bool(result and result.locked)
        response = {"type": "pair_result", "ok": False, "reason": "pairing_locked" if locked else "invalid_code"}
        if result and not locked: response["attempts_remaining"] = result.remaining_attempts
        await websocket.send(json.dumps(response))
        if locked: await websocket.close(code=4008, reason="pairing temporarily locked")
        return locked

    try:
        await websocket.send(json.dumps({"type": "remote_mouse", "version": 6, "name": socket.gethostname(), "pairing_required": pairing is not None, "encrypted": True}))
        async for raw_message in websocket:
            try:
                if not message_limiter.allow():
                    print("Conexión cerrada por exceso de mensajes.")
                    await websocket.close(code=4008, reason="message rate limit")
                    break
                if not isinstance(raw_message, str) or len(raw_message.encode("utf-8")) > MAX_MESSAGE_BYTES: raise MessageValidationError("message too large")
                message = validate_message(json.loads(raw_message))
                if not authenticated:
                    if message.get("type") == "session_init":
                        private, public = new_keypair()
                        mode, device_id, device_name = message.get("mode"), message.get("device_id"), message.get("device_name")
                        if mode == "code" and limiter and limiter.is_locked(source, device_id):
                            await websocket.send(json.dumps({"type": "pair_result", "ok": False, "reason": "pairing_locked"}))
                            await websocket.close(code=4008, reason="pairing temporarily locked")
                            break
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
                    if session_mode == "code" and limiter and limiter.is_locked(source, device_id):
                        await websocket.send(json.dumps({"type": "pair_result", "ok": False, "reason": "pairing_locked"}))
                        await websocket.close(code=4008, reason="pairing temporarily locked")
                        break
                    try:
                        confirmation = validate_message(session.decrypt(message))
                    except (ValueError, InvalidTag):
                        if session_mode == "code":
                            if await reject_code_attempt(device_id): break
                            continue
                        raise
                    if confirmation.get("type") != "confirm" or (confirmation.get("mode") == "code" and not pairing.verify(confirmation.get("code"))):
                        if session_mode == "code":
                            if await reject_code_attempt(device_id): break
                            continue
                        raise ValueError("invalid confirmation")
                    authenticated = True
                    if pairing_timeout:
                        pairing_timeout.cancel()
                    if session_mode == "code" and limiter: limiter.reset(source, device_id)

                    async def end_active_session(reason: str) -> None:
                        # El aviso cifrado permite que el móvil actualice su interfaz antes
                        # de completar el cierre normal del WebSocket.
                        await websocket.send(json.dumps(session.encrypt({"type": "session_ended"})))
                        await websocket.close(code=4000, reason=reason)

                    if sessions:
                        active_session = sessions.register(
                            device_id,
                            device_name,
                            websocket,
                            asyncio.get_running_loop(),
                            end_active_session,
                            MAX_ACTIVE_SESSIONS,
                        )
                        if active_session is None:
                            print("Conexión rechazada por límite de sesiones activas.")
                            await websocket.close(code=4013, reason="active session limit reached")
                            break
                    token = registry.register_temporary(device_id, device_name) if registry and session_mode in {"qr", "code"} else None
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
            except pyautogui.FailSafeException:
                motion.reset(); print("Protección de esquina activa: aparta el cursor con el ratón físico.")
            except (MessageValidationError, ValueError, KeyError, TypeError, json.JSONDecodeError) as error: print(f"Mensaje ignorado: {error}")
    except websockets.ConnectionClosed:
        return
    finally:
        if sessions: sessions.unregister(active_session)
        if pairing_timeout:
            pairing_timeout.cancel()
            await asyncio.gather(pairing_timeout, return_exceptions=True)
        animation.cancel()
        await asyncio.gather(animation, return_exceptions=True)
        if connection_guard: connection_guard.release(source)
        print("Móvil desconectado")
