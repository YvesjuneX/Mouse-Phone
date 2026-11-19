"""Códigos temporales de emparejamiento para la red local.

El canal aún no está cifrado: este módulo confirma que el usuario puede ver el
ordenador antes de aceptar comandos. TLS se añadirá como una capa posterior.
"""
from dataclasses import dataclass
import secrets
import threading
import time


@dataclass(frozen=True)
class PairingDetails:
    code: str
    expires_at: float


class PairingManager:
    def __init__(self, lifetime_seconds: int = 300, clock=time.time):
        self.lifetime_seconds = lifetime_seconds
        self.clock = clock
        self._details: PairingDetails | None = None
        self._lock = threading.Lock()

    def current(self) -> PairingDetails:
        with self._lock:
            now = self.clock()
            if self._details is None or now >= self._details.expires_at:
                self._details = PairingDetails(f"{secrets.randbelow(1_000_000):06d}", now + self.lifetime_seconds)
            return self._details

    def verify(self, code: object) -> bool:
        details = self.current()
        return isinstance(code, str) and secrets.compare_digest(code, details.code)

    def renew(self) -> PairingDetails:
        with self._lock:
            self._details = None
        return self.current()
