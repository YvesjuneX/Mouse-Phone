"""Registro persistente de dispositivos y sus políticas de acceso."""
import base64, json, os, secrets, threading, time
from pathlib import Path

from mouse_phone.security.file_permissions import restrict_to_current_user
from mouse_phone.security.windows_data_protection import protect, unprotect


class DeviceRegistry:
    def __init__(self, path: Path | None = None, clock=time.time):
        self.path = path or Path(os.environ.get("LOCALAPPDATA", Path.home())) / "MousePhone" / "devices.json"
        self.clock = clock
        self.lock = threading.Lock()
        self.data, needs_migration = self._load()
        if needs_migration: self._save()

    def _load(self):
        default = {"temporary_minutes": 30, "devices": {}}
        try:
            wrapper = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(wrapper, dict): return default, False
            if isinstance(wrapper.get("protected_data"), str):
                plaintext = unprotect(base64.b64decode(wrapper["protected_data"], validate=True))
                data = json.loads(plaintext.decode("utf-8"))
                return (data if isinstance(data, dict) and isinstance(data.get("devices"), dict) else default), False
            # Los datos heredados se migran al primer arranque sin conservar secretos legibles.
            return (wrapper if isinstance(wrapper.get("devices"), dict) else default), True
        except (OSError, ValueError, json.JSONDecodeError): return default, False
    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        restrict_to_current_user(self.path.parent)
        plaintext = json.dumps(self.data, separators=(",", ":")).encode("utf-8")
        wrapper = {"version": 2, "protected_data": base64.b64encode(protect(plaintext)).decode("ascii")}
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(wrapper, separators=(",", ":")), encoding="utf-8")
        restrict_to_current_user(temporary)
        os.replace(temporary, self.path)
        restrict_to_current_user(self.path)
    def temporary_minutes(self): return int(self.data.get("temporary_minutes", 30))
    def set_temporary_minutes(self, minutes: int):
        with self.lock:
            self.data["temporary_minutes"] = max(1, min(1440, minutes))
            # La configuración se aplica también a los accesos temporales ya activos.
            expires_at = self.clock() + self.data["temporary_minutes"] * 60
            for item in self.data["devices"].values():
                if item.get("state") == "temporary": item["expires_at"] = expires_at
            self._save()
    def authorize(self, device_id: str):
        with self.lock:
            item = self.data["devices"].get(device_id)
            if not item or item["state"] == "blocked": return None
            if item["state"] == "temporary" and item.get("expires_at", 0) <= self.clock(): return None
            return base64.b64decode(item["token"])
    def register_temporary(self, device_id: str, name: str):
        with self.lock:
            existing = self.data["devices"].get(device_id)
            if existing and existing["state"] == "blocked": return None
            token = base64.b64decode(existing["token"]) if existing else secrets.token_bytes(32)
            self.data["devices"][device_id] = {"name": name[:64] or "Móvil", "state": "temporary", "token": base64.b64encode(token).decode(), "expires_at": self.clock() + self.temporary_minutes() * 60}
            self._save(); return token
    def set_state(self, device_id: str, state: str):
        with self.lock:
            item = self.data["devices"].get(device_id)
            if item and state in {"trusted", "temporary", "blocked"}:
                item["state"] = state
                if state == "temporary": item["expires_at"] = self.clock() + self.temporary_minutes() * 60
                self._save()

    def revoke_temporary(self, device_id: str) -> bool:
        """Invalida la autorización actual, pero conserva el móvil en su lista temporal."""
        with self.lock:
            item = self.data["devices"].get(device_id)
            if not item or item.get("state") != "temporary": return False
            item["expires_at"] = 0
            self._save()
            return True
    def list_devices(self):
        with self.lock: return [(key, value.copy()) for key, value in self.data["devices"].items()]
