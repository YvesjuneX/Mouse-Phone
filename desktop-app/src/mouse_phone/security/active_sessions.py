"""Registro seguro de conexiones activas, independiente de las listas de acceso."""
import asyncio
import threading
import uuid


class ActiveSessions:
    def __init__(self, registry=None):
        self.registry = registry
        self._lock = threading.Lock()
        self._sessions = {}

    def register(self, device_id: str, name: str, websocket, loop) -> str:
        session_id = uuid.uuid4().hex
        with self._lock:
            self._sessions[session_id] = {"device_id": device_id, "name": name, "websocket": websocket, "loop": loop}
        return session_id

    def unregister(self, session_id: str | None) -> None:
        if session_id:
            with self._lock: self._sessions.pop(session_id, None)

    def list(self):
        with self._lock:
            return [(sid, {"device_id": item["device_id"], "name": item["name"]}) for sid, item in self._sessions.items()]

    def end(self, session_id: str) -> bool:
        with self._lock:
            item = self._sessions.pop(session_id, None)
        if not item: return False
        revoked = self.registry.revoke_temporary(item["device_id"]) if self.registry else False
        reason = "temporary access ended" if revoked else "ended by computer"
        item["loop"].call_soon_threadsafe(lambda: asyncio.create_task(item["websocket"].close(code=4000, reason=reason)))
        return True
